# Transify Care — Patient Privacy, Consent & Data Governance
**Standard**: Health Data Privacy, Role-Based Access Control (RBAC) & Tamper-Evident Auditing
**Status**: Release Candidate Security & Privacy Remediation

---

## 1. Explicit Patient Consent Framework

Healthcare intake requires the highest ethical standard of patient autonomy. Transify Care enforces a strict consent gate:

1. **Mandatory Checkbox Gate**: The frontend form includes an unambiguous, accessible checkbox (`#care-consent-check`).
2. **Explicit Consent Notice**: *"I voluntarily consent to having my communicated symptom details analyzed by Transify Care's deterministic clinical safety rules and queued for professional review in the clinician workflow prototype. I understand this tool assists clinical communication and does not replace emergency medical personnel or a medical doctor."*
3. **Server-Side Enforcement**: `consent_granted: bool = Field(...)` is a required non-default field in `PatientIntakeCreate`. If missing or `False`, the backend strictly returns HTTP 400 (`Bad Request`), terminating processing immediately before any database storage, triage evaluation, or queue insertion.

---

## 2. Patient Identity & Isolation

1. **Server-Derived Patient Identity**:
   - The patient identifier is derived strictly on the server from the authenticated session (`user-{id}`).
   - Client-supplied patient IDs, clinician IDs, or clinician names in request payloads are ignored.
   - User sessions are verified via cryptographically random session tokens (32-byte hex) with expiry.
2. **Access Isolation**:
   - Patients can only retrieve their own intakes (`GET /api/care/intakes`, `GET /api/care/intake/{id}`).
   - Unauthorized cross-user access attempts are rejected with HTTP 403 (`Forbidden`).
3. **Data Minimization & Aggregation**:
   - Dashboard statistics (`/api/care/dashboard/stats`) expose only aggregate counters without leaking identifiable patient records or clinical summaries.

---

## 3. Local Storage & Offline Draft Prototype Policy

1. **No Encryption Claims for Plaintext LocalStorage**:
   - Browser `localStorage` draft serialization is strictly documented as an **unassessed offline draft capture prototype**.
   - The platform **does NOT** describe plaintext `localStorage` as encrypted.
   - No clinical triage results or urgency classifications are rendered while offline: the UI explicitly displays *"Draft saved locally — no clinical assessment performed while offline."*
   - Offline drafts can only be synchronized to the backend with an authenticated user session.

---

## 4. Role-Based Access Control (RBAC) & Clinician Governance

1. **Patient Workspace**:
   - Can submit intakes, view own preliminary triage results, and use assistive communication tools.
   - Strictly forbidden from accessing clinician queues, review endpoints, or other patients' records.
2. **Clinician Workspace**:
   - Requires verified clinician credentials (`role == 'clinician'` or `role == 'admin'`).
   - In development environments without live hospital SSO, a controlled development clinician mode (`ENABLE_DEV_CLINICIAN_AUTH=1`) is available for testing, disabled by default in production.
   - Clinician review submissions require valid authenticated sessions; urgency overrides require a mandatory medical justification.

---

## 5. Tamper-Evident Audit Logging

1. **Append-Only SQLite Triggers**:
   - `prevent_care_audit_logs_update` and `prevent_care_audit_logs_delete` database triggers reject any `UPDATE` or `DELETE` queries on `care_audit_logs`.
2. **Cryptographic Chaining**:
   - Each audit log entry computes a SHA-256 hash chaining `prev_hash`, `event_type`, `intake_id`, `actor_id`, and `timestamp`, providing tamper evidence across events.
