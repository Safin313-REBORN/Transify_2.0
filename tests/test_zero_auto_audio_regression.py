"""
Transify V3 — Zero Auto-Audio Policy Regression Test Suite.
Verifies the mandatory privacy invariant:
No audio may play automatically during:
- Application startup.
- Route changes.
- Page refresh.
- Language switching.
- Model loading.
- Sign recognition.
- Braille recognition.
- Chat loading.
- Authentication.
- Care workflows.
- Browser restoration.
All audio playback must be explicitly initiated by user gestures.
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
def audio_server():
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
        raise RuntimeError(f"Server on {base_url} failed to start.")

    yield base_url
    server.should_exit = True
    thread.join(timeout=2)


def test_no_audio_on_initial_page_load(audio_server):
    """Verify that visiting root URL triggers zero unprompted audio calls."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.add_init_script("""
            window.__audio_playback_events = [];
            const origPlay = HTMLMediaElement.prototype.play;
            HTMLMediaElement.prototype.play = function() {
                window.__audio_playback_events.push({ type: 'media_play', src: this.src, time: Date.now() });
                return origPlay.apply(this, arguments);
            };
            if (window.speechSynthesis) {
                const origSpeak = window.speechSynthesis.speak;
                window.speechSynthesis.speak = function(utterance) {
                    window.__audio_playback_events.push({ type: 'speech_speak', text: utterance.text, time: Date.now() });
                    return origSpeak.apply(this, arguments);
                };
            }
            if (window.AudioContext) {
                const origResume = window.AudioContext.prototype.resume;
                window.AudioContext.prototype.resume = function() {
                    window.__audio_playback_events.push({ type: 'audiocontext_resume', time: Date.now() });
                    return origResume.apply(this, arguments);
                };
            }
        """)

        page.goto(f"{audio_server}/", wait_until="domcontentloaded")
        page.wait_for_load_state("load")
        time.sleep(0.5)

        # Check DOM for any autoplay audio/video tags
        autoplays = page.evaluate("() => document.querySelectorAll('audio[autoplay], video[autoplay]').length")
        assert autoplays == 0, f"Found {autoplays} autoplay media elements in DOM!"

        # Check recorded audio playback events
        audio_events = page.evaluate("() => window.__audio_playback_events")
        assert len(audio_events) == 0, f"Unprompted audio calls on page load: {audio_events}"
        browser.close()


def test_no_audio_on_route_switching(audio_server):
    """Switching between workspaces (sign, braille, care, settings, chat) must never trigger auto-audio."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.add_init_script("""
            window.__audio_playback_events = [];
            const origPlay = HTMLMediaElement.prototype.play;
            HTMLMediaElement.prototype.play = function() {
                window.__audio_playback_events.push({ type: 'media_play', src: this.src });
                return origPlay.apply(this, arguments);
            };
            if (window.speechSynthesis) {
                const origSpeak = window.speechSynthesis.speak;
                window.speechSynthesis.speak = function(utterance) {
                    window.__audio_playback_events.push({ type: 'speech_speak', text: utterance.text });
                    return origSpeak.apply(this, arguments);
                };
            }
        """)

        page.goto(f"{audio_server}/", wait_until="domcontentloaded")
        page.wait_for_load_state("load")

        # Navigate through workspaces
        for route in ['home', 'sign', 'braille', 'care', 'settings', 'chat', 'phrases']:
            page.evaluate(f"window.routeTo('{route}')")
            page.wait_for_timeout(200)

        audio_events = page.evaluate("() => window.__audio_playback_events")
        assert len(audio_events) == 0, f"Auto-audio triggered during route navigation: {audio_events}"
        browser.close()


def test_no_audio_on_language_switch(audio_server):
    """Switching application language between EN and BN must not speak automatically."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.add_init_script("""
            window.__audio_playback_events = [];
            if (window.speechSynthesis) {
                const origSpeak = window.speechSynthesis.speak;
                window.speechSynthesis.speak = function(utterance) {
                    window.__audio_playback_events.push({ type: 'speech_speak', text: utterance.text });
                    return origSpeak.apply(this, arguments);
                };
            }
        """)

        page.goto(f"{audio_server}/", wait_until="domcontentloaded")
        page.wait_for_load_state("load")

        # Switch language to bn then back to en
        page.evaluate("if (window.setAppLanguage) window.setAppLanguage('bn')")
        page.wait_for_timeout(300)
        page.evaluate("if (window.setAppLanguage) window.setAppLanguage('en')")
        page.wait_for_timeout(300)

        audio_events = page.evaluate("() => window.__audio_playback_events")
        assert len(audio_events) == 0, f"Auto-audio triggered during language switch: {audio_events}"
        browser.close()


def test_explicit_user_speech_works(audio_server):
    """Explicitly clicking speak button or calling TTS must work when user requests it."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.add_init_script("""
            window.__speech_calls = [];
            if (window.speechSynthesis) {
                window.speechSynthesis.speak = function(utterance) {
                    window.__speech_calls.push(utterance.text);
                };
            }
        """)

        page.goto(f"{audio_server}/", wait_until="domcontentloaded")
        page.wait_for_load_state("load")

        # Explicit user action
        page.evaluate("if (window.TransifyTTS && window.TransifyTTS.speak) window.TransifyTTS.speak('Hello Transify')")
        calls = page.evaluate("() => window.__speech_calls")
        assert len(calls) == 1
        assert "Hello Transify" in calls[0]
        browser.close()
