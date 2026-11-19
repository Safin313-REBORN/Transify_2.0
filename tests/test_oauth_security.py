"""
OAuth and OpenID Connect Security Tests.
Verifies protection against CSRF, token replay, confused deputy / audience mismatch,
untrusted issuers, expired ID tokens, and unvalidated callbacks.
"""

import time
import pytest
from fastapi.testclient import TestClient

from src.api.server import app
from src.api.oauth_validator import GoogleOAuthValidator, OAuthValidationError


@pytest.fixture
def client():
    return TestClient(app, base_url="http://testserver")


@pytest.fixture
def validator():
    return GoogleOAuthValidator(client_id="transify-google-client-id")


def test_google_oauth_config_endpoint_is_disabled(client):
    """Verifies that Google OAuth config endpoint truthfully declares it is disabled."""
    res = client.get("/api/auth/oauth/google/config")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is False
    assert data["status"] == "disabled"
    assert data["client_id"] is None
    assert "disabled" in data["message"].lower()


def test_google_oauth_callback_rejection(client):
    """Verifies that any attempted Google OAuth callback is rejected with HTTP 400."""
    # Missing parameters
    res_missing = client.get("/api/auth/oauth/google/callback")
    assert res_missing.status_code == 400

    # With parameters, rejected because feature is disabled
    res_disabled = client.get("/api/auth/oauth/google/callback?code=mock_code&state=mock_state")
    assert res_disabled.status_code == 400
    assert "disabled" in res_disabled.json()["detail"].lower()


def test_oauth_validator_invalid_and_missing_state(validator):
    """Verifies that empty, missing, or mismatched state parameters are rejected."""
    # Missing state
    with pytest.raises(OAuthValidationError, match="Invalid or missing"):
        validator.validate_callback_state(None, "expected_state_123")

    with pytest.raises(OAuthValidationError, match="Invalid or missing"):
        validator.validate_callback_state("", "expected_state_123")

    # Mismatched state (CSRF attempt)
    with pytest.raises(OAuthValidationError, match="mismatch"):
        validator.validate_callback_state("attacker_forged_state", "expected_state_123")


def test_oauth_validator_state_replay_prevention(validator):
    """Verifies that a state token cannot be consumed twice (callback replay protection)."""
    valid_state = "valid_secure_state_xyz"
    # First validation succeeds
    assert validator.validate_callback_state(valid_state, valid_state) is True

    # Replay attack with same state fails
    with pytest.raises(OAuthValidationError, match="replay attack detected"):
        validator.validate_callback_state(valid_state, valid_state)


def test_oauth_validator_untrusted_issuer(validator):
    """Verifies that ID tokens from untrusted issuers are strictly rejected."""
    untrusted_claims = {
        "iss": "https://evil-identity-provider.com",
        "aud": "transify-google-client-id",
        "nonce": "valid_nonce_abc",
        "exp": time.time() + 3600,
        "email_verified": True,
        "email": "user@example.com"
    }

    with pytest.raises(OAuthValidationError, match="Untrusted OAuth token issuer"):
        validator.validate_id_token_claims(untrusted_claims, expected_nonce="valid_nonce_abc")


def test_oauth_validator_audience_mismatch(validator):
    """Verifies that ID tokens issued for other applications (confused deputy) are rejected."""
    mismatched_aud_claims = {
        "iss": "https://accounts.google.com",
        "aud": "attacker-app-client-id",
        "nonce": "valid_nonce_abc",
        "exp": time.time() + 3600,
        "email_verified": True,
        "email": "user@example.com"
    }

    with pytest.raises(OAuthValidationError, match="OAuth audience mismatch"):
        validator.validate_id_token_claims(mismatched_aud_claims, expected_nonce="valid_nonce_abc")


def test_oauth_validator_wrong_nonce(validator):
    """Verifies that tokens with mismatched nonces are rejected."""
    wrong_nonce_claims = {
        "iss": "https://accounts.google.com",
        "aud": "transify-google-client-id",
        "nonce": "wrong_nonce_injected",
        "exp": time.time() + 3600,
        "email_verified": True,
        "email": "user@example.com"
    }

    with pytest.raises(OAuthValidationError, match="OAuth nonce mismatch"):
        validator.validate_id_token_claims(wrong_nonce_claims, expected_nonce="expected_nonce_123")


def test_oauth_validator_expired_token(validator):
    """Verifies that expired ID tokens are rejected."""
    expired_claims = {
        "iss": "https://accounts.google.com",
        "aud": "transify-google-client-id",
        "nonce": "valid_nonce_abc",
        "exp": time.time() - 60,  # Expired 1 minute ago
        "email_verified": True,
        "email": "user@example.com"
    }

    with pytest.raises(OAuthValidationError, match="OAuth ID token expired"):
        validator.validate_id_token_claims(expired_claims, expected_nonce="valid_nonce_abc")


def test_oauth_validator_unverified_email(validator):
    """Verifies that accounts without verified emails from Google are rejected."""
    unverified_email_claims = {
        "iss": "https://accounts.google.com",
        "aud": "transify-google-client-id",
        "nonce": "valid_nonce_abc",
        "exp": time.time() + 3600,
        "email_verified": False,
        "email": "unverified@example.com"
    }

    with pytest.raises(OAuthValidationError, match="email address is not verified"):
        validator.validate_id_token_claims(unverified_email_claims, expected_nonce="valid_nonce_abc")


def test_oauth_validator_valid_claims_success(validator):
    """Verifies that authentic Google ID tokens with all matching claims pass verification."""
    valid_claims = {
        "iss": "https://accounts.google.com",
        "aud": "transify-google-client-id",
        "nonce": "valid_nonce_123",
        "exp": time.time() + 3600,
        "email_verified": True,
        "email": "valid.user@gmail.com",
        "name": "Valid User",
        "sub": "google-sub-id-12345"
    }

    user_info = validator.validate_id_token_claims(valid_claims, expected_nonce="valid_nonce_123")
    assert user_info["email"] == "valid.user@gmail.com"
    assert user_info["name"] == "Valid User"
    assert user_info["sub"] == "google-sub-id-12345"

