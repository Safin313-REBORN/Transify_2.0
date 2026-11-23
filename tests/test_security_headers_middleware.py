"""
Transify V3 — Security Headers Middleware Unit & Integration Tests.
Verifies that all HTTP responses (HTML, API, static files, and error responses)
emit required security headers:
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- X-Frame-Options: SAMEORIGIN
- Permissions-Policy: camera=(self), microphone=(self), geolocation=()
- Content-Security-Policy (CSP)
- Strict-Transport-Security (HSTS, conditional in production)
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.server import app

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def assert_core_security_headers(headers):
    assert headers.get("x-content-type-options") == "nosniff", "Missing or invalid X-Content-Type-Options"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin", "Missing or invalid Referrer-Policy"
    assert headers.get("x-frame-options") == "SAMEORIGIN", "Missing or invalid X-Frame-Options"
    assert "camera=(self)" in headers.get("permissions-policy", ""), "Permissions-Policy missing camera=(self)"
    assert "microphone=(self)" in headers.get("permissions-policy", ""), "Permissions-Policy missing microphone=(self)"
    assert "geolocation=()" in headers.get("permissions-policy", ""), "Permissions-Policy missing geolocation=()"
    csp = headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp, "CSP missing default-src"
    assert "script-src 'self' 'unsafe-inline'" in csp, "CSP missing script-src"
    assert "frame-ancestors 'self'" in csp, "CSP missing frame-ancestors"

def test_html_root_security_headers(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert_core_security_headers(response.headers)

def test_api_endpoint_security_headers(client: TestClient):
    response = client.post("/api/auth/login", json={"email": "nonexistent@transify.ai", "password": "wrong"})
    # Even on 401 or auth rejection, security headers must be emitted
    assert response.status_code in (400, 401, 422)
    assert_core_security_headers(response.headers)

def test_static_asset_security_headers(client: TestClient):
    response = client.get("/static/styles.css")
    assert response.status_code == 200
    assert_core_security_headers(response.headers)

def test_error_404_security_headers(client: TestClient):
    response = client.get("/nonexistent-endpoint-definitely-404")
    assert response.status_code == 404
    assert_core_security_headers(response.headers)

def test_conditional_hsts_behavior(monkeypatch, client: TestClient):
    # In non-production, HSTS is omitted to avoid local dev HTTPS lockouts
    monkeypatch.setenv("ENVIRONMENT", "development")
    res_dev = client.get("/")
    assert "strict-transport-security" not in res_dev.headers

    # In production, HSTS must be emitted
    monkeypatch.setenv("ENVIRONMENT", "production")
    res_prod = client.get("/")
    assert res_prod.headers.get("strict-transport-security") == "max-age=31536000; includeSubDomains"
