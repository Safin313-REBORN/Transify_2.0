"""
Password Reset Email Delivery and Security Lifecycle Tests.
Verifies configurable SMTP delivery, MockMailAdapter, non-enumerating responses,
single-use token guarantees, bounded expiry, session revocation, and concurrency safety.
"""

import time
import pytest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from src.api.server import app
from src.api.email_service import MockMailAdapter, SMTPEmailAdapter, set_email_adapter, get_email_adapter
from src.database.db import (
    create_user,
    get_connection,
    create_password_reset_token,
    verify_and_consume_reset_token,
    create_session,
    get_user_by_session
)


@pytest.fixture
def client():
    return TestClient(app, base_url="http://testserver")


def test_password_reset_valid_delivery_via_mock_adapter(client, reset_mock_mail):
    """Verifies that requesting password reset for an existing user delivers email with secure token."""
    email = f"delivery_test_{int(time.time()*1000)}@transify.test"
    pwd = "ValidInitialPassword123!_2026"
    create_user("Delivery Tester", email, pwd, consent_terms=True)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "If an account with that email exists" in data["message"]

    # Verify email was captured in MockMailAdapter
    assert len(reset_mock_mail.sent_emails) == 1
    sent = reset_mock_mail.sent_emails[0]
    assert sent["to"] == email.lower()
    assert "token" in sent
    assert len(sent["token"]) >= 32
    assert "reset_url" in sent
    assert sent["token"] in sent["reset_url"]


def test_password_reset_unknown_email_prevents_enumeration(client, reset_mock_mail):
    """Verifies that an unknown email returns generic success and does NOT send email or leak user existence."""
    unknown_email = f"nonexistent_{int(time.time()*1000)}@transify.test"

    res = client.post("/api/auth/forgot-password", json={"email": unknown_email})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "If an account with that email exists" in data["message"]

    # No email should have been dispatched
    assert len(reset_mock_mail.sent_emails) == 0


def test_password_reset_mail_delivery_failure_returns_503(client, reset_mock_mail):
    """Verifies that an SMTP connection or delivery failure returns generic HTTP 503 without leaking data."""
    email = f"fail_delivery_{int(time.time()*1000)}@transify.test"
    create_user("Fail Tester", email, "SecurePassword123!_2026", consent_terms=True)

    # Simulate SMTP failure
    reset_mock_mail.simulate_failure(Exception("Connection refused by SMTP relay"))

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 503
    detail = res.json()["detail"]
    assert "unavailable" in detail.lower() or "failed" in detail.lower()
    assert email not in detail


def test_password_reset_unconfigured_smtp_returns_503(client, reset_mock_mail):
    """Verifies that when mail service is unconfigured, HTTP 503 is returned truthfully."""
    email = f"unconfigured_{int(time.time()*1000)}@transify.test"
    create_user("Unconfig Tester", email, "SecurePassword123!_2026", consent_terms=True)

    reset_mock_mail.set_configured(False)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 503
    assert "unavailable" in res.json()["detail"].lower()


def test_password_reset_token_expiry_rejection(client):
    """Verifies that an expired token cannot be consumed to change a password."""
    email = f"expired_{int(time.time()*1000)}@transify.test"
    user = create_user("Expired Tester", email, "OldPassword12345!_2026", consent_terms=True)

    # Generate token that expired 10 seconds ago
    raw_token, _ = create_password_reset_token(user["id"], expires_in_seconds=-10.0)

    res = client.post("/api/auth/reset-password", json={
        "token": raw_token,
        "new_password": "NewBrandPassword123!_2026"
    })
    assert res.status_code == 400
    assert "Invalid, expired, or already used" in res.json()["detail"]


