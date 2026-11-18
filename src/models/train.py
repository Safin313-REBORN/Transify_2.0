"""
Transify — BdSL Sign Language Model Training Harness
Trains candidate architectures on the training split, tunes hyperparameters using the validation split,
compares models, applies confidence calibration, and executes an independent evaluation on the untouched test split.
Outputs separate training_metrics.json, validation_metrics.json, and test_metrics.json with artifact hashes.
"""

import os
import json
import time
import hashlib
import argparse
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix
)
from sklearn.calibration import CalibratedClassifierCV

from architectures import (
    extract_temporal_features,
    build_champion_classifier,
    build_baseline_rf,
    build_baseline_hist_gb,
    BDSL_METADATA
)


def parse_args():
    parser = argparse.ArgumentParser(description="Transify BdSL Model Trainer")
    parser.add_argument("--train_split", type=str, default="data/sign/splits/train_split.csv", help="Train split CSV")
    parser.add_argument("--val_split", type=str, default="data/sign/splits/val_split.csv", help="Val split CSV")
    parser.add_argument("--test_split", type=str, default="data/sign/splits/test_split.csv", help="Test split CSV")
    parser.add_argument("--output_dir", type=str, default="models/sign", help="Output model directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    return parser.parse_args()


def compute_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_ece(probs: np.ndarray, y_true: np.ndarray, n_bins: int = 10):
    """
    Computes Expected Calibration Error (ECE) across n_bins.
    """
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = (predictions == y_true).astype(float)

    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    bin_details = []

    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        prop_in_bin = float(np.mean(in_bin))
        if prop_in_bin > 0:
            acc_in_bin = float(np.mean(accuracies[in_bin]))
            conf_in_bin = float(np.mean(confidences[in_bin]))
            ece += abs(conf_in_bin - acc_in_bin) * prop_in_bin
            bin_details.append({
                "bin_range": f"({bin_boundaries[i]:.2f}, {bin_boundaries[i+1]:.2f}]",
                "sample_count": int(np.sum(in_bin)),
                "accuracy": round(acc_in_bin, 4),
                "avg_confidence": round(conf_in_bin, 4)
            })

    return round(float(ece), 4), bin_details


def compute_multiclass_brier(probs: np.ndarray, y_true: np.ndarray, num_classes: int = 10) -> float:
    """
    Computes multi-class Brier score (mean squared error between predicted probability vector and one-hot true labels).
    """
    y_one_hot = np.zeros((len(y_true), num_classes), dtype=np.float32)
    for idx, label in enumerate(y_true):
        y_one_hot[idx, label] = 1.0
    brier = np.mean(np.sum((probs - y_one_hot) ** 2, axis=1))
    return round(float(brier), 4)


def load_dataset_split(split_csv: str):
    df = pd.read_csv(split_csv)
    X_list = []
    y_list = []

    for _, row in df.iterrows():
        npy_path = str(row["landmark_filename"]).replace("\\", "/")
        if not os.path.exists(npy_path):
            raise FileNotFoundError(f"Feature file missing: {npy_path}")

        seq = np.load(npy_path)
        feat = extract_temporal_features(seq)
        X_list.append(feat)
        y_list.append(int(row["class_id"]))

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int64), df


