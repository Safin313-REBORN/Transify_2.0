"""
Transify V3 — Security Headers Middleware Unit, Integration & Negative Tests.
RC1.4.5: Verifies that all HTTP responses (HTML, API, static files, error responses, and CORS preflights)
emit required production-grade security headers:
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- X-Frame-Options: DENY
- Permissions-Policy: camera=(self), microphone=(self), geolocation=()
- Content-Security-Policy (CSP): strict script-src 'self' (zero inline scripts), frame-ancestors 'none', base-uri 'self', form-action 'self'
- Strict-Transport-Security (HSTS: max-age=31536000, conditional on verified HTTPS / trusted proxy)
Includes real CORS preflight tests and negative security tests.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.server import app, is_trusted_proxy_host


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def assert_core_security_headers(headers):
    assert headers.get("x-content-type-options") == "nosniff", "Missing or invalid X-Content-Type-Options"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin", "Missing or invalid Referrer-Policy"
    assert headers.get("x-frame-options") in ("DENY", "SAMEORIGIN"), "Missing or invalid X-Frame-Options"
    assert "camera=(self)" in headers.get("permissions-policy", ""), "Permissions-Policy missing camera=(self)"
    assert "microphone=(self)" in headers.get("permissions-policy", ""), "Permissions-Policy missing microphone=(self)"
    assert "geolocation=()" in headers.get("permissions-policy", ""), "Permissions-Policy missing geolocation=()"
    csp = headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp, "CSP missing default-src"
    assert "script-src 'self'" in csp, "CSP missing script-src 'self'"
    # Strict CSP assertion: unsafe-inline must NOT be in script-src
    for part in csp.split(";"):
        part = part.strip()
        if part.startswith("script-src"):
            assert "'unsafe-inline'" not in part, f"script-src should be strict without 'unsafe-inline': {part}"
    assert "frame-ancestors 'none'" in csp or "frame-ancestors 'self'" in csp, "CSP missing frame-ancestors"
    assert "base-uri 'self'" in csp, "CSP missing base-uri"
    assert "form-action 'self'" in csp, "CSP missing form-action"


def test_html_root_security_headers(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert_core_security_headers(response.headers)
    assert response.headers.get("x-frame-options") == "DENY"
    assert "frame-ancestors 'none'" in response.headers.get("content-security-policy", "")


def test_api_endpoint_security_headers(client: TestClient):
    response = client.post("/api/auth/login", json={"email": "nonexistent@transify.ai", "password": "wrong"})
    assert response.status_code in (400, 401, 422, 429)
    assert_core_security_headers(response.headers)


def test_static_asset_security_headers(client: TestClient):
    response = client.get("/static/styles.css")
    assert response.status_code == 200
    assert_core_security_headers(response.headers)


def test_boot_js_asset_security_headers(client: TestClient):
    response = client.get("/static/boot.js")
    assert response.status_code == 200
    assert_core_security_headers(response.headers)


def test_error_404_security_headers(client: TestClient):
    response = client.get("/nonexistent-endpoint-definitely-404")
    assert response.status_code == 404
    assert_core_security_headers(response.headers)


def test_plain_options_health_security_headers(client: TestClient):
    """Plain OPTIONS request to /api/health returns 200 with Allow header and security headers."""
    response = client.options("/api/health")
    assert response.status_code == 200
    assert "GET" in response.headers.get("allow", "")
    assert_core_security_headers(response.headers)


def test_genuine_cors_preflight_login(monkeypatch):
    """Test genuine browser CORS preflight on /api/auth/login with approved origin."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://transify.ai,https://app.transify.ai,https://transify20-production.up.railway.app")
    prod_client = TestClient(app, base_url="https://transify20-production.up.railway.app")

    response = prod_client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://transify.ai",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"
        }
    )
    assert response.status_code in (200, 204), f"Preflight failed with status {response.status_code}"
    assert response.headers.get("access-control-allow-origin") == "https://transify.ai"
    assert response.headers.get("access-control-allow-credentials") == "true"
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "POST" in allow_methods
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "content-type" in allow_headers
    assert_core_security_headers(response.headers)


def test_cors_preflight_unapproved_origin_rejected(monkeypatch):
    """Test that preflight from an unapproved origin is not granted CORS access."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://transify.ai,https://app.transify.ai")
    prod_client = TestClient(app, base_url="https://transify20-production.up.railway.app")

    response = prod_client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://malicious-attacker.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type"
        }
    )
    assert response.headers.get("access-control-allow-origin") is None
    assert response.headers.get("access-control-allow-origin") != "*"


def test_cors_preflight_no_wildcard_with_credentials(monkeypatch):
    """Ensure wildcard origin '*' is NEVER returned when credentials are enabled."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://transify.ai")
    prod_client = TestClient(app, base_url="https://transify20-production.up.railway.app")

    response = prod_client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://transify.ai",
            "Access-Control-Request-Method": "POST"
        }
    )
    assert response.headers.get("access-control-allow-origin") != "*"
    assert response.headers.get("access-control-allow-origin") == "https://transify.ai"


