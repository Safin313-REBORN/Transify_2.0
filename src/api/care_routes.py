"""
Transify Care FastAPI Route Handler.
Provides secure endpoints for accessible healthcare intake, deterministic triage,
clinical RAG evidence queries, clinician queue management, and offline draft sync.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from src.care.db_care import (
    init_care_db, create_intake, get_intake, list_intakes,
    update_intake_triage, add_clinician_review, get_clinician_reviews,
    log_care_audit, get_connection
)
from src.care.triage import evaluate_triage
from src.care.clinical_rag import search_clinical_evidence, seed_clinical_sources_if_empty

router = APIRouter(prefix="/api/care", tags=["Transify Care"])

# Ensure Care tables and guideline seed on module load
init_care_db()
seed_clinical_sources_if_empty()


# --- Pydantic Schemas ---

class PatientIntakeCreate(BaseModel):
    patient_id: str = Field(default="guest-patient-101", description="Patient identifier")
    input_modality: str = Field(..., description="One of: 'sign', 'braille', 'voice', 'text'")
    raw_input: Optional[str] = Field(default="", description="Original sensor or transcript data")
    confirmed_text: str = Field(..., description="Patient-confirmed symptom text")
    chief_complaint: str = Field(..., description="Primary health concern in clear words")
    symptom_description: str = Field(..., description="Detailed description of symptoms")
    onset_duration: Optional[str] = Field(default="", description="When symptoms began")
    trajectory: Optional[str] = Field(default="stable", description="One of: 'improving', 'stable', 'worsening'")
    severity: Optional[int] = Field(default=1, ge=1, le=10, description="Patient-reported severity 1-10")
    medical_context: Optional[str] = Field(default="", description="Relevant health context or history")
    allergies_medications: Optional[str] = Field(default="", description="Known allergies or medications")
    consent_granted: bool = Field(default=True, description="Explicit patient consent for care intake")


class ClinicianReviewSubmit(BaseModel):
    clinician_id: str = Field(..., description="Healthcare professional ID")
    clinician_name: str = Field(..., description="Doctor or review clinician name")
    action: str = Field(..., description="One of: 'ACCEPTED', 'CLARIFICATION_REQUESTED', 'MODIFIED', 'OVERRIDDEN', 'COMPLETED'")
    urgency_override: Optional[str] = Field(default="NONE", description="Optional overridden status: 'RED', 'YELLOW', 'GREEN', 'NONE'")
    override_reason: Optional[str] = Field(default="", description="Documented medical justification if overriding AI")
    clinical_notes: Optional[str] = Field(default="", description="Reviewer clinical impression and next steps")


class OfflineSyncBatch(BaseModel):
    client_id: str
    drafts: List[PatientIntakeCreate]


# --- Route Implementations ---

@router.post("/intake", status_code=status.HTTP_201_CREATED)
def submit_patient_intake(intake: PatientIntakeCreate):
    """
    Creates a new accessible healthcare intake.
    Executes deterministic clinical triage safety rules and retrieves evidence via Clinical RAG.
    """
    if not intake.consent_granted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient consent is required to process health symptom intake."
        )

    # 1. Evaluate deterministic triage
    triage_result = evaluate_triage(
        chief_complaint=intake.chief_complaint,
        symptom_description=intake.symptom_description,
        severity=intake.severity or 1,
        trajectory=intake.trajectory or "stable",
        onset_duration=intake.onset_duration or ""
    )

    # 2. Retrieve clinical evidence from approved guidelines
    rag_result = search_clinical_evidence(
        query=f"{intake.chief_complaint} {intake.symptom_description}",
        limit=2
    )

    # 3. Create persistent intake record
    intake_id = create_intake(
        patient_id=intake.patient_id,
        input_modality=intake.input_modality,
        raw_input=intake.raw_input or "",
        confirmed_text=intake.confirmed_text,
        chief_complaint=intake.chief_complaint,
        symptom_description=intake.symptom_description,
        onset_duration=intake.onset_duration or "",
        trajectory=intake.trajectory or "stable",
        severity=intake.severity or 1,
        medical_context=intake.medical_context or "",
        allergies_medications=intake.allergies_medications or "",
        consent_granted=intake.consent_granted,
        status="SUBMITTED",
        urgency_level=triage_result["urgency_level"],
        triage_explanation=triage_result["explanation"],
        triage_rule_id=triage_result.get("rule_id", ""),
        evidence_citations=rag_result.get("citations", [])
    )

    return {
        "success": True,
        "intake_id": intake_id,
        "urgency_level": triage_result["urgency_level"],
        "triage_explanation": triage_result["explanation"],
        "rule_id": triage_result.get("rule_id"),
        "emergency_escalation": triage_result.get("emergency_escalation"),
        "evidence_citations": rag_result.get("citations", []),
        "evidence_found": rag_result.get("evidence_found", False),
        "message": "Healthcare intake created and queued for clinician review."
    }


@router.get("/intake/{intake_id}")
def get_single_intake(intake_id: int):
    """Retrieves an intake record with full triage explanation, citations, and review audit."""
    rec = get_intake(intake_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake record not found.")
    reviews = get_clinician_reviews(intake_id)
    rec["clinician_reviews"] = reviews
    return rec


@router.get("/intakes")
def get_intakes_list(
    patient_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100)
):
    """Lists intake submissions. Used for patient history and clinician queue."""
    pid = patient_id if isinstance(patient_id, str) else None
    st = status_filter if isinstance(status_filter, str) else None
    lim = limit if isinstance(limit, int) else 50
    records = list_intakes(patient_id=pid, status=st, limit=lim)
    return {"count": len(records), "records": records}


@router.post("/intake/{intake_id}/review")
def review_patient_intake(intake_id: int, review: ClinicianReviewSubmit):
    """Records a professional clinician review, verification, or override."""
    rec = get_intake(intake_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake record not found.")

    if review.urgency_override and review.urgency_override != "NONE" and not review.override_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A documented clinical justification is required when overriding AI urgency level."
        )

    rev_id = add_clinician_review(
        intake_id=intake_id,
        clinician_id=review.clinician_id,
        clinician_name=review.clinician_name,
        action=review.action,
        urgency_override=review.urgency_override,
        override_reason=review.override_reason,
        clinical_notes=review.clinical_notes or ""
    )

    return {
        "success": True,
        "review_id": rev_id,
        "intake_id": intake_id,
        "message": "Clinician review recorded and intake status updated."
    }


@router.get("/evidence/search")
def search_evidence(q: str = Query(..., min_length=2)):
    """Searches approved clinical guidelines via Clinical RAG."""
    result = search_clinical_evidence(query=q, limit=3)
    return result


@router.get("/sources")
def list_clinical_sources():
    """Lists all approved clinical source documents, checksums, and versions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM care_clinical_sources ORDER BY id ASC;")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"count": len(rows), "sources": rows}


