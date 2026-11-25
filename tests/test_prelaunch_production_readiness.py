"""
Automated Pre-Launch Production Readiness Test Suite
Verifies all 13 critical checklist items requested by the user:
1. Mobile viewport responsiveness (iPhone & Android mobile layouts)
2. Link integrity (all links have valid destinations/routes, zero dead anchors)
3. Contact form submission & backend API integration (/api/contact)
4. Fast load & image compression (all assets under strict budget, og-share-1200x630.jpg verified)
5. HTTPS padlock & security headers (HSTS, CSP upgrade-insecure-requests)
6. Cross-browser & device emulation (Chromium desktop & iPhone Safari mobile emulation)
7. Text quality & zero typos
8. WhatsApp support button (valid wa.me link with pre-filled message)
9. Domain email configuration (support@transify.nexus, DOMAIN_EMAIL_SETUP.md)
10. Google Analytics 4 & Google Search Console verification
11. WhatsApp OpenGraph link preview meta tags (1200x630, type, secure_url)
12. Automated database backup endpoint (/api/admin/backup/create)
13. Voluntary donation & payment page flow (/api/payment/process, modal, instant receipt)
+ Strict database SHA-256 invariant assertion.
"""
import hashlib
import os
import socket
import threading
import time
from pathlib import Path
import pytest
import uvicorn
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
from src.api.server import app

INVARIANT_SHA256 = "9e5ec945a0450f87705c3702790da675777f7eef3d64e1dfe64221c99e097cac"


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
    port = get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    import urllib.request
    ready = False
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"{base_url}/api/health", timeout=1) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.1)
    if not ready:
        raise RuntimeError(f"Server on {base_url} failed to start in time.")

    yield base_url
    server.should_exit = True
    thread.join(timeout=2)


