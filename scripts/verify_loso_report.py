"""Verification script for BdSL LOSO evaluation reports."""
import json
import sys


def verify_loso_report(report_path: str = "artifacts/bdsl_loso_evaluation_report.json"):
    with open(report_path) as f:
        d = json.load(f)

    folds = d.get("per_signer_loso_folds", [])
    assert len(folds) == 8, f"Expected 8 folds, got {len(folds)}"

    for f_info in folds:
        signer = f_info["held_out_signer"]
        acc = f_info["accuracy"]
        test_cnt = f_info["test_samples"]
        train_cnt = f_info["train_samples"]
        assert test_cnt == 150, f"Fold {signer} expected 150 test samples, got {test_cnt}"
        assert train_cnt == 1050, f"Fold {signer} expected 1050 train samples, got {train_cnt}"
        assert acc >= 0.90, f"Fold {signer} accuracy below threshold: {acc}"

    summary = d.get("training_procedure_loso_summary", {})
    mean_acc = summary.get("mean_accuracy", 0.0)
    mean_f1 = summary.get("mean_macro_f1", 0.0)
    mean_brier = summary.get("mean_calibrated_brier", 0.0)
    mean_ece = summary.get("mean_calibrated_top_label_ece", 0.0)

    print(f"Mean Accuracy: {mean_acc:.4f}")
    print(f"Mean Macro F1: {mean_f1:.4f}")
    print(f"Mean Calibrated Brier: {mean_brier:.4f}")
    print(f"Mean Calibrated ECE: {mean_ece:.4f}")
    print("[PASS] All 8 LOSO folds verified successfully.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "artifacts/bdsl_loso_evaluation_report.json"
    verify_loso_report(path)