@router.get("/dashboard/stats")
def get_care_dashboard_stats():
    """Returns real operational metrics for the Clinician Review Dashboard."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM care_patient_intakes;")
    total_intakes = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as pending FROM care_patient_intakes WHERE status IN ('SUBMITTED', 'UNDER_REVIEW');")
    pending_review = cursor.fetchone()["pending"]

    cursor.execute("SELECT urgency_level, COUNT(*) as count FROM care_patient_intakes GROUP BY urgency_level;")
    urgency_dist = {r["urgency_level"]: r["count"] for r in cursor.fetchall()}

    cursor.execute("SELECT COUNT(*) as reviewed FROM care_clinician_reviews;")
    total_reviews = cursor.fetchone()["reviewed"]

    cursor.execute("SELECT COUNT(*) as sources FROM care_clinical_sources WHERE status = 'APPROVED';")
    approved_sources = cursor.fetchone()["sources"]

    conn.close()

    return {
        "total_intakes": total_intakes,
        "pending_review": pending_review,
        "urgency_distribution": {
            "RED": urgency_dist.get("RED", 0),
            "YELLOW": urgency_dist.get("YELLOW", 0),
            "GREEN": urgency_dist.get("GREEN", 0),
            "REVIEW_REQUIRED": urgency_dist.get("REVIEW_REQUIRED", 0)
        },
        "total_completed_reviews": total_reviews,
        "approved_clinical_sources": approved_sources,
        "system_status": "ONLINE_NORMAL",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/offline/sync")
def sync_offline_drafts(batch: OfflineSyncBatch):
    """
    Idempotent offline draft synchronization.
    Accepts cached patient drafts created during disconnected or low-bandwidth states.
    """
    synced_ids = []
    for draft in batch.drafts:
        # Check if already present by patient_id + confirmed_text
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id FROM care_patient_intakes
        WHERE patient_id = ? AND confirmed_text = ?;
        """, (draft.patient_id, draft.confirmed_text))
        existing = cursor.fetchone()
        conn.close()

        if existing:
            synced_ids.append(existing["id"])
            continue

        resp = submit_patient_intake(draft)
        synced_ids.append(resp["intake_id"])

    log_care_audit("OFFLINE_SYNC_COMPLETED", batch.client_id, "PATIENT_OFFLINE_CLIENT", None, {"synced_count": len(synced_ids)})

    return {
        "success": True,
        "synced_count": len(synced_ids),
        "intake_ids": synced_ids,
        "message": f"Successfully synchronized {len(synced_ids)} offline drafts."
    }


