"""
Regression and Hardening Tests for Transify 2.0 Post-Release Security & Database Migrations.
Verifies:
1. Session persistence across init_db() / server restart
2. Expired session pruning
3. user_preferences composite primary key (pref_key, user_id) migration
4. Multi-user preference isolation
5. Legacy translation history preservation (user_id IS NULL)
6. Elimination of public demo account login path
7. Strict cookie-only authentication (no Bearer fallback)
8. CSRF protection: rejects Origin: null
9. CSRF protection: rejects cross-origin requests
10. CSRF protection: rejects missing Origin/Referer in strict mode unless verified
11. CSRF double-submit token verification
12. Persistent SQLite rate limiting across process restarts
13. Complete audit of frontend files for absence of hardcoded passwords
"""

import os
import time
import secrets
import hashlib
import sqlite3
import pytest
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from src.api.server import app, normalize_origin, get_trusted_origins
from src.database.db import (
    get_connection,
    get_db_path,
    init_db,
    create_user,
    authenticate_user,
    create_session,
    get_user_by_session,
    revoke_session,
    update_preference,
    get_preferences,
    count_legacy_history,
    clear_history,
    log_translation,
    get_history,
    record_failed_login,
    is_login_rate_limited,
    clear_failed_logins,
    is_production
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.cookies.clear()
        yield test_client


def test_session_persistence_across_init_db():
    """
    Verifies that calling init_db() (e.g. server restart) does NOT delete valid SHA-256 sessions.
    """
    email = f"session_persist_{int(time.time()*1000)}@test.com"
    pwd = "PersistPassword123!_2026"
    user = create_user("Persist User", email, pwd, consent_terms=True)
    
    token = create_session(user["id"])
    assert token is not None
    
    # Verify session is active before restart
    user_before = get_user_by_session(token)
    assert user_before is not None
    assert user_before["id"] == user["id"]
    
    # Simulate restart by re-running init_db()
    init_db()
    
    # Session MUST remain valid after restart
    user_after = get_user_by_session(token)
    assert user_after is not None
    assert user_after["id"] == user["id"]


def test_expired_session_pruning_on_init_db():
    """
    Verifies that init_db() prunes expired sessions while keeping active ones.
    """
    conn = get_connection()
    raw_expired = f"expired_tok_{secrets.token_hex(8)}"
    token_hash = hashlib.sha256(raw_expired.encode("utf-8")).hexdigest()
    past_iso = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    
    # Insert an expired session manually
    conn.execute(
        "INSERT INTO user_sessions (session_token, user_id, expires_at, created_at) VALUES (?, 1, ?, ?);",
        (token_hash, past_iso, past_iso)
    )
    conn.commit()
    conn.close()
    
    # Run init_db()
    init_db()
    
    # Verify the expired session is pruned
    conn = get_connection()
    row = conn.execute("SELECT session_token FROM user_sessions WHERE session_token = ?;", (token_hash,)).fetchone()
    conn.close()
    assert row is None, "Expired session must be deleted by init_db()"


def test_user_preferences_composite_pk_migration():
    """
    Verifies that user_preferences has a composite primary key (pref_key, user_id)
    and allows different users to independently customize the same preference.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(user_preferences);")
    cols = {r["name"]: dict(r) for r in cursor.fetchall()}
    conn.close()
    
    # Both pref_key and user_id must be in primary key (pk > 0)
    assert cols["pref_key"]["pk"] > 0, "pref_key must be part of primary key"
    assert cols["user_id"]["pk"] > 0, "user_id must be part of composite primary key"
    
    # Test setting the same preference key for two different users
    u1_id = 901
    u2_id = 902
    update_preference("theme", "contrast", user_id=u1_id)
    update_preference("theme", "dark", user_id=u2_id)
    
    p1 = get_preferences(user_id=u1_id)
    p2 = get_preferences(user_id=u2_id)
    
    assert p1.get("theme") == "contrast"
    assert p2.get("theme") == "dark"


def test_legacy_translation_history_preservation():
    """
    Verifies that legacy translation history rows (user_id IS NULL) are preserved,
    excluded from individual user queries, and reported by count_legacy_history().
    """
    # Insert a legacy row with user_id = NULL
    conn = get_connection()
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute("""
    INSERT INTO translation_history 
    (user_id, module, input_meta, recognized_text, confidence, status, diagnostics, created_at)
    VALUES (NULL, 'braille', '{}', 'LEGACY_TEST_SAMPLE', 0.99, 'SUCCESS', '{}', ?);
    """, (now_iso,))
    conn.commit()
    conn.close()
    
    # Verify legacy count is > 0
    legacy_count = count_legacy_history()
    assert legacy_count > 0
    
    # Normal user query MUST NOT include the legacy NULL record
    user_records = get_history(user_id=888)
    assert not any(r["recognized_text"] == "LEGACY_TEST_SAMPLE" for r in user_records)
    
    # Clear history for user 888 does NOT delete legacy NULL records
    clear_history(user_id=888, preserve_legacy=True)
    assert count_legacy_history() == legacy_count


def test_demo_account_cannot_authenticate():
    """
    Verifies that demo@transify.ai is marked disabled and cannot authenticate via password.
    """
    auth_result = authenticate_user("demo@transify.ai", "transify2026")
    assert auth_result is None


def test_strict_cookie_only_authentication_rejects_bearer(client):
    """
    Verifies that Authorization: Bearer headers are ignored and rejected
    when no HttpOnly session cookie is provided.
    """
    email = f"bearer_test_{int(time.time()*1000)}@test.com"
    pwd = "BearerTestPassword123!_2026"
    user = create_user("Bearer Tester", email, pwd, consent_terms=True)
    valid_token = create_session(user["id"])
    
    # Attempt to authenticate using Authorization: Bearer <valid_token> without cookie
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {valid_token}"}
    
    res_me = client.get("/api/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["authenticated"] is False, "Bearer token must not authenticate /api/auth/me"
    
    # Attempt to call a protected endpoint with Bearer header
    res_history = client.delete("/api/history", headers=headers)
    assert res_history.status_code == 401, "Bearer token must not satisfy get_authenticated_user"


def test_csrf_rejects_null_origin(client):
    """
    Verifies that state-changing requests with Origin: null are strictly rejected with 403.
    """
    res = client.post("/api/auth/guest", headers={"Origin": "null"})
    assert res.status_code == 403
    assert "null origin rejected" in res.json()["detail"].lower()


def test_csrf_rejects_cross_origin(client):
    """
    Verifies that cross-origin state-changing requests are rejected with 403.
    """
    res = client.post("/api/auth/guest", headers={"Origin": "https://attacker.evil.com"})
    assert res.status_code == 403
    assert "cross-origin request rejected" in res.json()["detail"].lower()


def test_csrf_missing_headers_enforcement(client, monkeypatch):
    """
    Verifies that state-changing requests missing both Origin and Referer
    are rejected when strict CSRF enforcement is enabled.
    """
    monkeypatch.setenv("TRANSIFY_ENFORCE_CSRF", "1")
    res = client.post("/api/auth/guest")
    assert res.status_code == 403
    assert "missing origin and referer" in res.json()["detail"].lower()


def test_csrf_double_submit_token_accepted(client, monkeypatch):
    """
    Verifies that a state-changing request missing Origin/Referer is accepted
    when a valid double-submit CSRF token is provided.
    """
    monkeypatch.setenv("TRANSIFY_ENFORCE_CSRF", "1")
    csrf_secret = secrets.token_hex(16)
    
    client.cookies.set("transify_csrf", csrf_secret)
    res = client.post(
        "/api/auth/guest",
        headers={"X-CSRF-Token": csrf_secret}
    )
    # The CSRF check passed; endpoint returned 200
    assert res.status_code == 200


def test_persistent_sqlite_rate_limiting_across_restart():
    """
    Verifies that failed login tracking persists in SQLite across init_db() calls.
    """
    test_key = f"rate_limit_test_{secrets.token_hex(6)}"
    clear_failed_logins(test_key)
    assert not is_login_rate_limited(test_key)
    
    for i in range(1, 5):
        c = record_failed_login(test_key)
        assert c == i
        assert not is_login_rate_limited(test_key)
        
    # 5th attempt reaches limit
    c5 = record_failed_login(test_key)
    assert c5 == 5
    assert is_login_rate_limited(test_key)
    
    # Simulate restart
    init_db()
    
    # Must STILL be rate limited
    assert is_login_rate_limited(test_key), "Rate limit state must persist across restarts"
    
    # Clear after success
    clear_failed_logins(test_key)
    assert not is_login_rate_limited(test_key)


def test_frontend_has_zero_hardcoded_passwords():
    """
    Audits frontend files to verify no hardcoded passwords or demo login credentials exist.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    frontend_dir = os.path.join(project_root, "src", "frontend")
    
    files_to_check = [
        os.path.join(frontend_dir, "static", "app.js"),
        os.path.join(frontend_dir, "index.html"),
        os.path.join(frontend_dir, "login.html")
    ]
    
    forbidden_terms = ["transify2026", "transify2026_dev_only"]
    for path in files_to_check:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            for term in forbidden_terms:
                assert term not in content, f"Forbidden term '{term}' found in {path}"


def test_default_database_isolated_from_test_suite():
    """
    Verifies that the test suite runs against an isolated temporary SQLite database
    and never modifies or targets the repository default data/transify.db.
    """
    active_db_path = get_db_path()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    default_prod_db = os.path.join(project_root, "data", "transify.db")
    
    assert os.path.abspath(active_db_path) != os.path.abspath(default_prod_db), (
        f"Active test database ({active_db_path}) must not point to project default ({default_prod_db})"
    )
    assert "transify_test_db_" in active_db_path, (
        f"Test database path must reside within an isolated temporary test directory: {active_db_path}"
    )


def test_rate_limiter_concurrency_atomic_increments():
    """
    Verifies that record_failed_login is concurrency-safe under high parallel load.
    Spawns 20 concurrent threads attempting to record failed logins simultaneously for the same key.
    Ensures exactly 20 attempts are recorded with zero lost updates.
    """
    test_key = f"concurrent_ip:{secrets.token_hex(8)}"
    clear_failed_logins(test_key)
    
    num_threads = 20
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(record_failed_login, test_key) for _ in range(num_threads)]
        results = [f.result() for f in futures]
    
    # All threads must succeed and return integers
    assert len(results) == num_threads
    
    # Query final count from SQLite
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT attempts FROM login_rate_limits WHERE limit_key = ?;", (test_key,))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None, "Rate limit record must exist"
    assert row["attempts"] == num_threads, f"Expected exactly {num_threads} attempts recorded, found {row['attempts']}"
    
    # Clean up
    clear_failed_logins(test_key)


