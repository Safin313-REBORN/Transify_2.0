"""
Transify Care Deterministic Triage Rule Engine.
Implements a safety-first, multi-tier clinical triage evaluation based on WHO Interagency
Integrated Triage protocols and verified emergency escalation criteria.
The LLM can never override or downgrade deterministic triage rules.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Official Bangladesh Emergency Numbers
EMERGENCY_CONTACTS = {
    "country": "Bangladesh",
    "national_emergency": "999",
    "health_helpline": "16263",
    "shastho_batayan": "16263",
    "ambulance": "999",
    "disclaimer": "Transify Care is an accessible intake and communication tool, not an emergency medical service. If experiencing a life-threatening emergency, immediately call 999 or visit the nearest hospital emergency department."
}

# Versioned Deterministic Clinical Rules Catalog
DETERMINISTIC_RULES = [
    {
        "rule_id": "RULE-EMERG-001",
        "name": "Acute Chest Pain with Cardiopulmonary Red Flags",
        "category": "CARDIOVASCULAR_EMERGENCY",
        "keywords": ["chest pain", "crushing chest", "heart attack", "radiating pain", "arm pain", "jaw pain", "বুকের ব্যথা", "বুকে চাপ"],
        "severity_min": 6,
        "assigned_level": "RED",
        "clinical_source": "WHO Integrated Management of Adult and Adolescent Illness / DGHS Bangladesh Clinical Protocol",
        "source_version": "2023.1",
        "explanation": "Reported acute or severe chest discomfort with potential ischemic or cardiopulmonary indicators requiring immediate emergency department evaluation.",
        "emergency_action": "Immediate emergency room referral via ambulance (Call 999)."
    },
    {
        "rule_id": "RULE-EMERG-002",
        "name": "Severe Acute Respiratory Distress",
        "category": "RESPIRATORY_EMERGENCY",
        "keywords": ["cannot breathe", "severe shortness of breath", "gasping", "choking", "blue lips", "cyanosis", "শ্বাসকষ্ট", "শ্বাস নিতে পারছি না"],
        "severity_min": 7,
        "assigned_level": "RED",
        "clinical_source": "WHO Interagency Integrated Triage Tool (Red Category)",
        "source_version": "2020.2",
        "explanation": "Reported severe compromise in airway, breathing mechanics, or signs of hypoxemia.",
        "emergency_action": "Immediate emergency airway and oxygen assessment required (Call 999)."
    },
    {
        "rule_id": "RULE-EMERG-003",
        "name": "Acute Neurological Deficit (FAST Stroke Indicators)",
        "category": "NEUROLOGICAL_EMERGENCY",
        "keywords": ["face drooping", "arm weakness", "slurred speech", "sudden numbness", "loss of vision", "facial asymmetry", "কথা জড়িয়ে যাওয়া", "মুখ বেঁকে যাওয়া"],
        "severity_min": 5,
        "assigned_level": "RED",
        "clinical_source": "National Guidelines for Management of Stroke in Bangladesh",
        "source_version": "2021.1",
        "explanation": "Sudden onset focal neurological deficits suspicious for acute cerebrovascular accident (stroke). Time-critical window for intervention.",
        "emergency_action": "Immediate transfer to stroke-ready emergency facility (Call 999)."
    },
    {
        "rule_id": "RULE-EMERG-004",
        "name": "Severe Hemorrhage or Uncontrolled Bleeding",
        "category": "TRAUMA_BLEEDING",
        "keywords": ["uncontrolled bleeding", "massive blood", "coughing blood", "vomiting blood", "রক্তপাত", "রক্তবমি"],
        "severity_min": 6,
        "assigned_level": "RED",
        "clinical_source": "WHO Basic Emergency Care Protocol",
        "source_version": "2022.1",
        "explanation": "Active uncontrolled bleeding or severe hemorrhage posing hemodynamic shock hazard.",
        "emergency_action": "Direct local pressure and emergency transport (Call 999)."
    },
    {
        "rule_id": "RULE-URGENT-001",
        "name": "High Fever with Dehydration or Progressive Deterioration",
        "category": "INFECTIOUS_DISEASE",
        "keywords": ["high fever", "persistent fever", "vomiting", "cannot keep fluids", "severe headache", "উচ্চ জ্বর", "জ্বর ও বমি"],
        "severity_min": 5,
        "assigned_level": "YELLOW",
        "clinical_source": "National Dengue & Acute Febrile Illness Clinical Management Guidelines, DGHS",
        "source_version": "2024.1",
        "explanation": "Elevated febrile illness with systemic symptoms warranting same-day medical clinical assessment and diagnostic blood count.",
        "emergency_action": "Visit healthcare center or outpatient doctor within 4-12 hours."
    },
    {
        "rule_id": "RULE-URGENT-002",
        "name": "Moderate Persistent Abdominal Pain",
        "category": "GASTROINTESTINAL",
        "keywords": ["severe stomach pain", "abdominal pain", "appendix", "persistent vomiting", "পেটে তীব্র ব্যথা", "পেট ব্যথা"],
        "severity_min": 5,
        "assigned_level": "YELLOW",
        "clinical_source": "WHO Integrated Primary Care Guidance",
        "source_version": "2022.3",
        "explanation": "Progressive or unremitting abdominal pain requiring clinical palpation and differential exclusion of acute abdomen.",
        "emergency_action": "Prompt physical clinical evaluation recommended today."
    },
    {
        "rule_id": "RULE-ROUTINE-001",
        "name": "Mild Upper Respiratory Symptoms or Non-Urgent Minor Concern",
        "category": "PRIMARY_CARE_ROUTINE",
        "keywords": ["mild cough", "dry cough", "cough", "runny nose", "sore throat", "sneezing", "sneeze", "mild headache", "cold", "সর্দি", "হালকা কাশি", "কাশি"],
        "severity_min": 1,
        "assigned_level": "GREEN",
        "clinical_source": "Standard Primary Healthcare Clinical Protocol, Bangladesh",
        "source_version": "2021.2",
        "explanation": "Mild self-limiting symptoms with stable vital signs, manageable with supportive hydration, rest, and non-emergency clinic visit if symptoms persist > 5 days.",
        "emergency_action": "Schedule standard routine clinic appointment or teleconsultation."
    }
]


def evaluate_triage(
    chief_complaint: str,
    symptom_description: str,
    severity: int = 1,
    trajectory: str = "stable",
    onset_duration: str = ""
) -> Dict[str, Any]:
    """
    Evaluates patient symptoms against deterministic safety rules.
    Prioritizes RED > YELLOW > GREEN.
    Returns structured assessment with rule ID, level, explanation, and emergency escalation.
    """
    full_text = f"{chief_complaint} {symptom_description}".lower()

    if not full_text.strip():
        return {
            "urgency_level": "INSUFFICIENT_INFORMATION",
            "rule_id": "RULE-NONE",
            "explanation": "Insufficient symptom detail provided to generate preliminary clinical urgency assessment.",
            "emergency_escalation": None,
            "can_wait": True,
            "requires_clinician_review": True,
            "missing_information": ["chief_complaint", "symptom_description"]
        }

    # 1. First pass: Evaluate RED / Emergency rules
    for rule in DETERMINISTIC_RULES:
        if rule["assigned_level"] == "RED":
            matched_keywords = [kw for kw in rule["keywords"] if kw.lower() in full_text]
            if matched_keywords:
                return {
                    "urgency_level": "RED",
                    "rule_id": rule["rule_id"],
                    "rule_name": rule["name"],
                    "explanation": f"{rule['explanation']} (Triggered by reported '{', '.join(matched_keywords)}')",
                    "clinical_source": f"{rule['clinical_source']} (v{rule['source_version']})",
                    "emergency_escalation": {
                        "is_emergency": True,
                        "action": rule["emergency_action"],
                        "hotline": EMERGENCY_CONTACTS["national_emergency"],
                        "health_helpline": EMERGENCY_CONTACTS["health_helpline"],
                        "disclaimer": EMERGENCY_CONTACTS["disclaimer"]
                    },
                    "can_wait": False,
                    "requires_clinician_review": True,
                    "missing_information": []
                }

    # 2. Second pass: Evaluate YELLOW / Urgent rules
    for rule in DETERMINISTIC_RULES:
        if rule["assigned_level"] == "YELLOW":
            matched_keywords = [kw for kw in rule["keywords"] if kw.lower() in full_text]
            if matched_keywords or (severity >= 6 and trajectory == "worsening"):
                return {
                    "urgency_level": "YELLOW",
                    "rule_id": rule["rule_id"],
                    "rule_name": rule["name"],
                    "explanation": f"{rule['explanation']}" + (f" (Triggered by '{', '.join(matched_keywords)}')" if matched_keywords else " (Triggered by high severity and deteriorating trajectory)"),
                    "clinical_source": f"{rule['clinical_source']} (v{rule['source_version']})",
                    "emergency_escalation": None,
                    "can_wait": False,
                    "requires_clinician_review": True,
                    "missing_information": ["vital_signs", "physical_examination"]
                }

    # 3. Third pass: Evaluate GREEN / Routine rules
    for rule in DETERMINISTIC_RULES:
        if rule["assigned_level"] == "GREEN":
            matched_keywords = [kw for kw in rule["keywords"] if kw.lower() in full_text]
            if matched_keywords and severity <= 4 and trajectory != "worsening":
                return {
                    "urgency_level": "GREEN",
                    "rule_id": rule["rule_id"],
                    "rule_name": rule["name"],
                    "explanation": f"{rule['explanation']} (Triggered by reported '{', '.join(matched_keywords)}')",
                    "clinical_source": f"{rule['clinical_source']} (v{rule['source_version']})",
                    "emergency_escalation": None,
                    "can_wait": True,
                    "requires_clinician_review": True,
                    "missing_information": ["symptom_progression_log"]
                }

    # 4. Fallback: Needs Clinician Review / Unknown
    return {
        "urgency_level": "REVIEW_REQUIRED",
        "rule_id": "RULE-REVIEW-FALLBACK",
        "rule_name": "Clinical Review Required for Unmatched Symptom Complex",
        "explanation": "Symptom presentation does not match deterministic emergency patterns. Requires clinician review to evaluate individualized care pathway.",
        "clinical_source": "General Clinical Triage Protocol",
        "emergency_escalation": None,
        "can_wait": True,
        "requires_clinician_review": True,
        "missing_information": ["clinician_evaluation", "relevant_history"]
    }
