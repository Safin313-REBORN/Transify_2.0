"""
CareAnywhere Test Suite.
Verifies:
1. RAG-based clinical reasoning over Merck Manuals, MIMIC-IV, MeSH, and WHO guidelines.
2. Computer vision analysis for skin lesions (erythema, ABCDE melanoma screening, burns) and eye conditions (red eye, cataract, corneal ulcers).
3. Localized speech-to-text / regional dialect parsing for Sylheti, Chittagonian, and rural Bengali idioms with MeSH normalization.
4. Predictive local outbreak & epidemic risk alerts based on GPS coordinates and district surveillance.
5. OpenStreetMap Health geospatial facility locator for nearest clinics, hospitals, and 24/7 pharmacies.
6. Store-and-Forward protocol with SHA-256 idempotency hashing and offline sync.
"""

import os
import sys
import io
import json
import base64
import pytest
import numpy as np
from PIL import Image

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from src.api.server import app
from src.database.db import create_user, create_session, get_connection, init_db
from src.care.db_care import init_care_db, get_intake
from src.care.clinical_rag import search_clinical_evidence, seed_clinical_sources_if_empty
from src.care.care_anywhere import (
    analyze_skin_lesion_cv,
    analyze_eye_condition_cv,
    analyze_multimodal_vision,
    process_regional_speech_intake,
    assess_local_outbreak_risk,
    find_nearby_health_facilities,
    compute_intake_idempotency_hash,
    map_text_to_mesh_descriptors
)

# Ensure databases initialized
init_db()
init_care_db()
seed_clinical_sources_if_empty(force_reseed=True)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        test_client.cookies.clear()
        yield test_client


def login_patient(client: TestClient, name="Care Patient", email="care_patient@transify.test"):
    pwd = "SecureCarePassword2026!"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role FROM users WHERE email = ? COLLATE NOCASE;", (email.lower(),))
    row = cursor.fetchone()
    conn.close()

    if not row:
        user = create_user(name=name, email=email, password=pwd, role="user", consent_terms=True)
    else:
        user = dict(row)

    token = create_session(user["id"])
    client.cookies.set("transify_session", token)
    return user


# ---------------------------------------------------------------------------
# 1. RAG-Based Clinical Reasoning over Merck Manuals & MeSH
# ---------------------------------------------------------------------------

def test_rag_merck_manuals_dermatology_and_ophthalmology():
    """Verifies clinical RAG retrieves Merck Manuals passages for skin and eye concerns."""
    # Query dermatological warning signs
    res_skin = search_clinical_evidence("skin lesion rash erythema cellulitis melanoma", limit=3)
    assert res_skin["evidence_found"] is True
    sources = [c["source_id"] for c in res_skin["citations"]]
    assert "SRC-MERCK-MANUALS-2024" in sources

    # Query ophthalmic red flags
    res_eye = search_clinical_evidence("red eye corneal ulcer vision loss cataract", limit=3)
    assert res_eye["evidence_found"] is True
    eye_sources = [c["source_id"] for c in res_eye["citations"]]
    assert "SRC-MERCK-MANUALS-2024" in eye_sources


def test_rag_mimic_iv_and_who_outbreak_guidelines():
    """Verifies clinical RAG retrieves MIMIC-IV critical care and WHO outbreak passages."""
    res_shock = search_clinical_evidence("shock vital signs sepsis hemodynamic instability", limit=3)
    assert res_shock["evidence_found"] is True
    assert any("MIMIC-IV" in c["source_title"] for c in res_shock["citations"])

    res_outbreak = search_clinical_evidence("outbreak epidemic dengue cholera surveillance", limit=3)
    assert res_outbreak["evidence_found"] is True
    assert any("WHO" in c["publisher"] for c in res_outbreak["citations"])


