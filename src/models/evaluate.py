"""
Transify — BdSL Sign Language Model Evaluation Suite
Evaluates the trained champion model on the strictly held-out independent test split (Signer S001),
computes confusion matrices, per-class metrics, latency profiling, and unknown sign rejection.
"""

import os
import time
import json
import argparse
import pickle
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix
)

from architectures import (
    extract_temporal_features,
    UnknownRejectionFilter,
    BDSL_METADATA
)


def parse_args():
    parser = argparse.ArgumentParser(description="Transify BdSL Model Evaluator")
    parser.add_argument("--test_split", type=str, default="data/sign/splits/test_split.csv", help="Test split CSV")
    parser.add_argument("--model_path", type=str, default="models/sign/bdsl_champion_model.pkl", help="Model weights path")
    parser.add_argument("--scaler_path", type=str, default="models/sign/scaler.pkl", help="Fitted scaler path")
    parser.add_argument("--report_out", type=str, default="models/sign/evaluation_results.json", help="Evaluation JSON report output")
    return parser.parse_args()


def load_test_data(test_csv: str):
    df = pd.read_csv(test_csv)
    raw_sequences = []
    features_list = []
    labels = []

    for _, row in df.iterrows():
        npy_path = str(row["landmark_filename"]).replace("\\", "/")
        seq = np.load(npy_path)
        raw_sequences.append(seq)
        features_list.append(extract_temporal_features(seq))
        labels.append(int(row["class_id"]))

    return df, raw_sequences, np.array(features_list, dtype=np.float32), np.array(labels, dtype=np.int64)