@router.post("/demo/reset")
def reset_competition_demo_fixtures():
    """
    Resets synthetic demonstration fixtures for repeatable 180-second video recording.
    Populates 3 representative cases (RED emergency, YELLOW urgent dengue, GREEN routine).
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Delete test fixtures
    cursor.execute("DELETE FROM care_patient_intakes WHERE patient_id LIKE 'demo-patient-%';")
    cursor.execute("DELETE FROM care_clinician_reviews WHERE clinician_id = 'demo-dr-rahim';")
    conn.commit()
    conn.close()

    # Fixture 1: RED - Acute Chest Pain (Sign Language Input)
    intake_red = PatientIntakeCreate(
        patient_id="demo-patient-001",
        input_modality="sign",
        raw_input="Recognized sign sequence: CHEST PAIN, HARD_TO_BREATH, EMERGENCY",
        confirmed_text="I have severe crushing chest pain radiating to my left arm for 45 minutes and feeling breathless.",
        chief_complaint="Severe crushing chest pain and shortness of breath",
        symptom_description="Crushing substernal pressure, left arm radiation, diaphoresis, sudden onset while resting.",
        onset_duration="45 minutes",
        trajectory="worsening",
        severity=9,
        medical_context="Hypertension, non-smoker, deaf signer (BdSL primary)",
        allergies_medications="Amlodipine 5mg",
        consent_granted=True
    )
    submit_patient_intake(intake_red)

    # Fixture 2: YELLOW - Febrile Illness / Dengue Warning Signs (Voice Input)
    intake_yellow = PatientIntakeCreate(
        patient_id="demo-patient-002",
        input_modality="voice",
        raw_input="Speech transcript: 3 days high fever, severe stomach pain and vomiting, cannot drink water",
        confirmed_text="High fever for 3 days with severe persistent stomach pain and vomiting. Feeling very weak.",
        chief_complaint="High fever and severe persistent stomach pain",
        symptom_description="High grade fever (103 F), body aches, severe abdominal tenderness, nausea, unable to keep liquids down.",
        onset_duration="3 days",
        trajectory="worsening",
        severity=7,
        medical_context="Dhaka urban resident, dengue prevalent area",
        allergies_medications="None reported",
        consent_granted=True
    )
    submit_patient_intake(intake_yellow)

    # Fixture 3: GREEN - Routine Mild Cough & Sore Throat (Braille Input)
    intake_green = PatientIntakeCreate(
        patient_id="demo-patient-003",
        input_modality="braille",
        raw_input="Braille UEB OCR output: mild dry cough and slight scratchy throat for two days, no fever",
        confirmed_text="Mild dry cough and slight scratchy throat for two days without fever or difficulty breathing.",
        chief_complaint="Mild dry cough and scratchy throat",
        symptom_description="Occasional dry cough, throat irritation, no fever, eating and sleeping normally.",
        onset_duration="2 days",
        trajectory="stable",
        severity=2,
        medical_context="Visually impaired student",
        allergies_medications="None",
        consent_granted=True
    )
    submit_patient_intake(intake_green)

    return {
        "success": True,
        "message": "Demo fixtures initialized: RED (Sign), YELLOW (Voice), GREEN (Braille)."
    }
