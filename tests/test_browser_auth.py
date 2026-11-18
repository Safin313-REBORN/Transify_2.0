"""
Playwright End-to-End Browser Tests for Transify 2.0 Authentication & Welcome Screen.
Tests real browser interaction, image fallback resilience, guest mode,
database authentication, validation, session persistence, and responsive viewports.
"""
import socket
import threading
import time
import uvicorn
import pytest
from playwright.sync_api import sync_playwright

from src.api.server import app

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

@pytest.fixture(scope="module")
def live_server():
    port = get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    
    # Wait for server ready
    base_url = f"http://127.0.0.1:{port}"
    max_wait = 10
    start = time.time()
    while time.time() - start < max_wait:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
            
    yield base_url
    server.should_exit = True
    thread.join(timeout=2)

@pytest.fixture(scope="module")
def browser_instance():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        yield browser
        browser.close()

def test_welcome_screen_renders_without_errors(live_server, browser_instance):
    """Verifies welcome card and hotspots render cleanly on desktop."""
    page = browser_instance.new_page(viewport={"width": 1280, "height": 800})
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
    page = browser_instance.new_page(viewport={"width": 1280, "height": 800})
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
    page = browser_instance.new_page(viewport={"width": 1280, "height": 800})
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

def test_real_login_flow(live_server, browser_instance):
    """Verifies genuine login with demo credentials authenticates, sets session, and opens dashboard."""
    page = browser_instance.new_page(viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    # Open Login sheet
    page.click("#btn-open-login")
    
    # Fill demo credentials
    page.fill("#input-email", "demo@transify.ai")
    page.fill("#input-password", "transify2026")
    page.click("#auth-submit-btn")
    
    # Wait for auth screen to close
    page.wait_for_selector("#transify-auth-screen", state="hidden", timeout=5000)
    
    # Verify localStorage has real user and session token
    user_data = page.evaluate("() => localStorage.getItem('transify_auth_user')")
    session_token = page.evaluate("() => localStorage.getItem('transify_session_token')")
    guest_mode = page.evaluate("() => localStorage.getItem('transify_guest_mode')")
    
    assert user_data is not None
    assert "demo@transify.ai" in user_data
    assert session_token is not None
    assert guest_mode is None
    page.close()

def test_invalid_login_rejection(live_server, browser_instance):
    """Verifies entering incorrect password displays error message and does not log in."""
    page = browser_instance.new_page(viewport={"width": 1280, "height": 800})
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
    """Verifies registering a new account creates user in DB and logs in."""
    import time
    page = browser_instance.new_page(viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    page.click("#btn-open-register")
    unique_email = f"playwright_{int(time.time()*1000)}@example.com"
    
    page.fill("#input-fullname", "Alice Browser")
    page.fill("#input-email", unique_email)
    page.fill("#input-password", "Secur3P@ssword")
    page.click("#auth-submit-btn")
    
    # Wait for auth screen to close
    page.wait_for_selector("#transify-auth-screen", state="hidden", timeout=5000)
    
    user_data = page.evaluate("() => localStorage.getItem('transify_auth_user')")
    assert unique_email in user_data
    page.close()

def test_guest_mode_flow(live_server, browser_instance):
    """Verifies Continue as Demo Guest opens app with explicit guest flag and no fake JWT."""
    page = browser_instance.new_page(viewport={"width": 1280, "height": 800})
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
    page.close()

def test_session_persistence_on_reload(live_server, browser_instance):
    """Verifies that an active session persists on reload without re-prompting login."""
    page = browser_instance.new_page(viewport={"width": 1280, "height": 800})
    page.goto(live_server)
    
    # Login
    page.click("#btn-open-login")
    page.fill("#input-email", "demo@transify.ai")
    page.fill("#input-password", "transify2026")
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
    page = browser_instance.new_page(viewport={"width": 375, "height": 667})
    page.goto(live_server)
    
    card = page.locator("#auth-welcome-card")
    assert card.is_visible()
    
    # Verify buttons are clickable on mobile
    page.click("#btn-open-login")
    sheet = page.locator("#auth-sheet-container")
    assert "active" in sheet.get_attribute("class")
    page.close()

def test_login_html_standalone_page(live_server, browser_instance):
    """Verifies standalone /login page operates with the same robust database authentication."""
    page = browser_instance.new_page(viewport={"width": 1280, "height": 800})
    page.goto(f"{live_server}/login")
    
    card = page.locator("#auth-welcome-card")
    assert card.is_visible()
    
    page.click("#btn-open-login")
    page.fill("#input-email", "demo@transify.ai")
    page.fill("#input-password", "transify2026")
    page.click("#auth-submit-btn")
    
    # Verify redirection to /?auth_completed=1
    page.wait_for_url(f"{live_server}/?auth_completed=1*", timeout=5000)
    page.close()
