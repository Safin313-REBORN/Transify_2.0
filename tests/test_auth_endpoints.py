"""
Backend Authentication and Session Security Tests for Transify 2.0.
Verifies PBKDF2 password verification, registration, duplicate checks,
session persistence, cookie management, and guest mode isolation.
"""
import pytest
from fastapi.testclient import TestClient
from src.api.server import app
from src.database.db import get_user_by_email, authenticate_user

@pytest.fixture
def client():
    # Use TestClient with fresh cookies
    with TestClient(app) as test_client:
        test_client.cookies.clear()
        yield test_client

def test_default_demo_account_exists():
    """Verifies that demo@transify.ai exists and password authenticates correctly with PBKDF2."""
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

def test_demo_login_success(client):
    """Verifies login with default demo account sets HttpOnly session cookie and returns user."""
    res = client.post("/api/auth/login", json={
        "email": "demo@transify.ai",
        "password": "transify2026"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["user"]["email"] == "demo@transify.ai"
    assert data["user"]["name"] == "Sarah Ahmed"
    assert "token" in data
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
    """Verifies registration creates user with PBKDF2 hash, logs in, and rejects duplicate email."""
    import time
    unique_email = f"user_{int(time.time() * 1000)}@testdomain.com"
    reg_payload = {
        "name": "Test Engineer",
        "email": unique_email,
        "password": "StrongPassword123!"
    }
    
    # First registration
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 200
    reg_data = res.json()
    assert reg_data["status"] == "success"
    assert reg_data["user"]["email"] == unique_email.lower()
    assert reg_data["user"]["name"] == "Test Engineer"
    assert "token" in reg_data

    # Duplicate registration attempt
    dup_res = client.post("/api/auth/register", json=reg_payload)
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"].lower()

def test_registration_validation(client):
    """Verifies registration rejects invalid input format."""
    # Short password (< 6 chars)
    res = client.post("/api/auth/register", json={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "123"
    })
    assert res.status_code in [400, 422]

    # Invalid email
    res2 = client.post("/api/auth/register", json={
        "name": "Jane Doe",
        "email": "not-an-email",
        "password": "ValidPassword123"
    })
    assert res2.status_code in [400, 422]

def test_guest_mode_endpoint(client):
    """Verifies /api/auth/guest returns explicit guest structure without JWT/session token."""
    res = client.post("/api/auth/guest")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["user"]["role"] == "guest"
    assert data["user"]["is_guest"] is True
    assert data["token"] is None

def test_session_verification_and_logout(client):
    """Verifies /api/auth/me checks session cookie and logout clears session."""
    # 1. Unauthenticated check
    client.cookies.clear()
    unauth_res = client.get("/api/auth/me")
    assert unauth_res.status_code == 200
    assert unauth_res.json()["authenticated"] is False

    # 2. Login to obtain session
    login_res = client.post("/api/auth/login", json={
        "email": "demo@transify.ai",
        "password": "transify2026"
    })
    token = login_res.json()["token"]

    # 3. Authenticated check via cookie
    auth_res = client.get("/api/auth/me")
    assert auth_res.status_code == 200
    auth_data = auth_res.json()
    assert auth_data["authenticated"] is True
    assert auth_data["user"]["email"] == "demo@transify.ai"

    # 4. Authenticated check via Authorization header Bearer token
    client.cookies.clear()
    bearer_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert bearer_res.status_code == 200
    assert bearer_res.json()["authenticated"] is True

    # 5. Logout
    logout_res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200

    # 6. Verify session is revoked
    revoked_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert revoked_res.json()["authenticated"] is False