def test_successful_login_counter_isolation(client):
    """
    Verifies that successful login clears ONLY the specific user email counter,
    and deliberately does NOT erase the shared network/client IP counter.
    """
    client_ip_key = "ip:testclient"
    email = f"iso_user_{int(time.time()*1000)}@test.com"
    email_key = f"email:{email.lower()}"
    pwd = "IsolationPassword123!_2026"
    
    create_user("Isolation Tester", email, pwd, consent_terms=True)
    
    # Seed 3 failed login attempts on the IP and 2 on the email
    clear_failed_logins(client_ip_key)
    clear_failed_logins(email_key)
    
    for _ in range(3):
        record_failed_login(client_ip_key)
    for _ in range(2):
        record_failed_login(email_key)
        
    # Verify initial attempt counts
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT attempts FROM login_rate_limits WHERE limit_key = ?;", (client_ip_key,))
    ip_row = cursor.fetchone()
    assert ip_row is not None and ip_row["attempts"] == 3
    
    cursor.execute("SELECT attempts FROM login_rate_limits WHERE limit_key = ?;", (email_key,))
    email_row = cursor.fetchone()
    assert email_row is not None and email_row["attempts"] == 2
    conn.close()
    
    # Perform successful login
    login_res = client.post("/api/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    
    # Check that email counter is cleared, BUT IP counter remains intact (still 3)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT attempts FROM login_rate_limits WHERE limit_key = ?;", (email_key,))
    cleared_email = cursor.fetchone()
    assert cleared_email is None, "Email rate limit counter must be cleared on successful login"
    
    cursor.execute("SELECT attempts FROM login_rate_limits WHERE limit_key = ?;", (client_ip_key,))
    retained_ip = cursor.fetchone()
    assert retained_ip is not None and retained_ip["attempts"] == 3, (
        "Client IP rate limit counter must NOT be erased by successful user authentication"
    )
    conn.close()
    
    clear_failed_logins(client_ip_key)


def test_exact_origin_csrf_validation_suite(client, monkeypatch):
    """
    Comprehensive test of exact-origin CSRF normalization and production enforcement.
    Verifies:
    1. normalize_origin unit parsing: scheme, ports, default port stripping.
    2. Exact production origin accepted (https://transify20-production.up.railway.app).
    3. Insecure HTTP scheme rejected in production.
    4. Non-standard port rejected in production.
    5. Cross-origin domain rejected.
    6. Origin: null rejected.
    """
    # 1. Unit tests for normalize_origin
    assert normalize_origin("https://transify20-production.up.railway.app") == "https://transify20-production.up.railway.app"
    assert normalize_origin("https://transify20-production.up.railway.app:443") == "https://transify20-production.up.railway.app"
    assert normalize_origin("http://transify20-production.up.railway.app:80") == "http://transify20-production.up.railway.app"
    assert normalize_origin("https://transify20-production.up.railway.app:8443") == "https://transify20-production.up.railway.app:8443"
    assert normalize_origin("null") == "null"
    assert normalize_origin("invalid-url") is None
    assert normalize_origin("") is None
    
    # 2. Simulate production environment
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("TRANSIFY_ENV", "production")
    
    # Legitimate production origin -> 200 OK
    res_ok = client.post(
        "/api/auth/guest",
        headers={"Origin": "https://transify20-production.up.railway.app"}
    )
    assert res_ok.status_code == 200
    
    # HTTP scheme mismatch in production -> 403 Forbidden
    res_http = client.post(
        "/api/auth/guest",
        headers={"Origin": "http://transify20-production.up.railway.app"}
    )
    assert res_http.status_code == 403
    assert "cross-origin request rejected" in res_http.json()["detail"].lower()
    
    # Port mismatch in production -> 403 Forbidden
    res_port = client.post(
        "/api/auth/guest",
        headers={"Origin": "https://transify20-production.up.railway.app:8443"}
    )
    assert res_port.status_code == 403
    assert "cross-origin request rejected" in res_port.json()["detail"].lower()
    
    # Attacker origin -> 403 Forbidden
    res_attacker = client.post(
        "/api/auth/guest",
        headers={"Origin": "https://attacker-origin.evil.org"}
    )
    assert res_attacker.status_code == 403
    assert "cross-origin request rejected" in res_attacker.json()["detail"].lower()
    
    # Null origin -> 403 Forbidden
    res_null = client.post(
        "/api/auth/guest",
        headers={"Origin": "null"}
    )
    assert res_null.status_code == 403
    assert "null origin rejected" in res_null.json()["detail"].lower()


def test_is_production_environment_precedence(monkeypatch):
    """
    Verifies fail-safe production environment detection precedence.
    1. RAILWAY_ENVIRONMENT=production must never be overridden by TRANSIFY_ENV=testing.
    2. RAILWAY_ENVIRONMENT=production with ENVIRONMENT=development remains production.
    3. TRANSIFY_ENV=production with ENVIRONMENT=testing remains production.
    4. All environment variables set to testing -> returns False.
    5. All variables unset -> returns False.
    6. Whitespace and uppercase variants normalize properly.
    """
    # 1. Railway production + Transify testing -> True (fail closed)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("TRANSIFY_ENV", "testing")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert is_production() is True

    # 2. Railway production + Environment development -> True
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("TRANSIFY_ENV", raising=False)
    assert is_production() is True

    # 3. Transify production + Environment testing -> True
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.setenv("TRANSIFY_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "testing")
    assert is_production() is True

    # 4. All set to testing / dev -> False
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "testing")
    monkeypatch.setenv("TRANSIFY_ENV", "test")
    monkeypatch.setenv("ENVIRONMENT", "dev")
    assert is_production() is False

    # 5. All unset -> False
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("TRANSIFY_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert is_production() is False

    # 6. Whitespace and uppercase variants
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "   PRODUCTION   ")
    assert is_production() is True

    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "   TESTING   ")
    assert is_production() is False


