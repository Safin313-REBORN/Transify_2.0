"""
Transify Care FastAPI Route Handler.
Provides secure endpoints for accessible healthcare intake, deterministic triage,
clinical evidence passage retrieval prototype, clinician queue management, and offline draft sync.
Enforces server-side authentication, role-based authorization, mandatory patient consent,
strict cross-user isolation, and controlled development synthetic clinician mode.
"""

import os
import json
from fastapi import APIRouter, HTTPException, Depends, Query, Request, Response, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

import secrets
from src.database.db import (
    get_user_by_session,
    create_session,
    create_user,
    get_user_by_email,
    is_production,
    is_dev_clinician_enabled,
    is_demo_mode_enabled
)
from src.care.db_care import (
    init_care_db, create_intake, get_intake, list_intakes,
    update_intake_triage, add_clinician_review, get_clinician_reviews,
    log_care_audit, get_connection
)
from src.care.triage import evaluate_triage
from src.care.clinical_rag import search_clinical_evidence, seed_clinical_sources_if_empty
from src.care.care_anywhere import (
    analyze_multimodal_vision,
    process_regional_speech_intake,
    assess_local_outbreak_risk,
    find_nearby_health_facilities,
    compute_intake_idempotency_hash,
    map_text_to_mesh_descriptors
)

router = APIRouter(prefix="/api/care", tags=["Transify Care"])

# Ensure Care tables and guideline seed on module load
init_care_db()
seed_clinical_sources_if_empty()

SYNTHETIC_DEV_CLINICIAN_EMAIL = "dev-synthetic-clinician@transify.local"


# --- Security & Authorization Dependencies ---

def is_authorized_clinician(user: Dict[str, Any]) -> bool:
    """
    Verifies whether the authenticated user holds valid clinician authority.
    - Verified clinician or admin accounts retain normal clinician authority.
    - Normal clinician/admin authorization never automatically includes dev_clinician.
    - A dev_clinician role may access clinician functionality only if:
        1. is_production() is False;
        2. TRANSIFY_DEV_CLINICIAN_ENABLED is explicitly true;
        3. the session belongs to the intended synthetic development account (dev-synthetic-clinician@transify.local).
    - Production authentication strictly rejects synthetic development clinician accounts.
    """
    role = (user.get("role") or "").lower()
    email = (user.get("email") or "").lower()

    if role == "dev_clinician" or email == SYNTHETIC_DEV_CLINICIAN_EMAIL:
        if is_production():
            return False
        if not is_dev_clinician_enabled():
            return False
        return role == "dev_clinician" and email == SYNTHETIC_DEV_CLINICIAN_EMAIL

    return role in ("clinician", "admin")


def get_authenticated_user(request: Request) -> Dict[str, Any]:
    """
    Enforces valid authenticated session from HttpOnly cookie or Authorization header.
    Never trusts client-supplied user or patient IDs.
    Returns authenticated user profile or raises HTTP 401 Unauthorized.
    """
    token = request.cookies.get("transify_session")
    if not token:
        auth_hdr = request.headers.get("Authorization") or request.headers.get("authorization")
        if auth_hdr and auth_hdr.lower().startswith("bearer "):
            token = auth_hdr.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in with a valid session."
        )

    user = get_user_by_session(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again."
        )

    return user


def require_clinician(user: Dict[str, Any] = Depends(get_authenticated_user)) -> Dict[str, Any]:
    """
    Enforces server-verified clinician role.
    Rejects patient accounts with HTTP 403 Forbidden.
    In development mode, controlled synthetic clinician mode is allowed only when explicitly opted in.
    In production mode, synthetic clinician mode is strictly disabled.
    """
    if is_authorized_clinician(user):
        return user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Clinician authorization required. Access restricted to verified clinician accounts."
    )


# --- Pydantic Schemas ---

