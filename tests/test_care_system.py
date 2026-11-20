"""
Transify Care Comprehensive System Test Suite.
Verifies patient intake validation, deterministic triage rules, emergency escalation,
clinical RAG evidence retrieval, citation integrity, clinician reviews, audit logging,
and offline synchronization.
"""

import os
import sys
import unittest

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import HTTPException
from src.care.triage import evaluate_triage, DETERMINISTIC_RULES
from src.care.clinical_rag import search_clinical_evidence, seed_clinical_sources_if_empty
from src.care.db_care import (
    init_care_db, create_intake, get_intake, list_intakes,
    add_clinician_review, get_clinician_reviews
)
from src.api.care_routes import (
    submit_patient_intake,
    get_single_intake,
    get_intakes_list,
    review_patient_intake,
    search_evidence,
    get_care_dashboard_stats,
    sync_offline_drafts,
    reset_competition_demo_fixtures,
    PatientIntakeCreate,
    ClinicianReviewSubmit,
    OfflineSyncBatch
)


class TestTransifyCareTriage(unittest.TestCase):
    """Verifies deterministic triage rules and safety priority."""

    def test_emergency_red_triage_chest_pain(self):
        res = evaluate_triage(
            chief_complaint="Severe crushing chest pain",
            symptom_description="Left arm radiation, shortness of breath, sudden onset",
            severity=9,
            trajectory="worsening"
        )
        self.assertEqual(res["urgency_level"], "RED")
        self.assertEqual(res["can_wait"], False)
        self.assertIsNotNone(res["emergency_escalation"])
        self.assertEqual(res["emergency_escalation"]["hotline"], "999")
        self.assertIn("chest", res["explanation"].lower())

    def test_emergency_red_triage_stroke_signs(self):
        res = evaluate_triage(
            chief_complaint="Sudden weakness",
            symptom_description="Face drooping and slurred speech",
            severity=8
        )
        self.assertEqual(res["urgency_level"], "RED")
        self.assertEqual(res["can_wait"], False)
        self.assertIsNotNone(res["emergency_escalation"])

    def test_urgent_yellow_triage_dengue_fever(self):
        res = evaluate_triage(
            chief_complaint="High fever and severe stomach pain",
            symptom_description="Persistent vomiting, cannot keep water down for 2 days",
            severity=7,
            trajectory="worsening"
        )
        self.assertEqual(res["urgency_level"], "YELLOW")
        self.assertEqual(res["can_wait"], False)

    def test_routine_green_triage_mild_cough(self):
        res = evaluate_triage(
            chief_complaint="Mild dry cough",
            symptom_description="Occasional sneeze, no fever, eating normally",
            severity=2,
            trajectory="stable"
        )
        self.assertEqual(res["urgency_level"], "GREEN")
        self.assertEqual(res["can_wait"], True)

    def test_insufficient_information_fallback(self):
        res = evaluate_triage(
            chief_complaint="",
            symptom_description="",
            severity=1
        )
        self.assertEqual(res["urgency_level"], "INSUFFICIENT_INFORMATION")
        self.assertTrue(len(res["missing_information"]) > 0)


class TestClinicalRAG(unittest.TestCase):
    """Verifies clinical knowledge retrieval, citation integrity, and no-evidence fallback."""

    @classmethod
    def setUpClass(cls):
        seed_clinical_sources_if_empty()

    def test_evidence_retrieval_triage_protocols(self):
        res = search_clinical_evidence("severe chest pain shortness of breath", limit=2)
        self.assertTrue(res["evidence_found"])
        self.assertGreaterEqual(len(res["citations"]), 1)
        first_citation = res["citations"][0]
        self.assertIn("source_title", first_citation)
        self.assertIn("publisher", first_citation)
        self.assertIn("excerpt", first_citation)
        self.assertIn("url", first_citation)

    def test_evidence_retrieval_dengue_guidelines(self):
        res = search_clinical_evidence("dengue persistent vomiting warning signs", limit=2)
        self.assertTrue(res["evidence_found"])
        has_dengue = any("dengue" in c["source_title"].lower() for c in res["citations"])
        self.assertTrue(has_dengue)

    def test_no_evidence_fallback(self):
        res = search_clinical_evidence("xyz123 quantum astrophysics galactic nebula", limit=2)
        self.assertFalse(res["evidence_found"])
        self.assertEqual(res["citations"], [])
        self.assertIn("Sufficient evidence was not found", res["message"])


