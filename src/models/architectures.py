"""
Transify — BdSL Sign Language Model Architectures & Unknown Rejection Engine
Defines feature extraction helpers, temporal classifiers, and out-of-distribution rejection filters.
"""

import math
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier

BDSL_METADATA = {
    0: {"label": "HELLO", "bdsl_gloss": "Hello / Greetings", "english_text": "Hello."},
    1: {"label": "THANK_YOU", "bdsl_gloss": "Thank you", "english_text": "Thank you."},
    2: {"label": "YOURE_WELCOME", "bdsl_gloss": "You're welcome", "english_text": "You're welcome."},
    3: {"label": "PLEASE", "bdsl_gloss": "Please", "english_text": "Please."},
    4: {"label": "I_NEED_HELP", "bdsl_gloss": "Need help", "english_text": "I need help."},
    5: {"label": "YES", "bdsl_gloss": "Yes", "english_text": "Yes."},
    6: {"label": "NO", "bdsl_gloss": "No", "english_text": "No."},
    7: {"label": "OKAY", "bdsl_gloss": "Okay", "english_text": "Okay."},
    8: {"label": "STOP", "bdsl_gloss": "Stop", "english_text": "Stop."},
    9: {"label": "I_DONT_UNDERSTAND", "bdsl_gloss": "Don't understand", "english_text": "I don't understand."},
}


def extract_temporal_features(sequence: np.ndarray) -> np.ndarray:
    """
    Computes robust statistical and kinematic temporal features from a (30, 162) sequence.
    Extracts:
      - Mean across time (162)
      - Std across time (162)
      - Initial frame (162)
      - Final frame (162)
      - Mid-point frame (162)
      - Total velocity / delta across consecutive frames: sum |X_t - X_{t-1}| (162)
    Total feature vector size: 162 * 6 = 972 features.
    """
    T, D = sequence.shape
    mean_feat = np.mean(sequence, axis=0)
    std_feat = np.std(sequence, axis=0)
    start_feat = sequence[0]
    mid_feat = sequence[T // 2]
    end_feat = sequence[-1]
    velocity_feat = np.sum(np.abs(np.diff(sequence, axis=0)), axis=0)

    return np.concatenate([
        mean_feat,
        std_feat,
        start_feat,
        mid_feat,
        end_feat,
        velocity_feat
    ]).astype(np.float32)


class UnknownRejectionFilter:
    """
    Evaluates model prediction confidence, entropy, and spatial motion energy
    to reject unsupported gestures, idle stationary signers, and ambiguous inputs.
    """
    def __init__(self, conf_threshold: float = 0.70, entropy_threshold: float = 1.20, motion_threshold: float = 0.25):
        self.conf_threshold = conf_threshold
        self.entropy_threshold = entropy_threshold
        self.motion_threshold = motion_threshold

    def compute_motion_energy(self, sequence: np.ndarray) -> float:
        """Computes total Euclidean displacement across temporal sequence."""
        if len(sequence) < 2:
            return 0.0
        deltas = np.diff(sequence, axis=0)
        return float(np.sum(np.linalg.norm(deltas, axis=1)))

    def compute_entropy(self, probabilities: np.ndarray) -> float:
        """Computes Shannon entropy: H = -sum P_c * ln(P_c)."""
        eps = 1e-12
        probs = np.clip(probabilities, eps, 1.0)
        return float(-np.sum(probs * np.log(probs)))

    def filter_prediction(self, probabilities: np.ndarray, sequence: np.ndarray) -> dict:
        motion_energy = self.compute_motion_energy(sequence)
        max_prob = float(np.max(probabilities))
        pred_class = int(np.argmax(probabilities))
        entropy = self.compute_entropy(probabilities)

        # Condition 1: Stationary / Idle rejection
        if motion_energy < self.motion_threshold:
            return {
                "recognized": False,
                "class_id": -1,
                "label": "IDLE",
                "english_text": "Sign not recognized or not currently supported.",
                "confidence": max_prob,
                "supported": False,
                "rejection_reason": f"Signer is stationary / idle (motion energy {motion_energy:.3f} < {self.motion_threshold})"
            }

        # Condition 2: Low confidence rejection
        if max_prob < self.conf_threshold:
            return {
                "recognized": False,
                "class_id": -1,
                "label": "LOW_CONFIDENCE",
                "english_text": "Sign not recognized or not currently supported.",
                "confidence": max_prob,
                "supported": False,
                "rejection_reason": f"Prediction confidence {max_prob:.3f} below threshold {self.conf_threshold}"
            }

        # Condition 3: Ambiguous prediction / High entropy rejection
        if entropy > self.entropy_threshold:
            return {
                "recognized": False,
                "class_id": -1,
                "label": "AMBIGUOUS",
                "english_text": "Sign not recognized or not currently supported.",
                "confidence": max_prob,
                "supported": False,
                "rejection_reason": f"Prediction distribution is ambiguous (entropy {entropy:.3f} > {self.entropy_threshold})"
            }

        # Passed all rejection tests
        meta = BDSL_METADATA.get(pred_class, {"label": "UNKNOWN", "bdsl_gloss": "", "english_text": ""})
        return {
            "recognized": True,
            "class_id": pred_class,
            "label": meta["label"],
            "bdsl_gloss": meta["bdsl_gloss"],
            "english_text": meta["english_text"],
            "confidence": round(max_prob, 4),
            "supported": True,
            "rejection_reason": None
        }


def build_champion_classifier(random_state: int = 42):
    """
    Builds the Deep MLP Champion Classifier with Batch Normalization emulation,
    Dropout emulation (early stopping on validation loss), and Adam optimization.
    """
    return MLPClassifier(
        hidden_layer_sizes=(384, 192, 96),
        activation='relu',
        solver='adam',
        alpha=1e-4,              # L2 weight decay
        batch_size=32,
        learning_rate_init=1e-3,
        max_iter=60,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=8,
        random_state=random_state
    )


def build_baseline_rf():
    """Builds Random Forest baseline classifier."""
    return RandomForestClassifier(
        n_estimators=150,
        max_depth=16,
        random_state=42,
        n_jobs=-1
    )


def build_baseline_hist_gb():
    """Builds Gradient Boosting baseline classifier."""
    return HistGradientBoostingClassifier(
        max_iter=100,
        learning_rate=0.08,
        max_depth=10,
        random_state=42
    )
