"""
Transify 2.0 Email Delivery Adapter.
Provides configurable SMTP delivery for password reset emails and system notifications.
Includes a MockMailAdapter for automated test environments without external dependencies.
"""

import os
import smtplib
import logging
import hashlib
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any

logger = logging.getLogger("transify.email")


def get_canonical_app_url() -> str:
    """
    Returns the configured canonical application URL.
    Validates that production environments strictly require HTTPS.
    Never trusts incoming request Host headers.
    """
    try:
        from src.database.db import is_production
        prod = is_production()
    except Exception:
        prod = os.getenv("TRANSIFY_ENV", "").lower() == "production"

    raw_url = os.getenv("APP_URL", "").strip()
    if prod:
        if not raw_url:
            raw_url = "https://transify20-production.up.railway.app"
        if not raw_url.startswith("https://"):
            raise ValueError(f"APP_URL in production must use HTTPS: '{raw_url}'")
    else:
        if not raw_url:
            raw_url = "http://localhost:8000"
    return raw_url.rstrip("/")


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

        app_url = (base_url or get_canonical_app_url()).rstrip("/")
        reset_url = f"{app_url}/login#reset_token={reset_token}"

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

        safe_token = html.escape(reset_token)
        safe_url = html.escape(reset_url)
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Transify Password Reset</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e1b4b; background-color: #f8fafc; margin: 0; padding: 24px; }}
.container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 32px; border: 1px solid #e2e8f0; }}
.btn {{ display: inline-block; background-color: #8338ec; color: #ffffff !important; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
.code-box {{ background-color: #f1f5f9; padding: 12px 20px; border-radius: 8px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 18px; letter-spacing: 2px; font-weight: bold; color: #8338ec; display: inline-block; }}
.footer {{ margin-top: 32px; font-size: 13px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 16px; }}
</style>
</head>
<body>
<div class="container">
<h2>Transify Password Reset</h2>
<p>Hello,</p>
<p>You recently requested to reset your password for your Transify account.</p>
<p>Use the following one-time reset code to set a new password:</p>
<p><span class="code-box">{safe_token}</span></p>
<p>Or click the button below to open the recovery page:</p>
<p><a href="{safe_url}" class="btn">Reset Password</a></p>
<p><small style="color: #64748b;">If the button does not work, copy and paste this link into your browser:<br><a href="{safe_url}" style="color: #8338ec;">{safe_url}</a></small></p>
<p>This link and code will expire in 30 minutes. If you did not request this, please disregard this email.</p>
<div class="footer">
<p>&mdash; The Transify Team<br>Breaking Communication Barriers</p>
</div>
</div>
</body>
</html>"""

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        recipient_hash = hashlib.sha256(clean_to.encode("utf-8")).hexdigest()[:8]
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10.0)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=10.0)

            with server as s:
                if self.use_tls and not self.use_ssl:
                    s.starttls()
                if self.user and self.password:
                    s.login(self.user, self.password)
                s.send_message(msg)

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
        app_url = (base_url or get_canonical_app_url()).rstrip("/")
        reset_url = f"{app_url}/login#reset_token={reset_token}"

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

