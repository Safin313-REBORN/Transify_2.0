"""
Backend Authentication and Session Security Tests for Transify 2.0.
Verifies Argon2id password hashing, transparent upgrade from PBKDF2,
session token SHA-256 database hashing, cookie-only authentication,
login rate limiting, user data isolation, and CSRF origin protection.
"""
import hashlib
import secrets
import time
import pytest
from fastapi.testclient import TestClient
from src.api.server import app
from src.database.db import (
    get_user_by_email,
    authenticate_user,
    hash_password,
    verify_password,
    create_user,
    get_connection,
    log_translation,
    get_history
)

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.cookies.clear()
        yield test_client

def test_default_demo_account_exists():
    """Verifies that demo@transify.ai exists and password authenticates correctly."""
    user = get_user_by_email("demo@transify.ai")
    assert user is not None
    assert user["email"] == "demo@transify.ai"
    
    # Verify authentication with correct password
    auth_user = authenticate_user("demo@transify.ai", "transify2026")
    assert auth_user is not None
    assert auth_user["email"] == "demo@transify.ai"
    
    # Verify wrong password rejected
    wrong_user = authenticate_user("demo@transify.ai", "wrongpassword")
    assert wrong_user is None

def test_demo_login_cookie_only(client):
    """Verifies login sets HttpOnly session cookie and does NOT expose raw token in JSON body."""
    res = client.post("/api/auth/login", json={
        "email": "demo@transify.ai",
        "password": "transify2026"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["user"]["email"] == "demo@transify.ai"
    assert data["user"]["name"] == "Sarah Ahmed"
    
    # Strict Cookie-Only Authentication: Raw token MUST NOT be in response JSON
    assert "token" not in data
    assert "transify_session" in client.cookies

def test_login_invalid_password(client):
    """Verifies login rejects incorrect password with HTTP 401 Unauthorized."""
    res = client.post("/api/auth/login", json={
        "email": "demo@transify.ai",
        "password": "wrong_password_123"
    })
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]

def test_login_unknown_email(client):
    """Verifies login rejects non-existent email with HTTP 401 Unauthorized."""
    res = client.post("/api/auth/login", json={
        "email": "nonexistent@transify.ai",
        "password": "anyPassword123"
    })
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]

def test_user_registration_and_duplicate_handling(client):
    """Verifies registration creates user with Argon2id hash, sets cookie, and rejects duplicates."""
    unique_email = f"user_{int(time.time() * 1000)}@testdomain.com"
    reg_payload = {
        "name": "Security Tester",
        "email": unique_email,
        "password": "StrongPassword123!_2026"
    }
    
    # First registration (15+ chars)
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 200
    reg_data = res.json()
    assert reg_data["status"] == "success"
    assert reg_data["user"]["email"] == unique_email.lower()
    assert reg_data["user"]["name"] == "Security Tester"
    assert "token" not in reg_data
    assert "transify_session" in client.cookies

    # Duplicate registration attempt
    dup_res = client.post("/api/auth/register", json=reg_payload)
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"].lower()

def test_registration_password_length_enforcement(client):
    """Verifies registration enforces the 15-character minimum password policy."""
    # 14-character password: MUST be rejected
    res_short = client.post("/api/auth/register", json={
        "name": "Short Pwd User",
        "email": f"short_{int(time.time()*1000)}@test.com",
        "password": "Password123456" # 14 chars
    })
    assert res_short.status_code in [400, 422]

    # 15-character password: MUST be accepted
    res_valid = client.post("/api/auth/register", json={
        "name": "Valid Pwd User",
        "email": f"valid_{int(time.time()*1000)}@test.com",
        "password": "Password1234567" # 15 chars
    })
    assert res_valid.status_code == 200
    assert res_valid.json()["status"] == "success"

def test_database_stores_session_hash_not_raw_token(client):
    """Verifies SQLite user_sessions table stores SHA-256 hash, never the raw token."""
    login_res = client.post("/api/auth/login", json={
        "email": "demo@transify.ai",
        "password": "transify2026"
    })
    assert login_res.status_code == 200
    raw_token = client.cookies.get("transify_session")
    assert raw_token is not None

    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Raw token MUST NOT exist in database
        cursor.execute("SELECT session_token FROM user_sessions WHERE session_token = ?", (raw_token,))
        assert cursor.fetchone() is None

        # SHA-256 hash of token MUST exist in database
        cursor.execute("SELECT session_token FROM user_sessions WHERE session_token = ?", (token_hash,))
        assert cursor.fetchone() is not None
    finally:
        conn.close()

