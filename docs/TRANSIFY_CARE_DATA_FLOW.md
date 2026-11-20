# Transify Care — End-to-End Data Flow Specification
**System Version**: 2.5.0-care

---

## 1. Sequence Diagram: Patient Intake to Clinician Sign-Off

```mermaid
sequenceDiagram
    autonumber
    actor Patient as Patient (Deaf / Blind / Speech-Impaired)
    participant Wizard as Intake Wizard (Slide 05)
    participant LocalCache as Local Cache (Offline Storage)
    participant API as FastAPI Care Router (/api/care)
    participant Triage as Deterministic Safety Engine
    participant RAG as Clinical RAG (WHO / DGHS)
    participant DB as SQLite Relational Store
    actor Clinician as Reviewing Physician (Slide 06)

    Patient->>Wizard: Selects Modality (Sign / Braille / Voice / Text)
    Patient->>Wizard: Communicates symptoms (signs, uploads, speaks)
    Wizard->>Patient: Clarifies Onset, Trajectory, Severity (1-10)
    Patient->>Wizard: Confirms summary & checks explicit consent

    alt Client is Offline
        Wizard->>LocalCache: Encrypt & Store Draft (localStorage)
        Wizard-->>Patient: Displays Offline Cached Notice + local safety info
        Note over LocalCache,API: When connection restores...
        LocalCache->>API: POST /api/care/offline/sync (batch of drafts)
    else Client is Online
        Wizard->>API: POST /api/care/intake (PatientIntakeCreate)
    end

    API->>Triage: evaluate_triage(complaint, desc, severity, trajectory)
    Triage-->>API: Returns Urgency (RED/YELLOW/GREEN), Rule ID, Escalation
    
    API->>RAG: search_clinical_evidence(symptoms)
    RAG-->>API: Returns verbatim citations (WHO/DGHS) or safe fallback

    API->>DB: create_intake(...) + log_care_audit(...)
    API-->>Wizard: HTTP 201 Created (Urgency, Rule, Citations, Escalation)
    Wizard-->>Patient: Visual Triage Result (Zero Auto-Audio: Text first)
    
    opt Patient Requests Audio
        Patient->>Wizard: Taps "🔊 Listen to Assessment"
        Wizard-->>Patient: Audio Vocalization (TTS Service)
    end

    Note over DB,Clinician: Clinician Queue Inspection
    Clinician->>API: GET /api/care/intakes?status=SUBMITTED
    API->>DB: Fetch pending intake records
    API-->>Clinician: Return queued intakes list
    
    Clinician->>API: GET /api/care/intake/{id}
    API-->>Clinician: Return full case details & citations
    
    Clinician->>API: POST /api/care/intake/{id}/review (Decision + Justification)
    alt Urgency Overridden without Reason
        API-->>Clinician: HTTP 400 Bad Request (Mandatory Justification Required)
    else Valid Review
        API->>DB: add_clinician_review(...) + log_care_audit(...)
        API-->>Clinician: HTTP 200 OK (Review Committed, Status = REVIEWED)
    end
```

---

## 2. Data Flow Validation Checks

1. **Consent Gate**: If `consent_granted == False`, the intake is rejected immediately with HTTP 400 before triage or RAG is called.
2. **Deterministic Triage Gate**: All inputs undergo rule-based pattern evaluation prior to persistence.
3. **Emergency Escalation Gate**: If RED urgency is triggered, the response payload must contain direct hotlines (`999`, `16263`).
4. **Override Governance Gate**: If `urgency_override != 'NONE'`, `override_reason` must be non-empty and minimum 5 characters, or the request fails.
5. **Audit Gate**: Every state mutation (`INTAKE_CREATED`, `CLINICIAN_REVIEW_RECORDED`, `OFFLINE_SYNC_COMPLETED`) writes a transaction-safe record to `care_audit_logs`.
