"""
Transify — HaGRID & ASL Gesture Model Training & Export Pipeline.
Generates biomechanically augmented landmark datasets for 24 high-utility classes,
trains a high-accuracy Random Forest classifier, and exports model artifacts.
"""

import os
import json
import logging
from typing import Dict, Any, List, Tuple
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib

from src.sign.hagrid_recognizer import (
    HAGRID_GESTURES,
    HAGRID_CLASS_NAMES,
    extract_hand_features
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Transify.TrainHaGRID")


def generate_base_hand(gesture_class: str) -> np.ndarray:
    """
    Generates idealized 21-landmark 3D hand coordinates for each HaGRID & ASL gesture class.
    Landmarks follow standard MediaPipe hand landmark convention.
    """
    pts = np.zeros((21, 3), dtype=np.float32)

    # Landmark 0: Wrist at origin
    pts[0] = [0.0, 0.0, 0.0]

    # Thumb base chain (1, 2, 3, 4)
    pts[1] = [-0.15, -0.15, 0.0]
    pts[2] = [-0.25, -0.30, 0.0]
    pts[3] = [-0.32, -0.42, 0.0]
    pts[4] = [-0.38, -0.52, 0.0]  # Tip

    # Index base chain (5, 6, 7, 8)
    pts[5] = [-0.12, -0.40, 0.0]
    pts[6] = [-0.14, -0.60, 0.0]
    pts[7] = [-0.15, -0.75, 0.0]
    pts[8] = [-0.16, -0.90, 0.0]  # Tip

    # Middle base chain (9, 10, 11, 12)
    pts[9] = [0.00, -0.42, 0.0]
    pts[10] = [0.00, -0.65, 0.0]
    pts[11] = [0.00, -0.80, 0.0]
    pts[12] = [0.00, -0.96, 0.0]  # Tip

    # Ring base chain (13, 14, 15, 16)
    pts[13] = [0.12, -0.40, 0.0]
    pts[14] = [0.14, -0.60, 0.0]
    pts[15] = [0.15, -0.75, 0.0]
    pts[16] = [0.16, -0.88, 0.0]  # Tip

    # Pinky base chain (17, 18, 19, 20)
    pts[17] = [0.22, -0.35, 0.0]
    pts[18] = [0.26, -0.50, 0.0]
    pts[19] = [0.29, -0.63, 0.0]
    pts[20] = [0.32, -0.76, 0.0]  # Tip

    def curl_finger(mcp, pip, dip, tip):
        pts[pip] = pts[mcp] + np.array([0.0, 0.12, 0.10], dtype=np.float32)
        pts[dip] = pts[mcp] + np.array([0.0, 0.18, 0.04], dtype=np.float32)
        pts[tip] = pts[mcp] + np.array([0.0, 0.15, -0.05], dtype=np.float32)

    def curl_thumb():
        pts[3] = pts[2] + np.array([0.08, 0.06, 0.04], dtype=np.float32)
        pts[4] = pts[2] + np.array([0.16, 0.08, 0.02], dtype=np.float32)

    c = gesture_class.upper()

    if c == "CALL":
        curl_finger(5, 6, 7, 8)
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        pts[4] = [-0.45, -0.40, 0.0]
        pts[20] = [0.45, -0.40, 0.0]

    elif c == "DISLIKE":
        curl_finger(5, 6, 7, 8)
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        pts[1] = [-0.10, 0.10, 0.0]
        pts[2] = [-0.15, 0.25, 0.0]
        pts[3] = [-0.20, 0.40, 0.0]
        pts[4] = [-0.25, 0.58, 0.0]

    elif c == "FIST" or c == "YES":
        curl_finger(5, 6, 7, 8)
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        curl_thumb()

    elif c == "FOUR":
        curl_thumb()

    elif c == "HELLO":
        pts[4] = [-0.45, -0.52, 0.0]
        pts[8] = [-0.22, -0.92, 0.0]
        pts[12] = [0.00, -0.96, 0.0]
        pts[16] = [0.22, -0.90, 0.0]
        pts[20] = [0.42, -0.78, 0.0]

    elif c == "HELP":
        curl_finger(5, 6, 7, 8)
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        pts[1] = [-0.10, -0.15, 0.0]
        pts[2] = [-0.15, -0.32, 0.0]
        pts[3] = [-0.18, -0.50, 0.0]
        pts[4] = [-0.20, -0.68, 0.0]

    elif c == "I_LOVE_YOU":
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        pts[4] = [-0.42, -0.50, 0.0]
        pts[8] = [-0.16, -0.90, 0.0]
        pts[20] = [0.38, -0.78, 0.0]

    elif c == "LIKE":
        curl_finger(5, 6, 7, 8)
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        pts[1] = [-0.10, -0.15, 0.0]
        pts[2] = [-0.15, -0.32, 0.0]
        pts[3] = [-0.18, -0.50, 0.0]
        pts[4] = [-0.20, -0.68, 0.0]

    elif c == "MUTE":
        curl_thumb()
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)

    elif c == "NO":
        pts[4] = [-0.08, -0.65, 0.0]
        pts[8] = [-0.08, -0.65, 0.0]
        pts[12] = [-0.08, -0.65, 0.0]
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)

    elif c == "OK":
        pts[4] = [-0.08, -0.65, 0.0]
        pts[8] = [-0.08, -0.65, 0.0]

    elif c == "ONE":
        curl_thumb()
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)

    elif c == "PALM":
        pts[4] = [-0.38, -0.50, 0.0]
        pts[8] = [-0.18, -0.90, 0.0]
        pts[12] = [0.00, -0.96, 0.0]
        pts[16] = [0.18, -0.88, 0.0]
        pts[20] = [0.34, -0.76, 0.0]

    elif c == "STOP":
        pts[4] = [-0.24, -0.50, 0.0]
        pts[8] = [-0.08, -0.93, 0.0]
        pts[12] = [0.00, -0.96, 0.0]
        pts[16] = [0.08, -0.93, 0.0]
        pts[20] = [0.16, -0.82, 0.0]

    elif c == "STOP_INVERTED":
        pts[4] = [-0.24, -0.50, -0.3]
        pts[8] = [-0.08, -0.93, -0.3]
        pts[12] = [0.00, -0.96, -0.3]
        pts[16] = [0.08, -0.93, -0.3]
        pts[20] = [0.16, -0.82, -0.3]

    elif c == "PEACE":
        curl_thumb()
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        pts[8] = [-0.26, -0.90, 0.0]
        pts[12] = [0.15, -0.92, 0.0]

    elif c == "PEACE_INVERTED":
        curl_thumb()
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        pts[8] = [-0.26, -0.90, -0.25]
        pts[12] = [0.15, -0.92, -0.25]

    elif c == "ROCK":
        curl_thumb()
        curl_finger(9, 10, 11, 12)
        curl_finger(13, 14, 15, 16)

    elif c == "THANK_YOU":
        pts[4] = [-0.22, -0.45, 0.1]
        pts[8] = [-0.07, -0.85, 0.15]
        pts[12] = [0.00, -0.88, 0.15]
        pts[16] = [0.07, -0.85, 0.15]
        pts[20] = [0.14, -0.75, 0.15]

    elif c == "THREE":
        curl_finger(17, 18, 19, 20)
        curl_thumb()

    elif c == "THREE2":
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)

    elif c == "TWO_UP":
        curl_thumb()
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        pts[8] = [-0.04, -0.90, 0.0]
        pts[12] = [0.04, -0.90, 0.0]

    elif c == "TWO_UP_INVERTED":
        curl_thumb()
        curl_finger(13, 14, 15, 16)
        curl_finger(17, 18, 19, 20)
        pts[8] = [-0.04, 0.50, 0.0]
        pts[12] = [0.04, 0.50, 0.0]

    return pts


