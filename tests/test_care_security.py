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

    # 8. GET /api/care/evidence/search
    r8 = client.get("/api/care/evidence/search?q=fever")
    assert r8.status_code == 401

    # 9. POST /api/care/evidence/search
    r9 = client.post("/api/care/evidence/search", json={"query": "fever"})
    assert r9.status_code == 401


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


# --- 11. Controlled Development Synthetic Clinician Mode (Fail-Closed) ---

def test_dev_clinician_mode_and_production_guard(client):
    """Development synthetic clinician mode requires explicit opt-in and is strictly blocked in production."""
    # 1. Dev Mode with explicit opt-in
    old_opt = os.environ.get("TRANSIFY_DEV_CLINICIAN_ENABLED")
    old_env = os.environ.get("ENVIRONMENT")
    try:
        os.environ["TRANSIFY_DEV_CLINICIAN_ENABLED"] = "true"
        os.environ.pop("ENVIRONMENT", None)
        client.cookies.clear()
        res_dev = client.post("/api/care/dev/clinician-session")
        assert res_dev.status_code == 200
        assert res_dev.json()["success"] is True
        assert res_dev.json()["role"] == "clinician"

        # 2. Production Guard (blocks even when opt-in flag is true)
        os.environ["ENVIRONMENT"] = "production"
        client.cookies.clear()
        res_prod = client.post("/api/care/dev/clinician-session")
        assert res_prod.status_code == 403
        assert "disabled in production" in res_prod.json()["detail"].lower()
    finally:
        if old_opt is not None:
            os.environ["TRANSIFY_DEV_CLINICIAN_ENABLED"] = old_opt
        else:
            os.environ.pop("TRANSIFY_DEV_CLINICIAN_ENABLED", None)
        if old_env is not None:
            os.environ["ENVIRONMENT"] = old_env
        else:
            os.environ.pop("ENVIRONMENT", None)


# --- 12. P0-1: Prevent Public Clinician Self-Registration ---

def test_public_registration_without_role_creates_normal_user(client):
    """Public registration without a role creates a normal user with role 'user'."""
    import uuid
    client.cookies.clear()
    email = f"normal_user_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/auth/register", json={
        "name": "Standard User One",
        "email": email,
        "password": "SecurePassword2026!#",
        "consent_terms": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "user"

    # Inspect the database to verify the server-stored role
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE email = ? COLLATE NOCASE;", (email,))
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row["role"] == "user"


def test_public_registration_with_role_clinician_cannot_elevate(client):
    """Public registration requesting role=clinician strictly receives role 'user'."""
    import uuid
    client.cookies.clear()
    email = f"fake_clinician_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/auth/register", json={
        "name": "Attempted Clinician",
        "email": email,
        "password": "SecurePassword2026!#",
        "role": "clinician",
        "consent_terms": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "user"

    # Inspect DB: verified role is 'user', NEVER 'clinician'
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE email = ? COLLATE NOCASE;", (email,))
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row["role"] == "user"


def test_public_registration_with_role_admin_cannot_elevate(client):
    """Public registration requesting role=admin strictly receives role 'user'."""
    import uuid
    client.cookies.clear()
    email = f"fake_admin_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/auth/register", json={
        "name": "Attempted Admin",
        "email": email,
        "password": "SecurePassword2026!#",
        "role": "admin",
        "consent_terms": True
    })
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "user"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE email = ? COLLATE NOCASE;", (email,))
    row = cursor.fetchone()
    conn.close()
    assert row["role"] == "user"


def test_public_registration_with_role_dev_clinician_cannot_elevate(client):
    """Public registration requesting role=dev_clinician strictly receives role 'user'."""
    import uuid
    client.cookies.clear()
    email = f"fake_dev_clinician_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/auth/register", json={
        "name": "Attempted Dev Clinician",
        "email": email,
        "password": "SecurePassword2026!#",
        "role": "dev_clinician",
        "consent_terms": True
    })
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "user"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE email = ? COLLATE NOCASE;", (email,))
    row = cursor.fetchone()
    conn.close()
    assert row["role"] == "user"


def test_newly_registered_normal_user_receives_403_on_clinician_review(client):
    """A newly registered normal user is rejected with HTTP 403 when calling clinician review."""
    import uuid
    client.cookies.clear()
    email = f"normal_denied_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post("/api/auth/register", json={
        "name": "Non Clinician User",
        "email": email,
        "password": "SecurePassword2026!#",
        "role": "clinician",  # Attempted escalation
        "consent_terms": True
    })
    assert reg_res.status_code == 200

    # User's session cookie is set; now attempt to review intake #1
    rev_res = client.post("/api/care/intake/1/review", json={
        "action": "COMPLETED",
        "urgency_override": "NONE"
    })
    assert rev_res.status_code == 403
    assert "Clinician authorization required" in rev_res.json()["detail"]


def test_existing_verified_clinician_retains_authorized_access(client):
    """Verified clinician accounts created via administrative processes retain review access."""
    clinician_user = register_and_login(client, "Dr. Verified", "dr_verified_access@example.com", role="clinician")
    assert clinician_user["role"] == "clinician"

    # Create an intake for reviewing
    intake_res = client.post("/api/care/intake", json={
        "input_modality": "text",
        "confirmed_text": "Fever and headache for 2 days",
        "chief_complaint": "Fever",
        "symptom_description": "Fever and headache",
        "severity": 3,
        "consent_granted": True
    })
    assert intake_res.status_code == 201
    intake_id = intake_res.json()["intake_id"]

    # Clinician review should succeed
    rev_res = client.post(f"/api/care/intake/{intake_id}/review", json={
        "action": "ACCEPTED",
        "urgency_override": "NONE",
        "clinical_notes": "Verified clinician approval."
    })
    assert rev_res.status_code == 200
    assert rev_res.json()["success"] is True


