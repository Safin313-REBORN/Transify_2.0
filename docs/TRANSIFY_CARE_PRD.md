# Product Requirements Document (PRD): Transify Care
**Product Name**: Transify Care  
**Tagline**: *Breaking Communication Barriers. Making Healthcare Accessible.*  
**Target Competition**: AI Builders Congress — HealthSphere AI (CareAnywhere Challenge)  
**Submission Category**: Idea to Unicorn (Preliminary Submission)  
**Version**: 2.5.0-care  
**Status**: Production Implemented & Verified

---

## 1. Executive Summary

Transify Care expands the established Transify 2.0 multi-modal assistive communication engine into an evidence-grounded healthcare intake and deterministic clinical triage platform. Designed specifically for low-resource and high-disparity health systems such as Bangladesh, Transify Care bridges the dangerous communication chasm faced by over 59.1% of patients with disabilities when seeking primary healthcare.

By translating acute symptoms communicated via Bangladesh Sign Language (BdSL), American Sign Language (ASL), Unified English Braille (UEB), or spoken Bengali/English into structured clinical summaries, Transify Care enables safe preliminary triage, emergency escalation, and auditable clinician verification.

---

## 2. Core User Personas

### Persona A: Sarah (The Deaf / Hard-of-Hearing Patient)
- **Background**: 24-year-old university student in Dhaka. Deaf since birth; communicates primarily through Bangladesh Sign Language (BdSL).
- **Pain Point**: Arriving at an Upazila health complex with acute crushing chest pressure and dizziness, there are no certified sign language interpreters. Doctors misinterpret her panic and gesture.
- **Transify Care Solution**: Opens Transify Care on her mobile device. Signs her symptoms toward the camera. The system parses her signs into structured clinical language, evaluates red-flag acute coronary symptoms, triggers Urgency RED, and surfaces Bangladesh National Emergency 999.

### Persona B: Rafiq (The Visually Impaired Patient)
- **Background**: 52-year-old rural artisan with bilateral visual impairment. Reads embossed Braille and uses screen magnification.
- **Pain Point**: Struggles with paper hospital registration forms and inaccessible health portals. Experiences sudden fever, severe vomiting, and body aches during monsoon season.
- **Transify Care Solution**: Communicates through the Voice Hub or scans an embossed Braille symptom record. The system clarifies trajectory, matches against DGHS Dengue Management Guidelines, and categorizes as Urgency YELLOW.

### Persona C: Dr. Ahmed (The Primary Care Medical Officer)
- **Background**: Government physician at a busy community health complex managing 80+ patients daily.
- **Pain Point**: Lacks sign language skills and has no extra time for trial-and-error gesturing with speech-disabled patients. Fears missing critical red-flag symptoms.
- **Transify Care Solution**: Uses the Clinician Review Portal. Reviews incoming cases with pre-extracted chief complaints, symptom trajectories, AI triage urgency, and cited WHO/DGHS guidelines. Can confirm or override triage urgency with an audit-logged clinical rationale.

---

## 3. Product Modules & Functional Requirements

### 3.1 Multi-Modal Healthcare Intake Wizard (`#slide-care-intake`)
- **FR-INTAKE-001**: Support four distinct input modalities: (1) Sign Language via camera, (2) Optical Braille Document OCR, (3) Live Speech-to-Text Captions, and (4) Direct Accessible Text.
- **FR-INTAKE-002**: Collect structured clinical dimensions: Chief Complaint, Detailed Symptoms, Onset/Duration, Trajectory (*Improving*, *Stable*, *Worsening*), Severity (*1-10 Slider*), Medical Context, and Allergies/Medications.
- **FR-INTAKE-003**: Enforce explicit, voluntary patient consent (`#care-consent-check`) before submitting health data to the triage pipeline.
- **FR-INTAKE-004**: Display preliminary urgency level (*RED*, *YELLOW*, *GREEN*, or *INSUFFICIENT_INFORMATION*), deterministic rule ID, and cited guideline excerpts.

### 3.2 Deterministic Clinical Triage Safety Engine (`src/care/triage.py`)
- **FR-TRIAGE-001**: Strictly prioritize safety: RED > YELLOW > GREEN > INSUFFICIENT_INFORMATION.
- **FR-TRIAGE-002**: Never claim autonomous diagnosis. The system performs preliminary *urgency routing*, not medical diagnosis.
- **FR-TRIAGE-003**: Emergency Escalation: Any case matching RED-flag criteria (e.g. `RULE-EMERG-001` Acute Coronary Syndrome, `RULE-EMERG-002` Stroke) must immediately display direct escalation actions and one-touch calling to **National Emergency 999** and **Health Helpline 16263**.

### 3.3 Clinical Knowledge Retrieval (Clinical RAG) (`src/care/clinical_rag.py`)
- **FR-RAG-001**: Retrieve clinical evidence from verified, peer-reviewed public health guidelines (WHO Integrated Primary Care, DGHS National Dengue Protocol, NINS Stroke Protocol).
- **FR-RAG-002**: Strict attribution: Every citation must include Source Title, Publisher, Version, Text Excerpt, and Official Publication URL.
- **FR-RAG-003**: No-Evidence Fallback: If no matching guideline is found, explicitly return `evidence_found: False` and disclaim the absence of evidence rather than hallucinating medical advice.

### 3.4 Clinician Review & Governance Portal (`#slide-clinician-portal`)
- **FR-CLIN-001**: Display filterable incoming queue of submitted patient intakes.
- **FR-CLIN-002**: Allow clinician to inspect full case provenance (original modality, sensor transcript, confirmed text, AI urgency, cited guidelines).
- **FR-CLIN-003**: Support clinician actions: `ACCEPTED`, `CLARIFICATION_REQUESTED`, `MODIFIED`, `OVERRIDDEN`, `COMPLETED`.
- **FR-CLIN-004**: Enforce mandatory clinical justification whenever a clinician overrides the AI urgency level. Overrides without written justification are strictly rejected (HTTP 400).

### 3.5 Offline-First Resilience (CareAnywhere Standard)
- **FR-OFFLINE-001**: Automatically detect network state (`navigator.onLine`).
- **FR-OFFLINE-002**: Cache symptom drafts securely in `localStorage` when offline.
- **FR-OFFLINE-003**: Automatically synchronize cached drafts via `POST /api/care/offline/sync` as soon as network connectivity is restored.

### 3.6 Strict Zero Auto-Audio Policy
- **FR-AUDIO-001**: Under no circumstances shall audio or speech playback initiate automatically without an explicit user tap. Results are presented visually and textually first. An explicit *"🔊 Listen to Assessment (TTS)"* button allows on-demand auditory access.
