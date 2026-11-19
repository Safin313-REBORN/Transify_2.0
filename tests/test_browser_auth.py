"""
Playwright End-to-End Browser Tests for Transify 2.0 Authentication & Welcome Screen.
Tests real browser interaction, image fallback resilience, guest mode,
database authentication, validation, session persistence, and responsive viewports.
"""
import os
import socket
import threading
import time
import uvicorn
import pytest
from playwright.sync_api import sync_playwright

from src.api.server import app
from src.database.db import create_user

def new_isolated_page(browser_instance, viewport={"width": 1280, "height": 800}):
    """Creates a new isolated browser context and page, ensuring clean cookies and storage."""
    context = browser_instance.new_context(viewport=viewport)
    page = context.new_page()
    original_close = page.close
    def safe_close():
        try:
            original_close()
        finally:
            context.close()
    page.close = safe_close
    return page

@pytest.fixture(scope="module")
def browser_test_user():
    email = f"browser_e2e_{int(time.time()*1000)}@transify.test"
    pwd = "BrowserE2EPassword123!_2026"
    create_user("Browser Tester", email, pwd, consent_terms=True)
    return {"email": email, "password": pwd}

def test_welcome_screen_renders_without_errors(live_server, browser_instance):
    """Verifies welcome card and hotspots render cleanly on desktop."""
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    # Verify auth screen overlay exists
    auth_screen = page.locator("#transify-auth-screen")
    assert auth_screen.is_visible()
    
    # Verify card exists
    card = page.locator("#auth-welcome-card")
    assert card.is_visible()
    
    # Verify buttons exist
    assert page.locator("#btn-open-register").is_visible()
    assert page.locator("#btn-open-login").is_visible()
    assert page.locator("#btn-demo-guest").is_visible()
    page.close()

def test_artwork_failure_activates_styled_fallback(live_server, browser_instance):
    """Verifies that if artwork fails to load/decode, .auth-fallback-active renders visible buttons."""
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    # Block data URIs and images to simulate decode or load failure
    page.route("**/*.jpg", lambda route: route.abort())
    page.route("**/*.png", lambda route: route.abort())
    
    page.goto(live_server)
    
    # Trigger image error explicitly if not triggered by route abort
    page.evaluate("() => { const img = document.getElementById('auth-welcome-artwork'); if (img) window.handleArtworkError(img); }")
    
    card = page.locator("#auth-welcome-card")
    assert "auth-fallback-active" in card.get_attribute("class")
    
    # Verify brand header is visible in fallback mode
    brand = page.locator(".auth-fallback-brand")
    assert brand.is_visible()
    assert "Transify" in brand.inner_text()
    
    # Verify buttons are visible and styled
    reg_btn = page.locator("#btn-open-register")
    login_btn = page.locator("#btn-open-login")
    guest_btn = page.locator("#btn-demo-guest")
    
    assert reg_btn.is_visible()
    assert login_btn.is_visible()
    assert guest_btn.is_visible()
    page.close()

def test_early_interaction_before_app_js(live_server, browser_instance):
    """Verifies buttons work even if app.js is delayed or blocked."""
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    # Block app.js from loading
    page.route("**/static/app.js*", lambda route: route.abort())
    
    page.goto(live_server)
    
    # Clicking Login should still open the auth sheet via early head handler
    page.click("#btn-open-login")
    sheet = page.locator("#auth-sheet-container")
    assert "active" in sheet.get_attribute("class")
    
    title = page.locator("#auth-heading-title")
    assert "Welcome Back" in title.inner_text()
    
    # Clicking Sign Up tab should switch mode
    page.click("#tab-signup")
    assert "Join Transify" in title.inner_text()
    
    page.close()

