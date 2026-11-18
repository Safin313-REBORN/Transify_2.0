"""
Sign Language Recognition Adapter for Transify API.
Powered by SignFrame AI (PyTorch CNN & Vectorized NumPy engine) trained on ASL Fingerspelling,
combined with MediaPipe Hand Landmark Tracking, 12-frame Prediction Stabilization,
and 98% Decision Gateway with MCP / ChatGPT fallback disambiguation.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np

logger = logging.getLogger("transify.sign_adapter")

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.sign.signframe_model import (
    SIGN_CLASSES,
    INDEX_TO_LETTER,
    LETTER_TO_INDEX,
    VALID_LABELS
)
from src.sign.signframe_pipeline import (
    SignPredictor,
    PredictionStabilizer,
    TextComposer,
    HandTracker,
    preprocess_hand,
    get_hand_bbox
)
from src.sign.mcp_sign_resolver import MCPSignResolver

# Backward compatible expression vocabulary mapping
BDSL_CLASSES: Dict[int, Dict[str, str]] = {
    0: {"label": "HELLO", "display": "Hello!", "gloss": "Hello / Greetings", "desc": "One-handed temple forward arc with slight bow."},
    1: {"label": "THANK_YOU", "display": "Thank you.", "gloss": "Thank You", "desc": "Flat hand chin to forward-downward arc with slight nod."},
    2: {"label": "YOURE_WELCOME", "display": "You're welcome.", "gloss": "You're Welcome", "desc": "Two open palms inward sweep toward torso."},
    3: {"label": "PLEASE", "display": "Please.", "gloss": "Please", "desc": "Flat palm clockwise circular motion on sternum."},
    4: {"label": "I_NEED_HELP", "display": "I need help.", "gloss": "I Need Help", "desc": "Dominant fist on non-dominant palm lifting toward chest."},
    5: {"label": "YES", "display": "Yes.", "gloss": "Yes / Affirmative", "desc": "Closed fist vertical nodding at wrist."},
    6: {"label": "NO", "display": "No.", "gloss": "No / Negative", "desc": "Extended index finger horizontal oscillating wag."},
    7: {"label": "OKAY", "display": "Okay.", "gloss": "Okay / Understood", "desc": "Index and thumb 'O' contact with forward double tap."},
    8: {"label": "STOP", "display": "Stop.", "gloss": "Stop / Halt", "desc": "Open palm forward projection with abrupt deceleration."},
    9: {"label": "I_DONT_UNDERSTAND", "display": "I don't understand.", "gloss": "I Don't Understand", "desc": "Temple tap transitioning to outward sweep with head shake."}
}


class SignLanguageAdapter:
    """
    Adapter bridging client landmark streams and webcam frames to SignFrame AI.
    Features:
      - SignFrame AI CNN (PyTorch / sub-millisecond NumPy)
      - 98% Decision Gateway (Custom Model if >= 0.98, MCP fallback if < 0.98)
      - Prediction Stabilization (Debounce consensus)
      - OOD / Idle rejection
    """

    def __init__(self, debounce_window: int = 5):
        self.init_error = None
        self.predictor = None
        self.model = None
        try:
            self.predictor = SignPredictor()
            self.model = self.predictor.torch_model if self.predictor.torch_model is not None else self.predictor.numpy_model
            logger.info(f"SignPredictor successfully initialized. Active backend: {type(self.model).__name__ if self.model else 'None'}")
        except Exception as e:
            self.init_error = str(e)
            logger.error(f"Failed to initialize SignPredictor: {e}", exc_info=True)

        self.stabilizer = PredictionStabilizer(window_size=12, required_votes=9, confidence_threshold=0.65)
        self.composer = TextComposer()
        self.mcp_resolver = MCPSignResolver()
        self.debounce_window = debounce_window
        self.history_buffer: List[int] = []

        # Load trained temporal sequence model and feature scaler for (T x 162) sequence inputs
        self.temporal_model = None
        self.temporal_scaler = None
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            t_model_p = os.path.join(project_root, "models/sign/bdsl_champion_model.pkl")
            t_scaler_p = os.path.join(project_root, "models/sign/scaler.pkl")
            if os.path.exists(t_model_p) and os.path.exists(t_scaler_p):
                import pickle
                with open(t_model_p, "rb") as f:
                    self.temporal_model = pickle.load(f)
                with open(t_scaler_p, "rb") as f:
                    self.temporal_scaler = pickle.load(f)
                logger.info("Loaded temporal sign model and scaler.")
        except Exception as e:
            logger.warning(f"Could not load temporal sign model: {e}")
            self.temporal_model = None
            self.temporal_scaler = None

    def reset_buffer(self):
        """Resets the debounce state buffer and stabilizer."""
        self.history_buffer.clear()
        self.stabilizer.reset()
        self.composer.clear()

    def predict_image_crop(self, crop_28x28: np.ndarray) -> Dict[str, Any]:
        """
        Runs SignFrame AI CNN prediction directly on a 28x28 normalized image tensor.
        """
        letter, raw_conf, probs = self.predictor.predict(crop_28x28)

        # Apply 98% Decision Gateway
        if not self.mcp_resolver.is_low_confidence(raw_conf):
            engine_info = {
                "engine": "LOCAL_CUSTOM_MODEL",
                "source": "SignFrame AI Custom Model (>= 98% Confidence)",
                "is_fallback": False,
                "confidence": raw_conf,
                "threshold": self.mcp_resolver.threshold,
                "badge": "SignFrame AI Model (>= 98%)",
                "notes": f"High confidence recognition ({raw_conf * 100:.1f}%) handled directly by SignFrame CNN."
            }
            final_letter = letter
            final_conf = raw_conf
            resolver_assisted = False
        else:
            top_3 = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)[:3]
            top_candidates = [{"label": k, "confidence": v} for k, v in top_3]
            mcp_res = self.mcp_resolver.resolve(
                candidate_label=letter,
                confidence=raw_conf,
                top_candidates=top_candidates,
                motion_energy=0.1
            )
            final_letter = mcp_res.get("label", letter)
            mcp_conf = mcp_res.get("confidence")
            final_conf = mcp_conf if mcp_conf is not None else raw_conf
            resolver_assisted = bool(mcp_res.get("resolver_assisted", True))
            engine_info = {
                "engine": mcp_res.get("engine", "MCP_SIGN_RESOLVER"),
                "source": mcp_res.get("source", "MCP Server / Chatbot"),
                "is_fallback": True,
                "confidence": mcp_conf,
                "threshold": self.mcp_resolver.threshold,
                "badge": mcp_res.get("badge", "MCP Resolver (< 98%)"),
                "notes": mcp_res.get("notes", f"SignFrame AI confidence was {raw_conf * 100:.1f}%. Shifted to MCP resolver."),
                "latency_ms": mcp_res.get("latency_ms", 3.0),
                "resolver_assisted": resolver_assisted
            }

        # Feed genuine raw_conf to stabilizer to prevent false debounce inflation
        stabilizer_conf = float(raw_conf) if raw_conf is not None else 0.0
        confirmed_letter, votes, req_votes = self.stabilizer.update(final_letter, stabilizer_conf)

        return {
            "letter": final_letter,
            "label": final_letter,
            "display_text": f"Letter {final_letter}",
            "confidence": round(final_conf, 4) if final_conf is not None else None,
            "raw_confidence": round(raw_conf, 4) if raw_conf is not None else None,
            "resolver_assisted": resolver_assisted,
            "status": "CONFIRMED" if confirmed_letter else "DEBOUNCING",
            "is_committed": bool(confirmed_letter),
            "is_confirmed": bool(confirmed_letter),
            "stable_letter": confirmed_letter,
            "consensus_progress": f"{votes}/{req_votes}",
            "engine_info": engine_info,
            "probabilities": probs
        }

    def predict_sequence(self, sequence_landmarks: np.ndarray, language_mode: str = "asl") -> Dict[str, Any]:
        """
        Predicts gesture from sequence of coordinates (T x 162).
        Supports language_mode: "asl" (American Sign) or legacy "bdsl".
        Includes idle/OOD motion rejection filter, 98% Decision Gateway, and debouncing.
        """
        if sequence_landmarks.ndim != 2 or sequence_landmarks.shape[1] != 162:
            raise ValueError(f"Expected sequence shape (T, 162), got {sequence_landmarks.shape}")

        active_lang = language_mode.strip().lower() if language_mode else "asl"
        if active_lang not in ("bdsl", "asl"):
            active_lang = "asl"

        model_name = "BdSL Recognition Model" if active_lang == "bdsl" else "ASL Model (SignFrame AI)"
        source_badge_prefix = "BdSL Model" if active_lang == "bdsl" else "ASL Model"

        # Check for idle / flat zero input
        motion_energy = float(np.std(sequence_landmarks))
        if motion_energy < 0.005 or np.all(sequence_landmarks == 0):
            self.history_buffer.clear()
            return {
                "class_id": -1,
                "label": "UNKNOWN",
                "display_text": f"Please hold {active_lang.upper()} gesture steady within camera view.",
                "gloss": "Unknown Gesture",
                "english_text": "",
                "confidence": 0.0,
                "status": "REJECTED",
                "rejection_reason": "Low motion energy / idle user posture.",
                "is_committed": False,
                "language_mode": active_lang,
                "model_name": model_name,
                "probabilities": {BDSL_CLASSES[i]["label"]: 0.0 for i in range(len(BDSL_CLASSES))}
            }

        # Perform genuine temporal inference if trained model is available
        if self.temporal_model is not None and self.temporal_scaler is not None:
            try:
                from src.models.architectures import extract_temporal_features
                feat = extract_temporal_features(sequence_landmarks).reshape(1, -1)
                feat_scaled = self.temporal_scaler.transform(feat)
                probs_arr = self.temporal_model.predict_proba(feat_scaled)[0]
                decision_id = int(np.argmax(probs_arr))
                raw_conf = float(probs_arr[decision_id])
                class_meta = BDSL_CLASSES.get(decision_id, BDSL_CLASSES[0])
                probs = {
                    BDSL_CLASSES[i]["label"]: round(float(probs_arr[i]), 4)
                    for i in range(len(probs_arr))
                    if i in BDSL_CLASSES
                }
                is_heuristic = False
            except Exception as e:
                logger.warning(f"Temporal inference error: {e}")
                decision_id = 0
                class_meta = BDSL_CLASSES[0]
                raw_conf = None
                probs = None
                is_heuristic = True
        else:
            # If no trained temporal model weights exist, do not fabricate probabilities
            decision_id = 0
            class_meta = BDSL_CLASSES[0]
            raw_conf = None
            probs = None
            is_heuristic = True

        # 98% Decision Gateway or Heuristic Fallback
        if is_heuristic:
            engine_info = {
                "engine": "HEURISTIC_FALLBACK",
                "source": f"{model_name} (Temporal Model Unavailable)",
                "is_fallback": True,
                "confidence": None,
                "threshold": self.mcp_resolver.threshold,
                "badge": "Heuristic Fallback",
                "notes": "Trained temporal model weights unavailable. Confidence is unavailable."
            }
            final_label = class_meta["label"]
            final_conf = None
            resolver_assisted = False
        elif not self.mcp_resolver.is_low_confidence(raw_conf):
            engine_info = {
                "engine": "LOCAL_CUSTOM_MODEL",
                "source": f"{model_name} (>= 98% Confidence)",
                "is_fallback": False,
                "confidence": raw_conf,
                "threshold": self.mcp_resolver.threshold,
                "badge": f"{source_badge_prefix} (>= 98%)",
                "notes": f"High confidence {active_lang.upper()} recognition ({raw_conf * 100:.1f}%) handled directly by custom model."
            }
            final_label = class_meta["label"]
            final_conf = raw_conf
            resolver_assisted = False
        else:
            top_candidates = [{"label": class_meta["label"], "confidence": raw_conf}]
            mcp_res = self.mcp_resolver.resolve(
                candidate_label=class_meta["label"],
                confidence=raw_conf,
                top_candidates=top_candidates,
                motion_energy=motion_energy,
                gloss_hint=class_meta["gloss"]
            )
            final_label = mcp_res.get("label", class_meta["label"])
            mcp_conf = mcp_res.get("confidence")
            final_conf = mcp_conf if mcp_conf is not None else raw_conf
            resolver_assisted = bool(mcp_res.get("resolver_assisted", True))
            engine_info = {
                "engine": mcp_res.get("engine", "MCP_SIGN_RESOLVER"),
                "source": mcp_res.get("source", "MCP Server / Chatbot"),
                "is_fallback": True,
                "confidence": mcp_conf,
                "threshold": self.mcp_resolver.threshold,
                "badge": mcp_res.get("badge", "MCP Fallback (< 98%)"),
                "notes": mcp_res.get("notes", f"{active_lang.upper()} confidence was {raw_conf * 100:.1f}%. Shifted to MCP."),
                "latency_ms": mcp_res.get("latency_ms", 3.0),
                "resolver_assisted": resolver_assisted
            }

        # Debounce buffer
        self.history_buffer.append(decision_id)
        if len(self.history_buffer) > self.debounce_window:
            self.history_buffer.pop(0)

        is_consensus = (
            len(self.history_buffer) == self.debounce_window and
            all(cid == decision_id for cid in self.history_buffer)
        )

        unified_translation = {
            "source_language": active_lang.upper(),
            "source_model": model_name,
            "recognized_concept": final_label,
            "english_text": class_meta["display"],
            "speech_ready": True
        }

        return {
            "class_id": decision_id,
            "label": final_label,
            "display_text": class_meta["display"],
            "gloss": class_meta["gloss"],
            "description": class_meta["desc"],
            "english_text": class_meta["display"],
            "unified_translation": unified_translation,
            "language_mode": active_lang,
            "model_name": model_name,
            "confidence": round(final_conf, 4) if final_conf is not None else None,
            "raw_confidence": round(raw_conf, 4) if raw_conf is not None else None,
            "resolver_assisted": resolver_assisted,
            "status": "HEURISTIC_FALLBACK" if is_heuristic else ("CONFIRMED" if is_consensus else "DEBOUNCING"),
            "is_committed": is_consensus and not is_heuristic,
            "engine_info": engine_info,
            "consensus_progress": f"{self.history_buffer.count(decision_id)}/{self.debounce_window}",
            "probabilities": probs
        }