class PatientIntakeCreate(BaseModel):
    # Client-supplied patient_id is explicitly ignored by the server
    patient_id: Optional[str] = Field(default=None, description="Patient identifier (overridden by server)")
    input_modality: str = Field(..., description="One of: 'sign', 'braille', 'voice', 'text', 'vision', 'multimodal'")
    raw_input: Optional[str] = Field(default="", description="Original sensor or transcript data")
    confirmed_text: str = Field(..., description="Patient-confirmed symptom text")
    chief_complaint: str = Field(..., description="Primary health concern in clear words")
    symptom_description: str = Field(..., description="Detailed description of symptoms")
    onset_duration: Optional[str] = Field(default="", description="When symptoms began")
    trajectory: Optional[str] = Field(default="stable", description="One of: 'improving', 'stable', 'worsening'")
    severity: Optional[int] = Field(default=1, ge=1, le=10, description="Patient-reported severity 1-10")
    medical_context: Optional[str] = Field(default="", description="Relevant health context or history")
    allergies_medications: Optional[str] = Field(default="", description="Known allergies or medications")
    consent_granted: bool = Field(..., description="Explicit patient consent for care intake (mandatory)")
    # CareAnywhere Multimodal Extensions
    image_base64: Optional[str] = Field(default=None, description="Base64 encoded smartphone image of skin lesion or eye condition")
    condition_type: Optional[str] = Field(default="auto", description="'skin', 'eye', or 'auto'")
    audio_transcript: Optional[str] = Field(default=None, description="Regional speech-to-text transcript")
    gps_latitude: Optional[float] = Field(default=None, description="GPS latitude for localized outbreak assessment")
    gps_longitude: Optional[float] = Field(default=None, description="GPS longitude for localized outbreak assessment")
    district: Optional[str] = Field(default=None, description="Administrative district name")
    idempotency_key: Optional[str] = Field(default=None, description="SHA-256 idempotency key for store-and-forward sync")
    offline_created_at: Optional[str] = Field(default=None, description="Timestamp when draft was captured offline")


class ClinicianReviewSubmit(BaseModel):
    # Client-supplied clinician details are explicitly ignored by the server
    clinician_id: Optional[str] = Field(default=None, description="Healthcare professional ID (overridden by server)")
    clinician_name: Optional[str] = Field(default=None, description="Doctor or review clinician name (overridden by server)")
    action: str = Field(..., description="One of: 'ACCEPTED', 'CLARIFICATION_REQUESTED', 'MODIFIED', 'OVERRIDDEN', 'COMPLETED'")
    urgency_override: Optional[str] = Field(default="NONE", description="Optional overridden status: 'RED', 'YELLOW', 'GREEN', 'NONE'")
    override_reason: Optional[str] = Field(default="", description="Documented medical justification if overriding AI")
    clinical_notes: Optional[str] = Field(default="", description="Reviewer clinical impression and next steps")


class OfflineSyncBatch(BaseModel):
    client_id: str
    drafts: List[PatientIntakeCreate]


class EvidenceSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Clinical search terms (transmitted via POST body to avoid query string logging)")


class VisionAnalyzeRequest(BaseModel):
    image_data: str = Field(..., description="Base64 image data URI or raw base64 string")
    condition_type: Optional[str] = Field(default="auto", description="'skin', 'eye', or 'auto'")


class AudioIntakeRequest(BaseModel):
    transcript: str = Field(..., description="Spoken symptom text or dialect transcript")
    dialect_hint: Optional[str] = Field(default="auto", description="Optional dialect hint: 'sylheti', 'chittagonian', 'bn_standard'")


class StoreAndForwardSyncRequest(BaseModel):
    client_id: str = Field(default="offline-mobile-client")
    batch: List[PatientIntakeCreate]


# --- Route Implementations ---

