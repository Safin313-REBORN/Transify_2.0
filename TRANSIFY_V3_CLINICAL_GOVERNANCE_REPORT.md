# TRANSIFY V3 — CLINICAL GOVERNANCE, ETHICS & SAFETY AUDIT REPORT

**Date:** November 22, 2026  
**Repository:** `Safin313-REBORN/Transify_2.0`  
**Branch:** `main`  
**Author:** Healthcare Governance Architect & Clinical Safety Auditor  
**Scope:** Transify Care (Assistive Healthcare & Chronic Disease Telemetry)  
**Status:** **GATE 2 CLOSED — GOVERNANCE FRAMEWORK FORMALIZED & VERIFIED**  

---

## 1. Ethical Boundary & Non-Diagnostic Clinical Charter

Transify Care is an **Assistive Communication and Clinical Decision Support Prototype (CDSS)**. It is **not** an autonomous diagnostic system, electronic medical prescription platform, or automated medical dispatch service.

### Fundamental Governance Principles:
1. **Zero Autonomous Clinical Decisions:** No algorithm, rule, or model in Transify autonomously executes medical diagnosis, alters patient medication regimens, or dispatches emergency services without human oversight.
2. **Physician-in-the-Loop:** All automated triage calculations, symptom summaries, and telemetry alerts are staged in the Clinician Portal (`/care/clinician`) for mandatory review by licensed medical professionals.
3. **Fail-Safe Determinism:** Machine learning models (e.g. LLM text generators) are strictly prohibited from evaluating, lowering, or overriding patient acuity levels. Acuity calculation is handled exclusively by deterministic rule engines.

---

## 2. Audit of the 11 Deterministic Triage Rules

The clinical triage engine (`src/care/triage.py`) enforces 11 deterministic rules based on verified clinical protocols from the **Directorate General of Health Services (DGHS) Bangladesh** and the **World Health Organization (WHO)**:

```
+----+--------------------------------------------+-----------------------+---------------+-------------------------+
| ID | Clinical Presentation                      | Evaluated Acuity Level| Action Type   | Escalation Protocol     |
+----+--------------------------------------------+-----------------------+---------------+-------------------------+
| 1  | Acute Coronary Syndrome (Chest Pain)       | RED (CRITICAL)        | Immediate     | Emergency Hotline (999) |
| 2  | Acute Stroke (FAST: Droop/Weakness/Slur)   | RED (CRITICAL)        | Immediate     | Emergency Hotline (999) |
| 3  | Severe Dyspnea (Respiratory Distress)      | RED (CRITICAL)        | Immediate     | Emergency Hotline (999) |
| 4  | Massive Hemorrhage / Hematemesis           | RED (CRITICAL)        | Immediate     | Emergency Hotline (999) |
| 5  | Sepsis Signs (Fever + Tachycardia + Shock) | RED (CRITICAL)        | Immediate     | Emergency Hotline (999) |
| 6  | Dengue / Tropical Infection Warning Signs  | YELLOW (URGENT)       | Same-Day      | DGHS Helpline (16263)   |
| 7  | Acute Abdomen (Severe Localized Pain)      | YELLOW (URGENT)       | Same-Day      | DGHS Helpline (16263)   |
| 8  | Intractable Dehydration (Vomiting > 18h)   | YELLOW (URGENT)       | Same-Day      | DGHS Helpline (16263)   |
| 9  | Contradictory Input (Mild text + Pain >=8) | YELLOW / REVIEW       | Same-Day      | Clinician Queue Audit   |
| 10 | Insufficient / Blank Information           | INSUFFICIENT_INFO     | Fail-Safe     | Requires Re-Intake      |
| 11 | Unmatched / Exotic Symptom Presentations   | REVIEW_REQUIRED       | Escalation    | Clinician Review Queue  |
+----+--------------------------------------------+-----------------------+---------------+-------------------------+
```

### Emergency Hotline Integration:
Every `RED` and `YELLOW` evaluation card renders direct click-to-dial links for verified national emergency services:
- **National Emergency Dispatcher:** `tel:999` (Police, Ambulance, Fire)
- **DGHS National Health Call Center:** `tel:16263` (24/7 Physician Consultation)

---

## 3. Chronic Disease & Insulin Safety Governance

In chronic metabolic care (`src/care/chronic_care.py`), algorithmic recommendations are bound by strict physiological failsafes:

1. **Severe Hypoglycemia Lockout:**
   - Any blood glucose entry $< 70\,\text{mg/dL}$ ($< 3.9\,\text{mmol/L}$) automatically locks out all insulin recommendations.
   - Recommended units are locked to **`0.0 units`**.
   - Outputs the emergency **"Rule of 15"** (consume 15g fast-acting carbohydrate, recheck blood glucose in 15 minutes).
