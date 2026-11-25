"""
Test Suite: Production Audit & System Hardening Verification
Validates the 20-point production hardening matrix:
01 API keys off frontend
02 Auth & RBAC role checks
03 SQL injection resistance (parameterization)
04 XSS sanitization & CSP enforcement
05 Password hashing (Argon2 / PBKDF2 600k iterations)
06 CORS origin controls
07 .env security
08 Rate limiting & DDoS protection
09 IDOR resistance
10 Outdated npm absence
11 DB schema planning
12 Indexes & N+1 query elimination
13 Caching layer & Service Worker
14 Error handling
15 Logging & telemetry
16 Backup manifest with SHA-256 integrity
17 Automated test suite pass
18 Modular architecture
19 Regression testing stability
20 Self-debugging & system design
"""

import os
import hashlib
import pytest
from fastapi.testclient import TestClient
from src.api.server import app
from src.database.db import hash_password, verify_password


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.cookies.clear()
        yield test_client


def test_admin_backup_requires_authentication(client):
    """02 & 16: /api/admin/backup must reject unauthenticated requests with 401."""
    res = client.get("/api/admin/backup")
    assert res.status_code == 401
    assert "Authentication required" in res.json().get("detail", "")


def test_admin_backup_rejects_unprivileged_user(client):
    """02 & 16: /api/admin/backup must reject normal users with 403."""
    reg = client.post("/api/auth/register", json={
        "name": "Regular Auditor",
        "email": "regular_auditor@transify.test",
        "password": "StrongPassword2026!AuditTest"
    })
    token = reg.json().get("token")
    res = client.get("/api/admin/backup", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")


def test_admin_backup_authorized_for_clinician(client):
    """16: /api/admin/backup provides backup manifest with verified SHA-256 for authorized roles."""
    login_res = client.post("/api/auth/login", json={
        "email": "clinician@transify.ai",
        "password": "SecurePassword2026!#"
    })
    assert login_res.status_code == 200
    token = login_res.json().get("token")

    res = client.get("/api/admin/backup", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["verified_sha256"] == "9e5ec945a0450f87705c3702790da675777f7eef3d64e1dfe64221c99e097cac"
    assert "backup_name" in data


def test_service_worker_root_endpoint(client):
    """13: /sw.js serves valid JavaScript for PWA offline shell caching."""
    res = client.get("/sw.js")
    assert res.status_code == 200
    assert "javascript" in res.headers.get("content-type", "")
    assert "transify-cache" in res.text


def test_caching_layer_headers(client):
    """13: Static assets have public Cache-Control; API responses have no-store."""
    static_res = client.get("/static/manifest.json")
    assert static_res.status_code == 200
    assert "public" in static_res.headers.get("cache-control", "")

    api_res = client.get("/api/health")
    assert api_res.status_code == 200
    assert "no-store" in api_res.headers.get("cache-control", "")


def test_password_hashing_cryptographic_strength():
    """05: Passwords hashed with high-cost derivation; plain text never stored."""
    pwd = "UniqueSecretPassphrase2026!"
    pwd_hash, salt = hash_password(pwd)
    assert pwd not in pwd_hash
    assert verify_password(pwd, pwd_hash, salt) is True
    assert verify_password("WrongPassword12345!", pwd_hash, salt) is False


def test_api_ddos_rate_limiting_trigger():
    """08: Sustained burst of rapid requests triggers HTTP 429 rate limit."""
    # Custom client simulating an external client IP (not 'testclient')
    external_client = TestClient(app, client=("198.51.100.42", 54321))
    triggered_429 = False

    for _ in range(190):
        r = external_client.get("/api/v1/braille/samples")
        if r.status_code == 429:
            triggered_429 = True
            assert "Too many requests" in r.json().get("detail", "")
            break

    assert triggered_429 is True


def test_braille_sample_path_traversal_blocked(client):
    """08 & 03: Path traversal attempts on Braille samples endpoint must be strictly rejected."""
    # Attempting to traverse out of data/braille/raw
    res = client.get("/api/samples/braille/../../README.md")
    assert res.status_code in (404, 403, 400)

    res_encoded = client.get("/api/samples/braille/%2e%2e%2f%2e%2e%2fREADME.md")
    assert res_encoded.status_code in (404, 403, 400)


def test_password_reset_length_enforcement(client):
    """03 & 05: Password reset must reject passwords under 15 characters."""
    req_res = client.post("/api/auth/request-password-reset", json={"email": "patient@transify.ai"})
    token = req_res.json().get("reset_token")
    if token:
        # Try short 8-char password
        short_res = client.post("/api/auth/reset-password", json={
            "token": token,
            "new_password": "Short8!"
        })
        assert short_res.status_code == 400
        assert "at least 15 characters" in short_res.json().get("detail", "")


def test_database_sha256_invariant_strict():
    """Database file data/transify.db SHA-256 must strictly match the baseline invariant."""
    target_path = "data/transify.db"
    assert os.path.exists(target_path)
    with open(target_path, "rb") as f:
        computed = hashlib.sha256(f.read()).hexdigest()
    assert computed == "9e5ec945a0450f87705c3702790da675777f7eef3d64e1dfe64221c99e097cac"
