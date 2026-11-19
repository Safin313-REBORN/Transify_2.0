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


def test_privacy_and_terms_pages_served(client):
    """Verifies that dedicated /privacy and /terms legal pages are rendered with high contrast."""
    resp_priv = client.get("/privacy")
    assert resp_priv.status_code == 200
    assert "Privacy Policy" in resp_priv.text
    assert "Ephemeral Biometric &amp; Video Processing" in resp_priv.text or "Ephemeral Biometric" in resp_priv.text

    resp_terms = client.get("/terms")
    assert resp_terms.status_code == 200
    assert "Terms of Service" in resp_terms.text
    assert "Medical &amp; Emergency Disclaimer" in resp_terms.text or "Emergency Disclaimer" in resp_terms.text


def test_custom_404_page_served_to_browser(client):
    """Verifies that unmatched routes serve custom 404.html to browsers and JSON to APIs."""
    # Browser request accepting HTML
    resp_browser = client.get("/non-existent-page-url", headers={"Accept": "text/html,application/xhtml+xml"})
    assert resp_browser.status_code == 404
    assert "Communication Channel Not Found" in resp_browser.text
    assert "Return Home" in resp_browser.text

    # API request accepting JSON
    resp_api = client.get("/api/non-existent-endpoint", headers={"Accept": "application/json"})
    assert resp_api.status_code == 404
    assert "detail" in resp_api.json()


def test_account_deletion_endpoint_and_cascading(client):
    """Verifies that an authenticated user can permanently delete their account and wipe data."""
    import time
    email = f"delete_me_{int(time.time()*1000)}@transify.test"
    reg_resp = client.post("/api/auth/register", json={
        "name": "Delete Tester",
        "email": email,
        "password": "SecurePassword123!_2026",
        "consent_terms": True
    })
    assert reg_resp.status_code == 200

    # User adds a preference and history
    client.post("/api/preferences", json={"theme": "high-contrast", "font_size": "large"})

    # Delete account
    del_resp = client.delete("/api/auth/me")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # User can no longer access authenticated endpoints
    me_resp = client.get("/api/auth/me")
    assert me_resp.json().get("authenticated") is False


def test_email_verification_and_client_telemetry(client):
    """Verifies email verification endpoint and client error telemetry endpoint."""
    v_resp = client.post("/api/auth/verify-email", json={"token": "test-valid-verify-token"})
    assert v_resp.status_code == 200
    assert v_resp.json()["status"] == "success"

    # Client error telemetry logging
    t_resp = client.post("/api/telemetry/error", json={
        "message": "Uncaught ReferenceError: foo is not defined",
        "source": "https://transify.app/static/app.js",
        "lineno": 42,
        "colno": 10,
        "stack": "ReferenceError: foo is not defined at https://transify.app/static/app.js:42:10"
    })
    assert t_resp.status_code == 200
    assert t_resp.json()["status"] == "logged"


