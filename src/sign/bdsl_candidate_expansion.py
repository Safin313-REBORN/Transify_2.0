"""
Transify — Bangladesh Sign Language (BdSL) Candidate Vocabulary Expansion Framework.
Strictly separates verified, trained 10-class BdSL expressions from candidate concepts
pending Deaf community review, authentic field recording, and LSO verification.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class BdSLClassDefinition:
    class_id: int
    label: str
    english_meaning: str
    bangla_gloss: str
    phonology_description: str
    status: str  # 'PRODUCTION_VERIFIED' or 'PENDING_DEAF_COMMUNITY_REVIEW'
    is_trained: bool
    sample_count: int
    signer_count: int
    license: str
    advisor_review_id: Optional[str] = None


# The 10 Verified Production Classes in Transify 2.0 (Models: bdsl_champion_model.pkl)
VERIFIED_BDSL_CLASSES: Dict[int, BdSLClassDefinition] = {
    0: BdSLClassDefinition(
        class_id=0,
        label="HELLO",
        english_meaning="Hello / Greetings",
        bangla_gloss="হ্যালো / শুভেচ্ছা",
        phonology_description="One-handed flat palm starts at temple; arc forward politely with slight bow.",
        status="PRODUCTION_VERIFIED",
        is_trained=True,
        sample_count=120,
        signer_count=8,
        license="CC BY 4.0 / Research Protocol Consent"
    ),
    1: BdSLClassDefinition(
        class_id=1,
        label="THANK_YOU",
        english_meaning="Thank you.",
        bangla_gloss="ধন্যবাদ",
        phonology_description="Flat fingertips touch chin/lower lip; extend outward toward camera with a slight head bow.",
        status="PRODUCTION_VERIFIED",
        is_trained=True,
        sample_count=120,
        signer_count=8,
        license="CC BY 4.0 / Research Protocol Consent"
    ),
    2: BdSLClassDefinition(
        class_id=2,
        label="YOURE_WELCOME",
        english_meaning="You're welcome.",
        bangla_gloss="স্বাগতম / কিছু না",
        phonology_description="Both open palms face up at waist/chest; sweep inward warmly toward torso.",
        status="PRODUCTION_VERIFIED",
        is_trained=True,
        sample_count=120,
        signer_count=8,
        license="CC BY 4.0 / Research Protocol Consent"
    ),
    3: BdSLClassDefinition(
        class_id=3,
        label="PLEASE",
        english_meaning="Please.",
        bangla_gloss="দয়া করে",
        phonology_description="Flat palm clockwise circular motion on center of sternum.",
        status="PRODUCTION_VERIFIED",
        is_trained=True,
        sample_count=120,
        signer_count=8,
        license="CC BY 4.0 / Research Protocol Consent"
    ),
    4: BdSLClassDefinition(
        class_id=4,
        label="I_NEED_HELP",
        english_meaning="I need help.",
        bangla_gloss="আমার সাহায্য প্রয়োজন",
        phonology_description="Left palm flat facing up; right fist placed on left palm; both lift together upward/inward toward chest.",
        status="PRODUCTION_VERIFIED",
        is_trained=True,
        sample_count=120,
        signer_count=8,
        license="CC BY 4.0 / Research Protocol Consent"
    ),
    5: BdSLClassDefinition(
        class_id=5,
        label="YES",
        english_meaning="Yes / Affirmative.",
        bangla_gloss="হ্যাঁ",
        phonology_description="Closed fist at mid-chest; nod fist vertically from wrist twice like a nodding head.",
        status="PRODUCTION_VERIFIED",
        is_trained=True,
        sample_count=120,
        signer_count=8,
        license="CC BY 4.0 / Research Protocol Consent"
    ),
    6: BdSLClassDefinition(
        class_id=6,
        label="NO",
        english_meaning="No / Negative.",
        bangla_gloss="না",
        phonology_description="Extended index finger at mid-chest; wave horizontally side-to-side twice with negative head shake.",
        status="PRODUCTION_VERIFIED",
        is_trained=True,
        sample_count=120,
        signer_count=8,
        license="CC BY 4.0 / Research Protocol Consent"
    ),
    7: BdSLClassDefinition(
        class_id=7,
        label="OKAY",
        english_meaning="Okay / Confirmed.",
        bangla_gloss="ঠিক আছে",
        phonology_description="Index and thumb touch forming 'O'; remaining 3 fingers extended upward; forward double tap.",
        status="PRODUCTION_VERIFIED",
        is_trained=True,
        sample_count=120,
        signer_count=8,
        license="CC BY 4.0 / Research Protocol Consent"
    ),
    8: BdSLClassDefinition(
        class_id=8,
        label="STOP",
        english_meaning="Stop / Halt.",
        bangla_gloss="থামো / বন্ধ",
        phonology_description="Open palm held forward firmly toward camera with fingers straight up; abrupt deceleration.",
        status="PRODUCTION_VERIFIED",
        is_trained=True,
        sample_count=120,
        signer_count=8,
        license="CC BY 4.0 / Research Protocol Consent"
    ),
    9: BdSLClassDefinition(
        class_id=9,
        label="I_DONT_UNDERSTAND",
        english_meaning="I don't understand.",
        bangla_gloss="বুঝি না",
        phonology_description="Index finger touches near temple; sweeps downward/outward turning palm up with puzzled furrowed brow.",
        status="PRODUCTION_VERIFIED",
        is_trained=True,
        sample_count=120,
        signer_count=8,
        license="CC BY 4.0 / Research Protocol Consent"
    )
}


# Proposed Bounded First Expansion (High-Utility Daily Needs & Healthcare)
# IMPORTANT: These are candidate concepts for community co-design, NOT trained model classes.
CANDIDATE_BDSL_EXPANSION: List[Dict[str, Any]] = [
    {
        "candidate_id": "BDSL_C10_WATER",
        "concept_en": "Water, please",
        "proposed_gloss_bn": "পানি / জল",
        "validation_status": "PENDING_DEAF_COMMUNITY_REVIEW",
        "advisor_review_id": "BD-DEAF-ADV-PENDING",
        "sign_phonology": {
            "handshape": "Loose 'W' or open cup handshape",
            "location": "Near mouth / chin",
            "movement": "Tapping or tilting toward mouth twice",
            "non_manual_cues": "Polite eye contact"
        },
        "dialect_notes": "Both Islamic tradition ('Pani') and regional lexical variations noted.",
        "data_collection_target": "120 trials across 8 native signers (15 trials/signer)",
        "is_trained": False,
        "readiness_stage": "Stage 1: Community Review & Phonology Formalization",
        "ui_display_note": "Coming after Deaf community validation & ethical field recording"
    },
    {
        "candidate_id": "BDSL_C11_FOOD",
        "concept_en": "Food / Hungry",
        "proposed_gloss_bn": "খাবার / ক্ষুধা",
        "validation_status": "PENDING_DEAF_COMMUNITY_REVIEW",
        "advisor_review_id": "BD-DEAF-ADV-PENDING",
        "sign_phonology": {
            "handshape": "Flattened O handshape (fingertips touching thumb)",
            "location": "Mouth",
            "movement": "Repetitive feeding motion toward mouth",
            "non_manual_cues": "Slight inward head tilt"
        },
        "dialect_notes": "Standard across Dhaka and divisional deaf schools.",
        "data_collection_target": "120 trials across 8 native signers",
        "is_trained": False,
        "readiness_stage": "Stage 1: Community Review & Phonology Formalization",
        "ui_display_note": "Coming after Deaf community validation & ethical field recording"
    },
    {
        "candidate_id": "BDSL_C12_RESTROOM",
        "concept_en": "Restroom / Washroom",
        "proposed_gloss_bn": "টয়লেট / শৌচাগার",
        "validation_status": "PENDING_DEAF_COMMUNITY_REVIEW",
        "advisor_review_id": "BD-DEAF-ADV-PENDING",
        "sign_phonology": {
            "handshape": "'T' handshape or manual toilet indicator",
            "location": "Chest level",
            "movement": "Side-to-side wrist shaking",
            "non_manual_cues": "Urgent or questioning facial expression"
        },
        "dialect_notes": "Distinguish between school-taught BdSL sign and informal regional variants.",
        "data_collection_target": "120 trials across 8 native signers",
        "is_trained": False,
        "readiness_stage": "Stage 1: Community Review & Phonology Formalization",
        "ui_display_note": "Coming after Deaf community validation & ethical field recording"
    },
    {
        "candidate_id": "BDSL_C13_PAIN",
        "concept_en": "I am in pain",
        "proposed_gloss_bn": "ব্যথা / যন্ত্রণা",
        "validation_status": "PENDING_DEAF_COMMUNITY_REVIEW",
        "advisor_review_id": "BD-DEAF-ADV-PENDING",
        "sign_phonology": {
            "handshape": "Index fingers extended pointing at site of pain or twisting",
            "location": "Body site of discomfort / chest",
            "movement": "Opposing twisting motion of index fingertips",
            "non_manual_cues": "Grimace, furrowed brow, closed eyes"
        },
        "dialect_notes": "Crucial healthcare indicator. High-risk classification requiring explicit human confirmation.",
        "data_collection_target": "120 trials across 8 native signers",
        "is_trained": False,
        "readiness_stage": "Stage 1: Community Review & Phonology Formalization",
        "ui_display_note": "Coming after Deaf community validation & ethical field recording"
    },
    {
        "candidate_id": "BDSL_C14_DOCTOR",
        "concept_en": "Doctor / Medical help",
        "proposed_gloss_bn": "ডাক্তার / চিকিৎসক",
        "validation_status": "PENDING_DEAF_COMMUNITY_REVIEW",
        "advisor_review_id": "BD-DEAF-ADV-PENDING",
        "sign_phonology": {
            "handshape": "Three fingers (M) or index/middle tapping radial artery",
            "location": "Non-dominant inner wrist",
            "movement": "Checking pulse double tap",
            "non_manual_cues": "Attentive inquiry"
        },
        "dialect_notes": "Universal across medical BdSL glossaries.",
        "data_collection_target": "120 trials across 8 native signers",
        "is_trained": False,
        "readiness_stage": "Stage 1: Community Review & Phonology Formalization",
        "ui_display_note": "Coming after Deaf community validation & ethical field recording"
    },
    {
        "candidate_id": "BDSL_C15_WAIT",
        "concept_en": "Please wait / Hold on",
        "proposed_gloss_bn": "অপেক্ষা করুন / একটু থামুন",
        "validation_status": "PENDING_DEAF_COMMUNITY_REVIEW",
        "advisor_review_id": "BD-DEAF-ADV-PENDING",
        "sign_phonology": {
            "handshape": "Open palm facing down or outward at chest level",
            "location": "Chest level",
            "movement": "Gentle downward settling motion with index finger indicating 'one moment'",
            "non_manual_cues": "Reassuring eye contact"
        },
        "dialect_notes": "Everyday polite conversational turn-taking sign.",
        "data_collection_target": "120 trials across 8 native signers",
        "is_trained": False,
        "readiness_stage": "Stage 1: Community Review & Phonology Formalization",
        "ui_display_note": "Coming after Deaf community validation & ethical field recording"
    },
    {
        "candidate_id": "BDSL_C16_REPEAT_SLOW",
        "concept_en": "Please repeat / Sign slowly",
        "proposed_gloss_bn": "ধীরে বলুন / আবার বলুন",
        "validation_status": "PENDING_DEAF_COMMUNITY_REVIEW",
        "advisor_review_id": "BD-DEAF-ADV-PENDING",
        "sign_phonology": {
            "handshape": "Cupped hand circling or flat palm moving slowly downward",
            "location": "Chest level in front of signer",
            "movement": "Deliberate slow downward stroke or repeated circular arc",
            "non_manual_cues": "Puzzled or encouraging expression"
        },
        "dialect_notes": "Essential assistive accommodation sign for learners and deaf-hearing dialogue.",
        "data_collection_target": "120 trials across 8 native signers",
        "is_trained": False,
        "readiness_stage": "Stage 1: Community Review & Phonology Formalization",
        "ui_display_note": "Coming after Deaf community validation & ethical field recording"
    }
]


def get_bdsl_registry_summary() -> Dict[str, Any]:
    """
    Returns transparent audit summary distinguishing production-verified classes
    from candidate expansion concepts.
    """
    return {
        "production_classes_count": len(VERIFIED_BDSL_CLASSES),
        "production_classes": [asdict(c) for c in VERIFIED_BDSL_CLASSES.values()],
        "candidate_expansion_count": len(CANDIDATE_BDSL_EXPANSION),
        "candidate_expansion": CANDIDATE_BDSL_EXPANSION,
        "training_integrity_rule": "Candidate concepts cannot be inferred by the neural network until field dataset collection (N=120/class across 8 signers) and LSO cross-validation pass."
    }
