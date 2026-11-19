"""
Transify — BdSL Multi-Signer Leave-One-Signer-Out (LOSO) Cross-Validation Suite
Evaluates generalization across all 8 signers (S001–S008) in data/sign/processed/landmarks/.
In each fold i:
  - Held-out test signer: S_i (150 samples across 10 classes)
  - Training signers: All 7 other signers (1,050 samples across 10 classes)
  - Feature scaler: Fitted strictly on training fold
  - Champion classifier: Fitted strictly on training fold
  - Platt calibration: Calibrated on training fold via internal CV (leak-free)
  - Evaluated on: Held-out test signer S_i
Outputs comprehensive summary statistics and per-signer metrics to models/sign/bdsl_loso_evaluation_report.json
"""

import os
import sys
import time
import json
import hashlib
import argparse
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix
)
from sklearn.calibration import CalibratedClassifierCV

# Add src/models to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "models")))
from architectures import (
    extract_temporal_features,
    build_champion_classifier,
    BDSL_METADATA
)


def compute_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_ece(probs: np.ndarray, y_true: np.ndarray, n_bins: int = 10):
    """Computes Expected Calibration Error (ECE) across n_bins."""
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
    """Computes multi-class Brier score."""
    y_one_hot = np.zeros((len(y_true), num_classes), dtype=np.float32)
    for idx, label in enumerate(y_true):
        y_one_hot[idx, label] = 1.0
    brier = np.mean(np.sum((probs - y_one_hot) ** 2, axis=1))
    return round(float(brier), 4)


def parse_args():
    parser = argparse.ArgumentParser(description="BdSL Leave-One-Signer-Out (LOSO) Cross-Validation")
    parser.add_argument("--manifest", type=str, default="data/sign/annotations/dataset_master_manifest.csv",
                        help="Path to dataset master manifest CSV")
    parser.add_argument("--output_json", type=str, default="models/sign/bdsl_loso_evaluation_report.json",
                        help="Path to output evaluation report JSON")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    return parser.parse_args()