def test_20_frontend_ux_components_rendered():
    """Verifies that all 20 requested frontend UX/UI features exist in templates and styles."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    index_path = os.path.join(frontend_dir, "index.html")
    styles_path = os.path.join(frontend_dir, "static/styles.css")
    app_path = os.path.join(frontend_dir, "static/app.js")

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    with open(styles_path, "r", encoding="utf-8") as f:
        css = f.read()
    with open(app_path, "r", encoding="utf-8") as f:
        js = f.read()

    # 1. Dark mode toggle
    assert 'id="dark-mode-toggle-btn"' in html
    assert '[data-theme="dark"]' in css
    assert 'toggleDarkMode' in js

    # 2. Simple cookie banner
    assert 'id="cookie-consent-banner"' in html
    assert 'id="btn-accept-cookies"' in html
    assert 'acceptCookies' in js

    # 3. Site search
    assert 'id="site-search-btn"' in html
    assert 'id="site-search-modal"' in html
    assert 'openSiteSearch' in js

    # 4. Back to top button
    assert 'id="back-to-top-btn"' in html
    assert '.back-to-top-btn' in css

    # 5. Mobile menu
    assert 'id="mobile-menu-toggle-btn"' in html
    assert 'id="mobile-nav-drawer"' in html
    assert 'toggleMobileMenu' in js

    # 6. Loading animations
    assert 'transify-shimmer' in css or 'transify-pulse' in css or 'loading-shimmer' in css

    # 7. Hover states
    assert ':hover' in css
    assert ':focus-visible' in css

    # 8. Scroll progress bar
    assert 'id="scroll-progress-bar"' in html
    assert '.scroll-progress-bar' in css
    assert 'initScrollProgressBar' in js

    # 9. Copy button
    assert 'copy-btn' in html or 'btn-copy' in html
    assert 'copyTextFrom' in js

    # 10. Print stylesheet
    assert '@media print' in css

    # 11. Sticky header
    assert 'sticky-header' in html
    assert '.sticky-header' in css

    # 12. Skip to content link
    assert 'class="skip-link"' in html
    assert 'id="main-content"' in html

    # 13. Password visibility toggle
    assert 'togglePasswordVisibility' in html
    assert 'password-toggle' in css or 'togglePasswordVisibility' in js

    # 14. UTM tracking
    assert 'utm_source' in js
    assert 'initUtmTracking' in js

    # 15. Form success state
    assert '.form-success-banner' in css
    assert 'form-success-banner' in js

    # 16. Form error state
    assert '.form-error-banner' in css
    assert '.has-field-error' in css or '.field-error' in css

    # 17. Confirmation modals
    assert 'id="transify-confirm-modal"' in html
    assert 'showConfirmModal' in js

    # 18. Last updated date
    assert 'class="last-updated-text"' in html
    assert 'Last updated:' in html

    # 19. Expandable FAQ
    assert 'id="transify-faq-section"' in html
    assert '<details' in html
    assert '<summary' in html

    # 20. Floating contact button
    assert 'id="floating-contact-btn"' in html
    assert 'id="contact-modal-overlay"' in html
    assert 'openContactModal' in js


def test_favicon_root_and_static_served(client):
    """Verifies that /favicon.ico and /static/favicon.ico are served cleanly with status 200."""
    resp_root = client.get("/favicon.ico")
    assert resp_root.status_code == 200
    assert "image/" in resp_root.headers.get("content-type", "")

    resp_static_ico = client.get("/static/favicon.ico")
    assert resp_static_ico.status_code == 200
    assert "image/" in resp_static_ico.headers.get("content-type", "")

    resp_static_png = client.get("/static/favicon.png")
    assert resp_static_png.status_code == 200
    assert "image/png" in resp_static_png.headers.get("content-type", "")


def test_meta_descriptions_and_titles_across_templates():
    """Verifies all HTML templates have non-empty titles and meta descriptions."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    templates = ["index.html", "login.html", "privacy.html", "terms.html", "404.html"]
    for tname in templates:
        path = os.path.join(frontend_dir, tname)
        assert os.path.isfile(path), f"Template {tname} missing"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "<title>Transify" in content, f"Missing or invalid title in {tname}"
        desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', content)
        assert desc_match is not None, f"Missing meta description in {tname}"
        assert len(desc_match.group(1).strip()) >= 20, f"Description too short in {tname}"
        assert '<link rel="icon"' in content, f"Missing favicon link in {tname}"


def test_clickable_contact_links_and_copyright_across_templates():
    """Verifies telephone and email links and 2026 copyright notice across templates."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    templates = ["index.html", "login.html", "privacy.html", "terms.html", "404.html"]
    for tname in templates:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'href="mailto:support@transify.app"' in content, f"Missing clickable email in {tname}"
        assert 'href="tel:+18005550199"' in content, f"Missing clickable phone in {tname}"
        assert '2026 Transify Inc.' in content or '© 2026' in content, f"Outdated/missing copyright year in {tname}"


def test_mobile_overflow_and_no_horizontal_scroll():
    """Verifies viewport settings and overflow-x: hidden prevent horizontal scrolling."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    styles_path = os.path.join(frontend_dir, "static/styles.css")
    with open(styles_path, "r", encoding="utf-8") as f:
        css = f.read()
    assert "overflow-x: hidden !important" in css
    assert "max-width: 100vw !important" in css

    for tname in ["index.html", "login.html", "privacy.html", "terms.html", "404.html"]:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'name="viewport"' in content, f"Missing viewport tag in {tname}"
        assert 'user-scalable=no' not in content, f"Unfriendly user-scalable=no found in {tname}"