def main():
    args = parse_args()
    print("=" * 65)
    print(" Transify BdSL Model Training, Calibration & Independent Evaluation")
    print(f" Train Split: {args.train_split}")
    print(f" Val Split:   {args.val_split}")
    print(f" Test Split:  {args.test_split}")
    print("=" * 65)

    # 1. Load training, validation, and untouched test splits
    X_train_raw, y_train, train_df = load_dataset_split(args.train_split)
    X_val_raw, y_val, val_df = load_dataset_split(args.val_split)
    X_test_raw, y_test, test_df = load_dataset_split(args.test_split)

    train_signers = sorted(list(train_df["signer_id"].unique()))
    val_signers = sorted(list(val_df["signer_id"].unique()))
    test_signers = sorted(list(test_df["signer_id"].unique()))

    # Verify strict signer independence
    assert not set(train_signers).intersection(set(val_signers)), "Signer leakage between train and val!"
    assert not set(train_signers).intersection(set(test_signers)), "Signer leakage between train and test!"
    assert not set(val_signers).intersection(set(test_signers)), "Signer leakage between val and test!"

    print(f"[DATA] Train: {X_train_raw.shape[0]} samples across signers {train_signers}")
    print(f"[DATA] Val:   {X_val_raw.shape[0]} samples across signers {val_signers}")
    print(f"[DATA] Test:  {X_test_raw.shape[0]} samples across signers {test_signers}")

    # 2. Fit Scaler STRICTLY on training split
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_val = scaler.transform(X_val_raw)
    X_test = scaler.transform(X_test_raw)

    os.makedirs(args.output_dir, exist_ok=True)
    scaler_path = os.path.join(args.output_dir, "scaler.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    scaler_hash = compute_sha256(scaler_path)
    print(f"[OK] Saved fitted feature scaler to: {scaler_path} (SHA256: {scaler_hash[:16]}...)")

    # 3. Candidate Architectures Comparison (strictly evaluated on validation split)
    candidates = {
        "Random_Forest_Baseline": build_baseline_rf(),
        "Hist_Gradient_Boosting": build_baseline_hist_gb(),
        "Deep_MLP_Champion": build_champion_classifier()
    }

    comparison_results = {}
    champion_name = None
    champion_f1 = -1.0
    champion_model = None

    for name, model in candidates.items():
        print(f"\n---> Training Architecture: {name}...")
        start_time = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - start_time

        # Evaluate strictly on validation split
        val_preds = model.predict(X_val)
        val_acc = accuracy_score(y_val, val_preds)
        val_prec, val_rec, val_f1, _ = precision_recall_fscore_support(y_val, val_preds, average='macro', zero_division=0)

        # Training set metrics for diagnosing overfitting
        train_preds = model.predict(X_train)
        train_acc = accuracy_score(y_train, train_preds)

        print(f"     Train Accuracy:    {train_acc * 100:.2f}%")
        print(f"     Val Accuracy:      {val_acc * 100:.2f}%")
        print(f"     Val Macro F1:      {val_f1 * 100:.2f}%")
        print(f"     Training Duration: {train_time:.2f}s")

        comparison_results[name] = {
            "train_accuracy": round(train_acc, 4),
            "val_accuracy": round(val_acc, 4),
            "val_precision": round(val_prec, 4),
            "val_recall": round(val_rec, 4),
            "val_macro_f1": round(val_f1, 4),
            "training_duration_sec": round(train_time, 2)
        }

        # Select champion strictly using validation macro F1
        if val_f1 > champion_f1:
            champion_f1 = val_f1
            champion_name = name
            champion_model = model

    print("\n" + "=" * 65)
    print(f"[CHAMPION SELECTION] {champion_name} selected with Validation Macro F1 = {champion_f1 * 100:.2f}%")
    print("=" * 65)

    # 4. Save Champion Model Weights
    model_path = os.path.join(args.output_dir, "bdsl_champion_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(champion_model, f)
    model_hash = compute_sha256(model_path)
    print(f"[OK] Saved champion model weights to: {model_path} (SHA256: {model_hash[:16]}...)")

    # 5. Confidence Calibration Evaluation on Validation Split
    val_probs_raw = champion_model.predict_proba(X_val)
    val_brier_raw = compute_multiclass_brier(val_probs_raw, y_val)
    val_ece_raw, val_bins_raw = compute_ece(val_probs_raw, y_val)

    # Fit probability calibration using validation data
    calibrated_model = CalibratedClassifierCV(champion_model, method="sigmoid", cv="prefit")
    calibrated_model.fit(X_val, y_val)
    calibrated_path = os.path.join(args.output_dir, "calibrated_classifier.pkl")
    with open(calibrated_path, "wb") as f:
        pickle.dump(calibrated_model, f)

    val_probs_cal = calibrated_model.predict_proba(X_val)
    val_brier_cal = compute_multiclass_brier(val_probs_cal, y_val)
    val_ece_cal, val_bins_cal = compute_ece(val_probs_cal, y_val)

    print(f"[CALIBRATION (VAL)] Raw Brier: {val_brier_raw:.4f}, Raw ECE: {val_ece_raw:.4f}")
    print(f"[CALIBRATION (VAL)] Calibrated Brier: {val_brier_cal:.4f}, Calibrated ECE: {val_ece_cal:.4f}")

    # 6. Independent Evaluation on Untouched Test Split
    print("\n" + "=" * 65)
    print(f" Independent Evaluation on Held-out Test Split ({X_test.shape[0]} samples, Signer: {test_signers})")
    print("=" * 65)

    test_preds = champion_model.predict(X_test)
    test_acc = accuracy_score(y_test, test_preds)
    test_prec, test_rec, test_f1, _ = precision_recall_fscore_support(y_test, test_preds, average='macro', zero_division=0)

    # Per-class metrics
    class_p, class_r, class_f, class_support = precision_recall_fscore_support(y_test, test_preds, average=None, zero_division=0)
    per_class_metrics = {}
    for c_id in range(len(BDSL_METADATA)):
        c_label = BDSL_METADATA[c_id]["label"]
        per_class_metrics[c_label] = {
            "class_id": c_id,
            "precision": round(float(class_p[c_id]), 4),
            "recall": round(float(class_r[c_id]), 4),
            "f1_score": round(float(class_f[c_id]), 4),
            "sample_count": int(class_support[c_id])
        }

    # Confusion matrix
    c_matrix = confusion_matrix(y_test, test_preds).tolist()

    # Test calibration metrics
    test_probs_raw = champion_model.predict_proba(X_test)
    test_brier_raw = compute_multiclass_brier(test_probs_raw, y_test)
    test_ece_raw, test_bins_raw = compute_ece(test_probs_raw, y_test)

    test_probs_cal = calibrated_model.predict_proba(X_test)
    test_brier_cal = compute_multiclass_brier(test_probs_cal, y_test)
    test_ece_cal, test_bins_cal = compute_ece(test_probs_cal, y_test)

    print(f" Test Accuracy:    {test_acc * 100:.2f}%")
    print(f" Test Macro F1:    {test_f1 * 100:.2f}%")
    print(f" Test Raw Brier:   {test_brier_raw:.4f} | Raw ECE: {test_ece_raw:.4f}")
    print(f" Test Calib Brier: {test_brier_cal:.4f} | Calib ECE: {test_ece_cal:.4f}")

    timestamp_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 7. Save Separate Training Metrics
    train_meta = {
        "project": "Transify",
        "module": "Sign Language Recognition",
        "primary_language": "Bangladesh Sign Language (BdSL)",
        "num_classes": 10,
        "classes": BDSL_METADATA,
        "champion_architecture": champion_name,
        "input_feature_dim": 972,
        "raw_sequence_shape": [30, 162],
        "candidate_comparison": comparison_results,
        "train_sample_count": int(X_train.shape[0]),
        "train_signers": train_signers,
        "model_artifact_sha256": model_hash,
        "scaler_artifact_sha256": scaler_hash,
        "timestamp": timestamp_str
    }
    with open(os.path.join(args.output_dir, "training_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(train_meta, f, indent=2)

    # 8. Save Separate Validation Metrics
    val_meta = {
        "dataset_version": "Transify BdSL Validation Split v2.0",
        "signer_id": val_signers,
        "sample_count": int(X_val.shape[0]),
        "champion_architecture": champion_name,
        "val_accuracy": round(float(champion_f1), 4),
        "val_macro_f1": round(float(champion_f1), 4),
        "calibration": {
            "raw_brier_score": val_brier_raw,
            "raw_ece": val_ece_raw,
            "calibrated_brier_score": val_brier_cal,
            "calibrated_ece": val_ece_cal,
            "raw_bins": val_bins_raw
        },
        "model_artifact_sha256": model_hash,
        "timestamp": timestamp_str
    }
    with open(os.path.join(args.output_dir, "validation_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(val_meta, f, indent=2)

    # 9. Save Separate Test Metrics
    test_meta = {
        "dataset_version": "Transify BdSL Independent Held-out Test Split v2.0",
        "signer_id": test_signers,
        "sample_count": int(X_test.shape[0]),
        "test_accuracy": round(float(test_acc), 4),
        "test_macro_precision": round(float(test_prec), 4),
        "test_macro_recall": round(float(test_rec), 4),
        "test_macro_f1": round(float(test_f1), 4),
        "per_class_metrics": per_class_metrics,
        "confusion_matrix": c_matrix,
        "calibration": {
            "raw_brier_score": test_brier_raw,
            "raw_ece": test_ece_raw,
            "calibrated_brier_score": test_brier_cal,
            "calibrated_ece": test_ece_cal,
            "test_bins": test_bins_raw
        },
        "model_artifact_sha256": model_hash,
        "scaler_artifact_sha256": scaler_hash,
        "timestamp": timestamp_str
    }
    with open(os.path.join(args.output_dir, "test_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(test_meta, f, indent=2)

    print(f"\n[OK] Successfully saved training_metrics.json, validation_metrics.json, and test_metrics.json.")


if __name__ == "__main__":
    main()