def test_mesh_standardized_terminology_mapping():
    """Verifies extraction and mapping to U.S. NLM MeSH terminology."""
    text = "Patient reports severe crushing chest pain, high fever, and cloudy eye vision with rash."
    mesh_terms = map_text_to_mesh_descriptors(text)
    mesh_ids = [m["mesh_id"] for m in mesh_terms]
    # D002637: Chest Pain, D005334: Fever, D012871: Skin Diseases
    assert "D002637" in mesh_ids
    assert "D005334" in mesh_ids
    assert "D012871" in mesh_ids


# ---------------------------------------------------------------------------
# 2. Computer Vision Pipeline (Skin Lesions & Eye Conditions)
# ---------------------------------------------------------------------------

def _create_synthetic_test_image(pattern: str = "red_rash") -> bytes:
    """Generates synthetic RGB test image simulating skin lesion or eye condition."""
    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    if pattern == "red_rash":
        # Skin base with intense red patch (erythema/cellulitis)
        arr[:, :] = [180, 140, 120]  # Base skin tone
        arr[80:180, 80:180] = [240, 40, 40]  # Severe inflammatory erythema
    elif pattern == "melanoma_abcde":
        # Skin base with dark, irregular, asymmetric pigmented lesion
        arr[:, :] = [200, 160, 140]
        # Asymmetric shape in quadrant
        arr[60:150, 70:180] = [30, 20, 15]
        arr[120:200, 100:160] = [60, 40, 20]
        arr[90:130, 140:190] = [10, 10, 10]
    elif pattern == "red_eye":
        # White sclera with central dark pupil and intense red perimeter injection
        arr[:, :] = [230, 230, 230]  # Sclera white
        arr[90:170, 90:170] = [20, 20, 20]  # Pupil
        arr[:, :60] = [220, 30, 30]  # Conjunctival injection left
        arr[:, 190:] = [220, 30, 30]  # Conjunctival injection right
    elif pattern == "corneal_opacity":
        # Eye with cloudy white lens / corneal infiltrate
        arr[:, :] = [220, 220, 220]
        arr[100:160, 100:160] = [210, 210, 215]  # Dense corneal opacity
        arr[:, :70] = [230, 50, 50]  # Injection
    else:
        # Uniform benign skin
        arr[:, :] = [190, 155, 135]

    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_skin_lesion_cv_analysis():
    """Verifies skin lesion computer vision pipeline identifies acute erythema and ABCDE features."""
    img_rash = _create_synthetic_test_image("red_rash")
    res_rash = analyze_skin_lesion_cv(img_rash)
    assert res_rash["target_organ"] == "DERMATOLOGY"
    assert res_rash["urgency_level"] in ("URGENT", "EMERGENT")
    assert res_rash["metrics"]["erythema_index"] > 15.0

    img_melanoma = _create_synthetic_test_image("melanoma_abcde")
    res_melanoma = analyze_skin_lesion_cv(img_melanoma)
    assert res_melanoma["target_organ"] == "DERMATOLOGY"
    assert "asymmetry_score" in res_melanoma["metrics"]


def test_eye_condition_cv_analysis():
    """Verifies ophthalmic computer vision pipeline identifies red eye and corneal opacity."""
    img_red_eye = _create_synthetic_test_image("red_eye")
    res_eye = analyze_eye_condition_cv(img_red_eye)
    assert res_eye["target_organ"] == "OPHTHALMOLOGY"
    assert res_eye["metrics"]["scleral_redness_index"] > 15.0

    img_ulcer = _create_synthetic_test_image("corneal_opacity")
    res_ulcer = analyze_eye_condition_cv(img_ulcer)
    assert res_ulcer["target_organ"] == "OPHTHALMOLOGY"
    assert res_ulcer["urgency_level"] in ("EMERGENT", "URGENT")


