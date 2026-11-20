# Transify Care — Patient Privacy, Consent & Data Governance
**Standard**: Health Data Privacy, Role-Based Access Control (RBAC) & Tamper-Evident Auditing
**Status**: Release Candidate Security & Privacy Remediation (Final Security Hardening)

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
2. **No Public Clinician Self-Registration**:
   - Public account registration (`POST /api/auth/register`) strictly assigns the server-defined role `'user'`.
   - Client-supplied `role` fields (e.g. attempting to register as `'clinician'`, `'admin'`, or `'dev_clinician'`) are explicitly discarded. Privileged roles require server-side administrative promotion.
3. **Access Isolation & Clinician Dashboard Protection**:
   - Patients can only retrieve their own intakes (`GET /api/care/intakes`, `GET /api/care/intake/{id}`).
   - Unauthorized cross-user access attempts are rejected with HTTP 403 (`Forbidden`).
   - Dashboard operational statistics (`GET /api/care/dashboard/stats`) are restricted to verified clinician accounts (`require_clinician`). Patients receive HTTP 403 Forbidden.
4. **Data Minimization & Aggregation**:
   - Dashboard statistics expose only aggregate counters without leaking identifiable patient records, complaints, or clinical summaries.
   - Evidence search (`GET` and `POST /api/care/evidence/search`) requires authenticated access. The POST route accepts queries in the JSON body to prevent personal health terms from being recorded in HTTP server access logs.

---

## 3. Local Storage & Offline Draft Prototype Policy

1. **No Encryption Claims for Plaintext LocalStorage**:
   - Browser `localStorage` draft serialization is strictly documented as an **unassessed offline draft capture prototype**.
   - The platform **does NOT** describe plaintext `localStorage` as encrypted.
   - No clinical triage results or urgency classifications are rendered while offline: the UI explicitly displays *"Draft saved locally — no clinical assessment performed while offline."*
2. **Explicit Application-Controlled Demo Fixture Isolation**:
   - Unencrypted browser storage is restricted exclusively to application-controlled synthetic demonstration fixtures (`synthetic-demo-patient-001`, `synthetic-demo-patient-002`, `synthetic-demo-patient-003`).
   - Synthetic classification is strictly verified against known fixture identities and explicit demo-session state; arbitrary user-entered substring matches (e.g. "demo", "synthetic") and globally writable JavaScript window flags are never accepted as proof of synthetic data.
   - Local offline draft caching of real personal health information is strictly disabled. Real patient drafts never enter plaintext `localStorage`.
   - Offline drafts can only be synchronized to the backend with an authenticated user session and explicit consent.

---

## 4. Role-Based Access Control (RBAC) & Clinician Governance

1. **Patient Workspace**:
   - Can submit intakes, view own preliminary triage results, and use assistive communication tools.
   - Strictly forbidden from accessing clinician queues, review endpoints, dashboard stats, or other patients' records.
2. **Clinician Workspace**:
   - Requires verified clinician credentials (`role == 'clinician'` or `role == 'admin'`).
   - Clinician review submissions require valid authenticated sessions; urgency overrides require a mandatory medical justification.
3. **Synthetic Clinician Role Isolation (role='dev_clinician')**:
   - Synthetic development accounts strictly use `role="dev_clinician"`, never `role="clinician"`.
   - Normal clinician/admin authorization dependencies never automatically include `dev_clinician`.
   - A `dev_clinician` role may access clinician functionality ONLY if:
     * `is_production()` is False;
     * `TRANSIFY_DEV_CLINICIAN_ENABLED` is explicitly true;
     * the session belongs to the designated synthetic development account (`dev-synthetic-clinician@transify.local`).
   - In production environments, authentication and session validation strictly reject synthetic development clinician accounts, even if an account exists in the database.
   - Credentials are delivered solely via HttpOnly session cookies without returning reusable session tokens in JSON response bodies.
   - Unique local-only credentials are generated cryptographically instead of hardcoded shared passwords.
   - Development clinician accounts cannot be created publicly or promoted to genuine clinician roles.
4. **Fail-Safe Demo Reset Guard**:
   - `POST /api/care/demo/reset` requires explicit demo-mode authorization (`TRANSIFY_DEMO_MODE_ENABLED` or `X-Transify-Demo-Auth`) in addition to a verified non-production environment.
   - Rejects production access (HTTP 403) and unconfigured remote environments.
   - Resets strictly only the documented synthetic demo fixtures (`synthetic-demo-patient-001`, `synthetic-demo-patient-002`, `synthetic-demo-patient-003`) and never modifies or deletes real patient records.

---

## 5. Tamper-Evident Audit Logging

1. **Append-Only SQLite Triggers**:
   - `prevent_care_audit_logs_update` and `prevent_care_audit_logs_delete` database triggers reject any `UPDATE` or `DELETE` queries on `care_audit_logs`.
2. **Cryptographic Chaining**:
   - Each audit log entry computes a SHA-256 hash chaining `prev_hash`, `event_type`, `intake_id`, `actor_id`, and `timestamp`, providing tamper evidence across events.