def run_loso_evaluation(manifest_path: str, output_json: str, seed: int = 42):
    print("=" * 70)
    print(" Transify BdSL 8-Fold Leave-One-Signer-Out (LOSO) Cross-Validation")
    print(f" Manifest:    {manifest_path}")
    print(f" Output JSON: {output_json}")
    print("=" * 70)

    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    df = pd.read_csv(manifest_path)
    total_samples = len(df)
    unique_signers = sorted(df["signer_id"].unique().tolist())
    print(f"[DATA] Loaded manifest with {total_samples} samples across {len(unique_signers)} signers: {unique_signers}")

    # Extract all 1,200 temporal feature vectors (972D)
    print("\n---> Extracting kinematic temporal features (972D) for all samples...")
    t0_feat = time.time()
    features_list = []
    labels_list = []
    signers_list = []

    for _, row in df.iterrows():
        npy_path = str(row["landmark_filename"]).replace("\\", "/")
        if not os.path.exists(npy_path):
            raise FileNotFoundError(f"Landmark file missing: {npy_path}")
        seq = np.load(npy_path)
        feat = extract_temporal_features(seq)
        features_list.append(feat)
        labels_list.append(int(row["class_id"]))
        signers_list.append(str(row["signer_id"]))

    X_all = np.array(features_list, dtype=np.float32)
    y_all = np.array(labels_list, dtype=np.int64)
    signers_all = np.array(signers_list, dtype=object)
    print(f"[DATA] Feature extraction complete in {time.time() - t0_feat:.2f}s. Feature matrix: {X_all.shape}")

    # LOSO Cross-Validation across each signer
    fold_reports = []
    all_fold_accuracies = []
    all_fold_f1s = []
    all_fold_briers = []
    all_fold_eces = []

    t_start_cv = time.time()

    for fold_idx, test_signer in enumerate(unique_signers):
        print(f"\n[{fold_idx + 1}/{len(unique_signers)}] Evaluating Fold: Held-Out Signer = {test_signer}...")
        test_mask = (signers_all == test_signer)
        train_mask = ~test_mask

        X_train_raw = X_all[train_mask]
        y_train = y_all[train_mask]
        X_test_raw = X_all[test_mask]
        y_test = y_all[test_mask]

        train_signers = sorted(np.unique(signers_all[train_mask]).tolist())
        assert test_signer not in train_signers, f"Data leakage: {test_signer} in training set!"
        assert len(X_test_raw) == 150, f"Expected 150 test samples, got {len(X_test_raw)}"
        assert len(X_train_raw) == 1050, f"Expected 1050 train samples, got {len(X_train_raw)}"

        # 1. Feature scaling strictly on training fold
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train_raw)
        X_test = scaler.transform(X_test_raw)

        # 2. Train Champion Classifier on training fold
        fold_model = build_champion_classifier()
        t0_train = time.time()
        fold_model.fit(X_train, y_train)
        fold_train_time = time.time() - t0_train

        # 3. Platt probability calibration using 3-fold CV on training fold only
        t0_cal = time.time()
        calibrated_fold_model = CalibratedClassifierCV(
            estimator=build_champion_classifier(),
            method="sigmoid",
            cv=3
        )
        calibrated_fold_model.fit(X_train, y_train)
        fold_cal_time = time.time() - t0_cal

        # 4. Predict on held-out test signer
        preds = fold_model.predict(X_test)
        probs_raw = fold_model.predict_proba(X_test)
        probs_cal = calibrated_fold_model.predict_proba(X_test)

        acc = accuracy_score(y_test, preds)
        macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(y_test, preds, average="macro", zero_division=0)
        class_p, class_r, class_f, class_supp = precision_recall_fscore_support(y_test, preds, average=None, zero_division=0)

        brier_raw = compute_multiclass_brier(probs_raw, y_test)
        ece_raw, _ = compute_ece(probs_raw, y_test)
        brier_cal = compute_multiclass_brier(probs_cal, y_test)
        ece_cal, _ = compute_ece(probs_cal, y_test)

        cm = confusion_matrix(y_test, preds).tolist()

        per_class_fold = {}
        for c_id in range(len(BDSL_METADATA)):
            label_name = BDSL_METADATA[c_id]["label"]
            per_class_fold[label_name] = {
                "class_id": c_id,
                "precision": round(float(class_p[c_id]), 4),
                "recall": round(float(class_r[c_id]), 4),
                "f1_score": round(float(class_f[c_id]), 4),
                "samples": int(class_supp[c_id])
            }

        fold_report = {
            "fold": fold_idx + 1,
            "held_out_signer": test_signer,
            "train_signers": train_signers,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "accuracy": round(float(acc), 4),
            "macro_precision": round(float(macro_p), 4),
            "macro_recall": round(float(macro_r), 4),
            "macro_f1": round(float(macro_f1), 4),
            "brier_score_raw": brier_raw,
            "ece_raw": ece_raw,
            "brier_score_calibrated": brier_cal,
            "ece_calibrated": ece_cal,
            "training_time_sec": round(fold_train_time, 2),
            "calibration_time_sec": round(fold_cal_time, 2),
            "per_class_metrics": per_class_fold,
            "confusion_matrix": cm
        }
        fold_reports.append(fold_report)

        all_fold_accuracies.append(acc)
        all_fold_f1s.append(macro_f1)
        all_fold_briers.append(brier_cal)
        all_fold_eces.append(ece_cal)

        print(f"      Accuracy: {acc * 100:.2f}% | Macro F1: {macro_f1 * 100:.2f}% | "
              f"Calibrated Brier: {brier_cal:.4f} | Calibrated ECE: {ece_cal:.4f} | "
              f"Time: {fold_train_time:.1f}s")

    total_cv_time = time.time() - t_start_cv
    mean_acc = float(np.mean(all_fold_accuracies))
    std_acc = float(np.std(all_fold_accuracies))
    mean_f1 = float(np.mean(all_fold_f1s))
    std_f1 = float(np.std(all_fold_f1s))
    mean_brier = float(np.mean(all_fold_briers))
    std_brier = float(np.std(all_fold_briers))
    mean_ece = float(np.mean(all_fold_eces))
    std_ece = float(np.std(all_fold_eces))

    print("\n" + "=" * 70)
    print(" BdSL 8-FOLD LEAVE-ONE-SIGNER-OUT (LOSO) SUMMARY")
    print("=" * 70)
    print(f"Mean Accuracy:       {mean_acc * 100:.2f}%  (± {std_acc * 100:.2f}%)")
    print(f"Mean Macro F1-Score: {mean_f1 * 100:.2f}%  (± {std_f1 * 100:.2f}%)")
    print(f"Mean Calibrated Brier: {mean_brier:.4f} (± {std_brier:.4f})")
    print(f"Mean Calibrated ECE:   {mean_ece:.4f} (± {std_ece:.4f})")
    print(f"Total LOSO Runtime:  {total_cv_time:.2f}s")
    print("=" * 70)

    summary_report = {
        "evaluation_name": "BdSL Multi-Signer Leave-One-Signer-Out (LOSO) Cross-Validation",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "manifest_path": manifest_path,
        "manifest_sha256": compute_sha256(manifest_path),
        "total_signers": len(unique_signers),
        "signers": unique_signers,
        "total_samples": total_samples,
        "samples_per_signer": 150,
        "classes_evaluated": len(BDSL_METADATA),
        "feature_dimension": 972,
        "champion_architecture": "Deep MLP (384-192-96, ReLU, Adam, Early Stopping, L2 Alpha=1e-4)",
        "calibration_method": "Platt Sigmoid Scaling (3-fold CV on training fold)",
        "summary_metrics": {
            "mean_accuracy": round(mean_acc, 4),
            "std_accuracy": round(std_acc, 4),
            "mean_macro_f1": round(mean_f1, 4),
            "std_macro_f1": round(std_f1, 4),
            "mean_calibrated_brier": round(mean_brier, 4),
            "std_calibrated_brier": round(std_brier, 4),
            "mean_calibrated_ece": round(mean_ece, 4),
            "std_calibrated_ece": round(std_ece, 4),
            "min_accuracy": round(float(np.min(all_fold_accuracies)), 4),
            "max_accuracy": round(float(np.max(all_fold_accuracies)), 4),
            "total_runtime_sec": round(total_cv_time, 2)
        },
        "per_signer_folds": fold_reports
    }

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w") as f:
        json.dump(summary_report, f, indent=2)

    print(f"[OK] Saved LOSO evaluation report to: {output_json}")
    return summary_report


if __name__ == "__main__":
    args = parse_args()
    run_loso_evaluation(args.manifest, args.output_json, args.seed)