2. **Aspiration & Swallowing Risk Assessment:**
   - Hypoglycemia warnings mandate an immediate caregiver assessment of patient responsiveness.
   - Outputs explicit clinical warning: *"DO NOT ADMINISTER ANYTHING BY MOUTH IF THE PATIENT IS CONFUSED OR UNCONSCIOUS. Prepare glucagon or seek emergency medical care immediately."*
3. **Physiological Bound Checks:**
   - Rejects implausible glucose inputs ($< 20\,\text{mg/dL}$ or $> 900\,\text{mg/dL}$), ICR ($< 1$ or $> 100$), ISF ($< 5$ or $> 400$), and IOB ($< 0$ or $> 40\,\text{U}$).
   - Detects unit confusion (e.g. entering a reading of $6.0$ while `mg/dL` is selected).
4. **Correction Bolus Flooring:**
   - Blood glucose below target target levels never calculates a negative correction factor that subtracts from meal boluses.

---

## 4. Patient Consent, Privacy & Data Isolation

1. **Mandatory Informed Consent:**
   - Intake endpoints (`/api/care/intake`) enforce explicit patient consent (`consent_granted: true`). Unauthenticated or unconsented requests return HTTP 401/400.
2. **Cross-Patient Data Isolation (Anti-IDOR):**
   - Database operations enforce patient ID tenancy scoping in `src/care/db_care.py`. Patients cannot access intake records, telemetry history, or medical questionnaires belonging to other users.
3. **Session Token Hardening:**
   - Session identifiers are stored exclusively in `HttpOnly`, `SameSite=Lax`, `Secure` browser cookies.
   - Persistent storage of raw Bearer tokens in browser `localStorage` is prohibited, eliminating token leakage via XSS.
4. **Immutable Audit Logging:**
   - SQLite database triggers enforce append-only audit logging for all patient record access and clinician notes.

---

## 5. Clinical Supervision, Roles & Responsibilities

```
+------------------------------------+-------------------------------------------------------------------------+
| Role                               | Authorized Responsibilities & Operational Boundaries                    |
+------------------------------------+-------------------------------------------------------------------------+
| Patient / Assistive User           | Enters symptoms, captures Braille/Sign inputs, views educational advice.|
| Registered Clinician               | Reviews triage queue, signs off on intakes, confirms insulin parameters.|
| System Administrator               | Manages user roles, inspects audit logs, maintains system uptime.       |
| CDSS Automated Engine (Transify)   | Calculates deterministic triage tier, retrieves evidence, formats data. |
+------------------------------------+-------------------------------------------------------------------------+
```

### Clinician Supervisory Duties:
1. **Verification of Chief Complaint:** Verify that patient-reported symptoms match physical observations before prescribing medication or ordering diagnostics.
2. **Validation of Physiological Parameters:** Insulin calculations require clinician parameter confirmation (`clinician_confirmed_parameters: true`) before being treated as clinical reference guidance.
3. **Queue Prioritization:** Clinicians must attend to `RED (CRITICAL)` queue items within 5 minutes and `YELLOW (URGENT)` items within 2 hours.

---

## 6. Clinical Pilot Governance Protocol

Before deploying Transify Care in a clinical setting (e.g. community health clinics or outpatient triage desks), the following operational protocol must be enforced:

### 6.1 Pilot Inclusion Criteria
- Age $\ge 18$ years.
- Capable of providing voluntary written informed consent.
- Non-critical presentation seeking outpatient triage assessment or chronic diabetes self-management education.
- Literacy in English or Bengali (or accompanied by an assistive caregiver).

### 6.2 Pilot Exclusion Criteria
- Acute pediatric emergencies ($< 18$ years old without guardian and pediatrician present).
- Severe hemodynamic instability (systolic BP $< 80\,\text{mmHg}$, heart rate $> 140\,\text{bpm}$).
- Acute altered mental state, psychosis, or severe traumatic head injury.
- Patients presenting with active suicidal ideation or psychiatric crisis (referred immediately to national crisis services).

### 6.3 Pilot Stopping Criteria
The clinical pilot must be immediately suspended upon the occurrence of:
- Any clinical adverse event resulting from incorrect algorithmic triage categorization.
- Failure of emergency hotline escalation hooks during an active acute presentation.
- Detection of a data breach, unauthorized privilege escalation, or HIPAA/local privacy violation.

---

## 7. Required Institutional Ethics & Regulatory Approvals

Prior to pilot launch in clinical facilities, the following institutional clearances must be secured:
1. **Institutional Review Board (IRB) / Ethics Committee:** Approval from the host hospital or research institute ethics committee.
2. **Bangladesh Medical Research Council (BMRC):** Ethical clearance for digital health research and assistive AI telemetry.
3. **DGHS MIS Approval:** Approval for integration with the Directorate General of Health Services (DGHS) digital health registry.