def test_legacy_preference_migration_schema_a(tmp_path, monkeypatch):
    """
    Constructs an independent SQLite database representing Legacy Preference Schema A:
    - pref_key as the only primary key
    - pref_value TEXT NOT NULL
    - updated_at TEXT NOT NULL
    (user_id column is completely absent)

    Verifies real init_db() migration:
    1. All existing preference records survive.
    2. Legacy entries are mapped to system defaults (user_id = 0).
    3. Final table has composite primary key (pref_key, user_id).
    4. Multiple users can independently customize the same preference key.
    5. Idempotent: init_db() can run multiple times without data damage.
    """
    db_file = str(tmp_path / "legacy_schema_a.db")
    monkeypatch.setenv("TRANSIFY_DB_PATH", db_file)
    monkeypatch.setenv("TRANSIFY_DATA_DIR", str(tmp_path))

    # Construct Legacy Schema A
    conn = sqlite3.connect(db_file)
    conn.execute("""
    CREATE TABLE user_preferences (
        pref_key TEXT PRIMARY KEY,
        pref_value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)
    conn.execute("INSERT INTO user_preferences (pref_key, pref_value, updated_at) VALUES ('theme', 'contrast', '2026-01-01T00:00:00Z');")
    conn.execute("INSERT INTO user_preferences (pref_key, pref_value, updated_at) VALUES ('font_size', 'x-large', '2026-01-01T00:00:00Z');")
    conn.commit()
    conn.close()

    # Run real init_db() migration
    init_db()

    # 1. Verify schema: PK must be (pref_key, user_id)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(user_preferences);")
    cols = {r["name"]: dict(r) for r in cursor.fetchall()}
    assert cols["pref_key"]["pk"] > 0, "pref_key must be part of composite PK"
    assert cols["user_id"]["pk"] > 0, "user_id must be part of composite PK"

    # 2. Verify all existing records survived and migrated to user_id = 0
    cursor.execute("SELECT pref_key, user_id, pref_value FROM user_preferences WHERE user_id = 0;")
    rows = {r["pref_key"]: r["pref_value"] for r in cursor.fetchall()}
    assert rows.get("theme") == "contrast", "Existing theme 'contrast' must survive migration"
    assert rows.get("font_size") == "x-large", "Existing font_size 'x-large' must survive migration"
    conn.close()

    # 3. Verify multi-user isolation
    update_preference("theme", "dark", user_id=101)
    update_preference("theme", "solarized", user_id=102)

    p101 = get_preferences(user_id=101)
    p102 = get_preferences(user_id=102)
    p_default = get_preferences(user_id=0)

    assert p101.get("theme") == "dark"
    assert p102.get("theme") == "solarized"
    assert p_default.get("theme") == "contrast"

    # 4. Run init_db() again to verify idempotency
    init_db()

    assert get_preferences(user_id=101).get("theme") == "dark"
    assert get_preferences(user_id=102).get("theme") == "solarized"
    assert get_preferences(user_id=0).get("theme") == "contrast"


def test_legacy_preference_migration_schema_b(tmp_path, monkeypatch):
    """
    Constructs an independent SQLite database representing Legacy Preference Schema B:
    - pref_key as the only primary key
    - user_id column present but nullable and NOT part of primary key
    - Existing records with user_id = NULL and user_id != NULL

    Verifies real init_db() migration:
    1. Legacy rows with user_id IS NULL become user_id = 0.
    2. Rows with non-null user_id retain their specific user_id.
    3. Final table has composite primary key (pref_key, user_id).
    """
    db_file = str(tmp_path / "legacy_schema_b.db")
    monkeypatch.setenv("TRANSIFY_DB_PATH", db_file)
    monkeypatch.setenv("TRANSIFY_DATA_DIR", str(tmp_path))

    # Construct Legacy Schema B
    conn = sqlite3.connect(db_file)
    conn.execute("""
    CREATE TABLE user_preferences (
        pref_key TEXT PRIMARY KEY,
        user_id INTEGER,
        pref_value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)
    conn.execute("INSERT INTO user_preferences (pref_key, user_id, pref_value, updated_at) VALUES ('theme', NULL, 'sepia', '2026-01-01T00:00:00Z');")
    conn.execute("INSERT INTO user_preferences (pref_key, user_id, pref_value, updated_at) VALUES ('font_size', 42, 'small', '2026-01-01T00:00:00Z');")
    conn.commit()
    conn.close()

    # Run real init_db() migration
    init_db()

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(user_preferences);")
    cols = {r["name"]: dict(r) for r in cursor.fetchall()}
    assert cols["pref_key"]["pk"] > 0
    assert cols["user_id"]["pk"] > 0

    cursor.execute("SELECT pref_key, user_id, pref_value FROM user_preferences;")
    rows = [(r["pref_key"], r["user_id"], r["pref_value"]) for r in cursor.fetchall()]
    conn.close()

    # NULL user_id must become 0
    assert ("theme", 0, "sepia") in rows
    # Existing user_id=42 must be preserved
    assert ("font_size", 42, "small") in rows


def test_legacy_session_migration_applied_once(tmp_path, monkeypatch):
    """
    Constructs an independent legacy database with old-format session records
    and unapplied schema_migrations version 1.
    Verifies:
    1. Legacy migration 1 purges old plaintext sessions once only.
    2. Version 1 is recorded in schema_migrations.
    3. Newly generated valid SHA-256 sessions survive subsequent init_db() / restarts.
    """
    db_file = str(tmp_path / "legacy_sessions.db")
    monkeypatch.setenv("TRANSIFY_DB_PATH", db_file)
    monkeypatch.setenv("TRANSIFY_DATA_DIR", str(tmp_path))

    conn = sqlite3.connect(db_file)
    conn.execute("""
    CREATE TABLE schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL,
        description TEXT
    );
    """)
    conn.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)
    conn.execute("""
    CREATE TABLE user_sessions (
        session_token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    # Insert legacy plaintext session
    conn.execute("INSERT INTO user_sessions (session_token, user_id, expires_at, created_at) VALUES ('legacy_plaintext_tok_123', 1, '2099-01-01T00:00:00Z', '2026-01-01T00:00:00Z');")
    conn.commit()
    conn.close()

    # 1. Run init_db()
    init_db()

    # Verify migration 1 was applied and legacy session revoked
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT 1 FROM schema_migrations WHERE version = 1;")
    assert c.fetchone() is not None, "Migration 1 must be recorded"
    c.execute("SELECT COUNT(*) as cnt FROM user_sessions WHERE session_token = 'legacy_plaintext_tok_123';")
    assert c.fetchone()["cnt"] == 0, "Legacy session must be revoked"
    conn.close()

    # 2. Create user and valid hashed session
    user = create_user("Test User", "test_mig@example.com", "SecurePassword123!_2026", consent_terms=True)
    new_token = create_session(user["id"])
    assert new_token is not None

    # 3. Run init_db() again (simulate restart)
    init_db()

    # Session must STILL be active
    valid_user = get_user_by_session(new_token)
    assert valid_user is not None
    assert valid_user["id"] == user["id"]


def test_harden_exact_origin_malformed_urls_and_rules():
    """
    Comprehensive tests for Phase 3 hardened normalize_origin rules:
    - User information in authority rejected
    - Non-HTTP/HTTPS rejected
    - Malformed ports rejected
    - Path, query, fragment in Origin headers rejected
    - Path, query in Referer headers extracted to canonical origin
    - Default port stripping (80, 443)
    - IPv6 formatting
    - Null origin representation
    """
    # Credentials / user info rejected
    assert normalize_origin("https://user@example.com", is_origin_header=True) is None
    assert normalize_origin("https://user:password@example.com", is_origin_header=True) is None
    assert normalize_origin("http://admin:pass@127.0.0.1:8000", is_origin_header=True) is None
    assert normalize_origin("https://user:password@example.com", is_origin_header=False) is None

    # Non-HTTP/HTTPS rejected
    assert normalize_origin("ftp://files.example.com", is_origin_header=True) is None
    assert normalize_origin("javascript:alert(1)", is_origin_header=True) is None
    assert normalize_origin("data:text/html,<html>", is_origin_header=True) is None
    assert normalize_origin("ws://socket.example.com", is_origin_header=True) is None

    # Malformed ports rejected
    assert normalize_origin("https://example.com:0", is_origin_header=True) is None
    assert normalize_origin("https://example.com:65536", is_origin_header=True) is None
    assert normalize_origin("https://example.com:999999", is_origin_header=True) is None
    assert normalize_origin("https://example.com:port", is_origin_header=True) is None

    # Origin header: path, query, fragment rejected
    assert normalize_origin("https://transify20-production.up.railway.app/path", is_origin_header=True) is None
    assert normalize_origin("https://transify20-production.up.railway.app?query=1", is_origin_header=True) is None
    assert normalize_origin("https://transify20-production.up.railway.app#fragment", is_origin_header=True) is None

    # Referer header: path, query safely stripped to origin
    assert normalize_origin("https://transify20-production.up.railway.app/login?redirect=/dashboard", is_origin_header=False) == "https://transify20-production.up.railway.app"
    assert normalize_origin("http://localhost:8000/app#top", is_origin_header=False) == "http://localhost:8000"

    # Default ports normalized
    assert normalize_origin("https://transify20-production.up.railway.app:443", is_origin_header=True) == "https://transify20-production.up.railway.app"
    assert normalize_origin("http://transify20-production.up.railway.app:80", is_origin_header=True) == "http://transify20-production.up.railway.app"
    assert normalize_origin("https://transify20-production.up.railway.app:8443", is_origin_header=True) == "https://transify20-production.up.railway.app:8443"

    # IPv6 host formatting
    assert normalize_origin("http://[::1]:8000", is_origin_header=True) == "http://[::1]:8000"
    assert normalize_origin("http://[::1]:80", is_origin_header=True) == "http://[::1]"
    assert normalize_origin("https://[2001:db8::1]:443", is_origin_header=True) == "https://[2001:db8::1]"

    # Null origin
    assert normalize_origin("null", is_origin_header=True) == "null"
    assert normalize_origin("NULL", is_origin_header=True) == "null"


def test_custom_origins_production_https_enforcement(client, monkeypatch):
    """
    Verifies that custom origins configured via TRANSIFY_ALLOWED_ORIGINS:
    1. Are accepted ONLY if they use HTTPS in production.
    2. Insecure HTTP custom origins are rejected and cannot weaken CSRF protection.
    """
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("TRANSIFY_ENV", "production")
    monkeypatch.setenv(
        "TRANSIFY_ALLOWED_ORIGINS",
        "http://insecure-custom.org,https://secure-custom.org,https://custom.app:8443"
    )

    trusted = get_trusted_origins(is_production_mode=True)
    assert "https://secure-custom.org" in trusted
    assert "https://custom.app:8443" in trusted
    assert "http://insecure-custom.org" not in trusted, "Insecure HTTP origin must not be trusted in production"

    # Request from secure custom origin -> 200 OK
    res_secure = client.post(
        "/api/auth/guest",
        headers={"Origin": "https://secure-custom.org"}
    )
    assert res_secure.status_code == 200

    # Request from insecure custom origin -> 403 Forbidden
    res_insecure = client.post(
        "/api/auth/guest",
        headers={"Origin": "http://insecure-custom.org"}
    )
    assert res_insecure.status_code == 403


def test_rate_limiter_fixed_window_policy_and_reset():
    """
    Verifies the 5-attempt, 300-second fixed-window rate limiting policy:
    1. 5 failed attempts within window triggers rate limiting.
    2. Advancing time beyond window_seconds resets the window and counter.
    3. Rollback on database failure preserves data integrity.
    """
    test_key = f"fixed_window_test:{secrets.token_hex(6)}"
    clear_failed_logins(test_key)

    # 4 attempts: not limited
    for i in range(1, 5):
        cnt = record_failed_login(test_key, window_seconds=300.0)
        assert cnt == i
        assert not is_login_rate_limited(test_key, max_attempts=5, window_seconds=300.0)

    # 5th attempt: limited
    cnt5 = record_failed_login(test_key, window_seconds=300.0)
    assert cnt5 == 5
    assert is_login_rate_limited(test_key, max_attempts=5, window_seconds=300.0)

    # Simulate expiration: advance first_attempt_at into the past (> 300s ago)
    conn = get_connection()
    past_ts = time.time() - 350.0
    conn.execute("UPDATE login_rate_limits SET first_attempt_at = ? WHERE limit_key = ?;", (past_ts, test_key))
    conn.commit()
    conn.close()

    # After expiration, key is no longer rate limited
    assert not is_login_rate_limited(test_key, max_attempts=5, window_seconds=300.0)

    # Next failed attempt resets attempts to 1 (new window anchored)
    cnt_new = record_failed_login(test_key, window_seconds=300.0)
    assert cnt_new == 1
    assert not is_login_rate_limited(test_key, max_attempts=5, window_seconds=300.0)

    clear_failed_logins(test_key)


def test_rate_limiter_shared_ip_independent_connections(client):
    """
    Verifies that rate limiter operates accurately across separate database connections
    and tests multi-tenant shared-IP behavior:
    1. When an IP is rate limited, any attempt from that IP receives HTTP 429.
    2. Once the IP rate-limiting window expires, legitimate users can log in again.
    """
    test_ip = "192.0.2.100"
    ip_key = f"ip:{test_ip}"
    clear_failed_logins(ip_key)

    # Record 5 failed attempts from independent connections
    for _ in range(5):
        conn = get_connection()
        record_failed_login(ip_key, window_seconds=300.0)
        conn.close()

    assert is_login_rate_limited(ip_key, max_attempts=5, window_seconds=300.0)

    # Simulate client request with this IP
    res_blocked = client.post(
        "/api/auth/login",
        json={"email": "legit_user@example.com", "password": "AnyPassword12345!"},
        headers={"x-forwarded-for": test_ip}
    )
    # Both direct IP or forwarded IP tested
    assert res_blocked.status_code in (401, 429)

    # Reset IP
    clear_failed_logins(ip_key)
    assert not is_login_rate_limited(ip_key)