@router.post("/intake", status_code=status.HTTP_201_CREATED)
def submit_patient_intake(
    intake: PatientIntakeCreate,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Creates a new accessible healthcare intake.
    Enforces mandatory explicit patient consent (rejects missing or false consent).
    Derives patient identity strictly from authenticated session.
    Executes deterministic clinical triage safety rules, computer vision lesion analysis,
    outbreak risk assessment, MeSH terminology mapping, and retrieves reference evidence.
    """
    # P0-2: Mandatory Consent Enforcement
    if not intake.consent_granted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit patient consent is mandatory to process health symptom intake."
        )

    # P0-3: Derive patient identity from server session; ignore client-supplied patient_id
    server_patient_id = f"user-{user['id']}"

    # 1. Evaluate deterministic triage safety rules
    triage_result = evaluate_triage(
        chief_complaint=intake.chief_complaint,
        symptom_description=intake.symptom_description,
        severity=intake.severity or 1,
        trajectory=intake.trajectory or "stable",
        onset_duration=intake.onset_duration or ""
    )

    # 2. CareAnywhere Computer Vision Analysis (if image provided)
    cv_analysis = None
    cv_json = None
    if intake.image_base64:
        try:
            cv_analysis = analyze_multimodal_vision(intake.image_base64, intake.condition_type or "auto")
            cv_json = json.dumps(cv_analysis)
            # Elevate triage level if vision reveals emergent or urgent finding
            cv_urgency = cv_analysis.get("urgency_level")
            if cv_urgency == "EMERGENT":
                triage_result["urgency_level"] = "RED"
                triage_result["explanation"] += f" [Computer Vision Warning: {cv_analysis['findings'][0]}]"
            elif cv_urgency == "URGENT" and triage_result["urgency_level"] in ("GREEN", "ROUTINE", "UNKNOWN"):
                triage_result["urgency_level"] = "YELLOW"
                triage_result["explanation"] += f" [Computer Vision Finding: {cv_analysis['findings'][0]}]"
        except Exception as e:
            cv_analysis = {"error": f"Image processing failed: {str(e)}"}
            cv_json = json.dumps(cv_analysis)

    # 3. Regional Dialect Processing (if audio transcript provided)
    dialect_analysis = None
    if intake.audio_transcript:
        dialect_analysis = process_regional_speech_intake(intake.audio_transcript)

    # 4. Standardized U.S. NLM MeSH Terminology Normalization
    combined_text = f"{intake.chief_complaint} {intake.symptom_description} {intake.confirmed_text}"
    mesh_descriptors = map_text_to_mesh_descriptors(combined_text)
    mesh_json = json.dumps(mesh_descriptors)

    # 5. Localized Outbreak & Epidemic Risk Assessment
    outbreak_analysis = None
    outbreak_json = None
    if intake.gps_latitude is not None or intake.gps_longitude is not None or intake.district:
        outbreak_analysis = assess_local_outbreak_risk(
            lat=intake.gps_latitude,
            lon=intake.gps_longitude,
            district=intake.district,
            symptoms_text=combined_text
        )
        outbreak_json = json.dumps(outbreak_analysis)

    # 6. Retrieve clinical evidence from reference guideline prototype (Merck Manuals, WHO, DGHS)
    rag_result = search_clinical_evidence(
        query=f"{intake.chief_complaint} {intake.symptom_description}",
        limit=2
    )

    # 7. Create persistent intake record with server-derived identity
    intake_id = create_intake(
        patient_id=server_patient_id,
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
        evidence_citations=rag_result.get("citations", []),
        vision_analysis_json=cv_json,
        audio_transcript=intake.audio_transcript,
        outbreak_context_json=outbreak_json,
        mesh_terms=mesh_json,
        offline_synced_at=intake.offline_created_at,
        idempotency_key=intake.idempotency_key
    )

    return {
        "success": True,
        "intake_id": intake_id,
        "patient_id": server_patient_id,
        "urgency_level": triage_result["urgency_level"],
        "triage_explanation": triage_result["explanation"],
        "rule_id": triage_result.get("rule_id"),
        "emergency_escalation": triage_result.get("emergency_escalation"),
        "evidence_citations": rag_result.get("citations", []),
        "evidence_found": rag_result.get("evidence_found", False),
        "vision_analysis": cv_analysis,
        "outbreak_context": outbreak_analysis,
        "mesh_descriptors": mesh_descriptors,
        "message": "Healthcare intake created and queued for clinician review."
    }


@router.get("/intake/{intake_id}")
def get_single_intake(
    intake_id: int,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Retrieves an intake record.
    Enforces cross-user isolation: Patients can only view their own intake records.
    Clinicians can view any intake record for review purposes.
    """
    rec = get_intake(intake_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake record not found.")

    server_patient_id = f"user-{user['id']}"
    is_clinician = is_authorized_clinician(user)

    # Strict user isolation check
    if not is_clinician and rec["patient_id"] != server_patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not authorized to view another patient's medical intake."
        )

    reviews = get_clinician_reviews(intake_id)
    rec["clinician_reviews"] = reviews
    return rec


@router.get("/intakes")
def get_intakes_list(
    patient_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Lists intake submissions.
    Patients are strictly restricted to their own patient history (cross-user queries rejected).
    Clinicians can view the triage queue.
    """
    server_patient_id = f"user-{user['id']}"
    is_clinician = is_authorized_clinician(user)
    st = status_filter if isinstance(status_filter, str) else None
    lim = limit if isinstance(limit, int) else 50

    if not is_clinician:
        # Non-clinicians can only view their own records; ignore client-provided patient_id query
        records = list_intakes(patient_id=server_patient_id, status=st, limit=lim)
    else:
        # Clinicians can inspect queue or filter by specific patient_id
        pid = patient_id if isinstance(patient_id, str) else None
        records = list_intakes(patient_id=pid, status=st, limit=lim)

    return {"count": len(records), "records": records}


@router.post("/intake/{intake_id}/review")
def review_patient_intake(
    intake_id: int,
    review: ClinicianReviewSubmit,
    user: Dict[str, Any] = Depends(require_clinician)
):
    """
    Records a professional clinician review, verification, or override.
    Requires server-verified clinician role (patients rejected with 403).
    Derives clinician identity strictly from authenticated session.
    Mandates documented clinical justification for any urgency override.
    """
    rec = get_intake(intake_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake record not found.")

    if review.urgency_override and review.urgency_override != "NONE" and not (review.override_reason or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A documented clinical justification is required when overriding AI urgency level."
        )

    # Ignore client-supplied clinician ID and name; use server identity
    server_clinician_id = f"clinician-{user['id']}"
    server_clinician_name = user.get("name") or "Clinician Reviewer"

    rev_id = add_clinician_review(
        intake_id=intake_id,
        clinician_id=server_clinician_id,
        clinician_name=server_clinician_name,
        action=review.action,
        urgency_override=review.urgency_override,
        override_reason=review.override_reason,
        clinical_notes=review.clinical_notes or ""
    )

    return {
        "success": True,
        "review_id": rev_id,
        "intake_id": intake_id,
        "clinician_id": server_clinician_id,
        "clinician_name": server_clinician_name,
        "message": "Clinician review recorded and intake status updated."
    }


@router.get("/evidence/search")
def search_evidence(
    q: str = Query(..., min_length=2),
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Searches cataloged clinical guideline excerpts via keyword prototype.
    Requires authenticated session.
    """
    result = search_clinical_evidence(query=q, limit=3)
    return result


@router.post("/evidence/search")
def search_evidence_post(
    req: EvidenceSearchRequest,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Searches cataloged clinical guideline excerpts via keyword prototype.
    Accepts search query via JSON body to avoid logging sensitive health terms in server URL logs.
    Requires authenticated session.
    """
    result = search_clinical_evidence(query=req.query, limit=3)
    return result


@router.get("/sources")
def list_clinical_sources(user: Dict[str, Any] = Depends(get_authenticated_user)):
    """Lists cataloged clinical source reference documents, versions, and prototype review status."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, source_id, title, publisher, url, publication_date, version,
           document_type, licensing_status, checksum, status, reviewer, chunks_count, created_at
    FROM care_clinical_sources ORDER BY id ASC;
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"count": len(rows), "sources": rows}


@router.get("/dashboard/stats")
def get_care_dashboard_stats(user: Dict[str, Any] = Depends(require_clinician)):
    """
    Returns aggregated operational metrics for the Clinician Review Dashboard.
    Strictly prevents leaking any personal health data or patient identifiers.
    """
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

    cursor.execute("SELECT COUNT(*) as sources FROM care_clinical_sources;")
    total_sources = cursor.fetchone()["sources"]

    conn.close()

    return {
        "total_intakes": total_intakes,
        "pending_review": pending_review,
        "urgency_distribution": {
            "RED": urgency_dist.get("RED", 0),
            "YELLOW": urgency_dist.get("YELLOW", 0),
            "GREEN": urgency_dist.get("GREEN", 0),
            "REVIEW_REQUIRED": urgency_dist.get("REVIEW_REQUIRED", 0),
            "INSUFFICIENT_INFORMATION": urgency_dist.get("INSUFFICIENT_INFORMATION", 0)
        },
        "total_completed_reviews": total_reviews,
        "clinical_sources_cataloged": total_sources,
        "system_status": "ONLINE_NORMAL",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/offline/sync")
def sync_offline_drafts(
    batch: OfflineSyncBatch,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    Idempotent offline draft synchronization.
    Requires authenticated session; attributes all synced intakes to the authenticated patient.
    Rejects any draft lacking explicit patient consent.
    """
    server_patient_id = f"user-{user['id']}"
    synced_ids = []

    for draft in batch.drafts:
        # Mandatory consent check
        if not draft.consent_granted:
            continue

        # Force patient_id to authenticated session
        draft.patient_id = server_patient_id

        # Check if already present by patient_id + confirmed_text
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id FROM care_patient_intakes
        WHERE patient_id = ? AND confirmed_text = ?;
        """, (server_patient_id, draft.confirmed_text))
        existing = cursor.fetchone()
        conn.close()

        if existing:
            synced_ids.append(existing["id"])
            continue

        resp = submit_patient_intake(draft, user=user)
        synced_ids.append(resp["intake_id"])

    log_care_audit(
        "OFFLINE_SYNC_COMPLETED",
        server_patient_id,
        "PATIENT",
        None,
        {"synced_count": len(synced_ids), "client_device_id": batch.client_id}
    )

    return {
        "success": True,
        "synced_count": len(synced_ids),
        "intake_ids": synced_ids,
        "patient_id": server_patient_id,
        "message": f"Successfully synchronized {len(synced_ids)} offline drafts."
    }


@router.post("/dev/clinician-session")
def create_dev_clinician_session(response: Response):
    """
    Controlled development-only synthetic clinician mode.
    Strictly disabled in production environments.
    Initializes a development session with role dev_clinician.
    Never returns session token in JSON response body (cookie-only delivery).
    Generates a unique local-only credential instead of a shared static password.
    """
    if is_production():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development synthetic clinician mode is strictly disabled in production environments."
        )
    if not is_dev_clinician_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development synthetic clinician mode is disabled."
        )

    dev_email = SYNTHETIC_DEV_CLINICIAN_EMAIL
    user = get_user_by_email(dev_email)
    if not user:
        secure_local_credential = secrets.token_urlsafe(32)
        user = create_user(
            name="Dr. Synthetic Clinician (Dev Prototype)",
            email=dev_email,
            password=secure_local_credential,
            role="dev_clinician",
            consent_terms=True
        )
    else:
        # Guarantee role is dev_clinician and cannot masquerade as real clinician
        if user.get("role") != "dev_clinician":
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = 'dev_clinician' WHERE id = ?;", (user["id"],))
            conn.commit()
            conn.close()
            user["role"] = "dev_clinician"

    token = create_session(user["id"])
    response.set_cookie(
        key="transify_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_production(),
        path="/"
    )

    log_care_audit(
        "SYNTHETIC_DEV_CLINICIAN_SESSION_INITIALIZED",
        f"user-{user['id']}",
        "SYNTHETIC_DEV_CLINICIAN",
        None,
        {"mode": "DEVELOPMENT_ONLY_PROTOTYPE"}
    )

    # Deliver credentials solely through HttpOnly session cookie; do not return reusable token in JSON
    return {
        "success": True,
        "clinician_id": f"clinician-{user['id']}",
        "clinician_name": user["name"],
        "role": "dev_clinician",
        "message": "Development synthetic clinician session active. Mode disabled in production."
    }


@router.post("/demo/reset")
def reset_competition_demo_fixtures(request: Request = None):
    """
    Resets synthetic demonstration fixtures for repeatable 180-second video recording.
    Restricted to non-production environments with explicit demo authorization.
    Rejects production access, rejects unconfigured remote environments, and protects against accidental invocation.
    Strictly deletes only documented synthetic demonstration fixtures and never real patient records.
    """
    if is_production():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo reset is strictly disabled in production environments."
        )

    if request is not None:
        client_host = request.client.host if request.client else "127.0.0.1"
        is_local = client_host in ("127.0.0.1", "::1", "localhost", "testclient")
        allow_remote = os.getenv("TRANSIFY_ALLOW_REMOTE_DEMO_RESET", "false").lower() in ("true", "1")
        if not is_local and not allow_remote:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Demo reset is restricted to local non-production environments."
            )

        if not is_demo_mode_enabled():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Demo reset requires explicit demo mode authorization (TRANSIFY_DEMO_MODE_ENABLED)."
            )

        # Validate caller authorization: requires verified clinician session OR explicit demo authorization header
        demo_auth_header = request.headers.get("X-Transify-Demo-Auth") or request.headers.get("x-demo-authorization")
        session_token = request.cookies.get("transify_session")
        auth_hdr = request.headers.get("Authorization") or request.headers.get("authorization")
        if not session_token and auth_hdr and auth_hdr.lower().startswith("bearer "):
            session_token = auth_hdr.split(" ", 1)[1].strip()

        user = get_user_by_session(session_token) if session_token else None

        has_demo_auth = False
        expected_secret = os.getenv("TRANSIFY_DEMO_SECRET", "transify-demo-authorized-2026")
        if demo_auth_header and demo_auth_header in (expected_secret, "local-demo-authorized", "true"):
            has_demo_auth = True
        elif user and is_authorized_clinician(user):
            has_demo_auth = True

        if not has_demo_auth:
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthenticated reset denied: explicit demo authorization or authenticated clinician session is required."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Clinician or demo administrator authorization required for demo reset."
                )

    conn = get_connection()
    cursor = conn.cursor()
    # Delete strictly only the documented synthetic demo fixtures; never real patient records (e.g. user-*)
    cursor.execute("DELETE FROM care_patient_intakes WHERE patient_id IN ('synthetic-demo-patient-001', 'synthetic-demo-patient-002', 'synthetic-demo-patient-003');")
    cursor.execute("DELETE FROM care_clinician_reviews WHERE clinician_id = 'demo-dr-rahim' OR clinician_id LIKE 'synthetic-clinician-%';")
    conn.commit()
    conn.close()

    # Synthetic Fixture 1: RED - Acute Chest Pain (Sign Language Input)
    intake_red = PatientIntakeCreate(
        patient_id="synthetic-demo-patient-001",
        input_modality="sign",
        raw_input="[SYNTHETIC DEMO] Recognized sign sequence: CHEST PAIN, HARD_TO_BREATH, EMERGENCY",
        confirmed_text="[SYNTHETIC DEMO] I have severe crushing chest pain radiating to my left arm for 45 minutes and feeling breathless.",
        chief_complaint="[SYNTHETIC DEMO] Severe crushing chest pain and shortness of breath",
        symptom_description="Crushing substernal pressure, left arm radiation, diaphoresis, sudden onset while resting.",
        onset_duration="45 minutes",
        trajectory="worsening",
        severity=9,
        medical_context="Synthetic profile: Deaf signer (BdSL primary)",
        allergies_medications="None reported",
        consent_granted=True
    )
    triage_red = evaluate_triage(intake_red.chief_complaint, intake_red.symptom_description, intake_red.severity, intake_red.trajectory, intake_red.onset_duration)
    rag_red = search_clinical_evidence(f"{intake_red.chief_complaint} {intake_red.symptom_description}", limit=2)
    create_intake(
        patient_id="synthetic-demo-patient-001",
        input_modality=intake_red.input_modality,
        raw_input=intake_red.raw_input or "",
        confirmed_text=intake_red.confirmed_text,
        chief_complaint=intake_red.chief_complaint,
        symptom_description=intake_red.symptom_description,
        onset_duration=intake_red.onset_duration or "",
        trajectory=intake_red.trajectory or "stable",
        severity=intake_red.severity or 1,
        medical_context=intake_red.medical_context or "",
        allergies_medications=intake_red.allergies_medications or "",
        consent_granted=True,
        status="SUBMITTED",
        urgency_level=triage_red["urgency_level"],
        triage_explanation=triage_red["explanation"],
        triage_rule_id=triage_red.get("rule_id", ""),
        evidence_citations=rag_red.get("citations", [])
    )

    # Synthetic Fixture 2: YELLOW - Febrile Illness / Dengue Warning Signs (Voice Input)
    intake_yellow = PatientIntakeCreate(
        patient_id="synthetic-demo-patient-002",
        input_modality="voice",
        raw_input="[SYNTHETIC DEMO] Speech transcript: 3 days high fever, severe stomach pain and vomiting, cannot drink water",
        confirmed_text="[SYNTHETIC DEMO] High fever for 3 days with severe persistent stomach pain and vomiting. Feeling very weak.",
        chief_complaint="[SYNTHETIC DEMO] High fever and severe persistent stomach pain",
        symptom_description="High grade fever (103 F), body aches, severe abdominal tenderness, nausea, unable to keep liquids down.",
        onset_duration="3 days",
        trajectory="worsening",
        severity=7,
        medical_context="Synthetic profile: Urban resident, dengue prevalent area",
        allergies_medications="None reported",
        consent_granted=True
    )
    triage_yellow = evaluate_triage(intake_yellow.chief_complaint, intake_yellow.symptom_description, intake_yellow.severity, intake_yellow.trajectory, intake_yellow.onset_duration)
    rag_yellow = search_clinical_evidence(f"{intake_yellow.chief_complaint} {intake_yellow.symptom_description}", limit=2)
    create_intake(
        patient_id="synthetic-demo-patient-002",
        input_modality=intake_yellow.input_modality,
        raw_input=intake_yellow.raw_input or "",
        confirmed_text=intake_yellow.confirmed_text,
        chief_complaint=intake_yellow.chief_complaint,
        symptom_description=intake_yellow.symptom_description,
        onset_duration=intake_yellow.onset_duration or "",
        trajectory=intake_yellow.trajectory or "stable",
        severity=intake_yellow.severity or 1,
        medical_context=intake_yellow.medical_context or "",
        allergies_medications=intake_yellow.allergies_medications or "",
        consent_granted=True,
        status="SUBMITTED",
        urgency_level=triage_yellow["urgency_level"],
        triage_explanation=triage_yellow["explanation"],
        triage_rule_id=triage_yellow.get("rule_id", ""),
        evidence_citations=rag_yellow.get("citations", [])
    )

    # Synthetic Fixture 3: GREEN - Routine Mild Cough & Sore Throat (Braille Input)
    intake_green = PatientIntakeCreate(
        patient_id="synthetic-demo-patient-003",
        input_modality="braille",
        raw_input="[SYNTHETIC DEMO] Braille OCR output: mild dry cough and slight scratchy throat for two days, no fever",
        confirmed_text="[SYNTHETIC DEMO] Mild dry cough and slight scratchy throat for two days without fever or difficulty breathing.",
        chief_complaint="[SYNTHETIC DEMO] Mild dry cough and scratchy throat",
        symptom_description="Occasional dry cough, throat irritation, no fever, eating and sleeping normally.",
        onset_duration="2 days",
        trajectory="stable",
        severity=2,
        medical_context="Synthetic profile: Visually impaired student",
        allergies_medications="None",
        consent_granted=True
    )
    triage_green = evaluate_triage(intake_green.chief_complaint, intake_green.symptom_description, intake_green.severity, intake_green.trajectory, intake_green.onset_duration)
    rag_green = search_clinical_evidence(f"{intake_green.chief_complaint} {intake_green.symptom_description}", limit=2)
    create_intake(
        patient_id="synthetic-demo-patient-003",
        input_modality=intake_green.input_modality,
        raw_input=intake_green.raw_input or "",
        confirmed_text=intake_green.confirmed_text,
        chief_complaint=intake_green.chief_complaint,
        symptom_description=intake_green.symptom_description,
        onset_duration=intake_green.onset_duration or "",
        trajectory=intake_green.trajectory or "stable",
        severity=intake_green.severity or 1,
        medical_context=intake_green.medical_context or "",
        allergies_medications=intake_green.allergies_medications or "",
        consent_granted=True,
        status="SUBMITTED",
        urgency_level=triage_green["urgency_level"],
        triage_explanation=triage_green["explanation"],
        triage_rule_id=triage_green.get("rule_id", ""),
        evidence_citations=rag_green.get("citations", [])
    )

    return {
        "success": True,
        "message": "Demo fixtures initialized: RED (Sign), YELLOW (Voice), GREEN (Braille). All cases explicitly flagged as synthetic."
    }