def main():
    args = parse_args()
    print("=" * 60)
    print(" Transify BdSL Independent Signer Evaluation Suite")
    print(f" Test Split (Unseen Signers): {args.test_split}")
    print(f" Model Artifact:              {args.model_path}")
    print("=" * 60)

    # 1. Load Model and Scaler
    with open(args.model_path, "rb") as f:
        model = pickle.load(f)
    with open(args.scaler_path, "rb") as f:
        scaler = pickle.load(f)

    # 2. Load Held-Out Test Data
    test_df, raw_seqs, X_test_raw, y_test = load_test_data(args.test_split)
    test_signers = sorted(test_df["signer_id"].unique().tolist())
    print(f"[DATA] Evaluated on {len(X_test_raw)} held-out samples from Signer(s): {test_signers}")

    X_test = scaler.transform(X_test_raw)

    # 3. Latency Profiling
    latencies = []
    for i in range(len(X_test)):
        sample = X_test[i:i+1]
        t0 = time.perf_counter()
        _ = model.predict(sample)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    mean_latency_ms = float(np.mean(latencies))
    p95_latency_ms = float(np.percentile(latencies, 95))
    fps = round(1000.0 / mean_latency_ms, 1)

    # 4. Standard Classification Performance
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)

    acc = accuracy_score(y_test, y_pred)
    macro_prec, macro_rec, macro_f1, _ = precision_recall_fscore_support(y_test, y_pred, average='macro', zero_division=0)
    per_class_prec, per_class_rec, per_class_f1, per_class_supp = precision_recall_fscore_support(y_test, y_pred, average=None, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)

    print("\n" + "=" * 60)
    print(" INDEPENDENT TEST PERFORMANCE (HELD-OUT SIGNER)")
    print("=" * 60)
    print(f"Overall Accuracy:  {acc * 100:.2f}%")
    print(f"Macro Precision:   {macro_prec * 100:.2f}%")
    print(f"Macro Recall:      {macro_rec * 100:.2f}%")
    print(f"Macro F1-Score:    {macro_f1 * 100:.2f}%")
    print(f"Inference Latency: {mean_latency_ms:.2f} ms (p95: {p95_latency_ms:.2f} ms) -> {fps} FPS")
    print("=" * 60)

    print("\n[PER-CLASS BREAKDOWN]")
    print(f"{'Class ID':<10} {'Label':<20} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<8}")
    per_class_report = {}
    for cid in range(10):
        lbl = BDSL_METADATA[cid]["label"]
        p = float(per_class_prec[cid])
        r = float(per_class_rec[cid])
        f = float(per_class_f1[cid])
        s = int(per_class_supp[cid])
        per_class_report[lbl] = {"precision": round(p, 4), "recall": round(r, 4), "f1_score": round(f, 4), "support": s}
        print(f"[{cid:<2}]       {lbl:<20} {p*100:>6.2f}%      {r*100:>6.2f}%      {f*100:>6.2f}%      {s:>4}")

    # 5. Unknown Sign Rejection Evaluation
    rejection_filter = UnknownRejectionFilter(conf_threshold=0.70, entropy_threshold=1.20, motion_threshold=0.25)

    # In-Distribution Acceptance Rate
    in_dist_accepted = 0
    for i in range(len(X_test)):
        res = rejection_filter.filter_prediction(y_prob[i], raw_seqs[i])
        if res["supported"] and res["recognized"]:
            in_dist_accepted += 1
    in_dist_acceptance_rate = (in_dist_accepted / len(X_test)) * 100.0

    # Out-Of-Distribution Rejection: Generate 50 stationary / idle sequences and 50 random noise sequences
    rng = np.random.default_rng(1337)
    idle_sequences = [np.zeros((30, 162), dtype=np.float32) for _ in range(50)]
    noise_sequences = [rng.normal(0, 0.5, size=(30, 162)).astype(np.float32) for _ in range(50)]

    idle_rejected = 0
    for seq in idle_sequences:
        feat = extract_temporal_features(seq).reshape(1, -1)
        prob = model.predict_proba(scaler.transform(feat))[0]
        res = rejection_filter.filter_prediction(prob, seq)
        if not res["supported"]:
            idle_rejected += 1

    noise_rejected = 0
    for seq in noise_sequences:
        feat = extract_temporal_features(seq).reshape(1, -1)
        prob = model.predict_proba(scaler.transform(feat))[0]
        res = rejection_filter.filter_prediction(prob, seq)
        if not res["supported"]:
            noise_rejected += 1

    idle_rejection_rate = (idle_rejected / len(idle_sequences)) * 100.0
    noise_rejection_rate = (noise_rejected / len(noise_sequences)) * 100.0

    print("\n" + "=" * 60)
    print(" UNKNOWN SIGN & OOD REJECTION PERFORMANCE")
    print("=" * 60)
    print(f"Valid Gesture Acceptance Rate: {in_dist_acceptance_rate:.2f}% ({in_dist_accepted}/{len(X_test)})")
    print(f"Stationary / Idle Rejection:   {idle_rejection_rate:.2f}% ({idle_rejected}/{len(idle_sequences)})")
    print(f"Random Noise OOD Rejection:    {noise_rejection_rate:.2f}% ({noise_rejected}/{len(noise_sequences)})")
    print("=" * 60)

    # 6. Save Complete Structured Results
    eval_results = {
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_signers": test_signers,
        "sample_count": len(y_test),
        "overall_accuracy": round(acc, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "macro_f1": round(macro_f1, 4),
        "mean_latency_ms": round(mean_latency_ms, 2),
        "p95_latency_ms": round(p95_latency_ms, 2),
        "fps": fps,
        "per_class": per_class_report,
        "confusion_matrix": cm.tolist(),
        "unknown_rejection": {
            "valid_gesture_acceptance_rate": round(in_dist_acceptance_rate, 2),
            "idle_rejection_rate": round(idle_rejection_rate, 2),
            "noise_ood_rejection_rate": round(noise_rejection_rate, 2)
        }
    }

    os.makedirs(os.path.dirname(args.report_out), exist_ok=True)
    with open(args.report_out, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    print(f"\n[OK] Evaluation results saved to: {args.report_out}")


if __name__ == "__main__":
    main()
