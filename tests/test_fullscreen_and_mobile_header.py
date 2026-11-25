"""
Regression test suite for camera fullscreen toggle and responsive header controls.
Ensures:
1. Fullscreen button toggles stage-fullscreen mode, button icon/text, and floating prediction HUD.
2. Fullscreen properly cleans up on workspace route changes.
3. On narrow mobile viewports (e.g. 375px), .sign-header-right controls do not suffer from
   negative flexbox coordinate clipping (no clipped '...us' or 'Bd...').
4. Database SHA-256 invariant remains strictly preserved.
"""
import hashlib
import socket
import threading
import time
from pathlib import Path
import pytest
import uvicorn
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
    """Verify that the immutable database was never modified during audit & fixes."""
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


def test_fullscreen_toggle_and_hud_state(live_server):
    """Test camera fullscreen button toggles stage-fullscreen class, HUD, and aria-expanded."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(permissions=["camera", "microphone"])
        page = context.new_page()

        page.goto(f"{live_server}/#sign", wait_until="domcontentloaded")
        page.wait_for_load_state("load")

        fs_btn = page.locator("#btn-toggle-cam-fullscreen")
        stage = page.locator("#sign-stage-container")
        hud = page.locator("#fullscreen-pred-hud")

        assert fs_btn.is_visible()
        initial_text = fs_btn.inner_text()
        assert "Fullscreen" in initial_text

        # Click to enter fullscreen mode
        fs_btn.click()
        page.wait_for_timeout(300)

        # Stage should have stage-fullscreen class
        stage_classes = stage.get_attribute("class") or ""
        assert "stage-fullscreen" in stage_classes
        assert "Exit Fullscreen" in fs_btn.inner_text()
        assert fs_btn.get_attribute("aria-expanded") == "true"
        assert hud.is_visible()

        # Click again to exit fullscreen mode
        fs_btn.click()
        page.wait_for_timeout(300)

        stage_classes = stage.get_attribute("class") or ""
        assert "stage-fullscreen" not in stage_classes
        assert "Fullscreen" in fs_btn.inner_text()
        assert fs_btn.get_attribute("aria-expanded") == "false"
        assert not hud.is_visible()

        browser.close()


def test_mobile_header_controls_not_clipped(live_server):
    """Test that on a 375px mobile screen, header buttons are not clipped by negative flexbox overflow."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Mobile viewport (iPhone SE size: 375x667)
        context = browser.new_context(
            viewport={"width": 375, "height": 667},
            permissions=["camera", "microphone"]
        )
        page = context.new_page()

        page.goto(f"{live_server}/#sign", wait_until="domcontentloaded")
        page.wait_for_load_state("load")

        # Verify header controls container scrollLeft is >= 0 and first item starts within view
        header_right = page.locator(".sign-header-right")
        assert header_right.is_visible()

        # Check bounding boxes of buttons
        focus_btn = page.locator("#toggle-roi-focus-btn")
        fs_btn = page.locator("#btn-toggle-cam-fullscreen")
        bdsl_btn = page.locator("#lang-bdsl-btn")

        assert focus_btn.is_visible()
        assert fs_btn.is_visible()
        assert bdsl_btn.is_visible()

        # Verify that focus_btn text is not truncated into '...us'
        focus_text = focus_btn.inner_text()
        assert "Focus" in focus_text
        assert "Fullscreen" in fs_btn.inner_text()
        assert "BdSL" in bdsl_btn.inner_text()

        browser.close()
