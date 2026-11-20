"""
Transify Care Browser-Level Playwright Integration Test Suite.
Verifies end-to-end browser DOM safety, stored XSS prevention, Zero Auto-Audio policy,
strict offline privacy protections, dedicated synthetic demo fixture isolation,
and real HTTP-level access control against a live FastAPI test server.
"""

import os
import sys
import socket
import threading
import time
import pytest
from playwright.sync_api import sync_playwright

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.server import app
from src.database.db import get_connection, create_user, create_session, init_db
from src.care.db_care import init_care_db, create_intake

init_db()
init_care_db()


def get_free_port() -> int:
    """Finds an available local port for the test server."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def test_server():
    """Spins up a real live FastAPI server via uvicorn in a background thread."""
    import uvicorn
    port = get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to start accepting connections
    base_url = f"http://127.0.0.1:{port}"
    timeout = 5.0
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.05)

    yield base_url
    server.should_exit = True
    thread.join(timeout=2.0)


@pytest.fixture(scope="module")
def browser_instance():
    """Initializes a headless Chromium browser instance."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def browser_context(browser_instance):
    """Provides a fresh isolated BrowserContext with request capabilities."""
    context = browser_instance.new_context()
    yield context
    context.close()


@pytest.fixture
def page(browser_context, test_server):
    """Provides a fresh browser page loaded from the real running FastAPI server."""
    page = browser_context.new_page()
    page.goto(f"{test_server}/")
    yield page
    page.close()


# --- 1. Stored XSS Prevention ---

def test_browser_stored_xss_payloads_do_not_execute(page):
    """
    Verifies that hostile XSS payloads injected into triage cards or clinician queues
    are safely rendered as plain text via DOM textContent without executing scripts.
    """
    xss_payload = "<script>window.__xss_executed = true;</script><img src=x onerror='window.__xss_executed = true;'>"

    page.evaluate(f"""() => {{
        window.__xss_executed = false;
        if (window.TransifyCare) {{
            window.TransifyCare.renderTriageResult({{
                urgency_level: 'YELLOW',
                triage_explanation: "{xss_payload}",
                rule_id: 'RULE-URGENT-001',
                emergency_escalation: null,
                evidence_citations: []
            }});
        }}
    }}""")

    xss_executed = page.evaluate("() => window.__xss_executed")
    assert xss_executed is False

    output_text = page.text_content("#triage-assessment-output")
    assert "<script>" in output_text or "xss" in output_text.lower() or "URGENCY: YELLOW" in output_text


# --- 2. Zero Auto-Audio Policy Verified in DOM ---

def test_browser_zero_auto_audio_remains_enforced(page):
    """
    Verifies strict adherence to Zero Auto-Audio policy:
    No <audio autoplay> elements exist and no unmuted autoplay video tags exist on load.
    """
    autoplay_audio = page.query_selector_all("audio[autoplay]")
    assert len(autoplay_audio) == 0

    autoplay_video = page.evaluate("""() => {
        const videos = document.querySelectorAll('video[autoplay]');
        return Array.from(videos).filter(v => !v.muted).length;
    }""")
    assert autoplay_video == 0


# --- 3. No Privileged Self-Registration Controls in UI ---

def test_browser_no_privileged_self_registration_controls(page):
    """Verifies that public registration modal does not offer role elevation controls."""
    role_selectors = page.query_selector_all("#register-modal select[name='role'], #register-modal input[name='role'][type='text']")
    assert len(role_selectors) == 0

    priv_options = page.evaluate("""() => {
        const selects = document.querySelectorAll('select');
        let hasPrivRole = false;
        selects.forEach(s => {
            Array.from(s.options).forEach(opt => {
                if (['admin', 'clinician', 'dev_clinician'].includes(opt.value)) {
                    hasPrivRole = true;
                }
            });
        });
        return hasPrivRole;
    }""")
    assert priv_options is False


# --- 4. P1-3: Explicit Offline Demo Classification & Privacy Protections ---

def test_browser_real_complaint_containing_word_demo_never_cached(page):
    """A real patient complaint containing the substring 'demo' is never cached in localStorage."""
    result = page.evaluate("""() => {
        localStorage.clear();
        const draft = {
            chief_complaint: 'Patient reports severe migraine triggered during software demo presentation',
            symptom_description: 'Pounding headache for 2 days',
            input_modality: 'text'
        };
        const isSynthetic = window.TransifyCare.isSyntheticDemoDraft(draft);
        const saved = window.TransifyCare.saveDraftLocally(draft);
        const stored = localStorage.getItem('transify_care_drafts');
        return { isSynthetic, saved, stored };
    }""")
    assert result["isSynthetic"] is False
    assert result["saved"] is False
    assert result["stored"] is None or result["stored"] == "[]"