def test_password_reset_single_use_token_cannot_be_reused(client):
    """Verifies that a reset token is single-use and cannot be consumed a second time."""
    email = f"single_use_{int(time.time()*1000)}@transify.test"
    user = create_user("Single Use Tester", email, "InitialPassword123!_2026", consent_terms=True)

    raw_token, _ = create_password_reset_token(user["id"], expires_in_seconds=1800.0)

    # First consumption: MUST succeed
    res1 = client.post("/api/auth/reset-password", json={
        "token": raw_token,
        "new_password": "NewPasswordFirstTime123!"
    })
    assert res1.status_code == 200
    assert res1.json()["status"] == "success"

    # Second consumption with same token: MUST fail
    res2 = client.post("/api/auth/reset-password", json={
        "token": raw_token,
        "new_password": "NewPasswordSecondTime123!"
    })
    assert res2.status_code == 400
    assert "Invalid, expired, or already used" in res2.json()["detail"]


def test_password_reset_invalid_token_rejection(client):
    """Verifies that a completely fabricated or malformed token is rejected with HTTP 400."""
    res = client.post("/api/auth/reset-password", json={
        "token": "fabricated_token_value_that_does_not_exist_in_db",
        "new_password": "ValidNewPassword123!_2026"
    })
    assert res.status_code == 400
    assert "Invalid, expired, or already used" in res.json()["detail"]


def test_password_reset_successful_flow_and_session_revocation(client, reset_mock_mail):
    """
    Verifies that successful password reset:
    1. Updates the user's password to the new value.
    2. Revokes all pre-existing sessions for that user.
    3. Allows login only with the new password.
    """
    email = f"full_flow_{int(time.time()*1000)}@transify.test"
    old_pwd = "OldPassword12345!_2026"
    new_pwd = "BrandNewSecurePassword123!_2026"
    user = create_user("Flow Tester", email, old_pwd, consent_terms=True)

    # 1. Establish an active session prior to reset
    login_res = client.post("/api/auth/login", json={"email": email, "password": old_pwd})
    assert login_res.status_code == 200
    old_session_token = client.cookies.get("transify_session")
    assert old_session_token is not None

    # Verify session is valid
    me_res = client.get("/api/auth/me")
    assert me_res.json()["authenticated"] is True

    # 2. Trigger forgot password
    forgot_res = client.post("/api/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 200
    assert len(reset_mock_mail.sent_emails) == 1
    reset_token = reset_mock_mail.sent_emails[0]["token"]

    # 3. Consume token and set new password
    reset_res = client.post("/api/auth/reset-password", json={
        "token": reset_token,
        "new_password": new_pwd
    })
    assert reset_res.status_code == 200

    # 4. Pre-existing session MUST now be revoked in database
    session_check = get_user_by_session(old_session_token)
    assert session_check is None

    me_revoked = client.get("/api/auth/me")
    assert me_revoked.json()["authenticated"] is False

    # 5. Old password no longer works
    client.cookies.clear()
    login_old = client.post("/api/auth/login", json={"email": email, "password": old_pwd})
    assert login_old.status_code == 401

    # 6. New password successfully authenticates
    login_new = client.post("/api/auth/login", json={"email": email, "password": new_pwd})
    assert login_new.status_code == 200
    assert login_new.json()["status"] == "success"


def test_password_reset_concurrent_token_consumption():
    """
    Verifies that SQLite atomic transaction (BEGIN IMMEDIATE) prevents
    double-spend race conditions when two requests attempt to consume the same reset token simultaneously.
    """
    email = f"concurrency_{int(time.time()*1000)}@transify.test"
    user = create_user("Concurrency Tester", email, "InitialPassword123!_2026", consent_terms=True)
    raw_token, _ = create_password_reset_token(user["id"], expires_in_seconds=1800.0)

    results = []

    def consume_token(pwd_suffix):
        return verify_and_consume_reset_token(raw_token, f"NewPassword{pwd_suffix}123!_2026")

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(consume_token, "A")
        f2 = executor.submit(consume_token, "B")
        results = [f1.result(), f2.result()]

    # Exactly one consumption must succeed, the other must fail
    assert results.count(True) == 1
    assert results.count(False) == 1