def test_vision_analyze_http_endpoint(client: TestClient):
    """Verifies POST /api/care/vision/analyze HTTP endpoint."""
    login_patient(client)
    img_bytes = _create_synthetic_test_image("red_rash")
    b64_img = base64.b64encode(img_bytes).decode("utf-8")

    resp = client.post("/api/care/vision/analyze", json={
        "image_data": f"data:image/jpeg;base64,{b64_img}",
        "condition_type": "skin"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["analysis"]["target_organ"] == "DERMATOLOGY"
    assert "confidence_score" in data["analysis"]


# ---------------------------------------------------------------------------
# 3. Localized Speech-to-Text & Regional Dialect Interface
# ---------------------------------------------------------------------------

def test_regional_dialect_processing():
    """Verifies speech parser maps Sylheti, Chittagonian, and rural idioms to clinical concepts."""
    # Sylheti dialect test
    sylheti_sample = "amar bukor bitor fura ar dom baand"
    res_sylheti = process_regional_speech_intake(sylheti_sample)
    assert res_sylheti["identified_dialect"] == "Sylheti Regional Dialect"
    assert res_sylheti["inferred_severity"] >= 8
    assert any(s["clinical_en"] == "chest pain" for s in res_sylheti["matched_dialect_symptoms"])

    # Chittagonian dialect test
    ctg_sample = "souk laal oise ar bukot asor maare"
    res_ctg = process_regional_speech_intake(ctg_sample)
    assert res_ctg["identified_dialect"] == "Chittagonian Regional Dialect"
    assert res_ctg["inferred_severity"] >= 8

    # Rural Bengali idioms
    idiom_sample = "গা থরথর করে কাঁপে এবং দম আটকে আসে"
    res_idiom = process_regional_speech_intake(idiom_sample)
    assert res_idiom["inferred_severity"] >= 8


def test_audio_intake_http_endpoint(client: TestClient):
    """Verifies POST /api/care/audio/intake HTTP endpoint."""
    login_patient(client)
    resp = client.post("/api/care/audio/intake", json={
        "transcript": "আমার বুকের ভেতর তীব্র ব্যথা এবং দম আটকে আসে",
        "dialect_hint": "bn_standard"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["inferred_severity"] >= 7
    assert len(data["data"]["mesh_terms"]) > 0


# ---------------------------------------------------------------------------
# 4. Predictive Local Outbreak & Epidemic Risk Alerts
# ---------------------------------------------------------------------------

def test_outbreak_risk_assessment_gps():
    """Verifies epidemic risk assessment by coordinates for Dhaka, Chittagong, and Rajshahi."""
    # Dhaka GPS coordinates
    dhaka_res = assess_local_outbreak_risk(lat=23.8103, lon=90.4125, symptoms_text="high fever persistent vomiting")
    assert dhaka_res["district"] == "Dhaka"
    assert dhaka_res["overall_epidemic_risk"] == "HIGH"
    assert any("Dengue" in a["pathogen"] for a in dhaka_res["outbreak_alerts"])

    # Chittagong GPS coordinates
    ctg_res = assess_local_outbreak_risk(lat=22.3569, lon=91.7832, symptoms_text="rice-water stool dehydration")
    assert ctg_res["district"] == "Chittagong"
    assert any("cholera" in a["pathogen"].lower() for a in ctg_res["outbreak_alerts"])


def test_outbreak_alerts_http_endpoint(client: TestClient):
    """Verifies GET /api/care/outbreak/alerts HTTP endpoint."""
    login_patient(client)
    resp = client.get("/api/care/outbreak/alerts?lat=23.8103&lon=90.4125&district=Dhaka&symptoms=fever")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["district"] == "Dhaka"
    assert data["data"]["active_outbreak_count"] > 0


# ---------------------------------------------------------------------------
# 5. OpenStreetMap Health & Geospatial Facility Locator
# ---------------------------------------------------------------------------

def test_osm_facility_locator():
    """Verifies nearby healthcare facilities retrieval with Haversine distance and hotlines."""
    # From Dhaka coordinates
    facs = find_nearby_health_facilities(lat=23.7500, lon=90.3900, limit=4)
    assert facs["status"] == "SUCCESS"
    assert len(facs["nearest_facilities"]) > 0
    nearest = facs["nearest_facilities"][0]
    assert "distance_km" in nearest
    assert "estimated_transit_minutes" in nearest
    assert nearest["national_emergency"] == "999"


def test_facilities_nearby_http_endpoint(client: TestClient):
    """Verifies GET /api/care/facilities/nearby HTTP endpoint."""
    login_patient(client)
    resp = client.get("/api/care/facilities/nearby?lat=23.7258&lon=90.3976&limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert len(data["nearest_facilities"]) > 0
    assert data["national_hotlines"]["emergency_ambulance"] == "999"


# ---------------------------------------------------------------------------
# 6. Store-and-Forward Protocol & Multimodal Intake Submission
# ---------------------------------------------------------------------------

def test_multimodal_intake_submission_with_vision_and_gps(client: TestClient):
    """Verifies submitting an intake with smartphone lesion photo and GPS coordinates."""
    user = login_patient(client, email="multimodal_patient@transify.test")
    img_bytes = _create_synthetic_test_image("red_rash")
    b64_img = base64.b64encode(img_bytes).decode("utf-8")

    resp = client.post("/api/care/intake", json={
        "input_modality": "multimodal",
        "confirmed_text": "Spreading red itchy skin rash over forearm",
        "chief_complaint": "Spreading red skin rash",
        "symptom_description": "Warm, tender red area that started yesterday",
        "onset_duration": "1 day",
        "severity": 6,
        "consent_granted": True,
        "image_base64": f"data:image/jpeg;base64,{b64_img}",
        "condition_type": "skin",
        "gps_latitude": 23.8103,
        "gps_longitude": 90.4125,
        "district": "Dhaka"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["success"] is True
    assert data["vision_analysis"] is not None
    assert data["outbreak_context"] is not None
    assert len(data["mesh_descriptors"]) > 0

    # Verify database persistence
    intake_rec = get_intake(data["intake_id"])
    assert intake_rec is not None
    assert intake_rec["vision_analysis"] is not None
    assert intake_rec["outbreak_context"] is not None


def test_store_and_forward_sync_idempotency(client: TestClient):
    """Verifies Store-and-Forward offline sync processes and deduplicates via SHA-256."""
    import secrets
    login_patient(client, email="store_forward_patient@transify.test")
    uniq_token = secrets.token_hex(4)
    confirmed_text = f"Severe headache and photophobia {uniq_token}"
    idem_key = compute_intake_idempotency_hash("user-offline", confirmed_text, "2026-11-20T10:00:00Z")

    batch_payload = {
        "client_id": "field-worker-phone-007",
        "batch": [
            {
                "input_modality": "text",
                "confirmed_text": confirmed_text,
                "chief_complaint": f"Severe headache {uniq_token}",
                "symptom_description": "Throbbing pain in forehead, started this morning",
                "onset_duration": "4 hours",
                "severity": 7,
                "consent_granted": True,
                "idempotency_key": idem_key,
                "offline_created_at": "2026-11-20T10:00:00Z"
            }
        ]
    }

    # First sync: should be SYNCHRONIZED
    resp1 = client.post("/api/care/store-and-forward/sync", json=batch_payload)
    assert resp1.status_code == 200
    res1_data = resp1.json()
    assert res1_data["success"] is True
    assert res1_data["results"][0]["status"] == "SYNCHRONIZED"

    # Second sync (duplicate transmission): should return ALREADY_SYNCHRONIZED
    resp2 = client.post("/api/care/store-and-forward/sync", json=batch_payload)
    assert resp2.status_code == 200
    res2_data = resp2.json()
    assert res2_data["success"] is True
    assert res2_data["results"][0]["status"] == "ALREADY_SYNCHRONIZED"
