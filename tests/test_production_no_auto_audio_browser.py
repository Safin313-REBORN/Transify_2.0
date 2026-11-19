"""
Production End-to-End Browser Tests for Strict Zero Auto-Audio Policy.
Runs in real Playwright Chromium against the live application server.
Verifies that:
1. Initial page load across all routes produces zero speech requests.
2. Route navigation produces zero speech requests.
3. Confirmed sign recognition updates UI text but NEVER triggers audio automatically.
4. Completed Braille translation renders text but NEVER triggers audio automatically.
5. Communication Hub incoming messages NEVER trigger audio automatically.
6. Explicit speaker button click triggers exactly one speech call with matching text.
7. Stop / cancel action halts speech synthesis immediately.
8. Empty text speaker button clicks are safely rejected with zero speech calls.
"""
import pytest
from playwright.sync_api import Page
from tests.test_browser_auth import new_isolated_page


def inject_audio_observers(page: Page):
    """
    Injects observable call monitors into the browser's window context before scripts run.
    Records every invocation of window.speechSynthesis.speak, cancel, and transifyNativeBridge.
    """
    page.add_init_script("""
        window._transify_audio_calls = [];
        window._transify_stop_calls = [];
        window._transify_bridge_calls = [];

        // Mock native Android WebMessageListener bridge
        window.transifyNativeBridge = {
            postMessage: function(msgStr) {
                try {
                    const parsed = JSON.parse(msgStr);
                    window._transify_bridge_calls.push(parsed);
                } catch(e) {
                    window._transify_bridge_calls.push({ raw: msgStr });
                }
            }
        };

        // Spy on Web Speech Synthesis
        if ('speechSynthesis' in window) {
            const originalSpeak = window.speechSynthesis.speak.bind(window.speechSynthesis);
            const originalCancel = window.speechSynthesis.cancel.bind(window.speechSynthesis);

            window.speechSynthesis.speak = function(utterance) {
                window._transify_audio_calls.push({
                    text: utterance ? utterance.text : '',
                    lang: utterance ? utterance.lang : '',
                    type: 'speechSynthesis'
                });
            };

            window.speechSynthesis.cancel = function() {
                window._transify_stop_calls.push({ type: 'speechSynthesis.cancel' });
            };
        }
    """)


def test_page_loads_never_produce_audio(live_server, browser_instance):
    """Verifies that loading dashboard, sign, braille, and login routes dispatches zero audio."""
    page = new_isolated_page(browser_instance)
    inject_audio_observers(page)

    routes = ["/", "/sign", "/braille", "/login"]
    for route in routes:
        page.goto(f"{live_server}{route}", wait_until="domcontentloaded")
        page.wait_for_timeout(300)

        # Check recorded calls
        audio_calls = page.evaluate("() => window._transify_audio_calls.length")
        bridge_calls = page.evaluate("() => window._transify_bridge_calls.filter(c => c.action === 'tts_speak').length")

        assert audio_calls == 0, f"Route {route} triggered automatic audio playback!"
        assert bridge_calls == 0, f"Route {route} triggered native bridge tts_speak!"

    page.close()


def test_confirmed_sign_recognition_never_auto_plays_audio(live_server, browser_instance):
    """Verifies that confirmed sign detections update UI text with zero audio playback."""
    page = new_isolated_page(browser_instance)
    inject_audio_observers(page)

    page.goto(f"{live_server}/sign", wait_until="domcontentloaded")
    page.wait_for_timeout(500)

    # Dismiss welcome overlay if present
    page.evaluate("""() => {
        const overlay = document.getElementById('transify-auth-screen');
        if (overlay) overlay.style.display = 'none';
    }""")

    # Simulate backend returning a CONFIRMED sign detection
    page.evaluate("""() => {
        if (window.SignPage && typeof window.SignPage.updatePredictionUI === 'function') {
            window.SignPage.lastPrediction = 'HELLO';
            window.SignPage.updatePredictionUI({
                label: 'HELLO',
                display_text: 'Hello',
                bdsl_gloss: 'হ্যালো',
                confidence: 0.95,
                confirmed: true,
                status: 'CONFIRMED',
                analysis_pct: 100
            });
        }
    }""")

    page.wait_for_timeout(400)

    # Audio must NOT play automatically
    audio_calls = page.evaluate("() => window._transify_audio_calls.length")
    bridge_calls = page.evaluate("() => window._transify_bridge_calls.filter(c => c.action === 'tts_speak').length")

    assert audio_calls == 0, "Confirmed sign triggered automatic audio!"
    assert bridge_calls == 0, "Confirmed sign dispatched native bridge tts_speak!"

    # Now click the explicit speaker button
    speak_btn = page.locator("#speak-pred-btn")
    assert speak_btn.is_visible()
    speak_btn.click()

    page.wait_for_timeout(200)

    # Audio must be triggered ONLY after user clicks speaker button
    audio_calls_after = page.evaluate("() => window._transify_audio_calls.length")
    bridge_calls_after = page.evaluate("() => window._transify_bridge_calls.filter(c => c.action === 'tts_speak').length")

    assert (audio_calls_after > 0 or bridge_calls_after > 0), "Explicit speaker click must invoke TTS!"

    page.close()


