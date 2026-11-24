"""
Transify Comprehensive Clinical Safety Matrix & Security Assurance Test Suite.
Verifies Phase 1 (Authentication Security, IDOR, Session Revocation) and Phase 2 (Deterministic Clinical Safety).
"""

import pytest
import os
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.api.server import app
from src.care.triage import evaluate_triage, EMERGENCY_CONTACTS, DETERMINISTIC_RULES
from src.care.clinical_rag import search_clinical_evidence
from src.database.db import (
    create_user,
    create_session,
    get_user_by_session,
    revoke_session,
    authenticate_user,
    init_db
)

VALID_PWD = "TransifySecurePass2026!"


# ============================================================================
# PHASE 1: AUTHENTICATION & SECURITY ASSURANCE
# ============================================================================

def test_session_revocation_via_bearer_token_logout():
    """Verifies that logging out with a Bearer token revokes the session on the server."""
    init_db()
    client = TestClient(app)
    email = f"user_logout_{os.urandom(4).hex()}@transify.test"
    user = create_user("Logout Test User", email, VALID_PWD, role="user", consent_terms=True)
    raw_token = create_session(user["id"], duration_days=1)

    # Verify session is initially valid
    session_user = get_user_by_session(raw_token)
    assert session_user is not None
    assert session_user["id"] == user["id"]

    # Call /api/auth/logout with Bearer token header
    resp = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {raw_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Verify session is now revoked in database
    revoked_user = get_user_by_session(raw_token)
    assert revoked_user is None


def test_production_guard_prevents_demo_credentials_seeding():
    """Verifies that production environment blocks automatic seeding of demo credentials."""
    with patch("src.database.db.is_production", return_value=True):
        init_db()
        auth_res = authenticate_user("demo@transify.ai", "transify2026demo")
        assert auth_res is None or auth_res.get("role") != "dev_clinician"


def test_normal_user_cannot_escalate_role_via_registration():
    """Verifies that public registration ignores requested role and assigns role 'user'."""
    client = TestClient(app)
    email = f"attacker_{os.urandom(4).hex()}@transify.test"
    reg_payload = {
        "name": "Attacker",
        "email": email,
        "password": VALID_PWD,
        "role": "clinician",
        "consent_terms": True
    }
    resp = client.post("/api/auth/register", json=reg_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["role"] == "user"


def test_unauthenticated_request_to_intake_rejected():
    """Verifies unauthenticated callers receive HTTP 401 on protected care endpoints."""
    fresh_client = TestClient(app)
    intake_payload = {
        "input_modality": "text",
        "raw_input": "Fever",
        "confirmed_text": "High fever",
        "chief_complaint": "High fever",
        "symptom_description": "Fever over 102F",
        "consent_granted": True
    }
    resp = fresh_client.post("/api/care/intake", json=intake_payload)
    assert resp.status_code == 401


def test_patient_cannot_view_other_patient_intake_idor():
    """Verifies cross-patient IDOR protection: Patient A cannot read Patient B's intake."""
    p_a = create_user("Patient A", f"patient_a_{os.urandom(4).hex()}@test.com", VALID_PWD, "user", True)
    tok_a = create_session(p_a["id"], 1)

    p_b = create_user("Patient B", f"patient_b_{os.urandom(4).hex()}@test.com", VALID_PWD, "user", True)
    tok_b = create_session(p_b["id"], 1)

    # Client for Patient B creates intake
    client_b = TestClient(app)
    b_payload = {
        "input_modality": "text",
        "confirmed_text": "Private Condition Patient B",
        "chief_complaint": "Private medical history",
        "symptom_description": "Sensitive details",
        "consent_granted": True
    }
    intake_res = client_b.post(
        "/api/care/intake",
        json=b_payload,
        headers={"Authorization": f"Bearer {tok_b}"}
    )
    assert intake_res.status_code == 201
    intake_id = intake_res.json()["intake_id"]

    # Fresh client for Patient A attempts to view Patient B's intake
    client_a = TestClient(app)
    idor_res = client_a.get(
        f"/api/care/intake/{intake_id}",
        headers={"Authorization": f"Bearer {tok_a}"}
    )
    assert idor_res.status_code == 403


# ============================================================================
# PHASE 2: CLINICAL SAFETY TEST MATRIX
# ============================================================================

def test_clinical_emergency_red_flags():
    """Verifies that emergency red flag conditions evaluate to RED and include emergency contacts."""
    red_cases = [
        ("Crushing chest pain radiating to left arm", "Severe pressure in chest, sweating", 9, "stable"),
        ("Severe shortness of breath, cannot breathe", "Gasping for air, cyanosis around lips", 8, "worsening"),
        ("Face drooping and slurred speech", "Sudden arm weakness on right side (FAST stroke)", 7, "sudden"),
        ("Massive uncontrolled bleeding", "Vomiting large volumes of blood", 9, "worsening"),
    ]
    for complaint, desc, sev, traj in red_cases:
        res = evaluate_triage(
            chief_complaint=complaint,
            symptom_description=desc,
            severity=sev,
            trajectory=traj
        )
        assert res["urgency_level"] == "RED", f"Failed for {complaint}"
        assert res["can_wait"] is False
        assert res["requires_clinician_review"] is True
        assert res["emergency_escalation"] is not None
        assert res["emergency_escalation"]["hotline"] == "999"
        assert res["emergency_escalation"]["health_helpline"] == "16263"


def test_clinical_high_risk_yellow_symptoms():
    """Verifies that high-risk acute symptoms evaluate to YELLOW and require same-day review."""
    yellow_cases = [
        ("High fever over 103F with petechial rash", "Severe body aches, tropical area dengue concern", 6, "worsening"),
        ("Severe acute abdominal pain", "Sharp localized lower right quadrant abdominal pain", 7, "stable"),
        ("Persistent vomiting unable to keep water down", "Vomiting for 18 hours, dry mouth, dehydration", 6, "worsening"),
    ]
    for complaint, desc, sev, traj in yellow_cases:
        res = evaluate_triage(
            chief_complaint=complaint,
            symptom_description=desc,
            severity=sev,
            trajectory=traj
        )
        assert res["urgency_level"] == "YELLOW", f"Failed for {complaint}"
        assert res["can_wait"] is False
        assert res["requires_clinician_review"] is True


def test_clinical_empty_and_insufficient_information_fails_safe():
    """Verifies that empty or insufficient information fails safely without reassurance."""
    empty_cases = [
        ("", "", 1, "stable"),
        ("   ", "", 1, "stable"),
        ("None", "", 1, "stable"),
        ("Unsure", "", 1, "stable")
    ]
    for complaint, desc, sev, traj in empty_cases:
        res = evaluate_triage(
            chief_complaint=complaint,
            symptom_description=desc,
            severity=sev,
            trajectory=traj
        )
        assert res["urgency_level"] in ("INSUFFICIENT_INFORMATION", "REVIEW_REQUIRED")
        assert res["can_wait"] is False, "Insufficient information must never claim waiting is safe"
        assert res["requires_clinician_review"] is True


def test_clinical_contradictory_information_escalates_to_review():
    """Verifies contradictory inputs (mild complaint + high severity/worsening) are not marked GREEN."""
    res = evaluate_triage(
        chief_complaint="Mild scratchy throat",
        symptom_description="Slight throat tickle, but pain is unbearable 8/10 and deteriorating rapidly",
        severity=8,
        trajectory="worsening"
    )
    assert res["urgency_level"] in ("YELLOW", "REVIEW_REQUIRED")
    assert res["urgency_level"] != "GREEN", "Contradictory high severity must not be classified as GREEN"
    assert res["can_wait"] is False


def test_clinical_multiple_simultaneous_symptoms_prioritize_highest_risk():
    """Verifies that multi-symptom presentations prioritize the highest acuity emergency rule."""
    res = evaluate_triage(
        chief_complaint="Runny nose and mild sneezing with severe crushing chest pain",
        symptom_description="Cold symptoms for 3 days, but today sudden chest pain radiating to shoulder",
        severity=9,
        trajectory="worsening"
    )
    assert res["urgency_level"] == "RED", "Chest pain emergency must dominate mild cold symptoms"


def test_clinical_unmatched_complaints_fail_to_review_required():
    """Verifies unmatched or exotic symptom presentations route to REVIEW_REQUIRED, never GREEN."""
    res = evaluate_triage(
        chief_complaint="Bilateral plantar paresthesia with fluctuating tingling",
        symptom_description="Intermittent sensory distortion over 3 weeks",
        severity=4,
        trajectory="stable"
    )
    assert res["urgency_level"] == "REVIEW_REQUIRED"
    assert res["can_wait"] is False
    assert res["requires_clinician_review"] is True


def test_clinical_evidence_retrieval_and_attribution():
    """Verifies clinical evidence retrieval links to official guideline publishers with citations."""
    res_dengue = search_clinical_evidence("dengue high fever warning signs", limit=2)
    assert res_dengue["evidence_found"] is True
    assert len(res_dengue["citations"]) > 0
    citation = res_dengue["citations"][0]
    assert "publisher" in citation
    assert "DGHS" in citation["publisher"] or "WHO" in citation["publisher"]
    assert citation["verification_status"] in ("APPROVED", "PENDING_REVIEW")

    # Query with no match fails gracefully without crash
    res_none = search_clinical_evidence("xyznonexistentunmatchedcondition12345")
    assert res_none["evidence_found"] is False
    assert len(res_none["citations"]) == 0
    assert "not found" in res_none["message"].lower() or "insufficient" in res_none["message"].lower()


def test_clinical_decision_support_disclaimer_present():
    """Verifies that clinical output includes non-diagnosis decision support disclaimer."""
    assert "disclaimer" in EMERGENCY_CONTACTS
    assert "does not autonomously dispatch" in EMERGENCY_CONTACTS["disclaimer"]
    assert "999" in EMERGENCY_CONTACTS["national_emergency"]
    assert "16263" in EMERGENCY_CONTACTS["health_helpline"]


def test_chronic_care_severe_hypoglycemia_lockout():
    """Verifies that BG < 70 mg/dL locks out all insulin (0.0 units) with urgent hypoglycemia warning."""
    from src.care.chronic_care import analyze_meal_and_calculate_insulin
    res = analyze_meal_and_calculate_insulin(
        meal_type="south_asian_roti_dal",
        current_glucose=58.0, # Severe hypoglycemia (<70)
        target_glucose=100.0,
        icr=10.0,
        isf=50.0,
        iob=0.0
    )
    dosage = res["insulin_dosage_recommendation"]
    breakdown = dosage["dosage_breakdown"]
    assert breakdown["recommended_injection_units"] == 0.0
    assert breakdown["educational_calculated_units"] == 0.0
    assert breakdown["meal_bolus_units"] == 0.0
    assert breakdown["correction_bolus_units"] == 0.0
    warnings = dosage["safety_warnings"]
    assert any("CRITICAL SEVERE HYPOGLYCEMIA LOCKOUT" in w for w in warnings)
    assert any("Rule of 15" in w for w in warnings)
    assert "disclaimer" in dosage["educational_prototype_disclaimer"].lower()


def test_chronic_care_insulin_input_validation_bounds():
    """Verifies that physiological out-of-bounds parameters raise ValueError."""
    from src.care.chronic_care import analyze_meal_and_calculate_insulin
    import pytest

    # Out-of-bounds current glucose
    with pytest.raises(ValueError, match="physiologically plausible range"):
        analyze_meal_and_calculate_insulin(current_glucose=15.0)

    with pytest.raises(ValueError, match="physiologically plausible range"):
        analyze_meal_and_calculate_insulin(current_glucose=950.0)

    # Out-of-bounds target glucose
    with pytest.raises(ValueError, match="valid clinical target range"):
        analyze_meal_and_calculate_insulin(target_glucose=50.0)

    # Out-of-bounds ICR
    with pytest.raises(ValueError, match="Insulin-to-Carbohydrate Ratio"):
        analyze_meal_and_calculate_insulin(icr=0.5)

    # Out-of-bounds ISF
    with pytest.raises(ValueError, match="Insulin Sensitivity Factor"):
        analyze_meal_and_calculate_insulin(isf=2.0)

    # Out-of-bounds IOB
    with pytest.raises(ValueError, match="Active Insulin On Board"):
        analyze_meal_and_calculate_insulin(iob=45.0)


def test_chronic_care_negative_correction_eliminated():
    """Verifies that BG below target does not calculate negative correction bolus."""
    from src.care.chronic_care import analyze_meal_and_calculate_insulin
    res = analyze_meal_and_calculate_insulin(
        meal_type="south_asian_roti_dal",
        current_glucose=85.0, # Below target 100, but > 80
        target_glucose=100.0,
        icr=10.0,
        isf=50.0,
        iob=0.0
    )
    dosage = res["insulin_dosage_recommendation"]["dosage_breakdown"]
    assert dosage["correction_bolus_units"] == 0.0, "Correction bolus must never be negative"
    assert dosage["recommended_injection_units"] == dosage["meal_bolus_units"]


def test_production_fail_closed_unknown_environment():
    """Verifies that unknown environments fail closed to production mode."""
    import os
    from src.database.db import is_production
    saved_env = dict(os.environ)
    try:
        os.environ["ENVIRONMENT"] = "unrecognized-cluster-v2"
        assert is_production() is True, "Unknown deployment environment must fail closed to production"
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


def test_production_fail_closed_insecure_cors():
    """Verifies that production startup fails closed if CORS has wildcard or localhost."""
    import os
    import pytest
    from src.api.server import validate_production_configuration
    saved_env = dict(os.environ)
    try:
        os.environ["TRANSIFY_ENV"] = "production"
        os.environ["CORS_ORIGINS"] = "*"
        with pytest.raises(RuntimeError, match="cannot be '\\*' in production"):
            validate_production_configuration()

        os.environ["CORS_ORIGINS"] = "http://localhost:3000,https://transify.ai"
        with pytest.raises(RuntimeError, match="Localhost is prohibited in production"):
            validate_production_configuration()
    finally:
        os.environ.clear()
        os.environ.update(saved_env)


def test_frontend_no_persistent_raw_bearer_token():
    """Verifies that no HTML or static JS files store raw bearer tokens in localStorage."""
    import glob
    token_setter = "localStorage.setItem('transify_auth_token'"
    files_to_check = glob.glob("src/frontend/**/*.html", recursive=True) + glob.glob("src/frontend/**/*.js", recursive=True)
    for fpath in files_to_check:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            assert token_setter not in content, f"File {fpath} must not store raw bearer tokens in localStorage"


def test_csrf_cross_origin_cookie_mutation_rejected():
    """Verifies that cross-origin state-changing requests with ambient cookies are rejected with 403."""
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.database.db import create_user, create_session
    import uuid

    email = f"csrf_victim_{uuid.uuid4().hex[:6]}@transify.ai"
    u = create_user("CSRF Victim", email, "TransifySecurePass2026!", consent_terms=True)
    token = create_session(u["id"])

    client = TestClient(app)
    client.cookies.set("transify_session", token)

    # Malicious cross-origin mutation
    res = client.post(
        "/api/care/intake",
        json={"chief_complaint": "Stomach pain", "symptom_description": "Aching pain", "severity": 4},
        headers={"Origin": "https://malicious-attacker-site.com"}
    )
    assert res.status_code == 403
    assert "CSRF protection" in res.json()["detail"]


def test_csrf_bearer_token_exempt_from_browser_csrf():
    """Verifies that non-browser API clients using Bearer tokens are exempt from ambient cookie CSRF checks."""
    from fastapi.testclient import TestClient
    from src.api.server import app
    from src.database.db import create_user, create_session
    import uuid

    email = f"api_client_{uuid.uuid4().hex[:6]}@transify.ai"
    u = create_user("API Client", email, "TransifySecurePass2026!", consent_terms=True)
    token = create_session(u["id"])

    client = TestClient(app)
    # No ambient cookies, only explicit Bearer header
    res = client.post(
        "/api/care/intake",
        json={
            "input_modality": "text",
            "confirmed_text": "Mild headache",
            "chief_complaint": "Headache",
            "symptom_description": "Mild headache",
            "severity": 3,
            "consent_granted": True
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "https://trusted-external-partner.org"
        }
    )
    assert res.status_code == 201


def test_insulin_calculator_mmol_conversion_and_bounds():
    """Verifies that glucose_unit='mmol/L' correctly converts and checks physiological bounds."""
    from src.care.chronic_care import analyze_meal_and_calculate_insulin
    import pytest

    # 1. Normal conversion: 6.0 mmol/L (~108.1 mg/dL)
    res = analyze_meal_and_calculate_insulin(
        meal_type="south_asian_roti_dal",
        current_glucose=6.0,
        target_glucose=5.5,
        glucose_unit="mmol/L",
        clinician_confirmed_parameters=True
    )
    dosage = res["insulin_dosage_recommendation"]
    params = dosage["patient_parameters"]
    assert params["glucose_unit"] == "mmol/L"
    assert params["current_glucose_input"] == 6.0
    assert 107.0 <= params["current_glucose_mg_dl"] <= 109.0

    # 2. Out-of-bounds mmol/L (<1.1 or >44.4)
    with pytest.raises(ValueError, match="physiologically plausible range"):
        analyze_meal_and_calculate_insulin(current_glucose=0.8, glucose_unit="mmol/L")

    # 3. Unit confusion detection (entering 6.0 with mg/dL)
    with pytest.raises(ValueError, match="appears to be in mmol/L rather than mg/dL"):
        analyze_meal_and_calculate_insulin(current_glucose=6.0, glucose_unit="mg/dL")


def test_insulin_calculator_swallowing_and_aspiration_warning():
    """Verifies that severe hypoglycemia (<70 mg/dL) includes ability-to-swallow and aspiration warnings."""
    from src.care.chronic_care import analyze_meal_and_calculate_insulin
    res = analyze_meal_and_calculate_insulin(
        meal_type="south_asian_roti_dal",
        current_glucose=55.0, # <70 mg/dL
        target_glucose=100.0
    )
    warnings = res["insulin_dosage_recommendation"]["safety_warnings"]
    assert any("ABILITY-TO-SWALLOW ASSESSMENT" in w for w in warnings)
    assert any("ASPIRATION HAZARD" in w for w in warnings)
    assert any("DO NOT ADMINISTER ANYTHING BY MOUTH" in w for w in warnings)
    assert any("glucagon" in w.lower() for w in warnings)


def test_insulin_calculator_unconfirmed_clinician_parameters():
    """Verifies that unconfirmed parameters trigger a prominent clinical simulation warning."""
    from src.care.chronic_care import analyze_meal_and_calculate_insulin
    res = analyze_meal_and_calculate_insulin(
        meal_type="south_asian_roti_dal",
        current_glucose=140.0,
        clinician_confirmed_parameters=False
    )
    warnings = res["insulin_dosage_recommendation"]["safety_warnings"]
    assert any("UNCONFIRMED CLINICAL PARAMETERS" in w for w in warnings)
    assumptions = res["insulin_dosage_recommendation"]["calculation_assumptions"]
    assert assumptions["clinician_confirmed_parameters"] is False
    assert assumptions["mode"] == "CLINICIAN_SUPERVISED_SIMULATION_PROTOTYPE"


def test_evidence_registry_isolation_of_research_from_clinical_recommendations():
    """Verifies that research datasets (MIMIC-IV) and ontologies (MeSH) are excluded from clinical recommendations."""
    from src.care.clinical_rag import search_clinical_evidence, seed_clinical_sources_if_empty
    seed_clinical_sources_if_empty(force_reseed=True)

    # Search for clinical recommendations
    res = search_clinical_evidence("chest pain emergency", limit=5, clinical_recommendations_only=True)
    assert res["evidence_found"] is True
    for cit in res["citations"]:
        assert cit["can_support_clinical_recommendations"] is True
        assert cit["source_id"] not in ("SRC-MIMIC-IV-CRITICAL-2023", "SRC-NLM-MESH-2024", "SRC-HMD-MORTALITY-2024")
        assert "retrieval_date" in cit
        assert "applicable_population" in cit
        assert "supported_claims" in cit


def test_openfda_polypharmacy_negative_result_disclaimer():
    """Verifies that an absence of interactions is not claimed as proof of safety."""
    from src.care.chronic_care import check_openfda_polypharmacy_interactions
    res = check_openfda_polypharmacy_interactions(["Metformin"])
    assert res["evidence_status"] == "NO_CATALOGED_INTERACTION_FOUND"
    assert "safety_disclaimer" in res
    assert "does NOT prove that your medications are free of interactions" in res["safety_disclaimer"]
    assert res["catalog_provenance"]["exhaustive_coverage"] is False


def test_elderly_voice_cognitive_non_diagnosis_disclaimer():
    """Verifies that speech acoustic cadence is explicitly marked as non-diagnostic for MCI/dementia."""
    from src.care.chronic_care import track_elderly_adherence_and_cognition
    res = track_elderly_adherence_and_cognition(
        medication_log=[{"dose_id": 1, "status": "TAKEN"}],
        audio_transcript="I took my medicine in the morning, maybe around 8 AM."
    )
    assert res["prototype_classification"] == "EDUCATIONAL_DEMONSTRATION_PROTOTYPE"
    biomarkers = res["acoustic_cognitive_biomarkers"]
    assert "clinical_non_diagnosis_disclaimer" in biomarkers
    assert "does NOT constitute a diagnosis of Mild Cognitive Impairment (MCI)" in biomarkers["clinical_non_diagnosis_disclaimer"]


def test_braille_grade2_and_bengali_limitations_cataloged():
    """Verifies that supported and unsupported Grade 2 contractions and Bengali limitations are cataloged."""
    from src.braille.decoder import (
        GRADE2_SUPPORTED_CONTRACTIONS,
        GRADE2_UNSUPPORTED_CONTRACTIONS,
        BENGALI_BHARATI_SUPPORTED_CHARS,
        BENGALI_BHARATI_UNSUPPORTED_SEQUENCES
    )
    assert len(GRADE2_SUPPORTED_CONTRACTIONS) == 5
    assert any("and" in c for c in GRADE2_SUPPORTED_CONTRACTIONS)
    assert len(GRADE2_UNSUPPORTED_CONTRACTIONS) >= 5
    assert len(BENGALI_BHARATI_SUPPORTED_CHARS) >= 40
    assert len(BENGALI_BHARATI_UNSUPPORTED_SEQUENCES) >= 4
    assert any("Juktoborno" in s for s in BENGALI_BHARATI_UNSUPPORTED_SEQUENCES)