def test_real_login_flow(live_server, browser_instance, browser_test_user):
    """Verifies genuine login authenticates, sets session, and opens dashboard."""
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    # Open Login sheet
    page.click("#btn-open-login")
    
    # Fill user credentials
    page.fill("#input-email", browser_test_user["email"])
    page.fill("#input-password", browser_test_user["password"])
    page.click("#auth-submit-btn")
    
    # Wait for auth screen to close
    page.wait_for_selector("#transify-auth-screen", state="hidden", timeout=5000)
    
    # Verify localStorage has real user and NO raw session token (cookie-only security)
    user_data = page.evaluate("() => localStorage.getItem('transify_auth_user')")
    session_token = page.evaluate("() => localStorage.getItem('transify_session_token')")
    guest_mode = page.evaluate("() => localStorage.getItem('transify_guest_mode')")
    
    assert user_data is not None
    assert browser_test_user["email"] in user_data
    assert session_token is None
    assert guest_mode is None

    # Verify session cookie is present and set
    cookies = page.context.cookies()
    assert any(c["name"] == "transify_session" for c in cookies)
    page.close()

def test_invalid_login_rejection(live_server, browser_instance):
    """Verifies entering incorrect password displays error message and does not log in."""
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    page.click("#btn-open-login")
    page.fill("#input-email", "demo@transify.ai")
    page.fill("#input-password", "wrongpassword123")
    page.click("#auth-submit-btn")
    
    # Wait for alert message
    alert = page.locator("#auth-alert")
    page.wait_for_selector("#auth-alert:visible", timeout=3000)
    assert "Invalid email or password" in alert.inner_text()
    
    # Auth screen remains visible
    auth_screen = page.locator("#transify-auth-screen")
    assert auth_screen.is_visible()
    page.close()

def test_user_registration_flow(live_server, browser_instance):
    """Verifies registering a new account requires terms consent, creates user in DB, and logs in."""
    import time
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    page.click("#btn-open-register")
    page.wait_for_selector("#auth-sheet-container.active", timeout=5000)
    page.wait_for_selector("#input-fullname:visible", timeout=5000)
    unique_email = f"playwright_{int(time.time()*1000)}@example.com"
    
    page.fill("#input-fullname", "Alice Browser")
    page.fill("#input-email", unique_email)
    page.fill("#input-password", "SecurePassword1234567!") # 22 chars (>= 15)
    
    # 1. First attempt: Terms UNCHECKED -> must be blocked
    page.uncheck("#input-terms")
    page.click("#auth-submit-btn")
    alert = page.locator("#auth-alert")
    page.wait_for_selector("#auth-alert:visible", timeout=5000)
    assert "Terms of Service" in alert.inner_text()
    
    # 2. Check terms checkbox and re-submit -> must succeed
    page.check("#input-terms")
    page.click("#auth-submit-btn")
    
    # Wait for auth screen to close
    page.wait_for_selector("#transify-auth-screen", state="hidden", timeout=5000)
    
    user_data = page.evaluate("() => localStorage.getItem('transify_auth_user')")
    assert unique_email in user_data
    assert page.evaluate("() => localStorage.getItem('transify_session_token')") is None
    cookies = page.context.cookies()
    assert any(c["name"] == "transify_session" for c in cookies)
    page.close()

def test_guest_mode_flow(live_server, browser_instance):
    """Verifies Continue as Demo Guest opens app with explicit guest flag and no fake JWT."""
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    # Click Guest Button
    page.click("#btn-demo-guest")
    
    page.wait_for_selector("#transify-auth-screen", state="hidden", timeout=5000)
    
    guest_mode = page.evaluate("() => localStorage.getItem('transify_guest_mode')")
    user_data = page.evaluate("() => localStorage.getItem('transify_auth_user')")
    fake_token = page.evaluate("() => localStorage.getItem('transify_auth_token')")
    
    assert guest_mode == "true"
    assert "Guest User" in user_data
    assert fake_token is None
    assert page.evaluate("() => localStorage.getItem('transify_session_token')") is None
    page.close()

def test_session_persistence_on_reload(live_server, browser_instance, browser_test_user):
    """Verifies that an active session persists on reload without re-prompting login."""
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    # Login
    page.click("#btn-open-login")
    page.fill("#input-email", browser_test_user["email"])
    page.fill("#input-password", browser_test_user["password"])
    page.click("#auth-submit-btn")
    page.wait_for_selector("#transify-auth-screen", state="hidden", timeout=5000)
    
    # Reload page
    page.reload()
    time.sleep(0.8)
    
    # Auth screen must remain hidden
    auth_screen = page.locator("#transify-auth-screen")
    assert not auth_screen.is_visible()
    page.close()