def test_cors_preflight_does_not_execute_route_logic(monkeypatch):
    """Preflight OPTIONS request must be intercepted by middleware and not trigger route handlers."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://transify.ai")
    prod_client = TestClient(app, base_url="https://transify20-production.up.railway.app")

    # /api/auth/register expects body with name, email, etc. Preflight has no body.
    response = prod_client.options(
        "/api/auth/register",
        headers={
            "Origin": "https://transify.ai",
            "Access-Control-Request-Method": "POST"
        }
    )
    # Must succeed as preflight, not 422 Unprocessable Entity
    assert response.status_code in (200, 204)


def test_trusted_proxy_host_helper():
    """Verify is_trusted_proxy_host accurately discriminates private/loopback networks."""
    assert is_trusted_proxy_host("127.0.0.1") is True
    assert is_trusted_proxy_host("::1") is True
    assert is_trusted_proxy_host("localhost") is True
    assert is_trusted_proxy_host("testclient") is True
    assert is_trusted_proxy_host("10.0.5.12") is True
    assert is_trusted_proxy_host("172.18.0.4") is True
    assert is_trusted_proxy_host("192.168.1.1") is True
    assert is_trusted_proxy_host("8.8.8.8") is False
    assert is_trusted_proxy_host("1.1.1.1") is False
    assert is_trusted_proxy_host(None) is False
    assert is_trusted_proxy_host("invalid-ip") is False


def test_conditional_hsts_behavior(monkeypatch):
    # In non-production over plain HTTP, HSTS is omitted to avoid local dev HTTPS lockouts
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    monkeypatch.delenv("TRANSIFY_ENV", raising=False)

    dev_client = TestClient(app, base_url="http://localhost:8000")
    res_dev = dev_client.get("/")
    assert "strict-transport-security" not in res_dev.headers

    # In production over trusted HTTPS proxy, HSTS must be emitted
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://transify.ai,https://app.transify.ai")
    prod_client = TestClient(app, base_url="https://transify20-production.up.railway.app", client=("10.0.0.1", 54321))
    res_prod = prod_client.get("/", headers={"x-forwarded-proto": "https"})
    assert res_prod.headers.get("strict-transport-security") == "max-age=31536000"


def test_negative_untrusted_forwarded_proto_in_development(monkeypatch):
    """An untrusted client-supplied X-Forwarded-Proto header in dev must NOT trigger HSTS."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    monkeypatch.delenv("TRANSIFY_ENV", raising=False)

    dev_client = TestClient(app, base_url="http://localhost:8000")
    res = dev_client.get("/", headers={"x-forwarded-proto": "https"})
    assert "strict-transport-security" not in res.headers, "Untrusted X-Forwarded-Proto incorrectly triggered HSTS in dev!"


def test_negative_untrusted_ip_forwarded_proto_in_production(monkeypatch):
    """In production, X-Forwarded-Proto from an untrusted public client IP must NOT trigger HSTS."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://transify.ai")
    prod_client = TestClient(app, base_url="http://transify20-production.up.railway.app", client=("8.8.8.8", 12345))
    res = prod_client.get("/", headers={"x-forwarded-proto": "https"})
    assert "strict-transport-security" not in res.headers, "Untrusted external client IP triggered HSTS via forwarded header!"


def test_negative_iframe_clickjacking_blocked(client: TestClient):
    """X-Frame-Options: DENY and frame-ancestors 'none' must be present to block iframe embedding."""
    response = client.get("/")
    assert response.headers.get("x-frame-options") == "DENY"
    csp = response.headers.get("content-security-policy", "")
    assert "frame-ancestors 'none'" in csp


def test_negative_mime_sniffing_disabled(client: TestClient):
    """MIME sniffing must be unconditionally disabled across all content types."""
    for path in ["/", "/static/styles.css", "/api/health", "/nonexistent"]:
        res = client.get(path)
        assert res.headers.get("x-content-type-options") == "nosniff"


def test_negative_unauthorized_cors_origin_rejected(monkeypatch):
    """In production, unknown arbitrary origins must NOT receive permissive Access-Control-Allow-Origin."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://transify.ai,https://app.transify.ai")
    prod_client = TestClient(app, base_url="https://transify20-production.up.railway.app")
    res = prod_client.options(
        "/api/health",
        headers={
            "Origin": "https://malicious-attacker.com",
            "Access-Control-Request-Method": "GET"
        }
    )
    allow_origin = res.headers.get("access-control-allow-origin")
    assert allow_origin != "*", "CORS policy must not return wildcard '*' for untrusted origin!"
    assert allow_origin != "https://malicious-attacker.com", "CORS policy allowed unauthorized origin!"


def test_negative_production_cookie_security_attributes(monkeypatch):
    """In production, session cookies must strictly include HttpOnly, Secure, and SameSite."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://transify.ai,https://app.transify.ai")
    prod_client = TestClient(app, base_url="https://transify20-production.up.railway.app")

    res = prod_client.post("/api/auth/register", json={
        "name": "Test Cookie User",
        "email": "test-cookie@transify.ai",
        "password": "Password123!",
        "consent_terms": True
    })
    set_cookie = res.headers.get("set-cookie")
    if set_cookie:
        assert "httponly" in set_cookie.lower(), "Session cookie missing HttpOnly attribute!"
        assert "secure" in set_cookie.lower(), "Production session cookie missing Secure attribute!"
        assert "samesite=lax" in set_cookie.lower(), "Session cookie missing SameSite=Lax attribute!"
