"""
Tests for Transify AI Chatbot & Knowledge Training Engine.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.server import app

client = TestClient(app)


def test_chatbot_status():
    """Verify chatbot status endpoint returns training diagnostics."""
    res = client.get("/api/chat/status")
    assert res.status_code == 200
    data = res.json()
    assert "model_name" in data
    assert "accuracy" in data
    assert "final_loss" in data
    assert "total_documents" in data


def test_chatbot_clinical_fever_query():
    """Verify clinical RAG guideline response for febrile illness."""
    res = client.post("/api/chat/message", json={
        "message": "I have a high fever and headache, what should I do?",
        "language": "en"
    })
    assert res.status_code == 200
    data = res.json()
    assert "Hydration" in data["response"] or "Paracetamol" in data["response"]
    assert data["domain"] == "care_clinical"
    assert data["confidence"] > 0.8
    assert len(data["citations"]) > 0


def test_chatbot_emergency_red_flag():
    """Verify immediate emergency detection for acute chest pain."""
    res = client.post("/api/chat/message", json={
        "message": "I am experiencing severe crushing chest pain radiating to left arm",
        "language": "en"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_emergency"] is True
    assert "EMERGENCY" in data["response"] or "999" in data["response"] or "911" in data["response"]
    assert data["domain"] == "emergency"


def test_chatbot_sign_language_inquiry():
    """Verify sign language guide response."""
    res = client.post("/api/chat/message", json={
        "message": "How do I use the sign translator with camera?",
        "language": "en"
    })
    assert res.status_code == 200
    data = res.json()
    assert "Sign" in data["response"]
    assert data["domain"] == "sign_language"
    assert len(data["suggested_replies"]) > 0


def test_chatbot_braille_inquiry():
    """Verify Braille Grade 1 vs Grade 2 contracted explanation."""
    res = client.post("/api/chat/message", json={
        "message": "Explain the difference between Grade 1 and Grade 2 Braille",
        "language": "en"
    })
    assert res.status_code == 200
    data = res.json()
    assert "Grade 1" in data["response"]
    assert "Grade 2" in data["response"]
    assert data["domain"] == "braille_literacy"


def test_chatbot_bengali_support():
    """Verify multilingual support for Bengali inquiries."""
    res = client.post("/api/chat/message", json={
        "message": "আমার জ্বর হয়েছে কি করব",
        "language": "bn"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["confidence"] > 0.75
    assert len(data["response"]) > 20


def test_chatbot_training_endpoint():
    """Verify iterative fine-tuning/training updates loss and weights."""
    res = client.post("/api/chat/train", json={
        "epochs": 5,
        "learning_rate": 0.03
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "metrics" in data
    assert len(data["metrics"]["loss_curve"]) == 5
    # Verify loss decreases across epochs
    assert data["metrics"]["loss_curve"][-1] < data["metrics"]["loss_curve"][0]


def test_chatbot_custom_training_sample():
    """Verify adding custom training sample and querying it immediately."""
    custom_sample = {
        "id": "custom_allergy_test",
        "domain": "care_clinical",
        "keywords": ["peanut allergy", "anaphylaxis test", "allergy reaction"],
        "patterns": ["what is the protocol for severe peanut allergy"],
        "response": "Administer intramuscular Epinephrine (EpiPen) into anterolateral thigh immediately and call emergency services.",
        "citations": ["Clinical Allergy & Anaphylaxis Protocol 2026"],
        "suggested_replies": ["EpiPen guide", "Call 999"]
    }

    train_res = client.post("/api/chat/train", json={
        "epochs": 3,
        "learning_rate": 0.02,
        "custom_samples": [custom_sample]
    })
    assert train_res.status_code == 200

    query_res = client.post("/api/chat/message", json={
        "message": "what is the protocol for severe peanut allergy"
    })
    assert query_res.status_code == 200
    assert "Epinephrine" in query_res.json()["response"]
