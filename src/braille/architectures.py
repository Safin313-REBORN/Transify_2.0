"""
Model Architectures & 6-Subcell Relief Feature Engineering for Optical Braille Recognition.
Supports Multi-Output Random Forest, Deep MLP, and ExtraTrees classifiers.
"""

from typing import Tuple, Dict, Any, List, Optional
import cv2
import numpy as np
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

from src.braille.decoder import vector_to_unicode


def extract_subcell_features(patch: np.ndarray) -> np.ndarray:
    """
    Extracts 244 spatiotemporal tactile relief features from a 28x28 grayscale Braille cell patch.
    6 sub-regions (D1..D6) x 8 relief metrics = 48 domain features + 196 downsampled pixels.
    """
    if patch.shape != (28, 28):
        patch = cv2.resize(patch, (28, 28), interpolation=cv2.INTER_AREA)

    if patch.dtype != np.uint8:
        patch = np.clip(patch, 0, 255).astype(np.uint8)

    # 6 sub-region slices: [ymin:ymax, xmin:xmax]
    subregions = [
        patch[0:9, 0:14],    # D1 (top-left)
        patch[9:19, 0:14],   # D2 (mid-left)
        patch[19:28, 0:14],  # D3 (bot-left)
        patch[0:9, 14:28],   # D4 (top-right)
        patch[9:19, 14:28],  # D5 (mid-right)
        patch[19:28, 14:28], # D6 (bot-right)
    ]

    domain_features = []
    for r in subregions:
        r_float = r.astype(np.float32)
        mean_val = float(np.mean(r_float))
        std_val = float(np.std(r_float))
        range_val = float(np.max(r_float) - np.min(r_float))

        # Sobel gradients to capture directional raking light highlights
        sobel_x = cv2.Sobel(r, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(r, cv2.CV_64F, 0, 1, ksize=3)
        grad_x = float(np.mean(np.abs(sobel_x)))
        grad_y = float(np.mean(np.abs(sobel_y)))

        # Laplacian curvature
        lap = cv2.Laplacian(r, cv2.CV_64F)
        lap_var = float(lap.var())

        # Center-to-edge contrast
        h_r, w_r = r.shape
        cy, cx = h_r // 2, w_r // 2
        center_val = float(np.mean(r_float[max(0, cy-1):cy+2, max(0, cx-1):cx+2]))
        contrast_diff = float(center_val - mean_val)

        # Fraction of pixels exceeding local threshold
        thresh_pct = float(np.count_nonzero(r_float > (mean_val + 0.5 * std_val)) / r_float.size)

        domain_features.extend([
            mean_val,
            std_val,
            range_val,
            grad_x,
            grad_y,
            lap_var,
            contrast_diff,
            thresh_pct
        ])

    # 196 downsampled spatial pixels (14x14)
    downsampled = cv2.resize(patch, (14, 14), interpolation=cv2.INTER_AREA).flatten().astype(np.float32)

    features = np.hstack([np.array(domain_features, dtype=np.float32), downsampled])
    return features  # 48 + 196 = 244 dimensions


def build_candidate_model(model_type: str = "random_forest", random_state: int = 42) -> Any:
    """Builds and returns an uninitialized candidate model instance."""
    if model_type == "random_forest":
        return RandomForestClassifier(
            n_estimators=150,
            max_depth=14,
            min_samples_split=2,
            min_samples_leaf=1,
            max_features='sqrt',
            random_state=random_state,
            n_jobs=-1
        )
    elif model_type == "extra_trees":
        return ExtraTreesClassifier(
            n_estimators=150,
            max_depth=16,
            min_samples_split=2,
            random_state=random_state,
            n_jobs=-1
        )
    elif model_type == "mlp":
        return MLPClassifier(
            hidden_layer_sizes=(256, 128, 64),
            activation='relu',
            solver='adam',
            alpha=1e-4,
            batch_size=64,
            max_iter=300,
            early_stopping=True,
            n_iter_no_change=15,
            random_state=random_state
        )
    else:
        raise ValueError(f"Unknown model_type: {model_type}")


class BrailleClassifierWrapper:
    """
    Unified inference wrapper for trained multi-output 6-dot Braille classifiers.
    """

    def __init__(self, model: Any, scaler: Optional[StandardScaler] = None):
        self.model = model
        self.scaler = scaler

    def predict_patches(self, patches: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extracts features and predicts 6-dot states for a batch of patches.
        Returns:
            discrete_dots: (N, 6) in {0, 1}
            probabilities: (N, 6) in [0.0, 1.0]
            confidences: (N,) minimum dot confidence per cell
        """
        X = np.array([extract_subcell_features(p) for p in patches], dtype=np.float32)
        if self.scaler is not None:
            X = self.scaler.transform(X)

        if hasattr(self.model, "predict_proba"):
            # Multi-output Random Forest / ExtraTrees returns list of 6 arrays, each (N, 2)
            proba_list = self.model.predict_proba(X)
            if isinstance(proba_list, list) and len(proba_list) == 6:
                probs = np.column_stack([p[:, 1] if p.shape[1] > 1 else np.zeros(len(X)) for p in proba_list])
            elif isinstance(proba_list, np.ndarray) and proba_list.ndim == 2 and proba_list.shape[1] == 6:
                # MLP multi-label output
                probs = proba_list
            else:
                probs = self.model.predict(X).astype(np.float32)
        else:
            probs = self.model.predict(X).astype(np.float32)

        discrete_dots = (probs >= 0.5).astype(int)
        # Confidence is distance from 0.5 boundary: max(p, 1 - p)
        dot_confs = np.maximum(probs, 1.0 - probs)
        confidences = np.min(dot_confs, axis=1)

        return discrete_dots, probs, confidences

    def predict_single_patch(self, patch: np.ndarray) -> Dict[str, Any]:
        """Predicts single cell patch and formats results."""
        discrete, probs, confs = self.predict_patches([patch])
        dot_vec = tuple(int(x) for x in discrete[0])
        prob_vec = [round(float(p), 4) for p in probs[0]]
        conf = float(confs[0])
        unicode_glyph = vector_to_unicode(dot_vec)

        return {
            "dots": dot_vec,
            "probabilities": prob_vec,
            "confidence": round(conf, 4),
            "unicode_glyph": unicode_glyph
        }
