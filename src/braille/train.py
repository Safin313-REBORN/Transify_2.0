"""
Model Training & Model Selection Pipeline for Optical Braille Recognition.
Trains multi-output Random Forest, ExtraTrees, and Deep MLP architectures under strict anti-leakage splitting.
"""

import os
import sys
import time
import json
import pickle
from typing import Dict, Any, Tuple
import cv2
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.braille.architectures import (
    extract_subcell_features,
    build_candidate_model,
    BrailleClassifierWrapper
)

SPLITS_DIR = "data/braille/splits"
MODELS_DIR = "models/braille"
os.makedirs(MODELS_DIR, exist_ok=True)


def load_partition_data(csv_path: str) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Loads image patches and extracts 244D feature matrices for a given partition."""
    df = pd.read_csv(csv_path)
    X_list = []
    y_list = []

    for idx, row in df.iterrows():
        p_path = row["patch_path"]
        patch = cv2.imread(p_path, cv2.IMREAD_GRAYSCALE)
        if patch is None:
            raise FileNotFoundError(f"Missing patch: {p_path}")

        feats = extract_subcell_features(patch)
        targets = [row["d1"], row["d2"], row["d3"], row["d4"], row["d5"], row["d6"]]

        X_list.append(feats)
        y_list.append(targets)

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)
    return X, y, df


def evaluate_model_on_partition(wrapper: BrailleClassifierWrapper, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    """Computes exact cell match, per-dot accuracy, precision, recall, and Macro F1."""
    if wrapper.scaler is not None:
        X_scaled = wrapper.scaler.transform(X)
    else:
        X_scaled = X

    if hasattr(wrapper.model, "predict_proba"):
        proba_list = wrapper.model.predict_proba(X_scaled)
        if isinstance(proba_list, list) and len(proba_list) == 6:
            probs = np.column_stack([p[:, 1] if p.shape[1] > 1 else np.zeros(len(X)) for p in proba_list])
        elif isinstance(proba_list, np.ndarray) and proba_list.ndim == 2:
            probs = proba_list
        else:
            probs = wrapper.model.predict(X_scaled).astype(np.float32)
    else:
        probs = wrapper.model.predict(X_scaled).astype(np.float32)

    discrete_pred = (probs >= 0.5).astype(int)

    # 1. Exact 6-dot match accuracy
    exact_matches = np.all(discrete_pred == y, axis=1)
    exact_cell_acc = float(np.mean(exact_matches))

    # 2. Per-dot accuracy & F1
    per_dot_acc = []
    per_dot_f1 = []
    for d in range(6):
        acc = accuracy_score(y[:, d], discrete_pred[:, d])
        f1 = f1_score(y[:, d], discrete_pred[:, d], zero_division=0)
        per_dot_acc.append(float(acc))
        per_dot_f1.append(float(f1))

    mean_dot_acc = float(np.mean(per_dot_acc))
    macro_f1 = float(np.mean(per_dot_f1))

    return {
        "exact_cell_accuracy": round(exact_cell_acc, 4),
        "mean_dot_accuracy": round(mean_dot_acc, 4),
        "macro_f1": round(macro_f1, 4),
        "per_dot_accuracy": [round(a, 4) for a in per_dot_acc],
        "per_dot_f1": [round(f, 4) for f in per_dot_f1]
    }


def train_and_select_champion():
    print("=" * 70)
    print("TRANSIFY MODULE 02: BRAILLE MODEL TRAINING & COMPARISON")
    print("=" * 70)

    train_csv = os.path.join(SPLITS_DIR, "train_cells.csv")
    val_csv   = os.path.join(SPLITS_DIR, "val_cells.csv")
    test_csv  = os.path.join(SPLITS_DIR, "test_cells.csv")

    print("Loading datasets and extracting 244D features...")
    t0 = time.time()
    X_train, y_train, df_train = load_partition_data(train_csv)
    X_val, y_val, df_val       = load_partition_data(val_csv)
    X_test, y_test, df_test    = load_partition_data(test_csv)
    print(f"Features extracted in {time.time() - t0:.2f}s:")
    print(f"  Train: {X_train.shape[0]} samples x {X_train.shape[1]} features")
    print(f"  Val:   {X_val.shape[0]} samples x {X_val.shape[1]} features")
    print(f"  Test:  {X_test.shape[0]} samples x {X_test.shape[1]} features")

    # Fit StandardScaler strictly on training set
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    candidates = ["random_forest", "extra_trees", "mlp"]
    metrics_summary = {}
    best_model_name = None
    best_val_score = -1.0
    best_wrapper = None

    for model_name in candidates:
        print(f"\nTraining Candidate Architecture: '{model_name}'...")
        model = build_candidate_model(model_name, random_state=42)

        t_start = time.time()
        model.fit(X_train_scaled, y_train)
        train_time = time.time() - t_start

        wrapper = BrailleClassifierWrapper(model, scaler=scaler)

        train_res = evaluate_model_on_partition(wrapper, X_train, y_train)
        val_res   = evaluate_model_on_partition(wrapper, X_val, y_val)

        print(f"  Train Time: {train_time:.2f}s")
        print(f"  Train Exact Cell Acc: {train_res['exact_cell_accuracy']*100:.2f}%, Macro F1: {train_res['macro_f1']*100:.2f}%")
        print(f"  Val Exact Cell Acc:   {val_res['exact_cell_accuracy']*100:.2f}%, Macro F1: {val_res['macro_f1']*100:.2f}%")

        metrics_summary[model_name] = {
            "train_time_sec": round(train_time, 2),
            "train_metrics": train_res,
            "val_metrics": val_res
        }

        # Model selection based on validation exact cell accuracy
        if val_res["exact_cell_accuracy"] > best_val_score:
            best_val_score = val_res["exact_cell_accuracy"]
            best_model_name = model_name
            best_wrapper = wrapper

    print("\n" + "=" * 70)
    print(f"CHAMPION MODEL SELECTED: '{best_model_name}' (Validation Cell Accuracy: {best_val_score*100:.2f}%)")
    print("=" * 70)

    # Evaluate Champion Model on Held-Out Test Set (DOC009, DOC010)
    test_res = evaluate_model_on_partition(best_wrapper, X_test, y_test)
    print(f"Held-Out Test Set Performance ({len(y_test)} cells across DOC009 & DOC010):")
    print(f"  Exact 6-Dot Cell Accuracy: {test_res['exact_cell_accuracy']*100:.2f}%")
    print(f"  Mean Dot Accuracy:         {test_res['mean_dot_accuracy']*100:.2f}%")
    print(f"  Macro F1-Score:            {test_res['macro_f1']*100:.2f}%")
    print(f"  Per-Dot Accuracy:          {test_res['per_dot_accuracy']}")
    print(f"  Per-Dot F1-Score:          {test_res['per_dot_f1']}")

    metrics_summary["champion_model"] = best_model_name
    metrics_summary["test_metrics"] = test_res

    # Save Checkpoints
    champion_path = os.path.join(MODELS_DIR, "braille_champion_model.pkl")
    scaler_path   = os.path.join(MODELS_DIR, "braille_scaler.pkl")
    metrics_path  = os.path.join(MODELS_DIR, "training_metrics.json")

    with open(champion_path, 'wb') as f:
        pickle.dump(best_wrapper.model, f)
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(metrics_summary, f, indent=2)

    print(f"\nSaved Champion Model Checkpoint: {champion_path}")
    print(f"Saved Feature Scaler:            {scaler_path}")
    print(f"Saved Training Metrics Log:      {metrics_path}")
    print("=" * 70)


if __name__ == "__main__":
    train_and_select_champion()