# ===========================================================================
# CareAnywhere Multimodal, Vision, Dialect, Outbreak & Geospatial Endpoints
# ===========================================================================

@router.post("/vision/analyze")
def analyze_vision_endpoint(req: VisionAnalyzeRequest):
    """
    CareAnywhere Computer Vision Pipeline:
    Analyzes smartphone photos of skin lesions (erythema, ABCDE melanoma screening, burns, ulcers)
    or ophthalmic eye conditions (conjunctival red eye, cataract opacity, corneal ulcers, scleral icterus).
    Returns quantitative features, urgency classification, confidence scores, and safety guidance.
    """
    try:
        analysis = analyze_multimodal_vision(req.image_data, req.condition_type or "auto")
        return {
            "success": True,
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Computer vision analysis failed: {str(e)}"
        )


@router.post("/audio/intake")
def audio_intake_endpoint(req: AudioIntakeRequest):
    """
    CareAnywhere Localized Speech-to-Text & Regional Dialect Interface:
    Processes verbal symptom descriptions in regional dialects (Sylheti, Chittagonian, Bengali idioms)
    and maps them to standardized chief complaints, severity ratings, and U.S. NLM MeSH terminology.
    """
    try:
        res = process_regional_speech_intake(req.transcript, req.dialect_hint or "auto")
        return {
            "success": True,
            "data": res
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Speech intake processing failed: {str(e)}"
        )


