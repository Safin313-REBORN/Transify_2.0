"""
Password Reset Email Delivery and Security Lifecycle Tests.
Verifies configurable SMTP delivery, MockMailAdapter, non-enumerating responses across all failure states,
single-use token guarantees, bounded expiry, session revocation, and concurrency safety.
"""

import time
import os
import hashlib
import logging
from unittest.mock import MagicMock, patch
import smtplib
import pytest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from src.api.server import app
from src.api.email_service import (
    MockMailAdapter,
    SMTPEmailAdapter,
    EmailDeliveryError,
    set_email_adapter,
    get_email_adapter,
    get_canonical_app_url,
)
from src.database.db import (
    create_user,
    get_connection,
    create_password_reset_token,
    verify_and_consume_reset_token,
    create_session,
    get_user_by_session,
    invalidate_password_reset_token,
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
    assert f"#reset_token={sent['token']}" in sent["reset_url"]


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


def test_password_reset_mail_delivery_failure_anti_enumeration_and_token_invalidation(client, reset_mock_mail):
    """
    Verifies that when SMTP connection/delivery fails:
    1. Returns HTTP 200 with the exact same generic message (anti-enumeration).
    2. Any generated token is immediately invalidated in the database.
    """
    email = f"fail_delivery_{int(time.time()*1000)}@transify.test"
    user = create_user("Fail Tester", email, "SecurePassword123!_2026", consent_terms=True)

    # Simulate SMTP failure
    reset_mock_mail.simulate_failure(Exception("Connection refused by SMTP relay"))

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "If an account with that email exists" in data["message"]
    assert "test_token" not in data  # Token not exposed on failed delivery

    # Verify that no active reset token exists in database for this user
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM password_reset_tokens WHERE user_id = ? AND used_at IS NULL;", (user["id"],))
    count = cursor.fetchone()["cnt"]
    conn.close()
    assert count == 0


def test_password_reset_unconfigured_smtp_anti_enumeration_and_token_invalidation(client, reset_mock_mail):
    """
    Verifies that when mail service is unconfigured:
    1. Returns HTTP 200 with the exact same generic message (anti-enumeration).
    2. Any generated token is immediately invalidated in the database.
    """
    email = f"unconfigured_{int(time.time()*1000)}@transify.test"
    user = create_user("Unconfig Tester", email, "SecurePassword123!_2026", consent_terms=True)

    reset_mock_mail.set_configured(False)

    res = client.post("/api/auth/forgot-password", json={"email": email})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "If an account with that email exists" in data["message"]
    assert "test_token" not in data

    # Verify no usable reset token exists
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM password_reset_tokens WHERE user_id = ? AND used_at IS NULL;", (user["id"],))
    count = cursor.fetchone()["cnt"]
    conn.close()
    assert count == 0


def test_password_reset_anti_enumeration_consistency_across_all_six_scenarios(client, reset_mock_mail):
    """
    REGRESSION TEST: Proves that all 6 externally visible scenarios return
    the EXACT same status code (200) and response body, preventing account enumeration.
    """
    pwd = "StandardPassword123!_2026"
    expected_msg = "If an account with that email exists, password reset instructions have been processed."

    # 1. Existing account with successful delivery
    email_success = f"enum_success_{int(time.time()*1000)}@transify.test"
    create_user("Enum User 1", email_success, pwd, consent_terms=True)
    reset_mock_mail.set_configured(True)
    reset_mock_mail.simulate_failure(None)
    res1 = client.post("/api/auth/forgot-password", json={"email": email_success})

    # 2. Unknown account
    email_unknown = f"enum_unknown_{int(time.time()*1000)}@transify.test"
    res2 = client.post("/api/auth/forgot-password", json={"email": email_unknown})

    # 3. Existing account with SMTP connection failure
    email_conn_fail = f"enum_conn_fail_{int(time.time()*1000)}@transify.test"
    create_user("Enum User 3", email_conn_fail, pwd, consent_terms=True)
    reset_mock_mail.simulate_failure(smtplib.SMTPConnectError(111, b"Connection refused"))
    res3 = client.post("/api/auth/forgot-password", json={"email": email_conn_fail})

    # 4. Existing account with SMTP authentication failure
    email_auth_fail = f"enum_auth_fail_{int(time.time()*1000)}@transify.test"
    create_user("Enum User 4", email_auth_fail, pwd, consent_terms=True)
    reset_mock_mail.simulate_failure(smtplib.SMTPAuthenticationError(535, b"Auth failed"))
    res4 = client.post("/api/auth/forgot-password", json={"email": email_auth_fail})

    # 5. Disabled account
    email_disabled = f"enum_disabled_{int(time.time()*1000)}@transify.test"
    user_dis = create_user("Enum User 5", email_disabled, pwd, consent_terms=True)
    conn = get_connection()
    conn.execute("UPDATE users SET role = 'disabled' WHERE id = ?;", (user_dis["id"],))
    conn.commit()
    conn.close()
    reset_mock_mail.simulate_failure(None)
    res5 = client.post("/api/auth/forgot-password", json={"email": email_disabled})

    # 6. Unconfigured email adapter
    email_unconfigured = f"enum_unconfig_{int(time.time()*1000)}@transify.test"
    create_user("Enum User 6", email_unconfigured, pwd, consent_terms=True)
    reset_mock_mail.set_configured(False)
    reset_mock_mail.simulate_failure(None)
    res6 = client.post("/api/auth/forgot-password", json={"email": email_unconfigured})

    responses = [res1, res2, res3, res4, res5, res6]
    for idx, r in enumerate(responses, 1):
        assert r.status_code == 200, f"Scenario {idx} returned status {r.status_code}"
        body = r.json()
        assert body["status"] == "success", f"Scenario {idx} status not success"
        assert body["message"] == expected_msg, f"Scenario {idx} message mismatch"


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

    assert results.count(True) == 1
    assert results.count(False) == 1


# --- PHASE 3: ISOLATED UNIT TESTS FOR SMTPEmailAdapter (Mocking smtplib) ---

def test_smtp_adapter_initialization_defaults_and_custom_ports():
    """Verifies SMTP adapter initializes host, default and custom ports, and security flags."""
    # Default port 587
    adapter = SMTPEmailAdapter(host="mail.transify.test", user="mailer", password="secret_password")
    assert adapter.is_configured() is True
    assert adapter.port == 587
    assert adapter.use_tls is True
    assert adapter.use_ssl is False
    assert adapter.from_email == "mailer"

    # Custom SSL port 465
    adapter_ssl = SMTPEmailAdapter(host="mail.transify.test", port=465, use_ssl=True, use_tls=False)
    assert adapter_ssl.port == 465
    assert adapter_ssl.use_ssl is True
    assert adapter_ssl.use_tls is False
    assert adapter_ssl.from_email == "no-reply@transify.ai"

    # Unconfigured adapter
    unconf = SMTPEmailAdapter(host="")
    assert unconf.is_configured() is False


@patch("smtplib.SMTP")
def test_smtp_adapter_starttls_flow(mock_smtp_cls):
    """Verifies STARTTLS connection, authentication, and message dispatch headers and content."""
    mock_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_instance

    adapter = SMTPEmailAdapter(
        host="smtp.relay.test",
        port=587,
        user="test_smtp_user@transify.ai",
        password="TopSecretSMTPPassword_2026",
        from_email="noreply@transify.ai",
        use_tls=True,
        use_ssl=False
    )

    token = "test_reset_token_value_abc123"
    result = adapter.send_password_reset_email("user@example.com", token, base_url="https://transify.ai")

    assert result is True
    mock_smtp_cls.assert_called_once_with("smtp.relay.test", 587, timeout=10.0)
    mock_instance.starttls.assert_called_once()
    mock_instance.login.assert_called_once_with("test_smtp_user@transify.ai", "TopSecretSMTPPassword_2026")
    mock_instance.send_message.assert_called_once()

    # Inspect message headers
    msg = mock_instance.send_message.call_args[0][0]
    assert msg["Subject"] == "Transify — Password Reset Request"
    assert msg["From"] == "noreply@transify.ai"
    assert msg["To"] == "user@example.com"

    # Inspect body content
    payload = msg.get_payload()[0].get_payload(decode=True).decode("utf-8")
    assert token in payload
    assert f"https://transify.ai/login#reset_token={token}" in payload


@patch("smtplib.SMTP_SSL")
def test_smtp_adapter_ssl_flow(mock_ssl_cls):
    """Verifies SSL connection flow does not invoke STARTTLS and sends email securely."""
    mock_instance = MagicMock()
    mock_ssl_cls.return_value.__enter__.return_value = mock_instance

    adapter = SMTPEmailAdapter(
        host="smtp.ssl.test",
        port=465,
        user="ssl_user@transify.ai",
        password="SSLSecretPassword_2026",
        from_email="ssl_noreply@transify.ai",
        use_tls=False,
        use_ssl=True
    )

    token = "ssl_token_1234567890"
    result = adapter.send_password_reset_email("ssl_recipient@example.com", token)

    assert result is True
    mock_ssl_cls.assert_called_once_with("smtp.ssl.test", 465, timeout=10.0)
    mock_instance.login.assert_called_once_with("ssl_user@transify.ai", "SSLSecretPassword_2026")
    mock_instance.send_message.assert_called_once()


def test_smtp_adapter_connection_and_auth_failures():
    """Verifies that connection and authentication failures raise EmailDeliveryError."""
    # 1. Connection error
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = smtplib.SMTPConnectError(111, b"Connection refused")
        adapter = SMTPEmailAdapter(host="smtp.fail.test")
        with pytest.raises(EmailDeliveryError) as exc_info:
            adapter.send_password_reset_email("user@fail.test", "dummy_token")
        assert "SMTP delivery error" in str(exc_info.value)

    # 2. Authentication error
    with patch("smtplib.SMTP") as mock_smtp2:
        mock_instance = MagicMock()
        mock_smtp2.return_value.__enter__.return_value = mock_instance
        mock_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Invalid credentials")

        adapter_auth = SMTPEmailAdapter(host="smtp.fail.test", user="bad_user", password="bad_password")
        with pytest.raises(EmailDeliveryError) as exc_info2:
            adapter_auth.send_password_reset_email("user@fail.test", "dummy_token")
        assert "SMTP delivery error" in str(exc_info2.value)


@patch("smtplib.SMTP")
def test_smtp_adapter_credential_and_token_redaction_in_logs(mock_smtp_cls, caplog):
    """
    SECURITY TEST: Asserts that SMTP delivery operations and error handling NEVER log
    passwords, raw tokens, or cleartext recipient email addresses.
    """
    mock_instance = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_instance

    raw_token = "SuperSecretResetTokenDoNotLogMe_12345"
    smtp_password = "SuperSecretSMTPPassword_98765"
    recipient_email = "confidential_patient@hospital.org"

    adapter = SMTPEmailAdapter(
        host="smtp.secure.test",
        user="transify_mailer",
        password=smtp_password,
        from_email="noreply@transify.ai"
    )

    with caplog.at_level(logging.DEBUG):
        adapter.send_password_reset_email(recipient_email, raw_token)

    log_text = caplog.text
    # Strict verification: sensitive data MUST NOT appear in logs
    assert raw_token not in log_text
    assert smtp_password not in log_text
    assert recipient_email not in log_text
    # Expected: only 8-character recipient hash appears
    expected_hash = hashlib.sha256(recipient_email.encode("utf-8")).hexdigest()[:8]
    assert expected_hash in log_text


def test_canonical_app_url_https_validation(monkeypatch):
    """Verifies that get_canonical_app_url enforces HTTPS in production environments."""
    # Production without HTTPS must raise ValueError
    monkeypatch.setenv("TRANSIFY_ENV", "production")
    monkeypatch.setenv("APP_URL", "http://insecure-production.com")
    with pytest.raises(ValueError) as exc:
        get_canonical_app_url()
    assert "must use HTTPS" in str(exc.value)

    # Production with valid HTTPS URL
    monkeypatch.setenv("APP_URL", "https://transify.production.app")
    assert get_canonical_app_url() == "https://transify.production.app"

    # Default production fallback
    monkeypatch.delenv("APP_URL", raising=False)
    assert get_canonical_app_url().startswith("https://")