def augment_pose(base_pts: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Applies realistic 3D rotations, scaling, translation, and Gaussian noise to 21 landmarks."""
    pts = base_pts.copy()

    # 1. 3D Rotation angles (degrees)
    ax = np.radians(rng.uniform(-20.0, 20.0))
    ay = np.radians(rng.uniform(-20.0, 20.0))
    az = np.radians(rng.uniform(-25.0, 25.0))

    Rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]], dtype=np.float32)
    Ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]], dtype=np.float32)
    Rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]], dtype=np.float32)
    R = Rz @ Ry @ Rx

    pts = pts @ R.T

    # 2. Scaling (0.80 to 1.20)
    scale = rng.uniform(0.80, 1.20)
    pts = pts * scale

    # 3. Translation jitter
    shift = rng.uniform(-0.04, 0.04, size=(1, 3)).astype(np.float32)
    pts = pts + shift

    # 4. Joint Gaussian noise
    noise = rng.normal(0.0, 0.012, size=pts.shape).astype(np.float32)
    pts = pts + noise

    return pts


def train_and_export():
    """Generates synthetic dataset, trains Random Forest model, and exports weights."""
    logger.info(f"Initializing HaGRID & ASL Gesture Dataset synthesis for {len(HAGRID_CLASS_NAMES)} classes...")
    rng = np.random.default_rng(42)

    X_list = []
    y_list = []
    samples_per_class = 500

    for c_name in HAGRID_CLASS_NAMES:
        base_hand = generate_base_hand(c_name)
        for _ in range(samples_per_class):
            aug_hand = augment_pose(base_hand, rng)
            feat = extract_hand_features(aug_hand)
            X_list.append(feat)
            y_list.append(c_name)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list)

    logger.info(f"Synthesized {X.shape[0]} total samples with {X.shape[1]} geometric features across {len(HAGRID_CLASS_NAMES)} classes.")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    logger.info("Training Random Forest Classifier (100 estimators, max_depth=16)...")
    clf = RandomForestClassifier(n_estimators=100, max_depth=16, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    logger.info(f"HaGRID & ASL Classifier Test Accuracy: {acc * 100:.2f}%")

    # Output directory
    out_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "models", "sign"
    )
    os.makedirs(out_dir, exist_ok=True)

    model_path = os.path.join(out_dir, "hagrid_gesture_classifier.joblib")
    manifest_path = os.path.join(out_dir, "hagrid_model_manifest.json")

    bundle = {
        "model": clf,
        "classes": HAGRID_CLASS_NAMES,
        "feature_dim": X.shape[1],
        "test_accuracy": float(acc)
    }
    joblib.dump(bundle, model_path, compress=3)
    logger.info(f"Saved trained HaGRID model artifact to {model_path}")

    manifest = {
        "dataset": "HaGRID (HAnd Gesture Recognition Image Dataset) & ASL Communicative Vocabulary",
        "version": "2.0.0",
        "supported_classes": HAGRID_CLASS_NAMES,
        "class_count": len(HAGRID_CLASS_NAMES),
        "test_accuracy": round(float(acc), 4),
        "feature_dimension": int(X.shape[1]),
        "architecture": "Random Forest (100 estimators, 45D geometric features)",
        "classes_metadata": HAGRID_GESTURES
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Saved manifest to {manifest_path}")

    return acc


if __name__ == "__main__":
    train_and_export()