# --- 13. P0-2: Fail-Closed Development Clinician Mode Suite ---

def test_dev_clinician_mode_fail_closed_scenarios(client):
    """Thoroughly tests fail-closed behavior across all environment configurations."""
    from src.database.db import is_dev_clinician_enabled, is_production

    saved_env = dict(os.environ)
    try:
        # Scenario A: Missing environment variable -> disabled by default
        os.environ.pop("TRANSIFY_DEV_CLINICIAN_ENABLED", None)
        os.environ.pop("ENVIRONMENT", None)
        os.environ.pop("RAILWAY_ENVIRONMENT", None)
        os.environ.pop("TRANSIFY_ENV", None)
        assert is_dev_clinician_enabled() is False

        client.cookies.clear()
        res_missing = client.post("/api/care/dev/clinician-session")
        assert res_missing.status_code == 403

        # Scenario B: Explicit false
        os.environ["TRANSIFY_DEV_CLINICIAN_ENABLED"] = "false"
        assert is_dev_clinician_enabled() is False
        res_false = client.post("/api/care/dev/clinician-session")
        assert res_false.status_code == 403

        # Scenario C: Explicit true in local dev -> allowed
        os.environ["TRANSIFY_DEV_CLINICIAN_ENABLED"] = "true"
        assert is_dev_clinician_enabled() is True
        res_true = client.post("/api/care/dev/clinician-session")
        assert res_true.status_code == 200

        # Scenario D: Production environment overrides explicit true -> disabled
        os.environ["ENVIRONMENT"] = "production"
        os.environ["TRANSIFY_DEV_CLINICIAN_ENABLED"] = "true"
        assert is_production() is True
        assert is_dev_clinician_enabled() is False
        res_prod = client.post("/api/care/dev/clinician-session")
        assert res_prod.status_code == 403

        # Scenario E: Conflicting indicators (TRANSIFY_ENV=production, ENVIRONMENT=development)
        os.environ["TRANSIFY_ENV"] = "production"
        os.environ["ENVIRONMENT"] = "development"
        assert is_production() is True
        assert is_dev_clinician_enabled() is False

        # Scenario F: Railway production configuration
        os.environ.pop("TRANSIFY_ENV", None)
        os.environ.pop("ENVIRONMENT", None)
        os.environ["RAILWAY_ENVIRONMENT"] = "production"
        assert is_production() is True
        assert is_dev_clinician_enabled() is False
        res_railway = client.post("/api/care/dev/clinician-session")
        assert res_railway.status_code == 403
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


# --- 14. P1-3: Protect Demo Reset ---

def test_demo_reset_production_guard_and_data_preservation(client):
    """Demo reset endpoint is blocked in production and preserves real patient records in development."""
    saved_env = dict(os.environ)
    try:
        # Register a real user and submit real patient intake
        user = register_and_login(client, "Real Patient", "real_patient_persist@example.com", role="user")
        real_intake_res = client.post("/api/care/intake", json={
            "input_modality": "text",
            "confirmed_text": "Real patient symptom records must never be deleted",
            "chief_complaint": "Persistent abdominal ache",
            "symptom_description": "Severe pain",
            "severity": 4,
            "consent_granted": True
        })
        assert real_intake_res.status_code == 201
        real_intake_id = real_intake_res.json()["intake_id"]

        # 1. In production -> demo reset must be rejected with HTTP 403
        os.environ["ENVIRONMENT"] = "production"
        res_prod_reset = client.post("/api/care/demo/reset")
        assert res_prod_reset.status_code == 403
        assert "disabled in production" in res_prod_reset.json()["detail"].lower()

        # 2. In non-production -> demo reset succeeds
        os.environ.pop("ENVIRONMENT", None)
        res_dev_reset = client.post("/api/care/demo/reset")
        assert res_dev_reset.status_code == 200
        assert res_dev_reset.json()["success"] is True

        # Verify real patient intake was NOT deleted!
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, patient_id FROM care_patient_intakes WHERE id = ?;", (real_intake_id,))
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert row["patient_id"] == f"user-{user['id']}"
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


# --- 15. P1-4: Clarify Evidence Search Access ---

def test_evidence_search_authenticated_access(client):
    """Evidence search requires authenticated session for both GET and POST requests."""
    client.cookies.clear()

    # Unauthenticated -> 401
    assert client.get("/api/care/evidence/search?q=dengue").status_code == 401
    assert client.post("/api/care/evidence/search", json={"query": "dengue"}).status_code == 401

    # Authenticated -> 200 with citations
    register_and_login(client, "Search User", "search_user@example.com", role="user")
    res_get = client.get("/api/care/evidence/search?q=dengue")
    assert res_get.status_code == 200
    assert "citations" in res_get.json()

    res_post = client.post("/api/care/evidence/search", json={"query": "dengue"})
    assert res_post.status_code == 200
    assert "citations" in res_post.json()