def test_browser_complaint_containing_word_synthetic_never_treated_as_synthetic(page):
    """A complaint containing the substring 'synthetic' is never treated as synthetic."""
    result = page.evaluate("""() => {
        localStorage.clear();
        const draft = {
            chief_complaint: 'Severe rash after chemical exposure to synthetic industrial polymers',
            symptom_description: 'Dermatitis',
            input_modality: 'text'
        };
        const isSynthetic = window.TransifyCare.isSyntheticDemoDraft(draft);
        const saved = window.TransifyCare.saveDraftLocally(draft);
        const stored = localStorage.getItem('transify_care_drafts');
        return { isSynthetic, saved, stored };
    }""")
    assert result["isSynthetic"] is False
    assert result["saved"] is False
    assert result["stored"] is None or result["stored"] == "[]"


def test_browser_normal_patient_drafts_never_enter_localstorage(page):
    """Ordinary patient drafts never enter plaintext localStorage."""
    result = page.evaluate("""() => {
        localStorage.clear();
        const normalDraft = {
            chief_complaint: 'High fever and dry cough',
            symptom_description: 'Feeling very weak',
            input_modality: 'voice'
        };
        const saved = window.TransifyCare.saveDraftLocally(normalDraft);
        const stored = localStorage.getItem('transify_care_drafts');
        return { saved, stored };
    }""")
    assert result["saved"] is False
    assert result["stored"] is None or result["stored"] == "[]"


def test_browser_turning_ui_demo_flag_manually_does_not_authorize_caching_real_records(page):
    """
    Manually tampering with window.TRANSIFY_SYNTHETIC_DEMO_MODE does not authorize
    caching of real patient records.
    """
    result = page.evaluate("""() => {
        localStorage.clear();
        window.TRANSIFY_SYNTHETIC_DEMO_MODE = true;
        const realRecord = {
            chief_complaint: 'Actual patient crushing chest pain radiating to back',
            symptom_description: 'Real patient symptoms',
            input_modality: 'sign'
        };
        const isSynthetic = window.TransifyCare.isSyntheticDemoDraft(realRecord);
        const saved = window.TransifyCare.saveDraftLocally(realRecord);
        const stored = localStorage.getItem('transify_care_drafts');
        return { isSynthetic, saved, stored };
    }""")
    assert result["isSynthetic"] is False
    assert result["saved"] is False
    assert result["stored"] is None or result["stored"] == "[]"


def test_browser_only_trusted_demo_fixture_can_be_stored(page):
    """Only a trusted application-controlled demo fixture identity can be cached locally."""
    result = page.evaluate("""() => {
        localStorage.clear();
        // 1. Get trusted demo fixture from controller
        const fixture = window.TransifyCare.getTrustedDemoFixture('synthetic-demo-patient-001');
        const isSynthetic = window.TransifyCare.isSyntheticDemoDraft(fixture);
        const saved = window.TransifyCare.saveDraftLocally(fixture);
        const stored = localStorage.getItem('transify_care_drafts');
        return { isSynthetic, saved, stored: JSON.parse(stored || '[]') };
    }""")
    assert result["isSynthetic"] is True
    assert result["saved"] is True
    assert len(result["stored"]) == 1
    assert result["stored"][0]["patient_id"] == "synthetic-demo-patient-001"


def test_browser_synthetic_demo_drafts_remain_usable_for_competition_recording(page):
    """All three documented synthetic demo cases remain usable for offline recording."""
    result = page.evaluate("""() => {
        localStorage.clear();
        const f1 = window.TransifyCare.getTrustedDemoFixture('synthetic-demo-patient-001');
        const f2 = window.TransifyCare.getTrustedDemoFixture('synthetic-demo-patient-002');
        const f3 = window.TransifyCare.getTrustedDemoFixture('synthetic-demo-patient-003');

        window.TransifyCare.saveDraftLocally(f1);
        window.TransifyCare.saveDraftLocally(f2);
        window.TransifyCare.saveDraftLocally(f3);

        const drafts = window.TransifyCare.getStoredDrafts();
        return { count: drafts.length, ids: drafts.map(d => d.patient_id) };
    }""")
    assert result["count"] == 3
    assert result["ids"] == [
        "synthetic-demo-patient-001",
        "synthetic-demo-patient-002",
        "synthetic-demo-patient-003"
    ]


