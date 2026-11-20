# Transify Care — Technical System Architecture
**System Version**: 2.5.0-care  
**Component Ecosystem**: FastAPI Backend + Pure Vanilla Frontend + SQLite + Deterministic Safety Rules + Clinical RAG

---

## 1. High-Level Architecture Diagram

```mermaid
graph TD
    subgraph Client Layer [Frontend Client - Vanilla HTML5 / CSS3 / ES2020]
        UI[Home Bento Hub]
        WIZ[Healthcare Intake Wizard Slide 05]
        CLIN[Clinician Review Portal Slide 06]
        OFFLINE[localStorage Offline Draft Cache]
        NAV[Responsive Floating Navigation Bar]
    end

    subgraph Modality Ingestion [Transify 2.0 Assistive Foundation]
        SIGN[MediaPipe 162-D Landmarks + Scikit-Learn Model]
        BRAILLE[OpenCV Adaptive Thresholding + ExtraTrees OCR]
        STT[Web Speech API Live Captioning]
        TTS[FastAPI eSpeak-NG / Web Speech Natural Synthesis]
    end

    subgraph API Gateway [FastAPI Server - src/api/server.py]
        R_BASE[Core Endpoints: /api/sign, /api/braille, /api/tts]
        R_CARE[Care Endpoints: /api/care/intake, /api/care/review, /api/care/offline/sync]
    end

    subgraph Intelligence & Safety Layer [src/care/]
        TRIAGE[Deterministic Triage Rules Engine: triage.py]
        RAG[Clinical RAG Knowledge Base: clinical_rag.py]
        ESCAL[Emergency Escalation: BD 999 & 16263]
    end

    subgraph Persistence Layer [SQLite Database - data/transify.db]
        DB_INTAKE[(care_patient_intakes)]
        DB_SOURCES[(care_clinical_sources & chunks)]
        DB_REVIEW[(care_clinician_reviews)]
        DB_AUDIT[(care_audit_logs)]
    end

    WIZ -->|Sensor Trigger| SIGN
    WIZ -->|Document Upload| BRAILLE
    WIZ -->|Voice Capture| STT
    WIZ -->|POST /api/care/intake| R_CARE
    OFFLINE <-->|Auto-Sync| R_CARE
    CLIN -->|GET /intakes, POST /review| R_CARE

    R_CARE --> TRIAGE
    R_CARE --> RAG
    TRIAGE -->|Red Flag Trigger| ESCAL
    R_CARE --> DB_INTAKE
    RAG --> DB_SOURCES
    R_CARE --> DB_REVIEW
    R_CARE --> DB_AUDIT
```

---

## 2. Component Specifications

### 2.1 Backend Modules (`src/care/`)

| File | Purpose | Key Classes & Functions |
|---|---|---|
| `db_care.py` | Schema initialization, relational persistence, and audit logging. | `init_care_db()`, `create_intake()`, `get_intake()`, `list_intakes()`, `add_clinician_review()`, `log_care_audit()` |
| `triage.py` | Versioned, deterministic clinical decision rules and emergency escalation. | `evaluate_triage()`, `DETERMINISTIC_RULES`, `EMERGENCY_CONTACTS` |
| `clinical_rag.py` | Evidence indexing, keyword/semantic chunk matching, and citation assembly. | `seed_clinical_sources_if_empty()`, `search_clinical_evidence()` |
| `../api/care_routes.py` | FastAPI route handlers and Pydantic validation schemas. | `submit_patient_intake()`, `get_single_intake()`, `review_patient_intake()`, `sync_offline_drafts()`, `reset_competition_demo_fixtures()` |

### 2.2 Relational Data Model (`data/transify.db`)

1. **`care_patient_intakes`**:
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `patient_id`: TEXT NOT NULL
   - `input_modality`: TEXT NOT NULL (`sign`, `braille`, `voice`, `text`)
   - `raw_input`: TEXT
   - `confirmed_text`: TEXT NOT NULL
   - `chief_complaint`: TEXT NOT NULL
   - `symptom_description`: TEXT NOT NULL
   - `onset_duration`: TEXT
   - `trajectory`: TEXT (`improving`, `stable`, `worsening`)
   - `severity`: INTEGER (1 to 10)
   - `medical_context`: TEXT
   - `allergies_medications`: TEXT
   - `consent_granted`: INTEGER NOT NULL (0 or 1)
   - `status`: TEXT (`SUBMITTED`, `REVIEWED`, `ESCALATED`)
   - `urgency_level`: TEXT (`RED`, `YELLOW`, `GREEN`, `INSUFFICIENT_INFORMATION`)
   - `triage_explanation`: TEXT
   - `triage_rule_id`: TEXT
   - `evidence_citations`: JSON TEXT
   - `created_at`: TEXT ISO8601

2. **`care_clinical_sources` & `care_clinical_chunks`**:
   - Stores approved protocols from WHO, DGHS, and NINS.
   - Chunks indexed by condition, tags, severity flags, and verbatim protocol excerpts.

3. **`care_clinician_reviews`**:
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `intake_id`: INTEGER NOT NULL (Foreign Key)
   - `clinician_id`: TEXT NOT NULL
   - `clinician_name`: TEXT NOT NULL
   - `action`: TEXT (`ACCEPTED`, `MODIFIED`, `OVERRIDDEN`, `COMPLETED`)
   - `urgency_override`: TEXT (`NONE`, `RED`, `YELLOW`, `GREEN`)
   - `override_reason`: TEXT (Mandatory when urgency overridden)
   - `clinical_notes`: TEXT
   - `reviewed_at`: TEXT ISO8601

4. **`care_audit_logs`**:
   - Immutable audit trail recording event types, actors, roles, target IDs, and structured payloads.