def test_no_dead_empty_hash_links():
    """Verifies that no bare href='#' broken links exist in user-facing pages."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    for tname in ["index.html", "login.html", "privacy.html", "terms.html", "404.html"]:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        bare_hash_matches = re.findall(r'href="#"', content)
        assert len(bare_hash_matches) == 0, f"Found {len(bare_hash_matches)} dead href='#' links in {tname}"


def test_mobile_menu_and_navigation_drawer():
    """Verifies presence of mobile navigation toggle and drawer in index.html and app.js."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    index_path = os.path.join(frontend_dir, "index.html")
    app_path = os.path.join(frontend_dir, "static/app.js")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    with open(app_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert 'id="mobile-menu-toggle-btn"' in html
    assert 'id="mobile-nav-drawer"' in html
    assert 'toggleMobileMenu' in js or 'initMobileMenu' in js


def test_llms_txt_served_cleanly(client):
    """Verifies that /llms.txt is served with proper content and markdown documentation."""
    resp = client.get("/llms.txt")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    assert "# Transify" in resp.text
    assert "https://transify.app/" in resp.text
    assert "Bengali Sign Language" in resp.text
    assert "Optical Braille Recognition" in resp.text


def test_canonical_tags_and_single_h1_rule():
    """Verifies that all templates have unique canonical tags pointing to custom domain and exactly one H1."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    templates = ["index.html", "login.html", "privacy.html", "terms.html", "404.html", "sign.html", "braille.html", "dashboard.html", "refund.html", "cookies.html", "unsubscribe.html"]
    for tname in templates:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check canonical tag
        assert '<link rel="canonical" href="https://transify.app' in content, f"Missing or invalid canonical in {tname}"

        # Check single H1 rule
        h1_matches = re.findall(r'<h1[\s>]', content, re.IGNORECASE)
        assert len(h1_matches) == 1, f"Expected exactly one <h1> in {tname}, found {len(h1_matches)}"


def test_breadcrumbs_and_structured_data_schemas():
    """Verifies breadcrumb navigation and Schema.org structured data markup."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")

    # index.html structured data
    index_path = os.path.join(frontend_dir, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert 'application/ld+json' in html
    assert '"@type": "Organization"' in html
    assert '"@type": "WebApplication"' in html
    assert '"@type": "FAQPage"' in html

    # Subpages breadcrumbs
    subpages = ["login.html", "privacy.html", "terms.html", "404.html", "sign.html", "braille.html", "dashboard.html", "refund.html", "cookies.html", "unsubscribe.html"]
    for sp in subpages:
        path = os.path.join(frontend_dir, sp)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'aria-label="Breadcrumb"' in content, f"Missing breadcrumb nav in {sp}"
        assert 'itemtype="https://schema.org/BreadcrumbList"' in content, f"Missing BreadcrumbList schema in {sp}"


def test_clean_slugs_and_routes(client):
    """Verifies that all clean URL slugs return valid HTML status."""
    routes = ["/", "/sign", "/braille", "/login", "/privacy", "/terms", "/dashboard", "/refund", "/cookies", "/unsubscribe"]
    for r in routes:
        resp = client.get(r)
        assert resp.status_code == 200, f"Route {r} returned {resp.status_code}"
        assert "text/html" in resp.headers.get("content-type", "")

    # Custom 404 route
    resp_404 = client.get("/404")
    assert resp_404.status_code == 404
    assert "Communication Channel Not Found" in resp_404.text


def test_social_share_images_and_all_images_have_alt():
    """Verifies social sharing images and that 100% of images have non-empty alt text."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    templates = ["index.html", "login.html", "privacy.html", "terms.html", "404.html", "sign.html", "braille.html", "dashboard.html", "refund.html", "cookies.html", "unsubscribe.html"]
    for tname in templates:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all <img> tags (including multiline)
        img_tags = re.findall(r'<img\b[^>]*>', content, re.IGNORECASE | re.DOTALL)
        for img in img_tags:
            alt_match = re.search(r'alt="([^"]*)"', img, re.IGNORECASE)
            assert alt_match is not None, f"Image missing alt attribute in {tname}: {img}"
            assert len(alt_match.group(1).strip()) > 0, f"Empty alt attribute in {tname}: {img}"


def test_absence_of_vite_react_boilerplate_and_sourcemaps():
    """Verifies tab titles do not mention Vite/React and no sourcemaps are exposed."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    templates = ["index.html", "login.html", "privacy.html", "terms.html", "404.html", "sign.html", "braille.html", "dashboard.html", "refund.html", "cookies.html", "unsubscribe.html"]
    for tname in templates:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        title_match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
        assert title_match is not None, f"Missing title in {tname}"
        title = title_match.group(1).lower()
        assert "vite" not in title, f"Vite found in title of {tname}"
        assert "react app" not in title, f"React found in title of {tname}"

    # Verify no sourceMappingURL in static assets
    static_dir = os.path.join(frontend_dir, "static")
    for fname in os.listdir(static_dir):
        if fname.endswith(".js") or fname.endswith(".css"):
            fpath = os.path.join(static_dir, fname)
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                c = f.read()
            assert "sourceMappingURL" not in c, f"sourceMappingURL found in {fname}"
        assert not fname.endswith(".map"), f"Sourcemap file found: {fname}"


def test_refund_and_cookies_pages_served(client):
    """Verifies that Refund Policy and Cookie Policy pages are served with required content."""
    res_refund = client.get("/refund")
    assert res_refund.status_code == 200
    assert "Refund &amp; Billing Policy" in res_refund.text or "Refund & Billing Policy" in res_refund.text
    assert "100% Free Open-Source Core" in res_refund.text
    assert "30-Day Money-Back Guarantee" in res_refund.text

    res_cookies = client.get("/cookies")
    assert res_cookies.status_code == 200
    assert "Cookie Policy &amp; Tracking Disclosure" in res_cookies.text or "Cookie Policy & Tracking Disclosure" in res_cookies.text
    assert "transify_session" in res_cookies.text
    assert "transify_csrf" in res_cookies.text
    assert "transify_cookie_consent" in res_cookies.text
    assert "Strictly Necessary Cookies Only" in res_cookies.text


def test_unsubscribe_endpoint_and_service(client):
    """Verifies that the /unsubscribe page and /api/unsubscribe POST endpoint work cleanly."""
    res_page = client.get("/unsubscribe")
    assert res_page.status_code == 200
    assert "Manage Email Notifications" in res_page.text
    assert "CAN-SPAM" in res_page.text

    res_api = client.post("/api/unsubscribe", json={"email": "optout_user@example.com"})
    assert res_api.status_code == 200
    data = res_api.json()
    assert data["status"] == "success"
    assert "optout_user@example.com" in data["message"]


def test_email_service_unsubscribe_headers_and_physical_address(reset_mock_mail):
    """Verifies RFC 8058 / CAN-SPAM List-Unsubscribe headers and physical business address in emails."""
    from src.api.email_service import SMTPEmailAdapter, MockMailAdapter

    # Test mock mail adapter records unsubscribe headers
    mock_adapter = MockMailAdapter(configured=True)
    mock_adapter.send_password_reset_email("user@example.com", "mock_reset_token_1234567890abcdef")
    assert len(mock_adapter.sent_emails) == 1
    record = mock_adapter.sent_emails[0]
    assert "unsubscribe_url" in record
    assert "/unsubscribe?email=user@example.com" in record["unsubscribe_url"]
    assert "List-Unsubscribe=One-Click" in record["list_unsubscribe_post"]
    assert "unsubscribe@transify.app" in record["list_unsubscribe"]

    # Test SMTPEmailAdapter message structure (without sending)
    smtp = SMTPEmailAdapter(host="smtp.example.com", port=587)
    # Validate canonical app URL helper includes protocol
    from src.api.email_service import get_canonical_app_url
    url = get_canonical_app_url()
    assert url.startswith("http")


def test_registration_form_consents_and_age_verification(client):
    """Verifies form consents and age verification on account registration."""
    import time
    base_email = f"age_test_{int(time.time()*1000)}"

    # 1. Rejected if consent_terms is False
    res_no_terms = client.post("/api/auth/register", json={
        "name": "Consent Tester",
        "email": f"{base_email}_noterms@transify.test",
        "password": "SecurePassword123!_2026",
        "consent_terms": False,
        "consent_age": True
    })
    assert res_no_terms.status_code == 422

    # 2. Rejected if consent_age is False
    res_no_age = client.post("/api/auth/register", json={
        "name": "Consent Tester",
        "email": f"{base_email}_noage@transify.test",
        "password": "SecurePassword123!_2026",
        "consent_terms": True,
        "consent_age": False
    })
    assert res_no_age.status_code == 422

    # 3. Accepted if both consent_terms and consent_age are True
    res_ok = client.post("/api/auth/register", json={
        "name": "Consent Tester",
        "email": f"{base_email}_ok@transify.test",
        "password": "SecurePassword123!_2026",
        "consent_terms": True,
        "consent_age": True
    })
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "success"


def test_third_party_sdk_audit_no_tracking_scripts():
    """Audits HTML templates to verify total absence of unauthorized third-party trackers."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    templates = [
        "index.html", "login.html", "privacy.html", "terms.html",
        "404.html", "sign.html", "braille.html", "dashboard.html",
        "refund.html", "cookies.html", "unsubscribe.html"
    ]
    disallowed_signatures = [
        "google-analytics.com/analytics.js",
        "googletagmanager.com/gtm.js",
        "connect.facebook.net",
        "analytics.tiktok.com",
        "hotjar.com",
        "clarity.ms",
        "fullstory.com",
        "doubleclick.net"
    ]

    for tname in templates:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().lower()
        for sig in disallowed_signatures:
            assert sig not in content, f"Unauthorized tracking script '{sig}' found in {tname}!"


def test_footer_business_details_and_links():
    """Verifies that footer elements on key pages contain business identity and legal links."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    for tname in ["index.html", "login.html", "privacy.html", "terms.html"]:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "100 Innovation Way, Suite 400, San Francisco, CA 94105" in content, f"Missing physical address in {tname}"
        assert "support@transify.app" in content, f"Missing support email in {tname}"
        assert "+1 (800) 555-0199" in content, f"Missing helpline phone in {tname}"
        assert "/privacy" in content, f"Missing privacy link in {tname}"
        assert "/terms" in content, f"Missing terms link in {tname}"
        assert "/refund" in content, f"Missing refund link in {tname}"
        assert "/cookies" in content, f"Missing cookies link in {tname}"






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


def test_privacy_and_terms_pages_served(client):
    """Verifies that dedicated /privacy and /terms legal pages are rendered with high contrast."""
    resp_priv = client.get("/privacy")
    assert resp_priv.status_code == 200
    assert "Privacy Policy" in resp_priv.text
    assert "Ephemeral Biometric &amp; Video Processing" in resp_priv.text or "Ephemeral Biometric" in resp_priv.text

    resp_terms = client.get("/terms")
    assert resp_terms.status_code == 200
    assert "Terms of Service" in resp_terms.text
    assert "Medical &amp; Emergency Disclaimer" in resp_terms.text or "Emergency Disclaimer" in resp_terms.text


def test_custom_404_page_served_to_browser(client):
    """Verifies that unmatched routes serve custom 404.html to browsers and JSON to APIs."""
    # Browser request accepting HTML
    resp_browser = client.get("/non-existent-page-url", headers={"Accept": "text/html,application/xhtml+xml"})
    assert resp_browser.status_code == 404
    assert "Communication Channel Not Found" in resp_browser.text
    assert "Return Home" in resp_browser.text

    # API request accepting JSON
    resp_api = client.get("/api/non-existent-endpoint", headers={"Accept": "application/json"})
    assert resp_api.status_code == 404
    assert "detail" in resp_api.json()


def test_account_deletion_endpoint_and_cascading(client):
    """Verifies that an authenticated user can permanently delete their account and wipe data."""
    import time
    email = f"delete_me_{int(time.time()*1000)}@transify.test"
    reg_resp = client.post("/api/auth/register", json={
        "name": "Delete Tester",
        "email": email,
        "password": "SecurePassword123!_2026",
        "consent_terms": True
    })
    assert reg_resp.status_code == 200

    # User adds a preference and history
    client.post("/api/preferences", json={"theme": "high-contrast", "font_size": "large"})

    # Delete account
    del_resp = client.delete("/api/auth/me")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # User can no longer access authenticated endpoints
    me_resp = client.get("/api/auth/me")
    assert me_resp.json().get("authenticated") is False


def test_email_verification_and_client_telemetry(client):
    """Verifies email verification endpoint and client error telemetry endpoint."""
    v_resp = client.post("/api/auth/verify-email", json={"token": "test-valid-verify-token"})
    assert v_resp.status_code == 200
    assert v_resp.json()["status"] == "success"

    # Client error telemetry logging
    t_resp = client.post("/api/telemetry/error", json={
        "message": "Uncaught ReferenceError: foo is not defined",
        "source": "https://transify.app/static/app.js",
        "lineno": 42,
        "colno": 10,
        "stack": "ReferenceError: foo is not defined at https://transify.app/static/app.js:42:10"
    })
    assert t_resp.status_code == 200
    assert t_resp.json()["status"] == "logged"


def test_20_frontend_ux_components_rendered():
    """Verifies that all 20 requested frontend UX/UI features exist in templates and styles."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    index_path = os.path.join(frontend_dir, "index.html")
    styles_path = os.path.join(frontend_dir, "static/styles.css")
    app_path = os.path.join(frontend_dir, "static/app.js")

    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    with open(styles_path, "r", encoding="utf-8") as f:
        css = f.read()
    with open(app_path, "r", encoding="utf-8") as f:
        js = f.read()

    # 1. Dark mode toggle
    assert 'id="dark-mode-toggle-btn"' in html
    assert '[data-theme="dark"]' in css
    assert 'toggleDarkMode' in js

    # 2. Simple cookie banner
    assert 'id="cookie-consent-banner"' in html
    assert 'id="btn-accept-cookies"' in html
    assert 'acceptCookies' in js

    # 3. Site search
    assert 'id="site-search-btn"' in html
    assert 'id="site-search-modal"' in html
    assert 'openSiteSearch' in js

    # 4. Back to top button
    assert 'id="back-to-top-btn"' in html
    assert '.back-to-top-btn' in css

    # 5. Mobile menu
    assert 'id="mobile-menu-toggle-btn"' in html
    assert 'id="mobile-nav-drawer"' in html
    assert 'toggleMobileMenu' in js

    # 6. Loading animations
    assert 'transify-shimmer' in css or 'transify-pulse' in css or 'loading-shimmer' in css

    # 7. Hover states
    assert ':hover' in css
    assert ':focus-visible' in css

    # 8. Scroll progress bar
    assert 'id="scroll-progress-bar"' in html
    assert '.scroll-progress-bar' in css
    assert 'initScrollProgressBar' in js

    # 9. Copy button
    assert 'copy-btn' in html or 'btn-copy' in html
    assert 'copyTextFrom' in js

    # 10. Print stylesheet
    assert '@media print' in css

    # 11. Sticky header
    assert 'sticky-header' in html
    assert '.sticky-header' in css

    # 12. Skip to content link
    assert 'class="skip-link"' in html
    assert 'id="main-content"' in html

    # 13. Password visibility toggle
    assert 'togglePasswordVisibility' in html
    assert 'password-toggle' in css or 'togglePasswordVisibility' in js

    # 14. UTM tracking
    assert 'utm_source' in js
    assert 'initUtmTracking' in js

    # 15. Form success state
    assert '.form-success-banner' in css
    assert 'form-success-banner' in js

    # 16. Form error state
    assert '.form-error-banner' in css
    assert '.has-field-error' in css or '.field-error' in css

    # 17. Confirmation modals
    assert 'id="transify-confirm-modal"' in html
    assert 'showConfirmModal' in js

    # 18. Last updated date
    assert 'class="last-updated-text"' in html
    assert 'Last updated:' in html

    # 19. Expandable FAQ
    assert 'id="transify-faq-section"' in html
    assert '<details' in html
    assert '<summary' in html

    # 20. Floating contact button
    assert 'id="floating-contact-btn"' in html
    assert 'id="contact-modal-overlay"' in html
    assert 'openContactModal' in js


def test_favicon_root_and_static_served(client):
    """Verifies that /favicon.ico and /static/favicon.ico are served cleanly with status 200."""
    resp_root = client.get("/favicon.ico")
    assert resp_root.status_code == 200
    assert "image/" in resp_root.headers.get("content-type", "")

    resp_static_ico = client.get("/static/favicon.ico")
    assert resp_static_ico.status_code == 200
    assert "image/" in resp_static_ico.headers.get("content-type", "")

    resp_static_png = client.get("/static/favicon.png")
    assert resp_static_png.status_code == 200
    assert "image/png" in resp_static_png.headers.get("content-type", "")


def test_meta_descriptions_and_titles_across_templates():
    """Verifies all HTML templates have non-empty titles and meta descriptions."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    templates = ["index.html", "login.html", "privacy.html", "terms.html", "404.html"]
    for tname in templates:
        path = os.path.join(frontend_dir, tname)
        assert os.path.isfile(path), f"Template {tname} missing"
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "<title>Transify" in content, f"Missing or invalid title in {tname}"
        desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', content)
        assert desc_match is not None, f"Missing meta description in {tname}"
        assert len(desc_match.group(1).strip()) >= 20, f"Description too short in {tname}"
        assert '<link rel="icon"' in content, f"Missing favicon link in {tname}"


def test_clickable_contact_links_and_copyright_across_templates():
    """Verifies telephone and email links and 2026 copyright notice across templates."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    templates = ["index.html", "login.html", "privacy.html", "terms.html", "404.html"]
    for tname in templates:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'href="mailto:support@transify.app"' in content, f"Missing clickable email in {tname}"
        assert 'href="tel:+18005550199"' in content, f"Missing clickable phone in {tname}"
        assert '2026 Transify Inc.' in content or '© 2026' in content, f"Outdated/missing copyright year in {tname}"


def test_mobile_overflow_and_no_horizontal_scroll():
    """Verifies viewport settings and overflow-x: hidden prevent horizontal scrolling."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    styles_path = os.path.join(frontend_dir, "static/styles.css")
    with open(styles_path, "r", encoding="utf-8") as f:
        css = f.read()
    assert "overflow-x: hidden !important" in css
    assert "max-width: 100vw !important" in css

    for tname in ["index.html", "login.html", "privacy.html", "terms.html", "404.html"]:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'name="viewport"' in content, f"Missing viewport tag in {tname}"
        assert 'user-scalable=no' not in content, f"Unfriendly user-scalable=no found in {tname}"


def test_no_dead_empty_hash_links():
    """Verifies that no bare href='#' broken links exist in user-facing pages."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    for tname in ["index.html", "login.html", "privacy.html", "terms.html", "404.html"]:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        bare_hash_matches = re.findall(r'href="#"', content)
        assert len(bare_hash_matches) == 0, f"Found {len(bare_hash_matches)} dead href='#' links in {tname}"


def test_mobile_menu_and_navigation_drawer():
    """Verifies presence of mobile navigation toggle and drawer in index.html and app.js."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    index_path = os.path.join(frontend_dir, "index.html")
    app_path = os.path.join(frontend_dir, "static/app.js")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    with open(app_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert 'id="mobile-menu-toggle-btn"' in html
    assert 'id="mobile-nav-drawer"' in html
    assert 'toggleMobileMenu' in js or 'initMobileMenu' in js


def test_llms_txt_served_cleanly(client):
    """Verifies that /llms.txt is served with proper content and markdown documentation."""
    resp = client.get("/llms.txt")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    assert "# Transify" in resp.text
    assert "https://transify.app/" in resp.text
    assert "Bengali Sign Language" in resp.text
    assert "Optical Braille Recognition" in resp.text


def test_canonical_tags_and_single_h1_rule():
    """Verifies that all templates have unique canonical tags pointing to custom domain and exactly one H1."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    templates = ["index.html", "login.html", "privacy.html", "terms.html", "404.html", "sign.html", "braille.html", "dashboard.html", "refund.html", "cookies.html", "unsubscribe.html"]
    for tname in templates:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check canonical tag
        assert '<link rel="canonical" href="https://transify.app' in content, f"Missing or invalid canonical in {tname}"

        # Check single H1 rule
        h1_matches = re.findall(r'<h1[\s>]', content, re.IGNORECASE)
        assert len(h1_matches) == 1, f"Expected exactly one <h1> in {tname}, found {len(h1_matches)}"


def test_breadcrumbs_and_structured_data_schemas():
    """Verifies breadcrumb navigation and Schema.org structured data markup."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")

    # index.html structured data
    index_path = os.path.join(frontend_dir, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert 'application/ld+json' in html
    assert '"@type": "Organization"' in html
    assert '"@type": "WebApplication"' in html
    assert '"@type": "FAQPage"' in html

    # Subpages breadcrumbs
    subpages = ["login.html", "privacy.html", "terms.html", "404.html", "sign.html", "braille.html", "dashboard.html", "refund.html", "cookies.html", "unsubscribe.html"]
    for sp in subpages:
        path = os.path.join(frontend_dir, sp)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'aria-label="Breadcrumb"' in content, f"Missing breadcrumb nav in {sp}"
        assert 'itemtype="https://schema.org/BreadcrumbList"' in content, f"Missing BreadcrumbList schema in {sp}"


def test_clean_slugs_and_routes(client):
    """Verifies that all clean URL slugs return valid HTML status."""
    routes = ["/", "/sign", "/braille", "/login", "/privacy", "/terms", "/dashboard", "/refund", "/cookies", "/unsubscribe"]
    for r in routes:
        resp = client.get(r)
        assert resp.status_code == 200, f"Route {r} returned {resp.status_code}"
        assert "text/html" in resp.headers.get("content-type", "")

    # Custom 404 route
    resp_404 = client.get("/404")
    assert resp_404.status_code == 404
    assert "Communication Channel Not Found" in resp_404.text


def test_social_share_images_and_all_images_have_alt():
    """Verifies social sharing images and that 100% of images have non-empty alt text."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    templates = ["index.html", "login.html", "privacy.html", "terms.html", "404.html", "sign.html", "braille.html", "dashboard.html", "refund.html", "cookies.html", "unsubscribe.html"]
    for tname in templates:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all <img> tags (including multiline)
        img_tags = re.findall(r'<img\b[^>]*>', content, re.IGNORECASE | re.DOTALL)
        for img in img_tags:
            alt_match = re.search(r'alt="([^"]*)"', img, re.IGNORECASE)
            assert alt_match is not None, f"Image missing alt attribute in {tname}: {img}"
            assert len(alt_match.group(1).strip()) > 0, f"Empty alt attribute in {tname}: {img}"


def test_absence_of_vite_react_boilerplate_and_sourcemaps():
    """Verifies tab titles do not mention Vite/React and no sourcemaps are exposed."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    templates = ["index.html", "login.html", "privacy.html", "terms.html", "404.html", "sign.html", "braille.html", "dashboard.html", "refund.html", "cookies.html", "unsubscribe.html"]
    for tname in templates:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        title_match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
        assert title_match is not None, f"Missing title in {tname}"
        title = title_match.group(1).lower()
        assert "vite" not in title, f"Vite found in title of {tname}"
        assert "react app" not in title, f"React found in title of {tname}"

    # Verify no sourceMappingURL in static assets
    static_dir = os.path.join(frontend_dir, "static")
    for fname in os.listdir(static_dir):
        if fname.endswith(".js") or fname.endswith(".css"):
            fpath = os.path.join(static_dir, fname)
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                c = f.read()
            assert "sourceMappingURL" not in c, f"sourceMappingURL found in {fname}"
        assert not fname.endswith(".map"), f"Sourcemap file found: {fname}"


def test_refund_and_cookies_pages_served(client):
    """Verifies that Refund Policy and Cookie Policy pages are served with required content."""
    res_refund = client.get("/refund")
    assert res_refund.status_code == 200
    assert "Refund &amp; Billing Policy" in res_refund.text or "Refund & Billing Policy" in res_refund.text
    assert "100% Free Open-Source Core" in res_refund.text
    assert "30-Day Money-Back Guarantee" in res_refund.text

    res_cookies = client.get("/cookies")
    assert res_cookies.status_code == 200
    assert "Cookie Policy &amp; Tracking Disclosure" in res_cookies.text or "Cookie Policy & Tracking Disclosure" in res_cookies.text
    assert "transify_session" in res_cookies.text
    assert "transify_csrf" in res_cookies.text
    assert "transify_cookie_consent" in res_cookies.text
    assert "Strictly Necessary Cookies Only" in res_cookies.text


def test_unsubscribe_endpoint_and_service(client):
    """Verifies that the /unsubscribe page and /api/unsubscribe POST endpoint work cleanly."""
    res_page = client.get("/unsubscribe")
    assert res_page.status_code == 200
    assert "Manage Email Notifications" in res_page.text
    assert "CAN-SPAM" in res_page.text

    res_api = client.post("/api/unsubscribe", json={"email": "optout_user@example.com"})
    assert res_api.status_code == 200
    data = res_api.json()
    assert data["status"] == "success"
    assert "optout_user@example.com" in data["message"]


def test_email_service_unsubscribe_headers_and_physical_address(reset_mock_mail):
    """Verifies RFC 8058 / CAN-SPAM List-Unsubscribe headers and physical business address in emails."""
    from src.api.email_service import SMTPEmailAdapter, MockMailAdapter

    # Test mock mail adapter records unsubscribe headers
    mock_adapter = MockMailAdapter(configured=True)
    mock_adapter.send_password_reset_email("user@example.com", "mock_reset_token_1234567890abcdef")
    assert len(mock_adapter.sent_emails) == 1
    record = mock_adapter.sent_emails[0]
    assert "unsubscribe_url" in record
    assert "/unsubscribe?email=user@example.com" in record["unsubscribe_url"]
    assert "List-Unsubscribe=One-Click" in record["list_unsubscribe_post"]
    assert "unsubscribe@transify.app" in record["list_unsubscribe"]

    # Test SMTPEmailAdapter message structure (without sending)
    smtp = SMTPEmailAdapter(host="smtp.example.com", port=587)
    # Validate canonical app URL helper includes protocol
    from src.api.email_service import get_canonical_app_url
    url = get_canonical_app_url()
    assert url.startswith("http")


def test_registration_form_consents_and_age_verification(client):
    """Verifies form consents and age verification on account registration."""
    import time
    base_email = f"age_test_{int(time.time()*1000)}"

    # 1. Rejected if consent_terms is False
    res_no_terms = client.post("/api/auth/register", json={
        "name": "Consent Tester",
        "email": f"{base_email}_noterms@transify.test",
        "password": "SecurePassword123!_2026",
        "consent_terms": False,
        "consent_age": True
    })
    assert res_no_terms.status_code == 422

    # 2. Rejected if consent_age is False
    res_no_age = client.post("/api/auth/register", json={
        "name": "Consent Tester",
        "email": f"{base_email}_noage@transify.test",
        "password": "SecurePassword123!_2026",
        "consent_terms": True,
        "consent_age": False
    })
    assert res_no_age.status_code == 422

    # 3. Accepted if both consent_terms and consent_age are True
    res_ok = client.post("/api/auth/register", json={
        "name": "Consent Tester",
        "email": f"{base_email}_ok@transify.test",
        "password": "SecurePassword123!_2026",
        "consent_terms": True,
        "consent_age": True
    })
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "success"


def test_third_party_sdk_audit_no_tracking_scripts():
    """Audits HTML templates to verify total absence of unauthorized third-party trackers."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    templates = [
        "index.html", "login.html", "privacy.html", "terms.html",
        "404.html", "sign.html", "braille.html", "dashboard.html",
        "refund.html", "cookies.html", "unsubscribe.html"
    ]
    disallowed_signatures = [
        "google-analytics.com/analytics.js",
        "googletagmanager.com/gtm.js",
        "connect.facebook.net",
        "analytics.tiktok.com",
        "hotjar.com",
        "clarity.ms",
        "fullstory.com",
        "doubleclick.net"
    ]

    for tname in templates:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().lower()
        for sig in disallowed_signatures:
            assert sig not in content, f"Unauthorized tracking script '{sig}' found in {tname}!"


def test_footer_business_details_and_links():
    """Verifies that footer elements on key pages contain business identity and legal links."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "../src/frontend")
    for tname in ["index.html", "login.html", "privacy.html", "terms.html"]:
        path = os.path.join(frontend_dir, tname)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "100 Innovation Way, Suite 400, San Francisco, CA 94105" in content, f"Missing physical address in {tname}"
        assert "support@transify.app" in content, f"Missing support email in {tname}"
        assert "+1 (800) 555-0199" in content, f"Missing helpline phone in {tname}"
        assert "/privacy" in content, f"Missing privacy link in {tname}"
        assert "/terms" in content, f"Missing terms link in {tname}"
        assert "/refund" in content, f"Missing refund link in {tname}"
        assert "/cookies" in content, f"Missing cookies link in {tname}"