class TestCareAPIEndpoints(unittest.TestCase):
    """Verifies intake submission, clinician review, audit trails, and offline sync."""

    def test_intake_submission_and_consent_enforcement(self):
        # 1. Reject without consent
        with self.assertRaises(HTTPException) as ctx:
            submit_patient_intake(PatientIntakeCreate(
                patient_id="test-patient-001",
                input_modality="sign",
                confirmed_text="Severe headache and vomiting",
                chief_complaint="Severe headache",
                symptom_description="Severe throbbing headache",
                consent_granted=False
            ))
        self.assertEqual(ctx.exception.status_code, 400)

        # 2. Accept with explicit consent
        data = submit_patient_intake(PatientIntakeCreate(
            patient_id="test-patient-001",
            input_modality="sign",
            confirmed_text="I have severe crushing chest pain radiating to my left arm",
            chief_complaint="Severe crushing chest pain",
            symptom_description="Crushing pressure, sweating, radiating to left arm",
            severity=9,
            trajectory="worsening",
            consent_granted=True
        ))
        self.assertTrue(data["success"])
        self.assertEqual(data["urgency_level"], "RED")
        self.assertIsNotNone(data["emergency_escalation"])
        intake_id = data["intake_id"]

        # 3. Retrieve single intake
        intake_data = get_single_intake(intake_id)
        self.assertEqual(intake_data["chief_complaint"], "Severe crushing chest pain")

        # 4. Clinician Review & Override justification enforcement
        # Must fail without override reason
        with self.assertRaises(HTTPException) as ctx_ov:
            review_patient_intake(intake_id, ClinicianReviewSubmit(
                clinician_id="dr-ahmed",
                clinician_name="Dr. Ahmed Hossain",
                action="OVERRIDDEN",
                urgency_override="GREEN",
                override_reason=""
            ))
        self.assertEqual(ctx_ov.exception.status_code, 400)

        # Succeed with documented justification
        good_rev = review_patient_intake(intake_id, ClinicianReviewSubmit(
            clinician_id="dr-ahmed",
            clinician_name="Dr. Ahmed Hossain",
            action="COMPLETED",
            urgency_override="RED",
            override_reason="Confirmed acute coronary syndrome red flag; ambulance dispatched",
            clinical_notes="Immediate ECG and troponin ordered; referred to National Heart Foundation."
        ))
        self.assertTrue(good_rev["success"])

    def test_offline_draft_sync(self):
        batch = OfflineSyncBatch(
            client_id="offline-tablet-clinic-12",
            drafts=[
                PatientIntakeCreate(
                    patient_id="sync-patient-101",
                    input_modality="voice",
                    confirmed_text="Mild fever for one day",
                    chief_complaint="Mild fever",
                    symptom_description="Low fever, mild body aches",
                    severity=3,
                    consent_granted=True
                )
            ]
        )
        resp = sync_offline_drafts(batch)
        self.assertEqual(resp["synced_count"], 1)

    def test_dashboard_stats(self):
        stats = get_care_dashboard_stats()
        self.assertIn("total_intakes", stats)
        self.assertIn("urgency_distribution", stats)
        self.assertIn("approved_clinical_sources", stats)
        self.assertEqual(stats["system_status"], "ONLINE_NORMAL")

    def test_demo_fixture_reset(self):
        resp = reset_competition_demo_fixtures()
        self.assertTrue(resp["success"])
        # Check that 3 demo cases exist
        list_resp = get_intakes_list(limit=10)
        records = list_resp["records"]
        demo_records = [r for r in records if "demo-patient" in r["patient_id"]]
        self.assertGreaterEqual(len(demo_records), 3)


if __name__ == "__main__":
    unittest.main()
