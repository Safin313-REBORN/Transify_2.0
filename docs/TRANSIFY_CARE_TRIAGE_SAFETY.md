# Transify Care — Deterministic Triage Safety & Escalation Rules
**Module**: `src/care/triage.py`  
**Safety Hierarchy**: RED (Emergency) > YELLOW (Urgent) > REVIEW_REQUIRED / INSUFFICIENT_INFORMATION > GREEN (Routine)
**Status**: Clinical Triage Research Prototype (Requires formal clinical review before real-patient deployment)

---

## 1. Safety Principles & Triage Matrix

The triage engine in Transify Care is deterministic, auditable, and rule-bounded. It evaluates reported symptoms, severity, and trajectory across versioned rules. Crucially, missing or contradictory information **never defaults to GREEN** and is never marked as safe to wait.

| Rule ID | Category | Level | Primary Triggers | Action & Escalation |
|---|---|---|---|---|
| `RULE-EMERG-001` | CARDIAC_EMERGENCY | **RED** | Crushing chest pain, left arm radiation, diaphoresis, acute pressure, বুকে ব্যথা | Immediate Emergency Escalation. Display actions for Bangladesh 999 & 16263. |
| `RULE-EMERG-002` | NEURO_STROKE_EMERGENCY | **RED** | Sudden weakness, facial droop, slurred speech, acute numbness, মুখ বেঁকে যাওয়া | Immediate Emergency Escalation. Advise stroke-ready facility transport within 4.5h window. |
| `RULE-EMERG-003` | RESPIRATORY_FAILURE | **RED** | Cannot breathe, stridor, choking, severe breathlessness, শ্বাস নিতে কষ্ট | Immediate Emergency Escalation. Immediate airway management indication. |
| `RULE-EMERG-004` | ANAPHYLAXIS_EMERGENCY | **RED** | Throat closing, lip swelling, severe allergic reaction, অ্যানাফিল্যাক্সিস | Immediate Emergency Escalation. Emergency medical attention indication. |
| `RULE-URGENT-001` | FEBRILE_WARNING_SIGNS | **YELLOW** | High fever (103°F+), persistent vomiting, severe abdominal pain, ডেঙ্গু | Prompt Same-Day Evaluation. DGHS Dengue protocol adherence. |
| `RULE-URGENT-002` | ACUTE_ABDOMEN | **YELLOW** | Severe stomach pain, abdominal cramping, unremitting nausea | Physical clinical examination advised today. |
| `RULE-SAFETY-CONTRADICTION` | CONTRADICTORY_PRESENTATION | **YELLOW** | Simultaneously reporting and denying critical symptoms | Clinical Review Required. Contradiction flagged; cannot safely wait. |
| `RULE-ACUTE-UNCLASSIFIED` | ACUTE_PRESENTATION_REVIEW | **REVIEW_REQUIRED** | Acute onset (< 24h) or high severity (>3) not matching specific emergency rules | Clinical Review Required. Cannot be classified routine; cannot safely wait. |
| `RULE-ROUTINE-001` | PRIMARY_CARE_ROUTINE | **GREEN** | Mild cough, dry cough, runny nose, sore throat, sneezing, cold, কাশি (Duration ≥ 24h, Severity ≤ 3) | Primary clinic visit or teleconsultation. Hydration & rest. |
| `RULE-INSUFFICIENT-001` | INSUFFICIENT_INFORMATION | **INSUFFICIENT_INFORMATION** | Missing symptom text, empty complaints, or non-informative input | Flags specific missing information. Cannot wait; prompt for clarification. |
| `RULE-UNRECOGNIZED` | UNRECOGNIZED_COMPLAINT | **REVIEW_REQUIRED** | Symptoms not matching known prototype rule catalogue | Flags unrecognized input. Directs to clinician evaluation; cannot assume routine. |

### Visual Urgency Mapping
Each triage state has distinct styling in `src/frontend/static/styles.css`:
- **RED**: Danger Crimson (`#DC2626` / `#FEF2F2`)
- **YELLOW**: Amber Alert (`#D97706` / `#FFFBEB`)
- **GREEN**: Safe Emerald (`#059669` / `#ECFDF5`)
- **REVIEW_REQUIRED**: Indigo Review (`#4F46E5` / `#EEF2FF`)
- **INSUFFICIENT_INFORMATION**: Slate Incomplete (`#64748B` / `#F1F5F9`)

Neither `REVIEW_REQUIRED` nor `INSUFFICIENT_INFORMATION` ever renders as GREEN, and both set `can_wait: False`.

---

## 2. Emergency Escalation Contacts (Bangladesh)

Whenever `urgency_level == 'RED'`, the emergency response payload includes verified national emergency hotlines:
- **National Emergency Service**: `999` (Police, Fire, Ambulance contact actions displayed)
- **National Health Helpline**: `16263` (24/7 Government of Bangladesh Health Call Center)
- **Legal Disclaimer**: *"Transify Care provides preliminary triage routing prototype guidance and does not replace emergency medical personnel, ambulance dispatch, or clinical diagnosis."*

---

## 3. Human-in-the-Loop Clinician Governance

To eliminate autonomous AI drift and prevent erroneous classification:
1. Every intake is placed in the clinician-review queue.
2. Clinical supervisors can accept or modify the care pathway.
3. If overriding urgency (e.g. downgrading RED to GREEN or upgrading GREEN to YELLOW), the backend strictly rejects the review unless an explicit clinical explanation is provided (`override_reason`).
4. All reviews and state changes are recorded in append-only, tamper-evident audit tables (`care_audit_logs`) protected by database-level triggers and SHA-256 cryptographic chaining.
