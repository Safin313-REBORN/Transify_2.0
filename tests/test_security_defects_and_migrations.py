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
    user = create_user("Persist User", email, pwd)
    
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
    user = create_user("Bearer Tester", email, pwd)
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
    
    create_user("Isolation Tester", email, pwd)
    
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