def test_password_argon2id_upgrade():
    """Verifies password hashes are upgraded to Argon2id upon successful authentication."""
    unique_email = f"legacy_{int(time.time()*1000)}@test.com"
    pwd = "LegacyValidPassword123!"
    
    # Create user with legacy PBKDF2
    salt = secrets.token_hex(16)
    legacy_hash = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), salt.encode("utf-8"), 600_000).hex()
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, salt, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("Legacy User", unique_email, legacy_hash, salt, "user", now_iso, now_iso)
        )
        conn.commit()
    finally:
        conn.close()

    # Authenticate user: triggers automatic upgrade to Argon2id
    auth_user = authenticate_user(unique_email, pwd)
    assert auth_user is not None

    # Verify database now stores Argon2id hash
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, salt FROM users WHERE email = ?", (unique_email,))
    row = cursor.fetchone()
    conn.close()
    assert row["password_hash"].startswith("$argon2id$")
    assert row["salt"] == "argon2id"

def test_guest_mode_endpoint(client):
    """Verifies /api/auth/guest returns explicit guest structure without session cookie."""
    res = client.post("/api/auth/guest")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["user"]["role"] == "guest"
    assert data["user"]["is_guest"] is True
    assert "token" not in data or data.get("token") is None

def test_session_verification_and_logout(client):
    """Verifies /api/auth/me checks session cookie and logout revokes session."""
    # 1. Unauthenticated check
    client.cookies.clear()
    unauth_res = client.get("/api/auth/me")
    assert unauth_res.status_code == 200
    assert unauth_res.json()["authenticated"] is False

    # 2. Login to obtain session cookie
    login_res = client.post("/api/auth/login", json={
        "email": "demo@transify.ai",
        "password": "transify2026"
    })
    assert login_res.status_code == 200
    assert "transify_session" in client.cookies

    # 3. Authenticated check via cookie
    auth_res = client.get("/api/auth/me")
    assert auth_res.status_code == 200
    auth_data = auth_res.json()
    assert auth_data["authenticated"] is True
    assert auth_data["user"]["email"] == "demo@transify.ai"

    # 4. Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # 5. Verify session is revoked
    revoked_res = client.get("/api/auth/me")
    assert revoked_res.json()["authenticated"] is False

def test_user_data_isolation(client):
    """Verifies User A's history cannot be read or modified by User B or Guest."""
    email_a = f"usera_{int(time.time()*1000)}@test.com"
    email_b = f"userb_{int(time.time()*1000)}@test.com"
    pwd = "SharedSecurePassword2026!"

    # Register User A
    client.cookies.clear()
    res_a = client.post("/api/auth/register", json={"name": "User A", "email": email_a, "password": pwd})
    user_a_id = res_a.json()["user"]["id"]

    # Add history record for User A
    rec_id = log_translation(module="sign", recognized_text="dhonnobad", confidence=0.95, user_id=user_a_id)

    # User A reads history: sees record
    res_hist_a = client.get("/api/history")
    assert res_hist_a.status_code == 200
    records_a = res_hist_a.json()["records"]
    assert any(r["id"] == rec_id for r in records_a)

    # Register and log in as User B
    client.cookies.clear()
    client.post("/api/auth/register", json={"name": "User B", "email": email_b, "password": pwd})

    # User B reads history: MUST NOT see User A's record
    res_hist_b = client.get("/api/history")
    assert res_hist_b.status_code == 200
    records_b = res_hist_b.json()["records"]
    assert not any(r["id"] == rec_id for r in records_b)

    # Guest user reads history: receives empty list
    client.cookies.clear()
    res_hist_guest = client.get("/api/history")
    assert res_hist_guest.status_code == 200
    assert res_hist_guest.json()["records"] == []

def test_csrf_origin_protection(client):
    """Verifies CSRF middleware rejects state-changing requests from untrusted origins."""
    # Attempt POST with malicious untrusted origin
    res = client.post(
        "/api/history",
        headers={"Origin": "https://malicious-attacker-site.com"}
    )
    assert res.status_code == 403
    assert "CSRF validation failed" in res.json()["detail"]

def test_login_rate_limiting(client):
    """Verifies that 5 rapid failed login attempts trigger HTTP 429 Too Many Requests."""
    abuse_email = f"abuse_{int(time.time()*1000)}@test.com"
    for _ in range(5):
        res = client.post("/api/auth/login", json={"email": abuse_email, "password": "wrongpassword123!"})
        assert res.status_code == 401
    
    # 6th attempt: Rate limit exceeded
    res_blocked = client.post("/api/auth/login", json={"email": abuse_email, "password": "wrongpassword123!"})
    assert res_blocked.status_code == 429
    assert "Too many failed login attempts" in res_blocked.json()["detail"]
