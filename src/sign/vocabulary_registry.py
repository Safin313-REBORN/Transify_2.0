"""
Transify — Comprehensive Sign Language Vocabulary Registry & Communicative Domains.
Structures Bangladesh Sign Language (BdSL) expressions into practical, real-world
communicative categories for speech- and hearing-impaired users.
"""

from typing import Dict, Any, List

EXPANDED_VOCABULARY = {
    "emergency_medical": {
        "title": "🚨 Emergency & Healthcare",
        "description": "Urgent medical assistance, pain indicators, and public safety.",
        "expressions": [
            {"id": 4, "label": "I_NEED_HELP", "display": "I need help.", "gloss": "Need Assistance", "desc": "Dominant fist on non-dominant palm lifting toward chest."},
            {"id": 8, "label": "STOP", "display": "Stop.", "gloss": "Stop / Halt", "desc": "Open palm forward projection with abrupt deceleration."},
            {"id": 10, "label": "PAIN", "display": "I am in pain.", "gloss": "Physical Pain", "desc": "Both index fingers pointing towards location of pain with facial grimace."},
            {"id": 11, "label": "DOCTOR", "display": "I need a doctor.", "gloss": "Medical Doctor", "desc": "Three fingers tap radial wrist (checking pulse)."},
            {"id": 12, "label": "HOSPITAL", "display": "Hospital.", "gloss": "Hospital / Clinic", "desc": "Index and middle finger drawing a cross '+' on upper arm."},
            {"id": 13, "label": "MEDICINE", "display": "Medicine.", "gloss": "Medicine / Pharmacy", "desc": "Middle finger tip grinding in palm of non-dominant hand."},
            {"id": 14, "label": "RESTROOM", "display": "Restroom / Toilet.", "gloss": "Restroom", "desc": "Shaking 'T' handshape gently side to side."}
        ]
    },
    "daily_needs": {
        "title": "🍞 Daily Living & Basic Needs",
        "description": "Food, hydration, physical comfort, and sustenance.",
        "expressions": [
            {"id": 15, "label": "WATER", "display": "Water, please.", "gloss": "Drinking Water", "desc": "'W' handshape index finger tapping lower lip twice."},
            {"id": 16, "label": "FOOD", "display": "I am hungry / Food.", "gloss": "Food / Meal", "desc": "Flattened 'O' handshape tapping mouth twice."},
            {"id": 17, "label": "SLEEP", "display": "I am tired / Sleep.", "gloss": "Sleep / Rest", "desc": "Open hand over face closing to flattened fist while eyes close."},
            {"id": 18, "label": "HOME", "display": "Home.", "gloss": "Home / Residence", "desc": "Flat fingers touching chin then temple."},
            {"id": 19, "label": "MONEY", "display": "Money.", "gloss": "Money / Cash", "desc": "Fingers rubbing against thumb tip in counting motion."}
        ]
    },
    "social_courtesy": {
        "title": "🤝 Social & Everyday Courtesy",
        "description": "Common polite phrases, greetings, affirmations, and agreements.",
        "expressions": [
            {"id": 0, "label": "HELLO", "display": "Hello!", "gloss": "Hello / Greetings", "desc": "One-handed temple forward arc with slight bow."},
            {"id": 1, "label": "THANK_YOU", "display": "Thank you.", "gloss": "Thank You", "desc": "Flat hand chin to forward-downward arc with slight nod."},
            {"id": 2, "label": "YOURE_WELCOME", "display": "You're welcome.", "gloss": "You're Welcome", "desc": "Two open palms inward sweep toward torso."},
            {"id": 3, "label": "PLEASE", "display": "Please.", "gloss": "Please", "desc": "Flat palm clockwise circular motion on sternum."},
            {"id": 5, "label": "YES", "display": "Yes.", "gloss": "Yes / Affirmative", "desc": "Closed fist vertical nodding at wrist."},
            {"id": 6, "label": "NO", "display": "No.", "gloss": "No / Negative", "desc": "Extended index finger horizontal oscillating wag."},
            {"id": 7, "label": "OKAY", "display": "Okay.", "gloss": "Okay / Confirmed", "desc": "Index and thumb 'O' contact with forward double tap."},
            {"id": 9, "label": "I_DONT_UNDERSTAND", "display": "I don't understand.", "gloss": "Don't Understand", "desc": "Temple tap transitioning to outward sweep with head shake."}
        ]
    },
    "questions_navigation": {
        "title": "❓ Questions & Inquiries",
        "description": "Asking for directions, identity, or clarification.",
        "expressions": [
            {"id": 20, "label": "WHERE", "display": "Where?", "gloss": "Where is it?", "desc": "Index finger extended upright oscillating left and right with furrowed brow."},
            {"id": 21, "label": "WHAT", "display": "What?", "gloss": "What is this?", "desc": "Both open palms facing up shaking side to side."},
            {"id": 22, "label": "WHEN", "display": "When?", "gloss": "When?", "desc": "Dominant index finger circling non-dominant index finger tip."},
            {"id": 23, "label": "WHO", "display": "Who?", "gloss": "Who is that?", "desc": "Index finger circling around mouth with puckered lips."}
        ]
    }
}


def get_all_categories() -> Dict[str, Any]:
    """Returns all communicative domains with expression counts."""
    total_expressions = sum(len(cat["expressions"]) for cat in EXPANDED_VOCABULARY.values())
    return {
        "total_categories": len(EXPANDED_VOCABULARY),
        "total_expressions": total_expressions,
        "categories": EXPANDED_VOCABULARY
    }
