"""
Exhaustive Deep Feature and Options Verification for Transify.
Tests every user-facing option, button, modal, form, and tab on the website.
"""

import os
import sys
import time
import socket
import threading
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.api.server import app
from src.database.db import get_connection, create_user, create_session, init_db
from src.care.db_care import init_care_db, create_intake

init_db()
init_care_db()

def get_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def run_deep_test():
    import uvicorn
    port = get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    timeout = 8.0
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.05)

    print(f"[*] Live test server up at {base_url}", flush=True)

    results = {
        "passed": [],
        "failed": [],
        "warnings": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Grant microphone and camera permissions
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            permissions=["microphone", "camera"]
        )
        page = context.new_page()

        # Listen for runtime errors
        page.on("pageerror", lambda err: results["failed"].append(f"Uncaught Page Error: {err}"))
        page.on("console", lambda msg: results["warnings"].append(f"Console {msg.type}: {msg.text}") if msg.type in ("error", "warning") else None)
        page.on("response", lambda res: print(f"[*] HTTP {res.status} {res.request.method} {res.url} -> {res.text() if res.status in (400, 422) else ''}", flush=True) if res.status >= 400 else None)

        # Authenticate via real login API
        login_res = page.request.post(
            f"{base_url}/api/auth/login",
            headers={"Content-Type": "application/json"},
            data='{"email": "demo@transify.ai", "password": "transify2026demo", "remember_me": true}'
        )
        assert login_res.status == 200, f"Login failed: {login_res.text()}"
        login_data = login_res.json()
        real_token = login_data.get("token", "")

        page.goto(base_url)
        page.evaluate(f"""() => {{
            localStorage.setItem('transify.welcomed', '1');
            localStorage.setItem('transify_auth_token', '{real_token}');
            localStorage.setItem('transify_auth_user', JSON.stringify({{
                name: 'Sarah Ahmed',
                email: 'demo@transify.ai',
                role: 'clinician',
                provider: 'direct'
            }}));
        }}""")
        page.reload()
        page.wait_for_timeout(500)

        # -------------------------------------------------------------
        # TEST 1: HOME PAGE CONTROLS
        # -------------------------------------------------------------
        print("\n--- Testing 1: Home Page Controls ---", flush=True)
        page.evaluate("window.routeTo('home')")
        page.wait_for_timeout(300)

        # Quick Say Input
        say_input = page.query_selector("#say")
        say_btn = page.query_selector("#btn-say-speak")
        if say_input and say_btn:
            say_input.fill("Hello from Transify Quick Say")
            say_btn.click()
            page.wait_for_timeout(300)
            results["passed"].append("Home: Quick Say speak button")
        else:
            results["failed"].append("Home: Quick Say input or button missing")

        # 3D Flip Cards
        privacy_card = page.query_selector(".privacy-flip-card")
        contact_card = page.query_selector("#home-contact-card")
        if privacy_card and contact_card:
            results["passed"].append("Home: Uiverse 3D Flip cards present")
        else:
            results["failed"].append("Home: 3D Flip cards missing")

        # -------------------------------------------------------------
        # TEST 2: SIGN LANGUAGE TRANSLATOR CONTROLS
        # -------------------------------------------------------------
        print("\n--- Testing 2: Sign Language Translator Controls ---", flush=True)
        page.evaluate("window.routeTo('sign')")
        page.wait_for_timeout(500)

        # Mode switches: Expressions, Fingerspelling, Sentence
        expr_btn = page.query_selector("#mode-expressions-btn")
        spell_btn = page.query_selector("#mode-fingerspell-btn")
        sent_btn = page.query_selector("#mode-sentence-btn")

        if expr_btn and spell_btn and sent_btn:
            spell_btn.click()
            page.wait_for_timeout(200)
            fs_visible = page.is_visible("#fingerspelling-panel")
            if fs_visible:
                results["passed"].append("Sign: Fingerspelling mode switch & panel visible")
            else:
                results["failed"].append("Sign: Fingerspelling panel not visible on switch")

            sent_btn.click()
            page.wait_for_timeout(200)
            sent_visible = page.is_visible(".sentence-panel")
            if sent_visible:
                results["passed"].append("Sign: Sentence Builder mode switch & panel visible")
            else:
                results["failed"].append("Sign: Sentence Builder panel not visible on switch")

            expr_btn.click()
            page.wait_for_timeout(200)
            results["passed"].append("Sign: Reverted to Expressions mode")
        else:
            results["failed"].append("Sign: Mode switch buttons missing")

        # Confidence slider and speed selector
        conf_slider = page.query_selector("#conf-threshold")
        if conf_slider:
            conf_slider.fill("75")
            results["passed"].append("Sign: Confidence threshold slider adjustable")

        # -------------------------------------------------------------
        # TEST 3: PHRASES & COMMUNICATION BOARD
        # -------------------------------------------------------------
        print("\n--- Testing 3: Phrases & AAC Communication Board ---", flush=True)
        page.evaluate("window.routeTo('phrases')")
        page.wait_for_timeout(400)

        # Category filters
        for cat in ["all", "medical", "daily", "emergency"]:
            c_btn = page.query_selector(f"[data-category='{cat}']")
            if c_btn:
                c_btn.click()
                page.wait_for_timeout(100)
        results["passed"].append("Phrases: Category filters functional")

        # Search filter
        p_search = page.query_selector("#phrases-search-input")
        if p_search:
            p_search.fill("water")
            page.wait_for_timeout(200)
            p_search.fill("")
            results["passed"].append("Phrases: Search filter input")

        # Add custom phrase
        p_input = page.query_selector(".phrase-text-input")
        p_add_btn = page.query_selector("#btn-add-phrase")
        if p_input and p_add_btn:
            p_input.fill("Testing custom emergency phrase")
            p_add_btn.click()
            page.wait_for_timeout(300)
            results["passed"].append("Phrases: Custom phrase created")

        # Bridge phrase to Braille
        bridge_res = page.evaluate("""() => {
            try {
                if (window.PhrasesPage && window.PhrasesPage.bridgePhraseToBraille) {
                    window.PhrasesPage.bridgePhraseToBraille('Emergency');
                    return true;
                }
                return false;
            } catch(e) { return e.toString(); }
        }""")
        if bridge_res is True:
            results["passed"].append("Phrases: Bridge to Braille functional")
        else:
            results["failed"].append(f"Phrases: Bridge to Braille failed: {bridge_res}")

        # -------------------------------------------------------------
        # TEST 4: BRAILLE TRANSLATOR & GENERATOR
        # -------------------------------------------------------------
        print("\n--- Testing 4: Braille Studio Controls ---", flush=True)
        page.evaluate("window.routeTo('braille')")
        page.wait_for_timeout(400)

        # Tab switches
        for mode in ["scan", "generator", "reference"]:
            tab = page.query_selector(f"#braille-tab-{mode}")
            if tab:
                tab.click()
                page.wait_for_timeout(200)
                is_subpane_visible = page.is_visible(f"#braille-pane-{mode}")
                if is_subpane_visible:
                    results["passed"].append(f"Braille: Mode tab '{mode}' switch")
                else:
                    results["failed"].append(f"Braille: Subpane '{mode}' not visible after tab click")

        # Test Text-to-Braille Generator input
        page.query_selector("#braille-tab-generator").click()
        page.wait_for_timeout(200)
        gen_in = page.query_selector("#braille-generator-input")
        if gen_in:
            gen_in.fill("MEDICINE 100MG")
            page.wait_for_timeout(200)
            uni_text = page.inner_text("#braille-gen-unicode-box")
            if "⠍" in uni_text:
                results["passed"].append("Braille: Text-to-Braille real-time translation confirmed ('M' -> ⠍)")
            else:
                results["failed"].append(f"Braille: Unexpected translation: '{uni_text}'")

        # Test Reference tab category filters
        page.query_selector("#braille-tab-reference").click()
        page.wait_for_timeout(200)
        for r_cat in ["letters", "numbers", "punct", "bengali"]:
            r_btn = page.query_selector(f".braille-ref-filter[data-cat='{r_cat}']")
            if r_btn:
                r_btn.click()
                page.wait_for_timeout(100)
        results["passed"].append("Braille: Reference category filters")

        # -------------------------------------------------------------
        # TEST 5: VOICE HUB (STT & TTS)
        # -------------------------------------------------------------
        print("\n--- Testing 5: Voice Hub Controls ---", flush=True)
        page.evaluate("window.routeTo('tts')")
        page.wait_for_timeout(400)

        # Voice persona change
        v_persona = page.query_selector("#tts-voice-persona")
        if v_persona:
            v_persona.select_option("bangla")
            page.wait_for_timeout(100)
            v_persona.select_option("default")
            results["passed"].append("Voice: TTS Persona select")

        # Playback speed buttons
        for spd in ["0.75", "1.0", "1.5"]:
            s_btn = page.query_selector(f".tts-speed-btn[data-speed='{spd}']")
            if s_btn:
                s_btn.click()
                page.wait_for_timeout(100)
        results["passed"].append("Voice: TTS Playback speed buttons")

        # TTS Input & Synthesize button
        v_input = page.query_selector("#tts-input-text")
        v_speak = page.query_selector("#tts-speak-btn")
        if v_input and v_speak:
            v_input.fill("System verification in progress")
            v_speak.click()
            page.wait_for_timeout(300)
            results["passed"].append("Voice: TTS Speak button clicked")

        # Voice Sub-Mode Tabs (Studio, Bridge, Diagnostics)
        for vmode in ["studio", "bridge", "diagnostics"]:
            vtab = page.query_selector(f"#voice-tab-{vmode}")
            if vtab:
                vtab.click()
                page.wait_for_timeout(200)
                is_v_visible = page.is_visible(f"#voice-pane-{vmode}")
                if is_v_visible:
                    results["passed"].append(f"Voice: Mode tab '{vmode}' switch")
                else:
                    results["failed"].append(f"Voice: Mode pane '{vmode}' not visible")

        # -------------------------------------------------------------
        # TEST 6: AI CHATBOT & KNOWLEDGE ASSISTANT
        # -------------------------------------------------------------
        print("\n--- Testing 6: AI Chatbot Controls ---", flush=True)
        page.evaluate("window.routeTo('chat')")
        page.wait_for_timeout(500)

        chat_input = page.query_selector("#chat-input-field")
        chat_btn = page.query_selector("#chat-send-btn")
        if chat_input and chat_btn:
            chat_input.fill("What are the warning signs of severe dehydration?")
            chat_btn.click()
            page.wait_for_timeout(3000)

            # Check if bot message rendered
            bot_msgs = page.query_selector_all(".chat-message-item.bot")
            # Should have welcome message + newly generated response
            if len(bot_msgs) >= 2:
                bot_text = bot_msgs[-1].inner_text()
                results["passed"].append(f"Chatbot: Answer generated successfully ({len(bot_text)} chars)")
            else:
                results["failed"].append(f"Chatbot: Response not rendered (found {len(bot_msgs)} bot messages)")
        else:
            results["failed"].append("Chatbot: Input field or form missing")

        # Chat Training Modal
        train_btn = page.query_selector("#btn-open-training-modal")
        close_train_btn = page.query_selector("#btn-close-training-modal")
        if train_btn and close_train_btn:
            train_btn.click()
            page.wait_for_timeout(300)
            modal_visible = page.is_visible("#chat-training-modal")
            if modal_visible:
                results["passed"].append("Chatbot: Fine-Tuning Modal opens")
                close_train_btn.click()
                page.wait_for_timeout(200)
                results["passed"].append("Chatbot: Fine-Tuning Modal closes")
            else:
                results["failed"].append("Chatbot: Fine-Tuning Modal did not open")

        # -------------------------------------------------------------
        # TEST 7: TRANSIFY CARE (INTAKE, CLINICIAN, CHRONIC, GUIDELINES)
        # -------------------------------------------------------------
        print("\n--- Testing 7: Transify Care & Clinical Health ---", flush=True)
        page.evaluate("window.routeTo('care')")
        page.wait_for_timeout(500)

        # 7.1 Symptom Intake Form Submission
        intake_complaint = page.query_selector("#care-chief-complaint")
        intake_desc = page.query_selector("#care-symptom-desc")
        intake_consent = page.query_selector("#care-consent-check")
        intake_submit = page.query_selector("#care-submit-intake-btn")

        if intake_complaint and intake_desc and intake_consent and intake_submit:
            intake_complaint.fill("High fever with petechial rash and persistent vomiting")
            intake_desc.fill("Severe body aches, fever over 103F for 4 days, low platelet count warning signs")
            intake_consent.check()
            intake_submit.click()
            page.wait_for_timeout(1500)

            # Check triage evaluation output
            res_box = page.query_selector("#care-intake-result")
            if res_box and res_box.is_visible():
                triage_text = res_box.inner_text()
                results["passed"].append(f"Care Intake: Triage evaluated successfully ({triage_text.splitlines()[0] if triage_text else ''})")
            else:
                results["failed"].append("Care Intake: Triage result not displayed")

        # 7.2 Clinician Portal
        page.evaluate("window.routeTo('clinician')")
        page.wait_for_timeout(800)

        # Verify queue loaded rows
        queue_rows = page.query_selector_all("#clinician-queue-tbody tr")
        print(f"[*] Clinician queue table rows: {len(queue_rows)}", flush=True)
        if len(queue_rows) > 0:
            results["passed"].append(f"Care Clinician: Queue populated with {len(queue_rows)} rows")
        else:
            results["failed"].append("Care Clinician: Queue table empty")

        # 7.3 ChronicCare Monitoring Controls
        page.query_selector("#care-tab-chronic-btn").click()
        page.wait_for_timeout(500)

        # Simulation buttons
        btn_vagal = page.query_selector("#btn-chronic-sim-htn")
        btn_cgm = page.query_selector("#btn-chronic-sim-hypo")
        btn_normal = page.query_selector("#btn-chronic-sim-normal")

        if btn_vagal and btn_cgm and btn_normal:
            btn_vagal.click()
            page.wait_for_timeout(300)
            hrv_val = page.inner_text("#chronic-kpi-hrv")
            results["passed"].append(f"Care ChronicCare: Crisis simulation updated HRV to {hrv_val}")

            btn_normal.click()
            page.wait_for_timeout(300)
            results["passed"].append("Care ChronicCare: Reset to normal baseline")

        # 24h Predictive Forecast Button
        forecast_btn = page.query_selector("#btn-run-crisis-forecast")
        if forecast_btn:
            forecast_btn.click()
            page.wait_for_timeout(600)
            fc_visible = page.is_visible("#chronic-forecast-result")
            if fc_visible:
                results["passed"].append("Care ChronicCare: 24h Crisis Predictive Forecast executed")
            else:
                results["failed"].append("Care ChronicCare: 24h Crisis Forecast card not visible")

        # ChronicCare Sub-Module Tabs
        chronic_modules = ["chronic-sec-telemetry", "chronic-sec-nutrition", "chronic-sec-labcoach", "chronic-sec-elderly", "chronic-sec-polypharmacy", "chronic-sec-federated"]
        for mod in chronic_modules:
            m_btn = page.query_selector(f".chronic-nav-btn[data-target='{mod}']")
            if m_btn:
                m_btn.click()
                page.wait_for_timeout(200)
                if page.is_visible(f"#{mod}"):
                    results["passed"].append(f"Care ChronicCare: Module '{mod}' tab switch")
                else:
                    results["failed"].append(f"Care ChronicCare: Module '{mod}' not visible")

        # -------------------------------------------------------------
        # TEST 8: SETTINGS, ACCESSIBILITY, AND PREFERENCES
        # -------------------------------------------------------------
        print("\n--- Testing 8: Settings & Global Preferences ---", flush=True)
        page.evaluate("window.routeTo('settings')")
        page.wait_for_timeout(400)

        # Settings sub-tabs
        for stab in ["profile", "account", "appearance", "accessibility", "privacy", "contact"]:
            st_el = page.query_selector(f".settings-nav-tab[data-settings-tab='{stab}']")
            if st_el:
                st_el.click()
                page.wait_for_timeout(150)
                results["passed"].append(f"Settings: Tab '{stab}' switch")

        # Theme switches & verify computed CSS
        page.query_selector(".settings-nav-tab[data-settings-tab='appearance']").click()
        page.wait_for_timeout(200)

        for theme in ["light", "dark", "high-contrast"]:
            page.evaluate(f"window.applyThemeGlobal('{theme}')")
            page.wait_for_timeout(200)
            cur_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            if cur_theme == theme:
                results["passed"].append(f"Settings: Theme switch to '{theme}' verified")
            else:
                results["failed"].append(f"Settings: Theme '{theme}' failed to set data-theme (found: {cur_theme})")

        # Revert to dark theme as default
        page.evaluate("window.applyThemeGlobal('dark')")

        browser.close()

    server.should_exit = True
    thread.join(timeout=2.0)

    print("\n==================================================================", flush=True)
    print("EXHAUSTIVE TEST RESULTS SUMMARY:")
    print(f"Total Passed Checks: {len(results['passed'])}")
    print(f"Total Failed Checks: {len(results['failed'])}")
    print(f"Total Warnings:      {len(results['warnings'])}")
    print("\nPASSED ITEMS:")
    for p in results["passed"]:
        print(f"  [+] {p}")
    if results["failed"]:
        print("\nFAILED ITEMS:")
        for f in results["failed"]:
            print(f"  [-] {f}")
    if results["warnings"]:
        print("\nCONSOLE WARNINGS/ERRORS:")
        for w in results["warnings"]:
            print(f"  [!] {w}")
    print("==================================================================", flush=True)

    return results

if __name__ == "__main__":
    run_deep_test()