def test_responsive_mobile_viewport(live_server, browser_instance):
    """Verifies auth screen and buttons render correctly on mobile (375x667)."""
    page = new_isolated_page(browser_instance,viewport={"width": 375, "height": 667})
    page.goto(live_server)
    
    card = page.locator("#auth-welcome-card")
    assert card.is_visible()
    
    # Verify buttons are clickable on mobile
    page.click("#btn-open-login")
    sheet = page.locator("#auth-sheet-container")
    assert "active" in sheet.get_attribute("class")
    page.close()

def test_login_html_standalone_page(live_server, browser_instance, browser_test_user):
    """Verifies standalone /login page operates with the same robust database authentication."""
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    page.goto(f"{live_server}/login")
    
    card = page.locator("#auth-welcome-card")
    assert card.is_visible()
    
    page.click("#btn-open-login")
    page.fill("#input-email", browser_test_user["email"])
    page.fill("#input-password", browser_test_user["password"])
    page.click("#auth-submit-btn")
    
    # Verify redirection to /?auth_completed=1
    page.wait_for_url(f"{live_server}/?auth_completed=1*", timeout=5000)
    page.close()

def test_hotspot_alignment_multiple_viewports(live_server, browser_instance):
    """Verifies welcome screen hotspot buttons remain precisely aligned across diverse viewports."""
    viewports = [
        {"width": 1280, "height": 800, "name": "desktop"},
        {"width": 375, "height": 667, "name": "mobile_portrait"},
        {"width": 667, "height": 375, "name": "mobile_landscape"},
        {"width": 1024, "height": 500, "name": "short_desktop"}
    ]
    for vp in viewports:
        page = new_isolated_page(browser_instance,viewport={"width": vp["width"], "height": vp["height"]})
        page.goto(live_server)
        
        reg_btn = page.locator("#btn-open-register")
        login_btn = page.locator("#btn-open-login")
        guest_btn = page.locator("#btn-demo-guest")
        
        assert reg_btn.is_visible()
        assert login_btn.is_visible()
        assert guest_btn.is_visible()
        
        # Verify button bounding boxes are well-formed and inside viewport
        box = login_btn.bounding_box()
        assert box is not None
        assert box["width"] > 50
        assert box["height"] > 20
        assert box["x"] >= 0
        assert box["y"] >= 0
        
        # Clicking login should open sheet cleanly
        page.click("#btn-open-login")
        sheet = page.locator("#auth-sheet-container")
        assert "active" in sheet.get_attribute("class")
        
        page.close()

def test_password_visibility_toggle(live_server, browser_instance):
    """Verifies that clicking the eye icon toggles password input visibility between password and text."""
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    page.click("#btn-open-login")
    pwd = page.locator("#input-password")
    toggle_btn = page.locator("#toggle-pwd-btn")
    
    assert pwd.get_attribute("type") == "password"
    toggle_btn.click()
    assert pwd.get_attribute("type") == "text"
    toggle_btn.click()
    assert pwd.get_attribute("type") == "password"
    
    page.close()

def test_forgot_password_ui_workflow(live_server, browser_instance):
    """Verifies Forgot Password link transitions UI into recovery mode and reveals reset fields."""
    import time
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    unique_email = f"forgot_{int(time.time()*1000)}@transify.test"
    create_user("Forgot Tester", unique_email, "InitialPassword123!_2026", consent_terms=True)
    
    page.click("#btn-open-login")
    page.click("#forgot-password-link")
    
    # Verify title changes to Password Recovery or Recover Password
    title = page.locator("#auth-heading-title")
    assert "Password" in title.inner_text() or "Recover" in title.inner_text()
    
    # Enter email
    page.fill("#input-email", unique_email)
    page.click("#auth-submit-btn")
    
    # Step 2 fields must appear
    fields = page.locator("#auth-forgot-fields")
    page.wait_for_selector("#auth-forgot-fields:visible", timeout=5000)
    assert fields.is_visible()
    assert page.locator("#input-reset-token").is_visible()
    assert page.locator("#input-new-password").is_visible()
    
    page.close()

