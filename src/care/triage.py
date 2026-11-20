"""
Transify Care Deterministic Triage Rule Engine.
Implements a safety-first, multi-tier clinical triage evaluation prototype based on WHO Interagency
Integrated Triage protocols and verified emergency escalation criteria.
NOTE: This deterministic engine is a clinical decision-support prototype intended for synthetic
demonstration and workflow evaluation. It is not approved for autonomous real-patient decision-making
without qualified healthcare professional oversight. Vital signs are not collected by this digital tool.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

# Official Bangladesh Emergency Numbers
EMERGENCY_CONTACTS = {
    "country": "Bangladesh",
    "national_emergency": "999",
    "health_helpline": "16263",
    "shastho_batayan": "16263",
    "ambulance": "999",
    "disclaimer": "Transify Care displays emergency escalation actions and hotlines. It does not autonomously dispatch emergency services. If experiencing a life-threatening emergency, immediately call 999 or visit the nearest hospital emergency department."
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
        "explanation": "Reported acute or severe chest discomfort with potential ischemic or cardiopulmonary indicators requiring immediate emergency department evaluation. (Vital signs not measured; emergency evaluation required).",
        "emergency_action": "Immediate emergency room evaluation required. Call Bangladesh Emergency 999 or Health Helpline 16263."
    },
    {
        "rule_id": "RULE-EMERG-002",
        "name": "Severe Acute Respiratory Distress",
        "category": "RESPIRATORY_EMERGENCY",
        "keywords": ["cannot breathe", "difficulty breathing", "severe shortness of breath", "shortness of breath", "hard to breath", "gasping", "choking", "blue lips", "cyanosis", "শ্বাসকষ্ট", "শ্বাস নিতে পারছি না"],
        "severity_min": 7,
        "assigned_level": "RED",
        "clinical_source": "WHO Interagency Integrated Triage Tool (Red Category Adaptation Prototype)",
        "source_version": "2020.2",
        "explanation": "Reported severe compromise in airway, breathing mechanics, or signs of hypoxemia. (Vital signs not measured; immediate airway evaluation required).",
        "emergency_action": "Immediate emergency airway and oxygen assessment required. Call Bangladesh Emergency 999."
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
        "emergency_action": "Immediate transfer to stroke-ready emergency facility. Call Bangladesh Emergency 999."
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
        "explanation": "Active uncontrolled bleeding or severe hemorrhage posing hemodynamic shock hazard. (Vital signs not measured; urgent intervention required).",
        "emergency_action": "Direct local pressure and emergency transport. Call Bangladesh Emergency 999."
    },
    {
        "rule_id": "RULE-URGENT-001",
        "name": "High Fever with Dehydration or Progressive Deterioration",
        "category": "INFECTIOUS_DISEASE",
        "keywords": ["high fever", "persistent fever", "vomiting", "cannot keep fluids", "severe headache", "উচ্চ জ্বর", "জ্বর ও বমি"],
        "severity_min": 5,
        "assigned_level": "YELLOW",
        "clinical_source": "National Guidelines for Clinical Management of Dengue Syndrome, DGHS Bangladesh",
        "source_version": "5th Edition (2023)",
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
        "explanation": "Progressive or unremitting abdominal pain requiring physical clinical examination and differential exclusion of acute abdomen.",
        "emergency_action": "Prompt physical clinical evaluation recommended today."
    },
    {
        "rule_id": "RULE-EMERG-DERM-001",
        "name": "Severe Full-Thickness Thermal/Chemical Burn or Necrotizing Skin Lesion",
        "category": "DERMATOLOGY_EMERGENCY",
        "keywords": ["severe burn", "third degree burn", "blistering all over", "skin peeling", "necrotizing", "black wound", "পুড়ে গেছে", "চামড়া ঝলসে গেছে"],
        "severity_min": 7,
        "assigned_level": "RED",
        "clinical_source": "Merck Manual of Diagnosis and Therapy (Professional Edition) / WHO Burn Management",
        "source_version": "2024.1",
        "explanation": "Extensive cutaneous barrier compromise or suspected necrotizing soft tissue infection posing immediate shock, sepsis, and fluid loss hazards.",
        "emergency_action": "Immediate emergency room or specialized burn center transfer required. Call Bangladesh Emergency 999."
    },
    {
        "rule_id": "RULE-EMERG-OPHTH-001",
        "name": "Acute Sudden Vision Loss or Penetrating Ocular Trauma",
        "category": "OPHTHALMIC_EMERGENCY",
        "keywords": ["sudden blindness", "loss of vision", "eye injury", "penetrating eye", "chemical in eye", "corneal tear", "চোখে দেখতে পাচ্ছি না", "চোখে আঘাত"],
        "severity_min": 7,
        "assigned_level": "RED",
        "clinical_source": "Merck Manual of Diagnosis and Therapy / National Institute of Ophthalmology Protocol",
        "source_version": "2024.1",
        "explanation": "Acute compromise of visual pathway or penetrating globe trauma risking permanent irreversible vision loss.",
        "emergency_action": "Immediate specialized ophthalmology emergency evaluation required. Call Bangladesh Emergency 999."
    },
    {
        "rule_id": "RULE-URGENT-DERM-001",
        "name": "Spreading Cutaneous Erythema, Suspect Cellulitis or Atypical Lesion",
        "category": "DERMATOLOGY_URGENT",
        "keywords": ["spreading red rash", "skin infection", "cellulitis", "melanoma", "skin ulcer", "pus in wound", "চামড়ায় ঘা", "চামড়া লাল ও গরম"],
        "severity_min": 5,
        "assigned_level": "YELLOW",
        "clinical_source": "Merck Manual of Diagnosis and Therapy (Professional Edition)",
        "source_version": "2024.1",
        "explanation": "Spreading erythematous cutaneous involvement or non-healing ulceration warranting same-day medical clinical assessment.",
        "emergency_action": "In-person clinical and dermoscopic examination recommended within 12-24 hours."
    },
    {
        "rule_id": "RULE-URGENT-OPHTH-001",
        "name": "Acute Red Eye with Severe Pain or Corneal Infiltrate",
        "category": "OPHTHALMIC_URGENT",
        "keywords": ["red eye", "corneal ulcer", "cloudy eye", "severe eye pain", "photophobia", "চোখ লাল", "চোখে তীব্র ব্যথা"],
        "severity_min": 5,
        "assigned_level": "YELLOW",
        "clinical_source": "Merck Manual of Diagnosis and Therapy (Ophthalmic Protocols)",
        "source_version": "2024.1",
        "explanation": "Ciliary conjunctival injection and anterior segment inflammation requiring slit-lamp verification to rule out corneal ulcer or uveitis.",
        "emergency_action": "Prompt ophthalmic clinical evaluation recommended today."
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
        "explanation": "Reported mild self-limiting symptoms with low reported severity and non-worsening trajectory. (Vital signs were not collected or verified by this digital tool; if shortness of breath develops, seek immediate care).",
        "emergency_action": "Schedule standard routine clinic appointment or teleconsultation if symptoms persist."
    }
]

# Negation terms in English and Bengali
NEGATION_PRE = [
    "no", "not", "without", "denies", "denied", "free of",
    "negative for", "zero", "no signs of", "neither", "nor", "rule out",
    "কোন", "কোনো"
]
NEGATION_POST = [
    "নেই", "নাই", "না", "free", "absent", "resolved"
]


def analyze_keyword_matches(text: str, keywords: List[str]) -> Tuple[List[str], List[str]]:
    """
    Scans text for occurrences of keywords and determines if they are affirmative or negated.
    Returns (affirmative_matches, negated_matches).
    """
    affirmative = []
    negated = []
    lower_text = text.lower()

    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in lower_text:
            continue

        # Find all occurrences of kw_lower in lower_text
        start_idx = 0
        while True:
            idx = lower_text.find(kw_lower, start_idx)
            if idx == -1:
                break

            # Check preceding context (up to 60 characters before)
            pre_chunk = lower_text[max(0, idx - 60):idx].strip()
            # Check succeeding context (up to 30 characters after)
            post_chunk = lower_text[idx + len(kw_lower):min(len(lower_text), idx + len(kw_lower) + 30)].strip()

            is_neg = False
            for neg in NEGATION_PRE:
                # Word boundary check for negation prefix (allowing intervening symptoms and conjunctions)
                pattern = rf"(^|\s|[,.;]){re.escape(neg)}(\s+[\w\s,]{{0,45}})?$"
                if re.search(pattern, pre_chunk):
                    is_neg = True
                    break

            if not is_neg:
                for neg in NEGATION_POST:
                    pattern = rf"^(\s+[\w\s,]{{0,20}})?{re.escape(neg)}(\s|[,.;]|$)"
                    if re.search(pattern, post_chunk):
                        is_neg = True
                        break
                        is_neg = True
                        break

            if is_neg:
                if kw not in negated:
                    negated.append(kw)
            else:
                if kw not in affirmative:
                    affirmative.append(kw)

            start_idx = idx + len(kw_lower)

    return affirmative, negated


def evaluate_triage(
    chief_complaint: str,
    symptom_description: str,
    severity: int = 1,
    trajectory: str = "stable",
    onset_duration: str = ""
) -> Dict[str, Any]:
    """
    Evaluates patient symptoms against deterministic safety rules.
    Prioritizes RED > YELLOW > REVIEW_REQUIRED / INSUFFICIENT_INFORMATION.
    ROUTINE GREEN is strictly gated and never used as a default or fallback.
    Never claims waiting is safe for unknown or incomplete states.
    Handles negations ('no chest pain') and contradictory inputs.
    """
    clean_complaint = (chief_complaint or "").strip()
    clean_description = (symptom_description or "").strip()
    full_text = f"{clean_complaint} {clean_description}".strip()
    full_lower = full_text.lower()

    # 1. Check for Missing or Insufficient Information
    # If chief complaint is empty or full text contains no clinical detail
    if not clean_complaint and not clean_description:
        return {
            "urgency_level": "INSUFFICIENT_INFORMATION",
            "rule_id": "RULE-INSUFFICIENT-001",
            "rule_name": "Insufficient Clinical Information Provided",
            "explanation": "No symptom information was provided. Digital triage cannot be performed. Waiting cannot be confirmed safe without clinical evaluation.",
            "emergency_escalation": None,
            "can_wait": False,
            "requires_clinician_review": True,
            "missing_information": ["chief_complaint", "symptom_description", "vital_signs_not_collected", "physical_examination"],
            "disclaimer": "Vital signs were not collected. Prototype rule engine for demonstration only."
        }

    # If text is extremely short or purely uninformative (e.g. 'hi', 'test', 'hello')
    uninformative_tokens = {"hi", "hello", "hey", "test", "ok", "yes", "no", "please", "help"}
    words = [w for w in re.split(r"\W+", full_lower) if w]
    if len(words) <= 1 and words and words[0] in uninformative_tokens:
        return {
            "urgency_level": "INSUFFICIENT_INFORMATION",
            "rule_id": "RULE-INSUFFICIENT-002",
            "rule_name": "Non-Specific Symptom Input",
            "explanation": "The provided input does not describe a clinical symptom or medical complaint. Triage cannot be safely completed. Waiting is not confirmed safe.",
            "emergency_escalation": None,
            "can_wait": False,
            "requires_clinician_review": True,
            "missing_information": ["chief_complaint", "symptom_description", "vital_signs_not_collected"],
            "disclaimer": "Vital signs were not collected. Prototype rule engine for demonstration only."
        }

    # 2. Check for Contradictory Input across Red-Flag Keywords
    # E.g. "Severe crushing chest pain" and "no chest pain"
    has_contradiction = False
    contradicted_keywords = []

    for rule in DETERMINISTIC_RULES:
        if rule["assigned_level"] in ("RED", "YELLOW"):
            aff, neg = analyze_keyword_matches(full_text, rule["keywords"])
            overlap = set(aff).intersection(set(neg))
            if overlap:
                has_contradiction = True
                contradicted_keywords.extend(list(overlap))

    if has_contradiction:
        return {
            "urgency_level": "REVIEW_REQUIRED",
            "rule_id": "RULE-SAFETY-CONTRADICTION",
            "rule_name": "Contradictory Symptom Report",
            "explanation": f"Contradictory clinical statements detected regarding '{', '.join(set(contradicted_keywords))}' (both affirmed and denied). A clinician must conduct a direct assessment. Waiting is not safe.",
            "emergency_escalation": None,
            "can_wait": False,
            "requires_clinician_review": True,
            "missing_information": ["clinician_clarification", "verified_symptom_history", "vital_signs_not_collected"],
            "disclaimer": "Vital signs were not collected. Prototype rule engine for demonstration only."
        }

    # 3. First Pass: Evaluate RED / Emergency Rules (Affirmative matches only)
    for rule in DETERMINISTIC_RULES:
        if rule["assigned_level"] == "RED":
            aff, _ = analyze_keyword_matches(full_text, rule["keywords"])
            if aff:
                return {
                    "urgency_level": "RED",
                    "rule_id": rule["rule_id"],
                    "rule_name": rule["name"],
                    "explanation": f"{rule['explanation']} (Triggered by reported '{', '.join(aff)}')",
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
                    "missing_information": ["vital_signs_not_collected", "emergency_medical_evaluation"]
                }

    # 4. Second Pass: Evaluate YELLOW / Urgent Rules (Affirmative matches only or acute deterioration)
    for rule in DETERMINISTIC_RULES:
        if rule["assigned_level"] == "YELLOW":
            aff, _ = analyze_keyword_matches(full_text, rule["keywords"])
            is_deteriorating = (severity >= 6 and trajectory == "worsening")
            if aff or is_deteriorating:
                trigger_desc = f"Triggered by reported '{', '.join(aff)}'" if aff else "Triggered by elevated severity and deteriorating trajectory"
                return {
                    "urgency_level": "YELLOW",
                    "rule_id": rule["rule_id"],
                    "rule_name": rule["name"],
                    "explanation": f"{rule['explanation']} ({trigger_desc})",
                    "clinical_source": f"{rule['clinical_source']} (v{rule['source_version']})",
                    "emergency_escalation": None,
                    "can_wait": False,
                    "requires_clinician_review": True,
                    "missing_information": ["vital_signs_not_collected", "physical_examination", "laboratory_tests"]
                }

    # 5. Check Acute Duration or High Severity without Red/Yellow match
    # Validate onset_duration: if sudden onset with moderate severity, route to REVIEW_REQUIRED, not GREEN
    onset_lower = (onset_duration or "").lower()
    is_acute_onset = any(term in onset_lower for term in ["minute", "hour", "sudden", "abrupt", "today", "yesterday", "acute"])
    if is_acute_onset and severity >= 5:
        return {
            "urgency_level": "REVIEW_REQUIRED",
            "rule_id": "RULE-ACUTE-UNCLASSIFIED",
            "rule_name": "Acute Onset Requiring Clinical Assessment",
            "explanation": f"Reported symptoms have an acute onset ('{onset_duration}') with elevated severity ({severity}/10) that do not match pre-programmed emergency patterns. Requires prompt human clinician evaluation. Waiting is not confirmed safe.",
            "emergency_escalation": None,
            "can_wait": False,
            "requires_clinician_review": True,
            "missing_information": ["vital_signs_not_collected", "clinician_evaluation"]
        }

    # 6. Third Pass: Gated Evaluation of GREEN / Routine Rules
    # Routine GREEN requires:
    # a) Affirmative match with routine symptoms (mild cough, cold, etc.)
    # b) Severity <= 3
    # c) Trajectory is not 'worsening'
    # d) Not an acute sudden presentation (< 24h)
    for rule in DETERMINISTIC_RULES:
        if rule["assigned_level"] == "GREEN":
            aff, _ = analyze_keyword_matches(full_text, rule["keywords"])
            if aff:
                if severity <= 3 and trajectory != "worsening" and not (is_acute_onset and severity > 2):
                    return {
                        "urgency_level": "GREEN",
                        "rule_id": rule["rule_id"],
                        "rule_name": rule["name"],
                        "explanation": f"{rule['explanation']} (Triggered by reported '{', '.join(aff)}')",
                        "clinical_source": f"{rule['clinical_source']} (v{rule['source_version']})",
                        "emergency_escalation": None,
                        "can_wait": True,
                        "requires_clinician_review": True,
                        "missing_information": ["vital_signs_not_collected"]
                    }
                else:
                    # Mild symptoms reported, but severity or trajectory is elevated -> REVIEW_REQUIRED
                    return {
                        "urgency_level": "REVIEW_REQUIRED",
                        "rule_id": "RULE-REVIEW-ELEVATED-MILD",
                        "rule_name": "Routine Symptoms with Elevated Severity or Worsening Trajectory",
                        "explanation": f"Reported symptoms include '{', '.join(aff)}', but patient reported severity ({severity}/10) or worsening trajectory warrants clinician review rather than routine self-care.",
                        "emergency_escalation": None,
                        "can_wait": False,
                        "requires_clinician_review": True,
                        "missing_information": ["vital_signs_not_collected", "clinician_review"]
                    }

    # 7. Unmatched / Unknown Complaints Fallback -> REVIEW_REQUIRED
    # NEVER fall back to GREEN!
    # NEVER claim waiting is safe!
    return {
        "urgency_level": "REVIEW_REQUIRED",
        "rule_id": "RULE-REVIEW-FALLBACK",
        "rule_name": "Clinical Review Required for Unmatched Symptom Complex",
        "explanation": "Reported symptoms do not match deterministic emergency or routine decision rules. A healthcare professional must review the presentation to recommend next steps. Waiting is not confirmed safe.",
        "emergency_escalation": None,
        "can_wait": False,
        "requires_clinician_review": True,
        "missing_information": ["clinician_evaluation", "relevant_history", "vital_signs_not_collected"]
    }
