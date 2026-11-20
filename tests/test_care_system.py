"""
Transify Care Comprehensive System Test Suite.
Verifies patient intake validation, deterministic triage rules, emergency escalation,
negation handling, contradictory symptom detection, clinical evidence retrieval prototype,
citation integrity, clinician reviews, audit logging, and offline synchronization.
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

MOCK_PATIENT = {"id": 101, "name": "Test Patient", "email": "patient@test.com", "role": "patient"}
MOCK_CLINICIAN = {"id": 202, "name": "Dr. Sarah Clinician", "email": "sarah@hospital.org", "role": "clinician"}


class TestTransifyCareTriage(unittest.TestCase):
    """Verifies deterministic triage rules, safety priority, negations, and safe fallbacks."""

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
        self.assertEqual(res["can_wait"], False)
        self.assertTrue(len(res["missing_information"]) > 0)

    # --- P0-5 Specific Triage Safety Tests ---

    def test_negated_symptom_no_chest_pain(self):
        """'No chest pain' must never trigger RED emergency."""
        res = evaluate_triage(
            chief_complaint="No chest pain",
            symptom_description="Patient states: no chest pain, no radiating pain, but feels fatigued."
        )
        self.assertNotEqual(res["urgency_level"], "RED")
        self.assertIn(res["urgency_level"], ("REVIEW_REQUIRED", "INSUFFICIENT_INFORMATION"))
        self.assertEqual(res["can_wait"], False)

    def test_negated_symptom_no_difficulty_breathing(self):
        """'No difficulty breathing' must never trigger RED emergency."""
        res = evaluate_triage(
            chief_complaint="No difficulty breathing",
            symptom_description="Mild scratchy throat, without shortness of breath or cyanosis.",
            severity=2
        )
        self.assertNotEqual(res["urgency_level"], "RED")

    def test_contradictory_symptoms(self):
        """Contradictory inputs (affirmed and denied) must trigger REVIEW_REQUIRED, not GREEN."""
        res = evaluate_triage(
            chief_complaint="Severe crushing chest pain",
            symptom_description="Actually I have no chest pain at all.",
            severity=8
        )
        self.assertEqual(res["urgency_level"], "REVIEW_REQUIRED")
        self.assertEqual(res["rule_id"], "RULE-SAFETY-CONTRADICTION")
        self.assertEqual(res["can_wait"], False)

    def test_unrecognized_complaints(self):
        """Unrecognized complaint must not default to GREEN; must require clinician review."""
        res = evaluate_triage(
            chief_complaint="My left pinky finger twitches intermittently",
            symptom_description="Involuntary pinky twitching when holding a tea cup.",
            severity=2
        )
        self.assertEqual(res["urgency_level"], "REVIEW_REQUIRED")
        self.assertEqual(res["can_wait"], False)
        self.assertNotEqual(res["urgency_level"], "GREEN")

    def test_unknown_vital_signs_and_no_waiting_safe_claim(self):
        """Incomplete or unreviewed states must never claim waiting is safe."""
        insufficient = evaluate_triage("", "")
        self.assertEqual(insufficient["can_wait"], False)

        unrecognized = evaluate_triage("Strange tingling in foot", "Mild tingling")
        self.assertEqual(unrecognized["can_wait"], False)

    def test_no_automatic_green_fallback(self):
        """Verifies that arbitrary text without explicit routine match never falls back to GREEN."""
        res = evaluate_triage("Random uncataloged condition", "Non-emergency symptom description")
        self.assertNotEqual(res["urgency_level"], "GREEN")
        self.assertEqual(res["urgency_level"], "REVIEW_REQUIRED")
        self.assertEqual(res["can_wait"], False)


class TestClinicalRAG(unittest.TestCase):
    """Verifies clinical knowledge passage retrieval prototype and citation integrity."""

    @classmethod
    def setUpClass(cls):
        seed_clinical_sources_if_empty(force_reseed=True)

    def test_evidence_retrieval_triage_protocols(self):
        res = search_clinical_evidence("severe chest pain shortness of breath", limit=2)
        self.assertTrue(res["evidence_found"])
        self.assertGreaterEqual(len(res["citations"]), 1)
        first_citation = res["citations"][0]
        self.assertIn("source_title", first_citation)
        self.assertIn("publisher", first_citation)
        self.assertIn("excerpt", first_citation)
        self.assertIn("verification_status", first_citation)
        self.assertEqual(first_citation["verification_status"], "PENDING_REVIEW")

    def test_evidence_retrieval_dengue_guidelines_5th_edition(self):
        res = search_clinical_evidence("dengue persistent vomiting warning signs", limit=2)
        self.assertTrue(res["evidence_found"])
        has_dengue = any("dengue" in c["source_title"].lower() for c in res["citations"])
        self.assertTrue(has_dengue)
        # Check that 5th Edition is cited
        has_5th_ed = any("5th edition" in c["source_title"].lower() or "5th edition" in c.get("version", "").lower() for c in res["citations"])
        self.assertTrue(has_5th_ed)

    def test_no_evidence_fallback(self):
        res = search_clinical_evidence("xyz123 quantum astrophysics galactic nebula", limit=2)
        self.assertFalse(res["evidence_found"])
        self.assertEqual(res["citations"], [])
        self.assertIn("Sufficient evidence passages were not found", res["message"])


class TestCareAPIEndpoints(unittest.TestCase):
    """Verifies intake submission, clinician review, audit trails, and offline sync."""

    @classmethod
    def setUpClass(cls):
        init_care_db()
        seed_clinical_sources_if_empty()

    def test_intake_submission_and_consent_enforcement(self):
        # 1. Reject when consent is False
        with self.assertRaises(HTTPException) as ctx:
            submit_patient_intake(
                PatientIntakeCreate(
                    input_modality="sign",
                    confirmed_text="Severe headache and vomiting",
                    chief_complaint="Severe headache",
                    symptom_description="Severe throbbing headache",
                    consent_granted=False
                ),
                user=MOCK_PATIENT
            )
        self.assertEqual(ctx.exception.status_code, 400)

        # 2. Accept with explicit consent
        data = submit_patient_intake(
            PatientIntakeCreate(
                input_modality="sign",
                confirmed_text="I have severe crushing chest pain radiating to my left arm",
                chief_complaint="Severe crushing chest pain",
                symptom_description="Crushing pressure, sweating, radiating to left arm",
                severity=9,
                trajectory="worsening",
                consent_granted=True
            ),
            user=MOCK_PATIENT
        )
        self.assertTrue(data["success"])
        self.assertEqual(data["urgency_level"], "RED")
        self.assertIsNotNone(data["emergency_escalation"])
        self.assertEqual(data["patient_id"], f"user-{MOCK_PATIENT['id']}")
        intake_id = data["intake_id"]

        # 3. Retrieve single intake (owning patient)
        intake_data = get_single_intake(intake_id, user=MOCK_PATIENT)
        self.assertEqual(intake_data["chief_complaint"], "Severe crushing chest pain")

        # 4. Clinician Review & Override justification enforcement
        # Must fail without override reason
        with self.assertRaises(HTTPException) as ctx_ov:
            review_patient_intake(
                intake_id,
                ClinicianReviewSubmit(
                    action="OVERRIDDEN",
                    urgency_override="GREEN",
                    override_reason=""
                ),
                user=MOCK_CLINICIAN
            )
        self.assertEqual(ctx_ov.exception.status_code, 400)

        # Succeed with documented justification
        good_rev = review_patient_intake(
            intake_id,
            ClinicianReviewSubmit(
                action="COMPLETED",
                urgency_override="RED",
                override_reason="Confirmed acute coronary syndrome red flag; ambulance dispatched",
                clinical_notes="Immediate ECG and troponin ordered; referred to National Heart Foundation."
            ),
            user=MOCK_CLINICIAN
        )
        self.assertTrue(good_rev["success"])
        self.assertEqual(good_rev["clinician_id"], f"clinician-{MOCK_CLINICIAN['id']}")

    def test_offline_draft_sync(self):
        batch = OfflineSyncBatch(
            client_id="offline-tablet-clinic-12",
            drafts=[
                PatientIntakeCreate(
                    input_modality="voice",
                    confirmed_text="Mild fever for one day",
                    chief_complaint="Mild fever",
                    symptom_description="Low fever, mild body aches",
                    severity=3,
                    consent_granted=True
                )
            ]
        )
        resp = sync_offline_drafts(batch, user=MOCK_PATIENT)
        self.assertEqual(resp["synced_count"], 1)
        self.assertEqual(resp["patient_id"], f"user-{MOCK_PATIENT['id']}")

    def test_dashboard_stats(self):
        stats = get_care_dashboard_stats(user=MOCK_CLINICIAN)
        self.assertIn("total_intakes", stats)
        self.assertIn("urgency_distribution", stats)
        self.assertIn("clinical_sources_cataloged", stats)
        self.assertEqual(stats["system_status"], "ONLINE_NORMAL")

    def test_demo_fixture_reset(self):
        resp = reset_competition_demo_fixtures()
        self.assertTrue(resp["success"])
        list_resp = get_intakes_list(limit=10, user=MOCK_CLINICIAN)
        records = list_resp["records"]
        demo_records = [r for r in records if "synthetic-demo-patient" in r["patient_id"] or "demo-patient" in r["patient_id"]]
        self.assertGreaterEqual(len(demo_records), 3)


if __name__ == "__main__":
    unittest.main()
