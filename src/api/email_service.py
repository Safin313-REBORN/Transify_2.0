"""
Transify 2.0 Email Delivery Adapter.
Provides configurable SMTP delivery for password reset emails and system notifications.
Includes a MockMailAdapter for automated test environments without external dependencies.
"""

import os
import smtplib
import logging
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any

logger = logging.getLogger("transify.email")


class EmailDeliveryError(Exception):
    """Raised when an email cannot be sent due to connection failure or SMTP rejection."""
    pass


class EmailAdapter:
    """Base interface for Transify email delivery adapters."""

    def is_configured(self) -> bool:
        raise NotImplementedError

    def send_password_reset_email(self, to_email: str, reset_token: str, base_url: Optional[str] = None) -> bool:
        raise NotImplementedError


class SMTPEmailAdapter(EmailAdapter):
    """
    Standard SMTP email delivery adapter.
    Configured via environment variables:
    - SMTP_HOST: Hostname of SMTP relay
    - SMTP_PORT: Port (default 587)
    - SMTP_USER: SMTP authentication username / email
    - SMTP_PASSWORD: SMTP authentication password or app token
    - SMTP_FROM: Sender address (defaults to SMTP_USER or no-reply@transify.ai)
    - SMTP_USE_TLS: Whether to invoke STARTTLS (default True)
    - SMTP_USE_SSL: Whether to connect directly via SSL (default False)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        use_tls: Optional[bool] = None,
        use_ssl: Optional[bool] = None,
    ):
        self.host = host if host is not None else os.getenv("SMTP_HOST", "").strip()
        raw_port = port if port is not None else os.getenv("SMTP_PORT", "587")
        try:
            self.port = int(raw_port)
        except (ValueError, TypeError):
            self.port = 587

        self.user = user if user is not None else os.getenv("SMTP_USER", "").strip()
        self.password = password if password is not None else os.getenv("SMTP_PASSWORD", "").strip()
        self.from_email = from_email if from_email is not None else os.getenv("SMTP_FROM", "").strip()
        if not self.from_email:
            self.from_email = self.user if self.user else "no-reply@transify.ai"

        if use_tls is not None:
            self.use_tls = use_tls
        else:
            self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

        if use_ssl is not None:
            self.use_ssl = use_ssl
        else:
            self.use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() in ("true", "1", "yes")

    def is_configured(self) -> bool:
        """Returns True only when SMTP host is specified."""
        return bool(self.host)

    def send_password_reset_email(self, to_email: str, reset_token: str, base_url: Optional[str] = None) -> bool:
        """
        Constructs and delivers a password recovery email over SMTP.
        Does not log the raw token to prevent credential exposure in application logs.
        """
        if not self.is_configured():
            raise EmailDeliveryError("SMTP host is not configured on this server.")

        clean_to = (to_email or "").strip().lower()
        if not clean_to:
            raise EmailDeliveryError("Recipient email address is required.")

        app_url = (base_url or os.getenv("APP_URL", "https://transify20-production.up.railway.app")).rstrip("/")
        reset_url = f"{app_url}/login?reset_token={reset_token}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Transify — Password Reset Request"
        msg["From"] = self.from_email
        msg["To"] = clean_to

        text_content = f"""Hello,

You recently requested to reset your password for your Transify account.

Use the following one-time reset code to set a new password:
{reset_token}

Or click the link below to open the recovery page:
{reset_url}

This link and code will expire in 30 minutes. If you did not request this, please disregard this email.

— The Transify Team
Breaking Communication Barriers
"""
        msg.attach(MIMEText(text_content, "plain", "utf-8"))

        recipient_hash = hashlib.sha256(clean_to.encode("utf-8")).hexdigest()[:8]
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10.0)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=10.0)

            with server:
                if self.use_tls and not self.use_ssl:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.send_message(msg)

            logger.info(f"Successfully delivered password reset email to recipient [{recipient_hash}].")
            return True
        except Exception as err:
            logger.error(f"SMTP delivery failed for recipient [{recipient_hash}]: {type(err).__name__}")
            raise EmailDeliveryError(f"SMTP delivery error: {err}") from err


class MockMailAdapter(EmailAdapter):
    """
    Mock email adapter for test environments.
    Captures sent emails in an in-memory queue for verification.
    Supports simulated failure conditions.
    """

    def __init__(self, configured: bool = True):
        self._configured = configured
        self.sent_emails: List[Dict[str, Any]] = []
        self.simulated_error: Optional[Exception] = None

    def is_configured(self) -> bool:
        return self._configured

    def set_configured(self, status: bool) -> None:
        self._configured = status

    def simulate_failure(self, error: Optional[Exception]) -> None:
        self.simulated_error = error

    def clear(self) -> None:
        self.sent_emails.clear()
        self.simulated_error = None

    def send_password_reset_email(self, to_email: str, reset_token: str, base_url: Optional[str] = None) -> bool:
        if not self.is_configured():
            raise EmailDeliveryError("Mock mail adapter is configured as disabled.")

        if self.simulated_error:
            raise EmailDeliveryError(f"Simulated SMTP error: {self.simulated_error}")

        clean_to = (to_email or "").strip().lower()
        app_url = (base_url or "https://transify20-production.up.railway.app").rstrip("/")
        reset_url = f"{app_url}/login?reset_token={reset_token}"

        record = {
            "to": clean_to,
            "token": reset_token,
            "reset_url": reset_url,
            "subject": "Transify — Password Reset Request"
        }
        self.sent_emails.append(record)
        return True


# Global Adapter Singleton
_GLOBAL_EMAIL_ADAPTER: Optional[EmailAdapter] = None


def get_email_adapter() -> EmailAdapter:
    """Returns the active email adapter singleton, initializing SMTPEmailAdapter if unset."""
    global _GLOBAL_EMAIL_ADAPTER
    if _GLOBAL_EMAIL_ADAPTER is None:
        _GLOBAL_EMAIL_ADAPTER = SMTPEmailAdapter()
    return _GLOBAL_EMAIL_ADAPTER


def set_email_adapter(adapter: Optional[EmailAdapter]) -> None:
    """Configures a custom email adapter (e.g. MockMailAdapter for automated tests)."""
    global _GLOBAL_EMAIL_ADAPTER
    _GLOBAL_EMAIL_ADAPTER = adapter


def reset_email_adapter() -> None:
    """Resets the email adapter back to default SMTPEmailAdapter."""
    global _GLOBAL_EMAIL_ADAPTER
    _GLOBAL_EMAIL_ADAPTER = None
