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
from fastapi.testclient import TestClient

from src.api.server import app
from src.database.db import (
    get_connection,
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
