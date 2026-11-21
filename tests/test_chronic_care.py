"""
ChronicCare AI Test Suite.
Verifies:
1. Wearable & continuous telemetry ingestion (Fitbit, Apple Health, CGM streams, nocturnal dipping).
2. 24-hour predictive physiological forecasting (Hypertensive crisis & heart failure decompensation via HRV, resting HR, and sleep architecture - MIMIC-IV & Biofourmis paradigm).
3. Computer vision & nutrition module for automated insulin dosage calculation (Meal recognition, net carbs, glycemic load, ICR/ISF bolus, hypoglycemia lockout - Livongo & Virta paradigm).
4. Culturally sensitive lab panel RAG & lifestyle coaching (Translates HbA1c, lipids, eGFR with South Asian, Mediterranean, Hispanic, East Asian, and Western diet swaps).
5. Voice-based AI agent for elderly medication adherence & cognitive decline speech biomarkers (PDC tracking, speech rate, pause latency, hesitation index).
6. OpenFDA polypharmacy safety & drug-drug interaction engine (Contraindications, adverse events, clinical action protocols).
7. Cross-border federated learning framework for privacy-preserving morbidity modeling (FedAvg with Differential Privacy noise across hospital nodes without PHI transfer).
8. FastAPI route endpoints integration (/api/care/chronic/*).
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
from src.care.chronic_care import (
    ingest_wearable_telemetry,
    predict_24h_crisis_forecasting,
    analyze_meal_and_calculate_insulin,
    translate_lab_panel_and_coach,
    track_elderly_adherence_and_cognition,
    check_openfda_polypharmacy_interactions,
    simulate_federated_learning_morbidity_round,
    CHRONIC_MEDICATION_INTERACTION_DB,
    CULTURAL_DIETARY_PROFILES,
    FOOD_CV_DATABASE
)

client = TestClient(app)


# ===========================================================================
# 1. Wearable Telemetry Ingestion Tests
# ===========================================================================

def test_wearable_telemetry_normal_dipper():
    payload = {
        "source": "Fitbit_Charge_6",
        "resting_heart_rate": 68.0,
        "hrv_rmssd_ms": 45.0,
        "sleep_metrics": {
            "total_sleep_minutes": 450.0,
            "deep_minutes": 80.0,
            "rem_minutes": 95.0,
            "light_minutes": 235.0,
            "awake_minutes": 40.0
        },
        "cgm_metrics": {
            "mean_glucose_mg_dl": 115.0,
            "time_in_range_pct": 82.0,
            "time_below_range_pct": 1.0,
            "glycemic_variability_cv_pct": 24.0
        },
        "ambulatory_bp": {
            "daytime_systolic": 128.0,
            "daytime_diastolic": 80.0,
            "nighttime_systolic": 112.0,
            "nighttime_diastolic": 70.0
        },
        "daily_steps": 8400,
        "active_zone_minutes": 35
    }
    res = ingest_wearable_telemetry(payload)
    assert res["status"] == "TELEMETRY_INGESTED"
    assert res["signal_integrity_score"] > 85.0

    summary = res["metrics_summary"]
    assert summary["autonomic"]["autonomic_balance"] == "PARASYMPATHETIC_DOMINANT"
    assert summary["hemodynamics"]["dipping_phenotype"] == "NORMAL_DIPPER"
    assert summary["glycemic_control"]["clinical_target_achieved"] is True


def test_wearable_telemetry_reverse_dipper_high_risk():
    payload = {
        "source": "Apple_HealthKit",
        "resting_heart_rate": 84.0,
        "hrv_rmssd_ms": 16.0,
        "ambulatory_bp": {
            "daytime_systolic": 140.0,
            "daytime_diastolic": 88.0,
            "nighttime_systolic": 148.0, # Nocturnal rise
            "nighttime_diastolic": 92.0
        }
    }
    res = ingest_wearable_telemetry(payload)
    summary = res["metrics_summary"]
    assert summary["hemodynamics"]["dipping_phenotype"] == "REVERSE_DIPPER"
    assert summary["autonomic"]["autonomic_balance"] == "SYMPATHETIC_OVERDRIVE"


# ===========================================================================
# 2. 24-Hour Predictive Time-Series Forecasting Tests
# ===========================================================================

def test_24h_crisis_forecasting_critical_hypertension():
    # Simulate high sympathetic tone, suppressed HRV, severe sleep fragmentation, reverse dipping
    telemetry = {
        "metrics_summary": {
            "autonomic": {
                "resting_heart_rate_bpm": 88.0,
                "hrv_rmssd_ms": 15.0
            },
            "sleep_architecture": {
                "sleep_fragmentation_index": 38.0
            },
            "hemodynamics": {
                "dipping_phenotype": "REVERSE_DIPPER",
                "nocturnal_dip_pct": -5.7
            },
            "glycemic_control": {
                "mean_glucose_mg_dl": 145.0,
                "time_below_range_pct": 1.0
            }
        }
    }
    patient_history = {
        "baseline_resting_hr": 68.0,
        "baseline_hrv_rmssd": 42.0,
        "hypertension_history": True
    }
    forecast = predict_24h_crisis_forecasting(telemetry, patient_history)
    assert forecast["status"] == "FORECAST_COMPLETED"
    htn = forecast["hypertensive_crisis_forecast"]
    assert htn["alert_level"] in ["CRITICAL_CRISIS_IMMINENT", "ELEVATED_RISK_WARNING"]
    assert htn["risk_score_0_100"] >= 70.0
    assert len(htn["primary_physiological_drivers"]) >= 3
    assert "URGENT" in htn["recommended_preventative_action"]


def test_24h_crisis_forecasting_stable_and_hypo_alert():
    # Stable telemetry with nocturnal hypoglycemia risk
    telemetry = {
        "metrics_summary": {
            "autonomic": {
                "resting_heart_rate_bpm": 69.0,
                "hrv_rmssd_ms": 46.0
            },
            "sleep_architecture": {
                "sleep_fragmentation_index": 11.0
            },
            "hemodynamics": {
                "dipping_phenotype": "NORMAL_DIPPER",
                "nocturnal_dip_pct": 13.5
            },
            "glycemic_control": {
                "mean_glucose_mg_dl": 88.0,
                "time_below_range_pct": 5.5 # high hypoglycemia
            }
        }
    }
    forecast = predict_24h_crisis_forecasting(telemetry)
    htn = forecast["hypertensive_crisis_forecast"]
    assert htn["alert_level"] == "STABLE_PHYSIOLOGY"

    hypo = forecast["nocturnal_hypoglycemia_forecast"]
    assert hypo["risk_detected"] is True
    assert "bedtime snack" in hypo["recommendation"].lower()


# ===========================================================================
# 3. Nutrition Computer Vision & Insulin Dosage Tests
# ===========================================================================

def test_meal_and_insulin_calculation_preset():
    # South Asian Roti Dal: 44g carbs, current BG = 150 mg/dL, target = 100, ICR = 10, ISF = 50
    res = analyze_meal_and_calculate_insulin(
        meal_type="south_asian_roti_dal",
        current_glucose=150.0,
        target_glucose=100.0,
        icr=10.0,
        isf=50.0,
        iob=0.0
    )
    assert res["status"] == "NUTRITION_AND_INSULIN_CALCULATED"
    meal = res["meal_recognition"]
    assert "Roti" in meal["detected_dish"]
    assert meal["macronutrients"]["net_carbohydrates_grams"] == 44.0

    dosage = res["insulin_dosage_recommendation"]["dosage_breakdown"]
    # Meal bolus = 44 / 10 = 4.4
    assert dosage["meal_bolus_units"] == 4.4
    # Correction bolus = (150 - 100) / 50 = 1.0
    assert dosage["correction_bolus_units"] == 1.0
    # Total = 4.4 + 1.0 = 5.4 units
    assert dosage["recommended_injection_units"] == 5.4


def test_meal_and_insulin_hypoglycemia_lockout():
    # Current BG = 72 mg/dL (<80): zero correction insulin, hypoglycemia safety warning
    res = analyze_meal_and_calculate_insulin(
        meal_type="mediterranean_salmon_quinoa",
        current_glucose=72.0,
        target_glucose=100.0,
        icr=10.0,
        isf=50.0,
        iob=0.0
    )
    dosage = res["insulin_dosage_recommendation"]
    assert dosage["dosage_breakdown"]["correction_bolus_units"] == 0.0
    warnings = dosage["safety_warnings"]
    assert any("HYPOGLYCEMIA ALERT" in w for w in warnings)


def test_meal_and_insulin_iob_subtraction_and_safety_cap():
    # Huge meal, current BG = 280, IOB = 2.0 units
    res = analyze_meal_and_calculate_insulin(
        meal_type="western_burger_fries", # 84g carbs
        portion_factor=2.0, # 168g carbs -> 16.8 units
        current_glucose=280.0, # (280-100)/50 = 3.6 units
        icr=10.0,
        isf=50.0,
        iob=2.0
    )
    # Total would exceed 15 units, must be capped at 15.0
    dose = res["insulin_dosage_recommendation"]["dosage_breakdown"]["recommended_injection_units"]
    assert dose <= 15.0
    warnings = res["insulin_dosage_recommendation"]["safety_warnings"]
    assert any("SAFETY CAP" in w for w in warnings)


def test_meal_cv_synthetic_image_recognition():
    # Create synthetic image with warm yellow hue
    img = Image.new("RGB", (128, 128), color=(200, 160, 40))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64_data = base64.b64encode(buf.getvalue()).decode()

    res = analyze_meal_and_calculate_insulin(image_data=b64_data)
    assert res["status"] == "NUTRITION_AND_INSULIN_CALCULATED"
    assert res["meal_recognition"]["macronutrients"]["net_carbohydrates_grams"] > 0


# ===========================================================================
# 4. Culturally Sensitive Lab Panel RAG & Coaching Tests
# ===========================================================================

def test_lab_translation_south_asian_diet():
    lab = {
        "hba1c_pct": 8.4,
        "fasting_glucose_mg_dl": 165.0,
        "ldl_cholesterol_mg_dl": 142.0,
        "triglycerides_mg_dl": 210.0,
        "hdl_cholesterol_mg_dl": 38.0,
        "serum_creatinine_mg_dl": 1.2,
        "egfr_ml_min": 64.0,
        "urine_albumin_creatinine_ratio": 55.0
    }
    res = translate_lab_panel_and_coach(lab, cultural_diet="south_asian")
    assert res["status"] == "LAB_TRANSLATION_COMPLETED"
    assert "South Asian" in res["cultural_framework"]

    glyc = res["plain_language_summary"]["glycemic_health"]
    assert glyc["status"] == "SEVERELY_ELEVATED"
    assert "averaging ~" in glyc["patient_explanation"]

    swaps = res["culturally_tailored_coaching"]["staple_swaps"]
    assert any("Polished White Rice" in s["replace"] for s in swaps)
    assert any("Fenugreek" in s["substitute"] or "Millet" in s["substitute"] for s in swaps)


def test_lab_translation_mediterranean_and_hispanic():
    lab = {"hba1c_pct": 6.1, "egfr_ml_min": 92.0}
    res_med = translate_lab_panel_and_coach(lab, cultural_diet="mediterranean")
    assert "Mediterranean" in res_med["cultural_framework"]
    assert any("Olive Oil" in sf or "Horta" in sf for sf in res_med["culturally_tailored_coaching"]["cultural_superfoods"])

    res_hisp = translate_lab_panel_and_coach(lab, cultural_diet="hispanic")
    assert "Hispanic" in res_hisp["cultural_framework"]
    assert any("Nopales" in sf for sf in res_hisp["culturally_tailored_coaching"]["cultural_superfoods"])


# ===========================================================================
# 5. Voice-Based Elderly Adherence & Cognitive Biomarker Tests
# ===========================================================================

def test_elderly_adherence_optimal_and_normal_cognition():
    med_log = [
        {"medication": "Metformin 500mg", "status": "TAKEN"},
        {"medication": "Lisinopril 10mg", "status": "CONFIRMED_BY_VOICE"},
        {"medication": "Atorvastatin 20mg", "status": "TAKEN"},
        {"medication": "Amlodipine 5mg", "status": "TAKEN"}
    ]
    transcript = "Good morning, I took my blood pressure and diabetes tablets with a glass of water right after oatmeal."
    acoustics = {
        "speech_duration_seconds": 6.5,
        "mean_pause_duration_seconds": 0.42,
        "vocal_jitter_pct": 0.9
    }
    res = track_elderly_adherence_and_cognition(med_log, transcript, acoustics)
    assert res["status"] == "ELDERLY_CARE_EVALUATED"
    assert res["medication_adherence"]["proportion_of_days_covered_pdc"] == 100.0
    assert res["medication_adherence"]["adherence_tier"] == "OPTIMAL_ADHERENCE"

    cog = res["acoustic_cognitive_biomarkers"]
    assert cog["cognitive_status"] == "NORMAL_COGNITIVE_AGING"
    assert cog["cognitive_hesitation_index_0_100"] < 30.0


def test_elderly_adherence_suboptimal_and_cognitive_hesitation():
    med_log = [
        {"medication": "Metformin 500mg", "status": "MISSED"},
        {"medication": "Lisinopril 10mg", "status": "TAKEN"},
        {"medication": "Atorvastatin 20mg", "status": "MISSED"},
        {"medication": "Amlodipine 5mg", "status": "MISSED"}
    ]
    # Slow speech, prolonged pauses, and uncertainty markers
    transcript = "Um, I think so... maybe I took the blue one, not sure... where was I?"
    acoustics = {
        "speech_duration_seconds": 12.0,
        "mean_pause_duration_seconds": 1.15, # high hesitation
        "vocal_jitter_pct": 2.4
    }
    res = track_elderly_adherence_and_cognition(med_log, transcript, acoustics)
    assert res["medication_adherence"]["proportion_of_days_covered_pdc"] == 25.0
    assert res["medication_adherence"]["adherence_tier"] == "CRITICAL_NON_ADHERENCE"

    cog = res["acoustic_cognitive_biomarkers"]
    assert cog["cognitive_status"] in ["CLINICAL_EVALUATION_RECOMMENDED", "MILD_COGNITIVE_HESITATION"]
    assert len(cog["detected_signals"]) >= 2


# ===========================================================================
# 6. OpenFDA Polypharmacy Interaction Checker Tests
# ===========================================================================

def test_openfda_polypharmacy_contraindication():
    # Statin + Clarithromycin is CONTRAINDICATED (Rhabdomyolysis)
    meds = ["Atorvastatin 40mg", "Clarithromycin 500mg", "Metformin 1000mg"]
    res = check_openfda_polypharmacy_interactions(meds)
    assert res["status"] == "POLYPHARMACY_CHECK_COMPLETED"
    assert res["overall_safety_rating"] == "CONTRAINDICATION_DETECTED"
    assert any("Rhabdomyolysis" in i["category"] for i in res["interactions"])


def test_openfda_polypharmacy_major_interactions():
    # Lisinopril + Spironolactone (Hyperkalemia) & Warfarin + Ibuprofen (Bleeding)
    meds = ["Lisinopril 20mg", "Spironolactone 25mg", "Warfarin 5mg", "Ibuprofen 400mg"]
    res = check_openfda_polypharmacy_interactions(meds)
    assert res["overall_safety_rating"] in ["MAJOR_INTERACTIONS_ALERT", "CONTRAINDICATION_DETECTED"]
    assert res["interaction_count"] >= 2
    assert any("Hyperkalemia" in i["category"] for i in res["interactions"])
    assert any("Bleed" in i["category"] for i in res["interactions"])


def test_openfda_polypharmacy_clean_regimen():
    meds = ["Acetaminophen 500mg", "Levothyroxine 50mcg"]
    res = check_openfda_polypharmacy_interactions(meds)
    assert res["interaction_count"] == 0
    assert res["overall_safety_rating"] == "NO_KNOWN_HIGH_RISK_INTERACTIONS"


# ===========================================================================
# 7. Federated Learning Simulator Tests
# ===========================================================================

def test_federated_learning_simulation_round():
    res = simulate_federated_learning_morbidity_round(num_nodes=4, privacy_budget_epsilon=1.2, round_number=3)
    assert res["status"] == "FEDERATED_ROUND_CONVERGED"
    assert res["total_contributing_nodes"] == 4
    assert res["total_deidentified_patients_across_borders"] > 10000

    privacy = res["privacy_guarantee"]
    assert "0 Bytes" in privacy["raw_phi_transmitted"]
    assert "HIPAA" in privacy["cross_border_compliance"]

    metrics = res["global_model_metrics"]
    assert metrics["global_auc_roc"] >= 0.80
    assert len(res["participating_nodes"]) == 4


# ===========================================================================
# 8. FastAPI Route Integration Tests (/api/care/chronic/*)
# ===========================================================================

def test_fastapi_chronic_telemetry_endpoint():
    resp = client.post("/api/care/chronic/telemetry", json={
        "source": "Fitbit_Health_Solutions_API",
        "resting_heart_rate": 72.0,
        "hrv_rmssd_ms": 40.0,
        "daily_steps": 7200
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "TELEMETRY_INGESTED"


def test_fastapi_chronic_forecast_endpoint():
    resp = client.post("/api/care/chronic/forecast", json={
        "patient_history": {"baseline_resting_hr": 70.0}
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FORECAST_COMPLETED"
    assert "hypertensive_crisis_forecast" in data


def test_fastapi_chronic_nutrition_insulin_endpoint():
    resp = client.post("/api/care/chronic/nutrition-insulin", json={
        "meal_type": "south_asian_biryani",
        "current_glucose": 140.0,
        "target_glucose": 100.0,
        "icr": 10.0,
        "isf": 50.0
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "NUTRITION_AND_INSULIN_CALCULATED"
    assert data["meal_recognition"]["food_id"] == "south_asian_biryani"


def test_fastapi_chronic_lab_coach_endpoint():
    resp = client.post("/api/care/chronic/lab-coach", json={
        "lab_panel": {"hba1c_pct": 7.4, "egfr_ml_min": 78.0},
        "cultural_diet": "south_asian"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "LAB_TRANSLATION_COMPLETED"


def test_fastapi_chronic_elderly_adherence_endpoint():
    resp = client.post("/api/care/chronic/elderly-adherence", json={
        "medication_log": [{"medication": "Metformin", "status": "TAKEN"}],
        "audio_transcript": "I took all my medicines on time today."
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ELDERLY_CARE_EVALUATED"


def test_fastapi_chronic_polypharmacy_endpoint():
    resp = client.post("/api/care/chronic/polypharmacy", json={
        "medications": ["Lisinopril", "Spironolactone"]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "POLYPHARMACY_CHECK_COMPLETED"
    assert data["interaction_count"] >= 1


def test_fastapi_chronic_federated_round_endpoint():
    resp = client.post("/api/care/chronic/federated-round", json={
        "num_nodes": 4,
        "privacy_budget_epsilon": 1.0,
        "round_number": 4
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FEDERATED_ROUND_CONVERGED"
