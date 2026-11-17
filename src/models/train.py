"""
Transify — BdSL Sign Language Model Training Harness
Trains candidate architectures on the training split, tunes hyperparameters using the validation split,
compares models, and exports the champion model artifact with full metadata.
"""

import os
import json
import time
import argparse
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

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
    parser.add_argument("--output_dir", type=str, default="models/sign", help="Output model directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    return parser.parse_args()


def load_dataset_split(split_csv: str):
    df = pd.read_csv(split_csv)
    X_list = []
    y_list = []

    for _, row in df.iterrows():
        npy_path = row["landmark_filename"]
        if not os.path.exists(npy_path):
            raise FileNotFoundError(f"Feature file missing: {npy_path}")

        seq = np.load(npy_path)
        feat = extract_temporal_features(seq)
        X_list.append(feat)
        y_list.append(int(row["class_id"]))

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int64)


def main():
    args = parse_args()
    print("=" * 60)
    print(" Transify BdSL Model Training & Candidate Architecture Comparison")
    print(f" Train Split: {args.train_split}")
    print(f" Val Split:   {args.val_split}")
    print("=" * 60)

    # 1. Load training and validation datasets
    X_train_raw, y_train = load_dataset_split(args.train_split)
    X_val_raw, y_val = load_dataset_split(args.val_split)

    print(f"[DATA] Train shape: {X_train_raw.shape} | Labels: {np.bincount(y_train)}")
    print(f"[DATA] Val shape:   {X_val_raw.shape} | Labels: {np.bincount(y_val)}")

    # 2. Fit Scaler STRICTLY on training split
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_val = scaler.transform(X_val_raw)

    os.makedirs(args.output_dir, exist_ok=True)
    scaler_path = os.path.join(args.output_dir, "scaler.pkl")
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
    print(f"[OK] Saved fitted feature scaler to: {scaler_path}")

    # 3. Candidate Architectures
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

        # Evaluate on validation split
        val_preds = model.predict(X_val)
        val_acc = accuracy_score(y_val, val_preds)
        val_prec, val_rec, val_f1, _ = precision_recall_fscore_support(y_val, val_preds, average='macro', zero_division=0)

        # Training set metrics (for diagnosing overfitting)
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

        if val_f1 > champion_f1:
            champion_f1 = val_f1
            champion_name = name
            champion_model = model

    print("\n" + "=" * 60)
    print(f"[CHAMPION SELECTION] {champion_name} selected with Validation Macro F1 = {champion_f1 * 100:.2f}%")
    print("=" * 60)

    # 4. Save Champion Model Artifact
    model_path = os.path.join(args.output_dir, "bdsl_champion_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(champion_model, f)
    print(f"[OK] Saved champion model weights to: {model_path}")

    # 5. Save Training Metadata & Comparison Log
    metadata = {
        "project": "Transify",
        "module": "Sign Language Recognition",
        "primary_language": "Bangladesh Sign Language (BdSL)",
        "num_classes": 10,
        "classes": BDSL_METADATA,
        "champion_architecture": champion_name,
        "input_feature_dim": 972,
        "raw_sequence_shape": [30, 162],
        "candidate_comparison": comparison_results,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    metadata_path = os.path.join(args.output_dir, "training_metrics.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"[OK] Saved training metadata to: {metadata_path}")


if __name__ == "__main__":
    main()