@router.get("/outbreak/alerts")
def get_outbreak_alerts_endpoint(
    lat: Optional[float] = Query(default=None),
    lon: Optional[float] = Query(default=None),
    district: Optional[str] = Query(default=None),
    symptoms: Optional[str] = Query(default="")
):
    """
    CareAnywhere Predictive Outbreak & Epidemic Risk Alerts:
    Correlates GPS coordinates / administrative district against WHO Global Health Observatory
    and DGHS epidemiological outbreak surveillance (Dengue, Cholera, Nipah, Heatstroke).
    """
    res = assess_local_outbreak_risk(lat=lat, lon=lon, district=district, symptoms_text=symptoms or "")
    return {
        "success": True,
        "data": res
    }


@router.get("/facilities/nearby")
def get_nearby_facilities_endpoint(
    lat: float = Query(default=23.7258, description="Latitude (default: Dhaka Medical)"),
    lon: float = Query(default=90.3976, description="Longitude (default: Dhaka Medical)"),
    facility_type: Optional[str] = Query(default="all"),
    limit: Optional[int] = Query(default=4, ge=1, le=10)
):
    """
    CareAnywhere OpenStreetMap Health Facility Locator:
    Finds nearest emergency hospitals, burn centers, eye clinics, and 24/7 pharmacies.
    Computes Haversine distance, estimated transit time, direct telephone hotlines, and OSM routing links.
    """
    res = find_nearby_health_facilities(lat=lat, lon=lon, facility_type=facility_type or "all", limit=limit or 4)
    return res


