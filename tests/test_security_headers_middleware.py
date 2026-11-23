"""
Transify V3 — Security Headers Middleware Unit, Integration & Negative Tests.
Verifies that all HTTP responses (HTML, API, static files, and error responses)
emit required production-grade security headers:
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- X-Frame-Options: DENY
- Permissions-Policy: camera=(self), microphone=(self), geolocation=()
- Content-Security-Policy (CSP) with frame-ancestors 'none', base-uri 'self', form-action 'self'
- Strict-Transport-Security (HSTS: max-age=31536000, conditional on verified HTTPS / production)
Includes negative security tests to ensure fail-closed behavior.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.server import app

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
    assert "script-src 'self' 'unsafe-inline'" in csp, "CSP missing script-src"
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

def test_error_404_security_headers(client: TestClient):
    response = client.get("/nonexistent-endpoint-definitely-404")
    assert response.status_code == 404
    assert_core_security_headers(response.headers)

def test_options_cors_preflight_security_headers(client: TestClient):
    response = client.options("/", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert response.status_code in (200, 204)
    assert_core_security_headers(response.headers)

def test_conditional_hsts_behavior(monkeypatch):
    # In non-production over plain HTTP, HSTS is omitted to avoid local dev HTTPS lockouts
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    monkeypatch.delenv("TRANSIFY_ENV", raising=False)

    dev_client = TestClient(app, base_url="http://localhost:8000")
    res_dev = dev_client.get("/")
    assert "strict-transport-security" not in res_dev.headers

    # In production over HTTPS or behind trusted HTTPS proxy, HSTS must be emitted
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://transify.ai,https://app.transify.ai")
    prod_client = TestClient(app, base_url="https://transify20-production.up.railway.app")
    res_prod = prod_client.get("/", headers={"x-forwarded-proto": "https"})
    assert res_prod.headers.get("strict-transport-security") == "max-age=31536000"

# --- Negative Security Tests (Phase 6) ---

def test_negative_untrusted_forwarded_proto_in_development(monkeypatch):
    """An untrusted client-supplied X-Forwarded-Proto header in dev must NOT trigger HSTS."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    monkeypatch.delenv("TRANSIFY_ENV", raising=False)

    dev_client = TestClient(app, base_url="http://localhost:8000")
    res = dev_client.get("/", headers={"x-forwarded-proto": "https"})
    assert "strict-transport-security" not in res.headers, "Untrusted X-Forwarded-Proto incorrectly triggered HSTS in dev!"

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
    # The response must not permit the malicious origin
    allow_origin = res.headers.get("access-control-allow-origin")
    assert allow_origin != "*", "CORS policy must not return wildcard '*' for untrusted origin!"
    assert allow_origin != "https://malicious-attacker.com", "CORS policy allowed unauthorized origin!"

def test_negative_production_cookie_security_attributes(monkeypatch):
    """In production, session cookies must strictly include HttpOnly, Secure, and SameSite."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://transify.ai,https://app.transify.ai")
    prod_client = TestClient(app, base_url="https://transify20-production.up.railway.app")
    
    # Negative test: register attempt
    res = prod_client.post("/api/auth/register", json={
        "name": "Test Cookie User",
        "email": "test-cookie@transify.ai",
        "password": "Password123!",
        "consent_terms": True
    })
    # If registered or rejected, verify cookie attributes if set-cookie header exists
    set_cookie = res.headers.get("set-cookie")
    if set_cookie:
        assert "httponly" in set_cookie.lower(), "Session cookie missing HttpOnly attribute!"
        assert "secure" in set_cookie.lower(), "Production session cookie missing Secure attribute!"
        assert "samesite=lax" in set_cookie.lower(), "Session cookie missing SameSite=Lax attribute!"
