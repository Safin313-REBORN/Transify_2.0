"""
Transify Care Route-Level Security & Access Control Test Suite.
Verifies HTTP-level role-based access control, cross-patient data isolation,
clinician authorization, mandatory consent, dashboard data minimization,
stored-XSS prevention, and SQLite audit-log append-only database triggers.
"""

import os
import sys
import sqlite3
import pytest
from fastapi.testclient import TestClient

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.server import app
from src.database.db import (
    create_user,
    create_session,
    get_connection,
    init_db
)
from src.care.db_care import init_care_db, log_care_audit

# Initialize databases
init_db()
init_care_db()

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.cookies.clear()
        yield test_client


def register_and_login(client: TestClient, name: str, email: str, role: str = "user") -> dict:
    """Helper to create a user and establish an authenticated session cookie."""
    pwd = "SecurePassword2026!#"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role FROM users WHERE email = ? COLLATE NOCASE;", (email.lower(),))
    row = cursor.fetchone()
    conn.close()

    if not row:
        user = create_user(name=name, email=email, password=pwd, role=role, consent_terms=True)
    else:
        user = dict(row)

    token = create_session(user["id"])
    client.cookies.set("transify_session", token)
    return user


# --- 1. Unauthenticated Requests Return 401 ---

def test_unauthenticated_requests_return_401(client):
    """All Care endpoints must reject unauthenticated requests with HTTP 401."""
    client.cookies.clear()

    # 1. POST /api/care/intake
    r1 = client.post("/api/care/intake", json={
        "input_modality": "text",
        "confirmed_text": "Fever and cough",
        "chief_complaint": "Fever",
        "symptom_description": "Fever for 2 days",
        "consent_granted": True
    })
    assert r1.status_code == 401

    # 2. GET /api/care/intake/{id}
    r2 = client.get("/api/care/intake/1")
    assert r2.status_code == 401

    # 3. GET /api/care/intakes
    r3 = client.get("/api/care/intakes")
    assert r3.status_code == 401

    # 4. POST /api/care/intake/{id}/review
    r4 = client.post("/api/care/intake/1/review", json={
        "action": "COMPLETED",
        "urgency_override": "NONE"
    })
    assert r4.status_code == 401

    # 5. GET /api/care/dashboard/stats
    r5 = client.get("/api/care/dashboard/stats")
    assert r5.status_code == 401

    # 6. POST /api/care/offline/sync
    r6 = client.post("/api/care/offline/sync", json={
        "client_id": "test-device",
        "drafts": []
    })
    assert r6.status_code == 401

    # 7. GET /api/care/sources
    r7 = client.get("/api/care/sources")
    assert r7.status_code == 401


# --- 2. Patient Cross-User Isolation (Patient A vs Patient B) ---

def test_patient_cross_user_isolation(client):
    """Patient A cannot retrieve or modify Patient B's intake records (HTTP 403)."""
    # 1. Login as Patient A and submit intake
    user_a = register_and_login(client, "Patient Alpha", "patient_a@example.com", role="user")
    res_a = client.post("/api/care/intake", json={
        "input_modality": "sign",
        "confirmed_text": "Severe crushing chest pain radiating to left arm",
        "chief_complaint": "Severe crushing chest pain",
        "symptom_description": "Substernal pressure, sweating",
        "severity": 9,
        "trajectory": "worsening",
        "onset_duration": "45 minutes",
        "consent_granted": True
    })
    assert res_a.status_code == 201
    intake_id = res_a.json()["intake_id"]
    assert res_a.json()["patient_id"] == f"user-{user_a['id']}"

    # Verify Patient A can read their own intake
    res_own = client.get(f"/api/care/intake/{intake_id}")
    assert res_own.status_code == 200
    assert res_own.json()["patient_id"] == f"user-{user_a['id']}"

    # 2. Switch session to Patient B
    user_b = register_and_login(client, "Patient Beta", "patient_b@example.com", role="user")
    assert user_b["id"] != user_a["id"]

    # Patient B attempts to access Patient A's intake -> 403 Forbidden
    res_b = client.get(f"/api/care/intake/{intake_id}")
    assert res_b.status_code == 403
    assert "Access denied" in res_b.json()["detail"]


# --- 3. Patient Cannot Submit Clinician Review ---

