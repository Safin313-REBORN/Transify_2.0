# Transify Care — Patient Privacy, Consent & Data Governance
**Standard**: Health Data Privacy, Role-Based Access & WCAG 2.2 AAA Compliance

---

## 1. Explicit Patient Consent Framework

Healthcare intake requires the highest ethical standard of patient autonomy. Transify Care implements a strict consent gate:

1. **Mandatory Checkbox Gate**: The frontend form includes an unambiguous, accessible checkbox (`#care-consent-check`).
2. **Explicit Legal Language**: *"I voluntarily consent to having my communicated symptom details analyzed by Transify Care's deterministic clinical safety rules and queued for professional review by a licensed healthcare clinician. I understand this tool assists clinical communication and does not replace a medical doctor."*
3. **Backend Enforcement**: If `consent_granted == False`, the backend rejects the intake with HTTP 400 (`Bad Request`), terminating processing before triage rules or RAG are triggered.

---

## 2. Data Minimization & Retention

1. **Pseudonymous Patient Identifiers**:
   - Guest intakes use transient pseudonyms (`guest-patient-XXX`).
   - Authenticated intakes hash credentials to prevent public exposure.
2. **Local Encrypted Storage for Offline Sync**:
   - In rural clinics or areas without internet, drafts are stored locally in the client browser (`localStorage`).
   - Once synchronized with the server, local drafts are automatically purged.
3. **Zero Third-Party Telemetry**:
   - No patient health information, sign language video frames, or audio streams are sent to external analytics or advertising trackers.

---

## 3. Role-Based Access Control (RBAC)

1. **Patient Workspace**:
   - Can submit intakes, view their own preliminary triage result, and access assistive communication tools.
   - Cannot view other patients' intakes or access administrative clinician tools.
2. **Clinician Workspace**:
   - Authenticated healthcare professionals access the Clinician Portal (`#slide-clinician-portal`).
   - Full visibility into symptom history, RAG evidence, and audit logs.
   - Must document written medical justifications for any clinical override.