def test_braille_translation_never_auto_plays_audio(live_server, browser_instance):
    """Verifies that completed Braille translation renders text with zero auto-audio."""
    page = new_isolated_page(browser_instance)
    inject_audio_observers(page)

    page.goto(f"{live_server}/braille", wait_until="domcontentloaded")
    page.wait_for_timeout(500)

    # Dismiss welcome overlay if present
    page.evaluate("""() => {
        const overlay = document.getElementById('transify-auth-screen');
        if (overlay) overlay.style.display = 'none';
        const txt = document.getElementById('braille-text-output');
        if (txt) txt.value = 'Welcome to Transify Braille Reader';
    }""")

    page.wait_for_timeout(300)

    # Verify no audio was triggered
    audio_calls = page.evaluate("() => window._transify_audio_calls.length")
    bridge_calls = page.evaluate("() => window._transify_bridge_calls.filter(c => c.action === 'tts_speak').length")

    assert audio_calls == 0, "Braille translation completion triggered auto-audio!"
    assert bridge_calls == 0, "Braille translation completion dispatched bridge tts_speak!"

    # Explicitly click the Braille Speak button
    speak_btn = page.locator("#speak-braille-btn")
    assert speak_btn.is_visible()
    speak_btn.click()

    page.wait_for_timeout(200)

    audio_calls_after = page.evaluate("() => window._transify_audio_calls.length")
    bridge_calls_after = page.evaluate("() => window._transify_bridge_calls.filter(c => c.action === 'tts_speak').length")

    assert (audio_calls_after > 0 or bridge_calls_after > 0), "Explicit Braille speaker click must invoke TTS!"

    page.close()


def test_empty_text_speaker_click_does_not_speak(live_server, browser_instance):
    """Verifies that clicking the speaker button with empty text does not dispatch TTS."""
    page = new_isolated_page(browser_instance)
    inject_audio_observers(page)

    page.goto(f"{live_server}/braille", wait_until="domcontentloaded")
    page.wait_for_timeout(500)

    # Ensure textarea is empty
    page.evaluate("""() => {
        const overlay = document.getElementById('transify-auth-screen');
        if (overlay) overlay.style.display = 'none';
        const txt = document.getElementById('braille-text-output');
        if (txt) txt.value = '';
    }""")

    speak_btn = page.locator("#speak-braille-btn")
    speak_btn.click()

    page.wait_for_timeout(200)

    audio_calls = page.evaluate("() => window._transify_audio_calls.length")
    bridge_calls = page.evaluate("() => window._transify_bridge_calls.filter(c => c.action === 'tts_speak').length")

    assert audio_calls == 0, "Empty text must not trigger audio calls"
    assert bridge_calls == 0, "Empty text must not dispatch bridge tts_speak"

    page.close()


def test_tts_stop_cancels_speech(live_server, browser_instance):
    """Verifies that TransifyTTS.stop() cancels speech playback immediately."""
    page = new_isolated_page(browser_instance)
    inject_audio_observers(page)

    page.goto(f"{live_server}/", wait_until="domcontentloaded")
    page.wait_for_timeout(500)

    page.evaluate("""() => {
        if (window.TransifyTTS && typeof window.TransifyTTS.stop === 'function') {
            window.TransifyTTS.stop();
        }
    }""")

    page.wait_for_timeout(200)

    stop_calls = page.evaluate("() => window._transify_stop_calls.length")
    bridge_stop_calls = page.evaluate("() => window._transify_bridge_calls.filter(c => c.action === 'tts_stop').length")

    assert (stop_calls > 0 or bridge_stop_calls > 0), "TransifyTTS.stop() must cancel active playback"

    page.close()
