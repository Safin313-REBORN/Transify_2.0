"""
Transify — Comprehensive Sign Language Vocabulary Registry & Communicative Domains.
Structures Bangladesh Sign Language (BdSL) expressions into practical, real-world
communicative categories for speech- and hearing-impaired users.
Explicitly distinguishes production-verified closed-vocabulary models from candidate concepts.
"""

from typing import Dict, Any, List
from src.sign.bdsl_candidate_expansion import (
    VERIFIED_BDSL_CLASSES,
    CANDIDATE_BDSL_EXPANSION
)

EXPANDED_VOCABULARY = {
    "social_courtesy": {
        "title": "🤝 Social & Everyday Courtesy",
        "description": "Production-verified polite phrases, greetings, affirmations, and agreements.",
        "expressions": [
            {
                "id": 0,
                "label": "HELLO",
                "display": "Hello!",
                "gloss": "Hello / Greetings",
                "desc": "One-handed temple forward arc with slight bow.",
                "is_trained": True,
                "status": "PRODUCTION_VERIFIED",
                "ui_badge": "Live Supported Sign"
            },
            {
                "id": 1,
                "label": "THANK_YOU",
                "display": "Thank you.",
                "gloss": "Thank You",
                "desc": "Flat hand chin to forward-downward arc with slight nod.",
                "is_trained": True,
                "status": "PRODUCTION_VERIFIED",
                "ui_badge": "Live Supported Sign"
            },
            {
                "id": 2,
                "label": "YOURE_WELCOME",
                "display": "You're welcome.",
                "gloss": "You're Welcome",
                "desc": "Two open palms inward sweep toward torso.",
                "is_trained": True,
                "status": "PRODUCTION_VERIFIED",
                "ui_badge": "Live Supported Sign"
            },
            {
                "id": 3,
                "label": "PLEASE",
                "display": "Please.",
                "gloss": "Please",
                "desc": "Flat palm clockwise circular motion on sternum.",
                "is_trained": True,
                "status": "PRODUCTION_VERIFIED",
                "ui_badge": "Live Supported Sign"
            },
            {
                "id": 5,
                "label": "YES",
                "display": "Yes.",
                "gloss": "Yes / Affirmative",
                "desc": "Closed fist vertical nodding at wrist.",
                "is_trained": True,
                "status": "PRODUCTION_VERIFIED",
                "ui_badge": "Live Supported Sign"
            },
            {
                "id": 6,
                "label": "NO",
                "display": "No.",
                "gloss": "No / Negative",
                "desc": "Extended index finger horizontal oscillating wag.",
                "is_trained": True,
                "status": "PRODUCTION_VERIFIED",
                "ui_badge": "Live Supported Sign"
            },
            {
                "id": 7,
                "label": "OKAY",
                "display": "Okay.",
                "gloss": "Okay / Confirmed",
                "desc": "Index and thumb 'O' contact with forward double tap.",
                "is_trained": True,
                "status": "PRODUCTION_VERIFIED",
                "ui_badge": "Live Supported Sign"
            },
            {
                "id": 9,
                "label": "I_DONT_UNDERSTAND",
                "display": "I don't understand.",
                "gloss": "Don't Understand",
                "desc": "Temple tap transitioning to outward sweep with head shake.",
                "is_trained": True,
                "status": "PRODUCTION_VERIFIED",
                "ui_badge": "Live Supported Sign"
            }
        ]
    },
    "emergency_medical": {
        "title": "🚨 Emergency & Healthcare",
        "description": "Urgent assistance indicators, pain concepts, and public safety.",
        "expressions": [
            {
                "id": 4,
                "label": "I_NEED_HELP",
                "display": "I need help.",
                "gloss": "Need Assistance",
                "desc": "Dominant fist on non-dominant palm lifting toward chest.",
                "is_trained": True,
                "status": "PRODUCTION_VERIFIED",
                "ui_badge": "Live Supported Sign"
            },
            {
                "id": 8,
                "label": "STOP",
                "display": "Stop.",
                "gloss": "Stop / Halt",
                "desc": "Open palm forward projection with abrupt deceleration.",
                "is_trained": True,
                "status": "PRODUCTION_VERIFIED",
                "ui_badge": "Live Supported Sign"
            },
            {
                "id": 13,
                "label": "PAIN",
                "display": "I am in pain.",
                "gloss": "Physical Pain",
                "desc": "Opposing index fingers twisting at site of pain with facial grimace.",
                "is_trained": False,
                "status": "PENDING_DEAF_COMMUNITY_REVIEW",
                "ui_badge": "In Validation Pipeline"
            },
            {
                "id": 14,
                "label": "DOCTOR",
                "display": "I need a doctor.",
                "gloss": "Medical Doctor",
                "desc": "Checking pulse double tap on radial wrist.",
                "is_trained": False,
                "status": "PENDING_DEAF_COMMUNITY_REVIEW",
                "ui_badge": "In Validation Pipeline"
            }
        ]
    },
    "daily_needs": {
        "title": "🍞 Daily Needs & Sustenance",
        "description": "Food, hydration, physical comfort, and sustenance.",
        "expressions": [
            {
                "id": 10,
                "label": "WATER",
                "display": "Water, please.",
                "gloss": "Drinking Water",
                "desc": "Tapping or tilting cup handshape toward mouth twice.",
                "is_trained": False,
                "status": "PENDING_DEAF_COMMUNITY_REVIEW",
                "ui_badge": "In Validation Pipeline"
            },
            {
                "id": 11,
                "label": "FOOD",
                "display": "I am hungry / Food.",
                "gloss": "Food / Meal",
                "desc": "Flattened 'O' handshape tapping mouth twice.",
                "is_trained": False,
                "status": "PENDING_DEAF_COMMUNITY_REVIEW",
                "ui_badge": "In Validation Pipeline"
            },
            {
                "id": 12,
                "label": "RESTROOM",
                "display": "Restroom / Washroom.",
                "gloss": "Restroom",
                "desc": "Side-to-side wrist shaking with 'T' handshape.",
                "is_trained": False,
                "status": "PENDING_DEAF_COMMUNITY_REVIEW",
                "ui_badge": "In Validation Pipeline"
            },
            {
                "id": 15,
                "label": "WAIT",
                "display": "Please wait a moment.",
                "gloss": "Wait / Hold on",
                "desc": "Open palm settling downward with 'one moment' index cue.",
                "is_trained": False,
                "status": "PENDING_DEAF_COMMUNITY_REVIEW",
                "ui_badge": "In Validation Pipeline"
            },
            {
                "id": 16,
                "label": "REPEAT_SLOW",
                "display": "Please repeat / Sign slowly.",
                "gloss": "Repeat / Slow",
                "desc": "Deliberate downward motion asking for slow repetition.",
                "is_trained": False,
                "status": "PENDING_DEAF_COMMUNITY_REVIEW",
                "ui_badge": "In Validation Pipeline"
            }
        ]
    },
    "questions_navigation": {
        "title": "❓ Questions & Inquiries",
        "description": "Asking for directions, identity, or clarification.",
        "expressions": [
            {
                "id": 20,
                "label": "WHERE",
                "display": "Where?",
                "gloss": "Where is it?",
                "desc": "Index finger extended upright oscillating left and right.",
                "is_trained": False,
                "status": "PENDING_DEAF_COMMUNITY_REVIEW",
                "ui_badge": "In Validation Pipeline"
            },
            {
                "id": 21,
                "label": "WHAT",
                "display": "What?",
                "gloss": "What is this?",
                "desc": "Both open palms facing up shaking side to side.",
                "is_trained": False,
                "status": "PENDING_DEAF_COMMUNITY_REVIEW",
                "ui_badge": "In Validation Pipeline"
            },
            {
                "id": 22,
                "label": "WHEN",
                "display": "When?",
                "gloss": "When?",
                "desc": "Dominant index finger circling non-dominant index finger tip.",
                "is_trained": False,
                "status": "PENDING_DEAF_COMMUNITY_REVIEW",
                "ui_badge": "In Validation Pipeline"
            },
            {
                "id": 23,
                "label": "WHO",
                "display": "Who?",
                "gloss": "Who is that?",
                "desc": "Index finger circling around mouth with puckered lips.",
                "is_trained": False,
                "status": "PENDING_DEAF_COMMUNITY_REVIEW",
                "ui_badge": "In Validation Pipeline"
            }
        ]
    }
}


def get_all_categories() -> Dict[str, Any]:
    """Returns all communicative domains with expression counts and validation transparency."""
    total_expressions = sum(len(cat["expressions"]) for cat in EXPANDED_VOCABULARY.values())
    production_count = sum(
        sum(1 for e in cat["expressions"] if e.get("is_trained"))
        for cat in EXPANDED_VOCABULARY.values()
    )
    candidate_count = total_expressions - production_count

    return {
        "total_categories": len(EXPANDED_VOCABULARY),
        "total_expressions": total_expressions,
        "production_count": production_count,
        "candidate_count": candidate_count,
        "categories": EXPANDED_VOCABULARY,
        "candidate_expansion": CANDIDATE_BDSL_EXPANSION
    }