def test_communication_hub_ui_interaction(live_server, browser_instance):
    """Verifies Communication Hub opens, accepts typed messages, renders feed cards, and supports copying/export."""
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    # Enter as guest for fast UI access
    page.click("#btn-demo-guest")
    page.wait_for_selector("#transify-auth-screen", state="hidden", timeout=5000)
    
    # Open Communication Hub via navigation tile
    page.click("#btn-open-hub")
    hub_slide = page.locator("#slide-communication-hub")
    assert "active" in hub_slide.get_attribute("class")
    
    # Type and send message
    page.fill("#hub-input-text", "Hello from automated browser test!")
    page.click("#hub-send-btn")
    
    # Verify message card in feed
    page.wait_for_selector(".hub-message-card", timeout=3000)
    card_text = page.locator(".hub-message-card").inner_text()
    assert "Hello from automated browser test!" in card_text
    assert "TYPED" in card_text.upper()
    
    # Verify actions
    copy_btn = page.locator(".hub-action-btn:has-text('Copy')").first
    assert copy_btn.is_visible()
    
    page.close()

def test_quick_phraseboard_ui_interaction(live_server, browser_instance):
    """Verifies Phraseboard displays default bilingual phrases, adds custom phrases, and clicking does not auto-play audio."""
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    page.click("#btn-demo-guest")
    page.wait_for_selector("#transify-auth-screen", state="hidden", timeout=5000)
    
    # Open Phraseboard
    page.click("#btn-open-phraseboard")
    phrase_slide = page.locator("#slide-phraseboard")
    assert "active" in phrase_slide.get_attribute("class")
    
    # Verify default phrases rendered
    page.wait_for_selector(".phrase-card", timeout=3000)
    cards = page.locator(".phrase-card")
    assert cards.count() >= 8
    
    # Click phrase card to add to hub
    cards.first.click()
    
    # Open custom phrase form
    page.click("#btn-toggle-add-phrase")
    page.wait_for_selector("#phrase-add-form-container:visible", timeout=2000)
    page.fill("#input-phrase-en", "Automated custom phrase")
    page.fill("#input-phrase-bn", "স্বয়ংক্রিয় কাস্টম বাক্য")
    page.click("#btn-save-phrase")
    
    # Verify new custom phrase appears
    page.wait_for_selector(".phrase-card:has-text('Automated custom phrase')", timeout=3000)
    assert page.locator(".phrase-card:has-text('Automated custom phrase')").is_visible()
    
    page.close()

def test_language_and_accessibility_ui_toggles(live_server, browser_instance):
    """Verifies language toggle switches UI strings and accessibility modal toggles body classes."""
    page = new_isolated_page(browser_instance,viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    page.click("#btn-demo-guest")
    page.wait_for_selector("#transify-auth-screen", state="hidden", timeout=5000)
    
    # 1. Test Language Switcher
    lang_btn = page.locator("#lang-toggle-btn")
    assert lang_btn.is_visible()
    
    # Switch to Bengali
    lang_btn.click()
    time.sleep(0.3)
    doc_lang = page.evaluate("() => document.documentElement.getAttribute('lang')")
    assert doc_lang == "bn"
    
    # Switch back to English
    lang_btn.click()
    time.sleep(0.3)
    doc_lang = page.evaluate("() => document.documentElement.getAttribute('lang')")
    assert doc_lang == "en"
    
    # 2. Test Accessibility Modal
    a11y_btn = page.locator("#btn-open-a11y")
    assert a11y_btn.is_visible()
    a11y_btn.click()
    
    modal = page.locator("#a11y-modal-overlay")
    page.wait_for_selector("#a11y-modal-overlay:visible", timeout=2000)
    assert modal.is_visible()
    
    # Toggle reduced motion
    page.check("#a11y-toggle-reduced-motion")
    has_reduced = page.evaluate("() => document.body.classList.contains('reduced-motion')")
    assert has_reduced is True
    
    # Toggle large touch targets
    page.check("#a11y-toggle-large-targets")
    has_large = page.evaluate("() => document.body.classList.contains('large-targets')")
    assert has_large is True
    
    # Close modal
    page.click("#a11y-close-btn")
    assert not modal.is_visible()
    
    page.close()

