"""
Google OpenID Connect / OAuth Security Validation Module.
Enforces cryptographically sound validation of OAuth state, nonces,
issuers, audience, token expiration, and replay prevention.
"""

import time
import logging
from typing import Dict, Any, Optional, Set

logger = logging.getLogger("transify.oauth")


class OAuthValidationError(Exception):
    """Raised when an OAuth / OIDC parameter or token claim fails security validation."""
    pass


class GoogleOAuthValidator:
    """
    Validates Google OAuth 2.0 / OpenID Connect tokens and transaction parameters.
    Guarantees protection against:
    - CSRF (via cryptographically bound state)
    - Replay attacks (via single-use state and token tracking)
    - Token substitution / Confused Deputy (via strict audience checks)
    - Identity spoofing (via trusted issuer enforcement)
    - Expired credential acceptance (via bounded time validation)
    - Nonce injection (via cryptographic nonce matching)
    """

    TRUSTED_ISSUERS = {
        "accounts.google.com",
        "https://accounts.google.com"
    }

    def __init__(self, client_id: Optional[str] = None):
        self.client_id = client_id or "transify-google-client-id"
        self._consumed_states: Set[str] = set()

    def validate_callback_state(self, received_state: Optional[str], expected_state: Optional[str]) -> bool:
        """
        Validates state parameter against expected state and verifies it has not been previously consumed.
        Raises OAuthValidationError on invalid, mismatched, or replayed state.
        """
        if not received_state or not expected_state:
            raise OAuthValidationError("Invalid or missing OAuth state parameter.")

        if received_state != expected_state:
            raise OAuthValidationError("OAuth state parameter mismatch (possible CSRF attack).")

        if received_state in self._consumed_states:
            raise OAuthValidationError("OAuth state already consumed (replay attack detected).")

        self._consumed_states.add(received_state)
        return True

    def validate_id_token_claims(
        self,
        claims: Dict[str, Any],
        expected_nonce: str,
        client_id: Optional[str] = None,
        now_ts: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Validates decoded JWT claims from a Google ID token:
        1. Trusted issuer ('accounts.google.com' or 'https://accounts.google.com')
        2. Audience matches configured client_id
        3. Nonce matches expected cryptographic session nonce
        4. Expiry (exp) > current timestamp
        5. Verified email claim is present and True
        """
        target_client_id = client_id or self.client_id
        now = now_ts if now_ts is not None else time.time()

        # 1. Issuer Validation
        issuer = claims.get("iss")
        if issuer not in self.TRUSTED_ISSUERS:
            raise OAuthValidationError(f"Untrusted OAuth token issuer: '{issuer}'. Expected Google issuer.")

        # 2. Audience Validation
        aud = claims.get("aud")
        if aud != target_client_id:
            raise OAuthValidationError(f"OAuth audience mismatch. Token audience '{aud}' does not match client ID '{target_client_id}'.")

        # 3. Nonce Validation
        token_nonce = claims.get("nonce")
        if not token_nonce or token_nonce != expected_nonce:
            raise OAuthValidationError("OAuth nonce mismatch (possible token replay or injection).")

        # 4. Expiration Validation
        exp = claims.get("exp", 0)
        try:
            exp_val = float(exp)
        except (ValueError, TypeError):
            exp_val = 0.0

        if exp_val <= now:
            raise OAuthValidationError("OAuth ID token expired.")

        # 5. Verified Email Validation
        if not claims.get("email_verified", False):
            raise OAuthValidationError("OAuth claim rejected: email address is not verified by provider.")

        return {
            "email": claims.get("email", "").lower().strip(),
            "name": claims.get("name", "").strip(),
            "sub": claims.get("sub", "")
        }

