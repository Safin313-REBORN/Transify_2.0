"""
DOM-based XSS Prevention and Injection Safety Tests for Transify 2.0.
Verifies that CommunicationHub and Phraseboard use safe DOM construction (textContent,
addEventListener, replaceChildren) and never execute injected script, img, or svg handlers.
"""

import time
import pytest
from fastapi.testclient import TestClient

from src.api.server import app
from src.database.db import (
    create_user,
    create_hub_conversation,
    add_hub_message,
    add_user_phrase,
    get_connection
)


@pytest.fixture
def client():
    return TestClient(app, base_url="http://testserver")


XSS_PAYLOADS = [
    "<script>window.__xss_1=true;</script>",
    "<img src='invalid_image.jpg' onerror='window.__xss_2=true;'>",
    "<svg onload='window.__xss_3=true;'><circle r=10/></svg>",
    "Hello \" ' \\ \n &amp; &lt;script&gt; \u2028 \u2029 world!",
    "';alert('xss');//",
    "\"><script>alert(document.domain)</script>",
    "<iframe src=\"javascript:alert(1)\"></iframe>",
]


def test_api_preserves_xss_strings_literally_without_corruption(client):
    """Verifies backend API securely stores and returns special characters without corrupting or executing them."""
    email = f"xss_test_{int(time.time()*1000)}@transify.test"
    pwd = "SecurePassword123!_2026"
    client.post("/api/auth/register", json={"name": "XSS Tester", "email": email, "password": pwd, "consent_terms": True})

    # Create conversation
    conv_res = client.post("/api/hub/conversations", json={"title": "XSS Test Session"})
    assert conv_res.status_code == 200
    conv_id = conv_res.json()["conversation"]["id"]

    for idx, payload in enumerate(XSS_PAYLOADS):
        msg_res = client.post(f"/api/hub/conversations/{conv_id}/messages", json={
            "content": payload,
            "source": "typed"
        })
        assert msg_res.status_code == 200
        saved_content = msg_res.json()["message"]["content"]
        assert saved_content == payload

    # Read messages back
    list_res = client.get(f"/api/hub/conversations/{conv_id}/messages")
    assert list_res.status_code == 200
    retrieved_messages = list_res.json()["messages"]
    assert len(retrieved_messages) == len(XSS_PAYLOADS)
    for idx, payload in enumerate(XSS_PAYLOADS):
        assert retrieved_messages[idx]["content"] == payload


def test_custom_phrases_preserve_xss_strings_literally(client):
    """Verifies personal phrasebook saves and returns complex injection payloads literally."""
    email = f"phrase_xss_{int(time.time()*1000)}@transify.test"
    pwd = "SecurePassword123!_2026"
    client.post("/api/auth/register", json={"name": "Phrase XSS Tester", "email": email, "password": pwd, "consent_terms": True})

    for payload in XSS_PAYLOADS:
        phrase_res = client.post("/api/phrases", json={
            "text_en": payload,
            "text_bn": payload,
            "category": "Security"
        })
        assert phrase_res.status_code == 200
        data = phrase_res.json()["phrase"]
        assert data["text_en"] == payload
        assert data["text_bn"] == payload


def test_browser_dom_xss_prevention_in_hub_and_phraseboard(live_server, browser_instance):
    """
    Playwright browser test:
    Injects malicious XSS payloads into Communication Hub and Phraseboard,
    and verifies that NO scripts execute, NO alert or global flags are set,
    and text content is rendered literally using safe DOM APIs.
    """
    context = browser_instance.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    page.goto(live_server)

    # Inject test flags on window
    page.evaluate("""() => {
        window.__xss_executed = false;
        window.__alert_called = false;
        window.alert = () => { window.__alert_called = true; };
    }""")

    # Verify CommunicationHub renderFeed with malicious payloads
    result = page.evaluate("""() => {
        if (!window.CommunicationHub) return { status: 'no_hub' };

        window.CommunicationHub.messages = [
            { id: 'm1', content: '<script>window.__xss_executed=true;</script>', modality: 'typed', created_at: '10:00 AM' },
            { id: 'm2', content: '<img src=x onerror=\"window.__xss_executed=true;\">', modality: 'speech', created_at: '10:01 AM' },
            { id: 'm3', content: '<svg onload=\"window.__xss_executed=true;\"><rect width=10 height=10/></svg>', modality: 'sign', created_at: '10:02 AM' },
            { id: 'm4', content: 'Special: \" \\' \\\\ \\n &amp; &lt;script&gt; test', modality: 'braille', created_at: '10:03 AM' }
        ];

        window.CommunicationHub.renderFeed();

        const container = document.getElementById('hub-feed-container');
        const cards = container ? container.querySelectorAll('.hub-message-card') : [];
        const bodies = container ? Array.from(container.querySelectorAll('.hub-msg-body')).map(b => b.textContent) : [];

        // Verify that copy button handler does not throw syntax error with quotes
        let copyError = null;
        try {
            const copyBtn = container.querySelector('.hub-action-btn');
            if (copyBtn) copyBtn.click();
        } catch (e) {
            copyError = e.message;
        }

        return {
            cardCount: cards.length,
            bodies: bodies,
            xssExecuted: window.__xss_executed,
            alertCalled: window.__alert_called,
            copyError: copyError
        };
    }""")

    assert result["cardCount"] == 4
    assert result["xssExecuted"] is False
    assert result["alertCalled"] is False
    assert result["copyError"] is None
    assert "<script>window.__xss_executed=true;</script>" in result["bodies"]

    # Verify Phraseboard renderGrid with malicious payloads
    phrase_result = page.evaluate("""() => {
        if (!window.Phraseboard) return { status: 'no_phraseboard' };

        window.Phraseboard.phrases = [
            { id: 101, text_en: '<img src=x onerror=\"window.__xss_executed=true;\">', text_bn: 'বাংলা', category: 'General', is_favorite: false, is_custom: true },
            { id: 102, text_en: '\"><script>window.__xss_executed=true;</script>', text_bn: 'টেস্ট \" \\' ', category: 'General', is_favorite: true, is_custom: false }
        ];

        window.Phraseboard.renderGrid();

        const grid = document.getElementById('phraseboard-grid');
        const cards = grid ? grid.querySelectorAll('.phrase-card') : [];
        const enTexts = grid ? Array.from(grid.querySelectorAll('.phrase-text-en')).map(el => el.textContent) : [];

        // Click card to verify onPhraseClick works safely without script execution
        let clickError = null;
        try {
            if (cards.length > 0) cards[0].click();
        } catch (e) {
            clickError = e.message;
        }

        return {
            cardCount: cards.length,
            enTexts: enTexts,
            xssExecuted: window.__xss_executed,
            alertCalled: window.__alert_called,
            clickError: clickError
        };
    }""")

    assert phrase_result["cardCount"] == 2
    assert phrase_result["xssExecuted"] is False
    assert phrase_result["alertCalled"] is False
    assert phrase_result["clickError"] is None
    assert '<img src=x onerror="window.__xss_executed=true;">' in phrase_result["enTexts"]

    page.close()
    context.close()
