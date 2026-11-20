# Transify Care — Deterministic Triage Safety & Escalation Rules
**Module**: `src/care/triage.py`  
**Safety Hierarchy**: RED (Emergency) > YELLOW (Urgent) > GREEN (Routine) > INSUFFICIENT_INFORMATION

---

## 1. Safety Principles & Triage Matrix

The triage engine in Transify Care is deterministic, auditable, and rule-bounded. It evaluates reported symptoms, severity, and trajectory across versioned rules:

| Rule ID | Category | Level | Primary Triggers | Action & Escalation |
|---|---|---|---|---|
| `RULE-EMERG-001` | CARDIAC_EMERGENCY | **RED** | Crushing chest pain, left arm radiation, diaphoresis, acute pressure, বুকে ব্যথা | Immediate Emergency Escalation. Call Bangladesh 999 & 16263. Immediate dispatch. |
| `RULE-EMERG-002` | NEURO_STROKE_EMERGENCY | **RED** | Sudden weakness, facial droop, slurred speech, acute numbness, মুখ বেঁকে যাওয়া | Immediate Emergency Escalation. Stroke-ready facility transport within 4.5 hours. |
| `RULE-EMERG-003` | RESPIRATORY_FAILURE | **RED** | Cannot breathe, stridor, choking, severe breathlessness, শ্বাস নিতে কষ্ট | Immediate Emergency Escalation. Emergency airway management. |
| `RULE-EMERG-004` | ANAPHYLAXIS_EMERGENCY | **RED** | Throat closing, lip swelling, severe allergic reaction, অ্যানাফিল্যাক্সিস | Immediate Emergency Escalation. Epinephrine indication. |
| `RULE-URGENT-001` | FEBRILE_WARNING_SIGNS | **YELLOW** | High fever (103°F+), persistent vomiting, severe abdominal pain, ডেঙ্গু | Prompt Same-Day Evaluation. DGHS Dengue protocol adherence. |
| `RULE-URGENT-002` | ACUTE_ABDOMEN | **YELLOW** | Severe stomach pain, abdominal cramping, unremitting nausea | Physical clinical palpation required today. |
| `RULE-ROUTINE-001` | PRIMARY_CARE_ROUTINE | **GREEN** | Mild cough, dry cough, runny nose, sore throat, sneezing, cold, কাশি | Standard primary clinic visit or teleconsultation. Hydration & rest. |
| `RULE-NONE` | UNMATCHED_OR_INCOMPLETE | **REVIEW_REQUIRED** / **INSUFFICIENT** | Missing symptom text, or unmatched complex presentation | Flags specific missing information. Queues for physician evaluation. |

---

## 2. Emergency Escalation Contacts (Bangladesh)

Whenever `urgency_level == 'RED'`, the emergency response payload includes verified national emergency hotlines:
- **National Emergency Service**: `999` (Police, Fire, Ambulance)
- **National Health Helpline**: `16263` (24/7 Government of Bangladesh Health Call Center)
- **Legal Disclaimer**: *"Transify Care provides preliminary triage routing and does not replace emergency medical personnel or clinical diagnosis."*

---

## 3. Human-in-the-Loop Clinician Governance

To eliminate autonomous AI drift and prevent erroneous classification:
1. Every intake is placed in the clinician queue.
2. The clinician can accept or modify the care pathway.
3. If overriding urgency (e.g. downgrading RED to GREEN or upgrading GREEN to YELLOW), the backend strictly rejects the review unless an explicit clinical explanation is provided (`override_reason`).
4. All reviews are permanently committed to `care_clinician_reviews` and `care_audit_logs`.