def test_patient_cannot_submit_clinician_review(client):
    """Patient role cannot submit clinician reviews (HTTP 403)."""
    user_p = register_and_login(client, "Patient Charlie", "patient_c@example.com", role="user")

    # Create intake
    res = client.post("/api/care/intake", json={
        "input_modality": "text",
        "confirmed_text": "Headache for 1 day",
        "chief_complaint": "Headache",
        "symptom_description": "Mild headache",
        "severity": 3,
        "consent_granted": True
    })
    intake_id = res.json()["intake_id"]

    # Patient attempts to review intake -> 403 Forbidden
    rev_res = client.post(f"/api/care/intake/{intake_id}/review", json={
        "action": "COMPLETED",
        "urgency_override": "GREEN",
        "override_reason": "Patient self-review attempt"
    })
    assert rev_res.status_code == 403
    assert "Clinician authorization required" in rev_res.json()["detail"]


# --- 4. Fake Clinician Identity is Ignored & Replaced ---

def test_fake_clinician_identity_is_ignored(client):
    """Client-supplied clinician IDs or names are completely ignored; server derives identity."""
    # Login as verified clinician
    user_doc = register_and_login(client, "Dr. Verified Clinician", "doctor_v@example.com", role="clinician")

    # Create test intake under clinician or separate patient
    intake_res = client.post("/api/care/intake", json={
        "input_modality": "voice",
        "confirmed_text": "High fever and persistent vomiting",
        "chief_complaint": "High fever",
        "symptom_description": "High fever for 3 days",
        "severity": 7,
        "trajectory": "worsening",
        "consent_granted": True
    })
    intake_id = intake_res.json()["intake_id"]

    # Clinician reviews, attempting to spoof clinician_id and clinician_name
    rev_res = client.post(f"/api/care/intake/{intake_id}/review", json={
        "clinician_id": "spoofed-fake-doctor-999",
        "clinician_name": "Dr. Impostor",
        "action": "ACCEPTED",
        "urgency_override": "NONE",
        "clinical_notes": "Assessed and admitted to ward"
    })
    assert rev_res.status_code == 200
    data = rev_res.json()
    # Server identity MUST override client spoof
    assert data["clinician_id"] == f"clinician-{user_doc['id']}"
    assert data["clinician_name"] == user_doc["name"]


# --- 5. Clinician Override Requires Justification ---

def test_clinician_override_requires_justification(client):
    """Urgency override without documented justification must be rejected with HTTP 400."""
    register_and_login(client, "Dr. Reviewer Two", "doctor_two@example.com", role="clinician")

    intake_res = client.post("/api/care/intake", json={
        "input_modality": "text",
        "confirmed_text": "Mild dry cough",
        "chief_complaint": "Mild cough",
        "symptom_description": "Occasional cough",
        "severity": 2,
        "consent_granted": True
    })
    intake_id = intake_res.json()["intake_id"]

    # Override without reason -> 400 Bad Request
    fail_res = client.post(f"/api/care/intake/{intake_id}/review", json={
        "action": "OVERRIDDEN",
        "urgency_override": "YELLOW",
        "override_reason": ""
    })
    assert fail_res.status_code == 400
    assert "justification is required" in fail_res.json()["detail"]

    # Override with documented justification -> 200 OK
    good_res = client.post(f"/api/care/intake/{intake_id}/review", json={
        "action": "OVERRIDDEN",
        "urgency_override": "YELLOW",
        "override_reason": "Patient has underlying severe chronic obstructive pulmonary disease.",
        "clinical_notes": "Upgraded urgency due to high-risk comorbid pulmonary history."
    })
    assert good_res.status_code == 200


# --- 6. Missing Consent is Rejected ---

def test_missing_consent_is_rejected(client):
    """Intake omitting consent_granted or passing false must be rejected without processing."""
    register_and_login(client, "Patient Consent Test", "consent_test@example.com", role="user")

    # 1. Missing field in JSON -> 422 Unprocessable Entity
    r_missing = client.post("/api/care/intake", json={
        "input_modality": "text",
        "confirmed_text": "Pain in shoulder",
        "chief_complaint": "Pain",
        "symptom_description": "Shoulder pain"
    })
    assert r_missing.status_code == 422

    # 2. consent_granted = False -> 400 Bad Request
    r_false = client.post("/api/care/intake", json={
        "input_modality": "text",
        "confirmed_text": "Pain in shoulder",
        "chief_complaint": "Pain",
        "symptom_description": "Shoulder pain",
        "consent_granted": False
    })
    assert r_false.status_code == 400
    assert "consent is mandatory" in r_false.json()["detail"]


# --- 7. Dashboard Stats Does Not Leak Sensitive PHI ---