@router.post("/store-and-forward/sync")
def store_and_forward_sync_endpoint(
    req: StoreAndForwardSyncRequest,
    user: Dict[str, Any] = Depends(get_authenticated_user)
):
    """
    CareAnywhere 'Store-and-Forward' Protocol Sync Handler:
    Synchronizes offline edge-inferred intakes captured during low-bandwidth or disconnected states.
    Uses SHA-256 idempotency hashing to guarantee duplicate-free background reconciliation.
    """
    server_patient_id = f"user-{user['id']}"
    synced_intakes = []

    for draft in req.batch:
        if not draft.consent_granted:
            continue

        draft.patient_id = server_patient_id

        # Compute or verify idempotency key
        idem_key = draft.idempotency_key or compute_intake_idempotency_hash(
            server_patient_id,
            draft.chief_complaint,
            draft.offline_created_at or datetime.now(timezone.utc).isoformat()
        )
        draft.idempotency_key = idem_key

        # Deduplication check by idempotency_key or confirmed_text
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id FROM care_patient_intakes
        WHERE patient_id = ? AND (idempotency_key = ? OR confirmed_text = ?);
        """, (server_patient_id, idem_key, draft.confirmed_text))
        existing = cursor.fetchone()
        conn.close()

        if existing:
            synced_intakes.append({
                "intake_id": existing["id"],
                "status": "ALREADY_SYNCHRONIZED",
                "idempotency_key": idem_key
            })
            continue

        # Ingest intake through standard submit pipeline
        resp = submit_patient_intake(draft, user=user)
        synced_intakes.append({
            "intake_id": resp["intake_id"],
            "urgency_level": resp["urgency_level"],
            "status": "SYNCHRONIZED",
            "idempotency_key": idem_key
        })

    log_care_audit(
        "STORE_AND_FORWARD_SYNC_COMPLETED",
        server_patient_id,
        "PATIENT",
        None,
        {"client_id": req.client_id, "synced_count": len(synced_intakes)}
    )

    return {
        "success": True,
        "client_id": req.client_id,
        "total_synced": len(synced_intakes),
        "results": synced_intakes,
        "protocol": "CareAnywhere Store-and-Forward v2.0"
    }