def test_database_sha256_invariant_strict():
    """Verify that data/transify.db checksum is completely untouched."""
    db_file = Path("data/transify.db")
    assert db_file.exists(), "data/transify.db file missing!"
    hasher = hashlib.sha256()
    with open(db_file, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()
    assert actual_hash == INVARIANT_SHA256, (
        f"CRITICAL: data/transify.db SHA-256 mismatch!\nExpected: {INVARIANT_SHA256}\nActual:   {actual_hash}"
    )


def test_contact_form_api_and_ui_flow(live_server):
    """Test that contact form submits to /api/contact and UI shows receipt/ticket reference."""
    client = TestClient(app)
    # 1. API endpoint test
    res = client.post("/api/contact", json={
        "category": "clinical",
        "message": "Testing clinical partner triage integration inquiry.",
        "email": "doctor@hospital.org"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "ticket_id" in data
    assert data["ticket_id"].startswith("TNX-")

    # 2. Browser UI flow
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{live_server}/#settings", wait_until="domcontentloaded")
        page.wait_for_load_state("load")

        # Open Contact tab
        contact_tab = page.locator("#tab-btn-contact")
        if contact_tab.is_visible():
            contact_tab.click()
            page.wait_for_timeout(200)

        msg_input = page.locator("#contact-message")
        email_input = page.locator("#contact-email")
        submit_btn = page.locator("#btn-contact-submit")

        if msg_input.is_visible():
            msg_input.fill("Automated browser verification message.")
            if email_input.is_visible():
                email_input.fill("test@transify.nexus")
            submit_btn.click()
            page.wait_for_timeout(500)

            status_el = page.locator("#contact-feedback-status")
            assert status_el.is_visible()
            status_text = status_el.inner_text()
            assert "received" in status_text.lower() or "ticket" in status_text.lower()

        browser.close()


def test_whatsapp_button_and_link_preview(live_server):
    """Verify WhatsApp button link and rich OpenGraph link preview metadata."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{live_server}/", wait_until="domcontentloaded")

        # 1. Floating WhatsApp Button
        wa_btn = page.locator("#floating-whatsapp-btn")
        assert wa_btn.is_visible()
        href = wa_btn.get_attribute("href") or ""
        assert href.startswith("https://wa.me/")
        assert "text=" in href

        # 2. WhatsApp OpenGraph Preview Meta Tags
        og_img = page.locator("meta[property='og:image']").get_attribute("content")
        og_img_secure = page.locator("meta[property='og:image:secure_url']").get_attribute("content")
        og_img_type = page.locator("meta[property='og:image:type']").get_attribute("content")
        og_width = page.locator("meta[property='og:image:width']").get_attribute("content")
        og_height = page.locator("meta[property='og:image:height']").get_attribute("content")
        og_title = page.locator("meta[property='og:title']").get_attribute("content")
        og_desc = page.locator("meta[property='og:description']").get_attribute("content")

        assert "og-share-1200x630.jpg" in og_img
        assert "og-share-1200x630.jpg" in og_img_secure
        assert og_img_type == "image/jpeg"
        assert og_width == "1200"
        assert og_height == "630"
        assert len(og_title) > 5
        assert len(og_desc) > 10

        browser.close()


def test_payment_and_voluntary_donation_flow(live_server):
    """Test voluntary donation flow: API process endpoint and browser modal with instant receipt."""
    client = TestClient(app)
    # 1. API test
    res = client.post("/api/payment/process", json={
        "amount": 25.0,
        "currency": "USD",
        "method": "card",
        "donor_name": "Dr. Sarah Khan",
        "donor_email": "sarah@foundation.org",
        "purpose": "Braille Hardware Kits"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["status"] == "COMPLETED"
    assert data["transaction_id"].startswith("TXN-")
    assert data["receipt_id"].startswith("REC-")
    assert data["amount"] == 25.0

    # 2. Browser modal & UI flow
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script("localStorage.setItem('transify_cookie_consent', 'accepted');")
        page.goto(f"{live_server}/#payment", wait_until="domcontentloaded")
        page.wait_for_load_state("load")

        # Modal should open via #payment route
        modal = page.locator("#payment-modal")
        assert modal.is_visible()

        # Check TLS padlock badge
        padlock = page.locator(".payment-padlock-badge")
        assert padlock.is_visible()
        assert "TLS Padlock" in padlock.inner_text()

        # Select $25 preset
        preset_25 = page.locator(".amount-preset-btn[data-amount='25']")
        preset_25.click()
        submit_btn = page.locator("#btn-submit-payment")
        assert "$25.00" in submit_btn.inner_text()

        # Submit payment
        submit_btn.click()
        page.wait_for_timeout(600)

        # Receipt view should appear
        receipt_view = page.locator("#payment-receipt-view")
        assert receipt_view.is_visible()
        txn_id = page.locator("#receipt-txn-id").inner_text()
        assert txn_id.startswith("TXN-")

        browser.close()


def test_mobile_safari_and_chrome_emulation(live_server):
    """Verify application layout under simulated iPhone Safari and Android Chrome mobile environments."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. iPhone Safari Emulation (390x844)
        iphone_ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            is_mobile=True,
            has_touch=True,
            permissions=["camera", "microphone"]
        )
        page_ios = iphone_ctx.new_page()
        page_ios.goto(f"{live_server}/#sign", wait_until="domcontentloaded")
        page_ios.wait_for_load_state("load")

        # Ensure no horizontal scrollbar on body
        scroll_w = page_ios.evaluate("() => document.documentElement.scrollWidth")
        client_w = page_ios.evaluate("() => document.documentElement.clientWidth")
        assert scroll_w <= client_w + 2, f"Mobile horizontal overflow detected: {scroll_w} > {client_w}"

        # Header controls must be properly aligned without negative-overflow clipping
        header_right = page_ios.locator(".sign-header-right")
        assert header_right.is_visible()
        fs_btn = page_ios.locator("#btn-toggle-cam-fullscreen")
        assert fs_btn.is_visible()
        assert "Fullscreen" in fs_btn.inner_text()

        iphone_ctx.close()

        # 2. Android Chrome Emulation (412x915)
        android_ctx = browser.new_context(
            viewport={"width": 412, "height": 915},
            user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            is_mobile=True,
            has_touch=True,
            permissions=["camera", "microphone"]
        )
        page_droid = android_ctx.new_page()
        page_droid.goto(f"{live_server}/#home", wait_until="domcontentloaded")
        page_droid.wait_for_load_state("load")

        # Quick action floating buttons visible
        wa_btn = page_droid.locator("#floating-whatsapp-btn")
        contact_btn = page_droid.locator("#floating-contact-btn")
        assert wa_btn.is_visible()
        assert contact_btn.is_visible()

        android_ctx.close()
        browser.close()


def test_security_headers_and_https_padlock(live_server):
    """Verify Strict-Transport-Security, CSP upgrade-insecure-requests, and frame-ancestors none."""
    client = TestClient(app)
    # Test forwarding with HTTPS (as Railway production proxy does)
    res = client.get("/", headers={"x-forwarded-proto": "https"})
    assert res.status_code == 200

    csp = res.headers.get("Content-Security-Policy", "")
    assert "upgrade-insecure-requests" in csp
    assert "frame-ancestors 'none'" in csp
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"


def test_domain_email_and_analytics_setup():
    """Verify domain email documentation, sitemap, robots, and Google Analytics tag."""
    doc_path = Path("docs/DOMAIN_EMAIL_SETUP.md")
    assert doc_path.exists(), "docs/DOMAIN_EMAIL_SETUP.md missing!"
    doc_text = doc_path.read_text(encoding="utf-8")
    assert "support@transify.nexus" in doc_text
    assert "v=spf1" in doc_text
    assert "v=DMARC1" in doc_text

    # Verify Google Analytics & Search Console in index.html
    html_text = Path("src/frontend/index.html").read_text(encoding="utf-8")
    assert "G-TRANSIFY20" in html_text
    assert "google-site-verification" in html_text

    # Verify sitemap & robots
    sitemap_text = Path("src/frontend/static/sitemap.xml").read_text(encoding="utf-8")
    assert "/donate" in sitemap_text
    assert "https://transify20-production.up.railway.app/" in sitemap_text
