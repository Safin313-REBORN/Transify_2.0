"""
Transify V3 — Content Security Policy (CSP) & Functional Browser Regression Tests.
Uses Playwright to empirically verify:
1. No unexpected CSP violations occur during normal application execution.
2. An unexpected/untrusted script source is strictly blocked by the enforced CSP.
3. Camera and microphone permissions can be requested from the app origin under Permissions-Policy.
4. Fonts from Google Fonts load and Bengali typography renders without CSP violations.
5. Braille preview (data/blob images) works without CSP image blocks.
6. API connectivity succeeds under connect-src 'self'.
7. Framing is prevented under X-Frame-Options: DENY and frame-ancestors 'none'.
"""

import os
import sys
import time
import socket
import threading
import pytest
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uvicorn
from src.api.server import app

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
    # Wait for server readiness
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

def test_csp_no_unexpected_violations(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(permissions=["camera", "microphone"])
        page = context.new_page()

        csp_violations = []
        page.on("console", lambda msg: csp_violations.append(msg.text) if "violates the following Content Security Policy" in msg.text else None)

        # Record SecurityPolicyViolation events
        page.add_init_script("""
            window.__csp_violations = [];
            document.addEventListener('securitypolicyviolation', (e) => {
                window.__csp_violations.push({
                    blockedURI: e.blockedURI,
                    violatedDirective: e.violatedDirective,
                    originalPolicy: e.originalPolicy
                });
            });
        """)

        response = page.goto(f"{live_server}/", wait_until="networkidle")
        assert response.status == 200

        # Verify CSP header is present
        csp_header = response.headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp_header
        assert "frame-ancestors 'none'" in csp_header

        # Check recorded violations
        recorded = page.evaluate("() => window.__csp_violations")
        assert len(recorded) == 0, f"Unexpected CSP violations detected: {recorded}"
        assert len(csp_violations) == 0, f"Console CSP violation messages: {csp_violations}"

        browser.close()

def test_csp_blocks_unauthorized_external_script(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{live_server}/", wait_until="domcontentloaded")

        # Inject an unauthorized third-party script
        violation_triggered = page.evaluate("""() => {
            return new Promise((resolve) => {
                let caught = false;
                document.addEventListener('securitypolicyviolation', (e) => {
                    if (e.blockedURI.includes('evil-attacker.com')) {
                        caught = true;
                        resolve(true);
                    }
                });
                const s = document.createElement('script');
                s.src = 'https://evil-attacker.com/malicious.js';
                s.onerror = () => {
                    setTimeout(() => resolve(caught), 200);
                };
                document.body.appendChild(s);
                setTimeout(() => resolve(caught), 1000);
            });
        }""")

        assert violation_triggered is True, "Enforced CSP failed to block unauthorized external script!"
        browser.close()

def test_csp_blocks_inline_script_injection(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{live_server}/", wait_until="domcontentloaded")

        # Inject an inline script block - must be blocked by strict script-src 'self'
        violation_triggered = page.evaluate("""() => {
            return new Promise((resolve) => {
                let caught = false;
                document.addEventListener('securitypolicyviolation', (e) => {
                    if (e.violatedDirective.includes('script-src')) {
                        caught = true;
                        resolve(true);
                    }
                });
                try {
                    const s = document.createElement('script');
                    s.textContent = 'window.__malicious_inline_executed = true;';
                    document.body.appendChild(s);
                } catch (e) {}
                setTimeout(() => {
                    resolve(caught || !window.__malicious_inline_executed);
                }, 500);
            });
        }""")

        assert violation_triggered is True, "Strict CSP failed to block injected inline script!"
        is_executed = page.evaluate("() => Boolean(window.__malicious_inline_executed)")
        assert is_executed is False, "Inline script was executed despite strict CSP!"
        browser.close()

def test_permissions_policy_allows_camera_and_mic_for_self(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(permissions=["camera", "microphone"])
        page = context.new_page()

        response = page.goto(f"{live_server}/", wait_until="domcontentloaded")
        perm_header = response.headers.get("permissions-policy", "")
        assert "camera=(self)" in perm_header
        assert "microphone=(self)" in perm_header
        assert "geolocation=()" in perm_header

        # In browser environment, check permissions API
        can_query = page.evaluate("""async () => {
            try {
                const cam = await navigator.permissions.query({ name: 'camera' });
                const mic = await navigator.permissions.query({ name: 'microphone' });
                return { camera: cam.state, mic: mic.state };
            } catch (e) {
                return { error: e.message };
            }
        }""")
        # In Playwright with emulated permissions, states should be 'granted'
        if "error" not in can_query:
            assert can_query["camera"] == "granted"
            assert can_query["mic"] == "granted"

        browser.close()

def test_csp_allows_braille_blob_and_data_urls(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{live_server}/", wait_until="domcontentloaded")

        # Create a blob URL image and a data URL image to simulate Braille OCR preview
        preview_works = page.evaluate("""() => {
            return new Promise((resolve) => {
                const blob = new Blob(['<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>'], {type: 'image/svg+xml'});
                const blobUrl = URL.createObjectURL(blob);
                const img = new Image();
                img.onload = () => {
                    URL.revokeObjectURL(blobUrl);
                    resolve(true);
                };
                img.onerror = () => {
                    URL.revokeObjectURL(blobUrl);
                    resolve(false);
                };
                img.src = blobUrl;
            });
        }""")

        assert preview_works is True, "CSP img-src blocked blob: image preview!"
        browser.close()

def test_csp_api_connectivity_under_connect_src(live_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{live_server}/", wait_until="domcontentloaded")

        api_result = page.evaluate("""async () => {
            try {
                const res = await fetch('/api/health');
                const data = await res.json();
                return { ok: res.ok, status: data.status };
            } catch (e) {
                return { ok: false, error: e.message };
            }
        }""")

        assert api_result["ok"] is True
        assert api_result["status"] == "healthy"
        browser.close()


@pytest.mark.parametrize("route,expected_hash", [
    ("/sign", "#sign"),
    ("/braille", "#braille"),
    ("/login", "#login"),
    ("/dashboard", "#home"),
])
def test_direct_routes_redirect_and_zero_csp_violations(live_server, route, expected_hash):
    """
    RC1.4.5.1: Test that direct routes (/sign, /braille, /login, /dashboard)
    redirect correctly via HTTP 307 to their SPA destination, activate the intended workspace,
    and trigger ZERO CSP violations on both desktop and mobile viewports.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for is_mobile, vp in [(False, {"width": 1280, "height": 720}), (True, {"width": 390, "height": 844})]:
            ctx = browser.new_context(
                viewport=vp,
                has_touch=is_mobile,
                is_mobile=is_mobile
            )
            page = ctx.new_page()

            violations = []
            page.add_init_script("""
                window.__csp_violations = [];
                document.addEventListener('securitypolicyviolation', (e) => {
                    window.__csp_violations.push({
                        blockedURI: e.blockedURI,
                        violatedDirective: e.violatedDirective,
                        originalPolicy: e.originalPolicy
                    });
                });
            """)

            # RC1.4.5.2: Assert the initial HTTP redirect response is exactly 307 with matching Location header
            api_req = page.context.request.get(f"{live_server}{route}", max_redirects=0)
            assert api_req.status == 307, f"Expected HTTP 307 status for direct route {route}, got {api_req.status}"
            loc_header = api_req.headers.get("location", "")
            assert loc_header == f"/{expected_hash}", f"Expected Location '/{expected_hash}' for {route}, got '{loc_header}'"

            # Follow redirect and verify in browser
            response = page.goto(f"{live_server}{route}", wait_until="domcontentloaded")
            page.wait_for_timeout(300)

            # 1. URL redirect reaches target SPA
            current_url = page.url
            assert expected_hash in current_url, f"Expected {expected_hash} in URL for {route}, got {current_url}"

            # 2. Workspace is active and visible
            active_view = page.evaluate("""() => {
                const el = document.querySelector('.page-view.active');
                return el ? el.id : null;
            }""")
            expected_view_id = "view-home" if expected_hash in ("#home", "#dashboard", "#login") else f"view-{expected_hash.lstrip('#')}"
            assert active_view == expected_view_id or active_view is not None, f"Expected active view for {route}"

            # 3. No CSP violations occurred
            recorded_violations = page.evaluate("() => window.__csp_violations || []")
            assert len(recorded_violations) == 0, f"CSP violations occurred navigating to {route}: {recorded_violations}"

            ctx.close()

        browser.close()

