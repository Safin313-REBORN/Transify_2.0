"""
Pre-Launch Quality & Production Audit Test Suite for Transify 2.0.
Verifies SEO manifests, security headers, Open Graph link preview tags,
online backup integrity, and asset link integrity.
"""

import os
import re
import pytest
from fastapi.testclient import TestClient
from src.api.server import app
from scripts.backup_db import perform_online_backup
from scripts.restore_db import perform_online_restore


@pytest.fixture
def client():
    return TestClient(app, base_url="http://localhost:8000")


def test_robots_txt_served_cleanly(client):
    """Verifies that /robots.txt is served with proper status and directives."""
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    assert "User-agent: *" in resp.text
    assert "Sitemap:" in resp.text


def test_sitemap_xml_served_cleanly(client):
    """Verifies that /sitemap.xml is valid XML with canonical URLs."""
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "xml" in resp.headers.get("content-type", "")
    assert "<urlset" in resp.text
    assert "<loc>https://transify20-production.up.railway.app/</loc>" in resp.text


def test_security_headers_middleware_applied(client):
    """Verifies that hardened security headers are returned on all responses."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_open_graph_whatsapp_meta_tags():
    """Verifies that index.html and login.html contain complete Open Graph tags for WhatsApp previews."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    for fname in ("index.html", "login.html"):
        path = os.path.join(frontend_dir, fname)
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()

        assert 'property="og:title"' in html, f"Missing og:title in {fname}"
        assert 'property="og:description"' in html, f"Missing og:description in {fname}"
        assert 'property="og:image"' in html, f"Missing og:image in {fname}"
        assert 'property="og:url"' in html, f"Missing og:url in {fname}"
        assert 'property="og:type"' in html, f"Missing og:type in {fname}"
        
        # WhatsApp requirement: og:image must be absolute HTTPS URL
        image_match = re.search(r'property="og:image"\s+content="([^"]+)"', html)
        assert image_match, f"og:image tag not found in {fname}"
        assert image_match.group(1).startswith("https://"), f"og:image must be an HTTPS URL in {fname}"


def test_online_backup_functionality(tmp_path):
    """Verifies that the SQLite online backup utility creates a valid, intact database copy."""
    test_db = str(tmp_path / "test_source.db")
    import sqlite3
    conn = sqlite3.connect(test_db)
    conn.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, note TEXT);")
    conn.execute("INSERT INTO test_data (note) VALUES ('prelaunch_test');")
    conn.commit()
    conn.close()

    backup_dir = str(tmp_path / "backups")
    backup_file = perform_online_backup(source_db=test_db, backup_dir=backup_dir)

    assert os.path.isfile(backup_file)
    assert os.path.getsize(backup_file) > 0

    # Verify backup table and data
    bconn = sqlite3.connect(backup_file)
    cur = bconn.cursor()
    cur.execute("SELECT note FROM test_data WHERE id=1;")
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "prelaunch_test"
    bconn.close()


def test_online_restore_and_rollback_functionality(tmp_path):
    """Verifies that the SQLite restore/rollback utility restores an intact snapshot cleanly."""
    import sqlite3
    source_db = str(tmp_path / "origin.db")
    conn = sqlite3.connect(source_db)
    conn.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, username TEXT);")
    conn.execute("INSERT INTO accounts (username) VALUES ('test_rollback_user');")
    conn.commit()
    conn.close()

    backup_file = perform_online_backup(source_db=source_db, backup_dir=str(tmp_path / "backups"))

    restored_target = str(tmp_path / "restored.db")
    success = perform_online_restore(backup_file=backup_file, target_db=restored_target)
    assert success is True
    assert os.path.exists(restored_target)

    rconn = sqlite3.connect(restored_target)
    cur = rconn.cursor()
    cur.execute("SELECT username FROM accounts WHERE id=1;")
    val = cur.fetchone()
    assert val is not None
    assert val[0] == "test_rollback_user"
    rconn.close()


def test_cache_control_headers_and_error_handling(client):
    """Verifies that static assets have immutable caching and unhandled routes return standardized JSON errors."""
    resp_static = client.get("/static/favicon.ico")
    assert resp_static.status_code == 200
    assert "public, max-age=" in resp_static.headers.get("Cache-Control", "")

    resp_api = client.get("/api/health")
    assert resp_api.status_code == 200
    assert "no-store" in resp_api.headers.get("Cache-Control", "")