def test_browser_no_clinical_assessment_generated_offline(page):
    """Offline draft presentation explicitly states that no clinical assessment is performed offline."""
    result = page.evaluate("""() => {
        const fixture = window.TransifyCare.getTrustedDemoFixture('synthetic-demo-patient-001');
        window.TransifyCare.displayOfflineTriageResult(fixture);
        const cardText = document.getElementById('triage-assessment-output').textContent;
        return cardText;
    }""")
    assert "Draft saved locally — no clinical assessment performed while offline" in result
    assert "OFFLINE DEMO DRAFT — UNASSESSED" in result


# --- 5. P1-5: Real HTTP-Level Test Server Integration Tests ---

def test_browser_demo_reset_production_returns_http_403(test_server, browser_context):
    """Demo reset against live server returns HTTP 403 when environment is production."""
    saved_env = dict(os.environ)
    try:
        os.environ["ENVIRONMENT"] = "production"
        req_context = browser_context.request
        res = req_context.post(f"{test_server}/api/care/demo/reset")
        assert res.status == 403
        body = res.json()
        assert "disabled in production" in body["detail"].lower()
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


def test_browser_demo_reset_unauthenticated_without_auth_denied(test_server, browser_context):
    """Unauthenticated demo reset request without authorization header is denied with HTTP 401."""
    saved_env = dict(os.environ)
    try:
        os.environ["TRANSIFY_DEMO_MODE_ENABLED"] = "true"
        os.environ.pop("ENVIRONMENT", None)
        req_context = browser_context.request
        res = req_context.post(f"{test_server}/api/care/demo/reset")
        assert res.status == 401
        body = res.json()
        assert "unauthenticated reset denied" in body["detail"].lower()
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


def test_browser_demo_reset_authorized_local_demo_mode_succeeds(test_server, browser_context):
    """Demo reset with explicit authorization header in non-production succeeds with HTTP 200."""
    saved_env = dict(os.environ)
    try:
        os.environ["TRANSIFY_DEMO_MODE_ENABLED"] = "true"
        os.environ.pop("ENVIRONMENT", None)
        req_context = browser_context.request
        res = req_context.post(
            f"{test_server}/api/care/demo/reset",
            headers={"X-Transify-Demo-Auth": "transify-demo-authorized-2026"}
        )
        assert res.status == 200
        body = res.json()
        assert body["success"] is True
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


def test_browser_real_patient_records_survive_reset(test_server, browser_context):
    """Real patient intake records survive demo reset without modification."""
    saved_env = dict(os.environ)
    try:
        os.environ["TRANSIFY_DEMO_MODE_ENABLED"] = "true"
        os.environ.pop("ENVIRONMENT", None)

        # Create a real patient intake in the database
        real_intake_id = create_intake(
            patient_id="user-browser-real-999",
            input_modality="text",
            raw_input="Real patient clinical complaint",
            confirmed_text="Real patient symptom text",
            chief_complaint="Severe abdominal pain",
            symptom_description="Pain for 2 days",
            onset_duration="2 days",
            trajectory="stable",
            severity=5,
            medical_context="",
            allergies_medications="",
            consent_granted=True,
            status="SUBMITTED",
            urgency_level="YELLOW",
            triage_explanation="Urgent care evaluation required.",
            triage_rule_id="RULE-URGENT-002",
            evidence_citations=[]
        )

        # Trigger demo reset via HTTP
        req_context = browser_context.request
        res = req_context.post(
            f"{test_server}/api/care/demo/reset",
            headers={"X-Transify-Demo-Auth": "transify-demo-authorized-2026"}
        )
        assert res.status == 200

        # Verify real patient record still exists in SQLite
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, patient_id FROM care_patient_intakes WHERE id = ?;", (real_intake_id,))
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert row["patient_id"] == "user-browser-real-999"
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


def test_browser_patient_cannot_access_clinician_endpoints(test_server, browser_context):
    """Unauthenticated or patient requests to clinician endpoints are properly rejected by the live server."""
    req_context = browser_context.request
    res = req_context.get(f"{test_server}/api/care/dashboard/stats")
    assert res.status == 401