def test_dashboard_stats_does_not_leak_phi(client):
    """Dashboard statistics return aggregated numbers only, never leaking patient names or complaints."""
    register_and_login(client, "Stats Viewer", "stats_viewer@example.com", role="user")
    res = client.get("/api/care/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_intakes" in data
    assert "urgency_distribution" in data
    # Ensure no patient identifiers or personal medical text are present in the stats envelope
    assert "patient_id" not in data
    assert "chief_complaint" not in data
    assert "records" not in data


# --- 8. Offline Sync Strictly Attributes Patient to Authenticated Session ---

def test_offline_sync_patient_isolation(client):
    """Offline sync forces patient_id to the authenticated session, preventing spoofing."""
    user = register_and_login(client, "Sync User", "sync_user@example.com", role="user")

    res = client.post("/api/care/offline/sync", json={
        "client_id": "tablet-offline-sync-device",
        "drafts": [
            {
                "patient_id": "spoofed-other-patient-999",
                "input_modality": "braille",
                "confirmed_text": "Mild throat tickle",
                "chief_complaint": "Throat tickle",
                "symptom_description": "Slight tickle in throat",
                "severity": 1,
                "consent_granted": True
            }
        ]
    })
    assert res.status_code == 200
    data = res.json()
    assert data["synced_count"] == 1
    assert data["patient_id"] == f"user-{user['id']}"

    # Verify in DB that intake belongs to user-{user['id']}, NOT spoofed ID
    intake_id = data["intake_ids"][0]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM care_patient_intakes WHERE id = ?;", (intake_id,))
    row = cursor.fetchone()
    conn.close()
    assert row["patient_id"] == f"user-{user['id']}"


# --- 9. Stored XSS Prevention ---

def test_stored_xss_payload_safety(client):
    """Hostile XSS injection strings in patient input are stored and retrieved safely as text."""
    register_and_login(client, "XSS Tester", "xss_tester@example.com", role="user")

    xss_payload = "<script>alert('XSS-TEST')</script><img src=x onerror=alert(1)>\" onload=\"alert(1)\""
    res = client.post("/api/care/intake", json={
        "input_modality": "text",
        "raw_input": xss_payload,
        "confirmed_text": xss_payload,
        "chief_complaint": xss_payload,
        "symptom_description": xss_payload,
        "severity": 1,
        "consent_granted": True
    })
    assert res.status_code == 201
    intake_id = res.json()["intake_id"]

    # Retrieve intake
    rec_res = client.get(f"/api/care/intake/{intake_id}")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    # Verifies literal string storage without executing or corrupting the response
    assert rec_data["chief_complaint"] == xss_payload


# --- 10. Audit Log Append-Only Database Triggers ---

def test_audit_log_append_only_triggers():
    """Direct SQL UPDATE or DELETE on care_audit_logs must be aborted by SQLite triggers."""
    # Insert test audit log first
    log_care_audit("TEST_EVENT", "system-test", "SYSTEM", None, {"test": True})

    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Attempt direct UPDATE -> must fail with append-only trigger abort
        with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as exc_update:
            cursor.execute("UPDATE care_audit_logs SET event_type = 'TAMPERED' WHERE actor_id = 'system-test';")
        assert "append-only" in str(exc_update.value).lower()
        conn.rollback()

        # Attempt direct DELETE -> must fail with append-only trigger abort
        with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as exc_delete:
            cursor.execute("DELETE FROM care_audit_logs WHERE actor_id = 'system-test';")
        assert "append-only" in str(exc_delete.value).lower()
        conn.rollback()
    finally:
        conn.close()


# --- 11. Controlled Development Synthetic Clinician Mode ---

def test_dev_clinician_mode_and_production_guard(client):
    """Development synthetic clinician mode works in dev but is strictly blocked in production."""
    # 1. Dev Mode (Default)
    res_dev = client.post("/api/care/dev/clinician-session")
    assert res_dev.status_code == 200
    assert res_dev.json()["success"] is True
    assert res_dev.json()["role"] == "clinician"

    # 2. Production Guard
    old_env = os.environ.get("ENVIRONMENT")
    try:
        os.environ["ENVIRONMENT"] = "production"
        client.cookies.clear()
        res_prod = client.post("/api/care/dev/clinician-session")
        assert res_prod.status_code == 403
        assert "disabled in production" in res_prod.json()["detail"]
    finally:
        if old_env is not None:
            os.environ["ENVIRONMENT"] = old_env
        else:
            os.environ.pop("ENVIRONMENT", None)
