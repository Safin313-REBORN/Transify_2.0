"""
Verification script for BdSL LOSO evaluation reports.
Enforces the complete Phase 16 validation contract and internal CI regression gates.
"""
import json
import math
import os
import sys
from typing import Any, Dict, List

EXPECTED_SIGNERS = {"S001", "S002", "S003", "S004", "S005", "S006", "S007", "S008"}
EXPECTED_CLASSES = {
    "HELLO", "THANK_YOU", "YOURE_WELCOME", "PLEASE", "I_NEED_HELP",
    "YES", "NO", "OKAY", "STOP", "I_DONT_UNDERSTAND"
}
CRITICAL_SIGNS = {"I_NEED_HELP", "STOP"}

# Internal CI engineering regression gates (NOT clinical/safety thresholds)
MIN_REGRESSION_ACCURACY = 0.90
MIN_REGRESSION_MACRO_F1 = 0.90
MAX_REGRESSION_BRIER = 0.15
MAX_REGRESSION_ECE = 0.15


def is_valid_finite_float(val: Any) -> bool:
    """Checks whether val is a float or int, finite, and not NaN."""
    if val is None or isinstance(val, bool):
        return False
    if not isinstance(val, (int, float)):
        return False
    return not (math.isnan(val) or math.isinf(val))


def verify_loso_report(report_path: str = "artifacts/bdsl_loso_evaluation_report.json") -> Dict[str, Any]:
    """
    Validates a BdSL LOSO evaluation report against the Phase 16 evaluation contract.
    Raises ValueError or AssertionError with a descriptive failure message if invalid.
    """
    if not os.path.exists(report_path):
        raise FileNotFoundError(f"Evaluation report file not found: {report_path}")

    with open(report_path, "r", encoding="utf-8") as f:
        try:
            d = json.load(f)
        except Exception as e:
            raise ValueError(f"Malformed JSON in evaluation report {report_path}: {e}") from e

    # 1. Top-Level Schema & Metadata Validation
    required_top_keys = [
        "evaluation_name", "timestamp", "manifest_path", "manifest_sha256",
        "random_seed", "total_signers", "signers", "total_samples",
        "samples_per_signer", "classes_evaluated", "feature_dimension",
        "champion_architecture", "preprocessing_pipeline",
        "data_integrity_audit", "kinematic_similarity_diagnostics",
        "production_model_checkpoint_evaluation",
        "training_procedure_loso_summary", "per_signer_loso_folds"
    ]
    for k in required_top_keys:
        if k not in d:
            raise ValueError(f"Missing required top-level key: '{k}'")

    if d["total_signers"] != 8:
        raise ValueError(f"Expected total_signers == 8, got {d.get('total_signers')}")
    if set(d.get("signers", [])) != EXPECTED_SIGNERS:
        raise ValueError(f"Signers mismatch: expected {EXPECTED_SIGNERS}, got {d.get('signers')}")
    if d["total_samples"] != 1200:
        raise ValueError(f"Expected total_samples == 1200, got {d.get('total_samples')}")
    if d["samples_per_signer"] != 150:
        raise ValueError(f"Expected samples_per_signer == 150, got {d.get('samples_per_signer')}")
    if d["classes_evaluated"] != 10:
        raise ValueError(f"Expected classes_evaluated == 10, got {d.get('classes_evaluated')}")
    if d["feature_dimension"] != 972:
        raise ValueError(f"Expected feature_dimension == 972, got {d.get('feature_dimension')}")

    # 2. Per-Signer Folds Validation
    folds: List[Dict[str, Any]] = d.get("per_signer_loso_folds", [])
    if len(folds) != 8:
        raise ValueError(f"Contract violation: Expected exactly 8 LOSO folds, got {len(folds)}")

    seen_held_out = set()
    for f_idx, fold in enumerate(folds):
        fold_num = fold.get("fold", f_idx + 1)
        signer = fold.get("held_out_signer")
        if not signer or signer not in EXPECTED_SIGNERS:
            raise ValueError(f"Fold {fold_num}: Invalid or missing held_out_signer '{signer}'")
        if signer in seen_held_out:
            raise ValueError(f"Fold {fold_num}: Duplicate held_out_signer '{signer}' observed across folds")
        seen_held_out.add(signer)

        train_signers = fold.get("train_signers", [])
        if signer in train_signers:
            raise ValueError(f"Fold {fold_num} ({signer}): Data leakage! Held-out signer '{signer}' in train_signers")
        if len(train_signers) != 7 or set(train_signers) != (EXPECTED_SIGNERS - {signer}):
            raise ValueError(f"Fold {fold_num} ({signer}): Expected exactly 7 distinct training signers, got {train_signers}")

        test_samples = fold.get("test_samples")
        if test_samples != 150:
            raise ValueError(f"Fold {fold_num} ({signer}): Expected test_samples == 150, got {test_samples}")
        train_samples = fold.get("train_samples")
        if train_samples != 1050:
            raise ValueError(f"Fold {fold_num} ({signer}): Expected train_samples == 1050, got {train_samples}")

        # Metrics finiteness and internal regression threshold validation
        acc = fold.get("accuracy")
        if not is_valid_finite_float(acc) or acc < 0.0 or acc > 1.0:
            raise ValueError(f"Fold {fold_num} ({signer}): Invalid accuracy value '{acc}'")
        if acc < MIN_REGRESSION_ACCURACY:
            raise AssertionError(f"Fold {fold_num} ({signer}): Accuracy {acc:.4f} below internal regression floor ({MIN_REGRESSION_ACCURACY})")

        f1 = fold.get("macro_f1")
        if not is_valid_finite_float(f1) or f1 < 0.0 or f1 > 1.0:
            raise ValueError(f"Fold {fold_num} ({signer}): Invalid macro_f1 value '{f1}'")
        if f1 < MIN_REGRESSION_MACRO_F1:
            raise AssertionError(f"Fold {fold_num} ({signer}): Macro F1 {f1:.4f} below internal regression floor ({MIN_REGRESSION_MACRO_F1})")

        brier = fold.get("brier_score_calibrated")
        if not is_valid_finite_float(brier) or brier < 0.0 or brier > MAX_REGRESSION_BRIER:
            raise ValueError(f"Fold {fold_num} ({signer}): Calibrated Brier score {brier} exceeds internal gate ({MAX_REGRESSION_BRIER}) or invalid")

        ece = fold.get("top_label_ece_calibrated")
        if not is_valid_finite_float(ece) or ece < 0.0 or ece > MAX_REGRESSION_ECE:
            raise ValueError(f"Fold {fold_num} ({signer}): Calibrated ECE {ece} exceeds internal gate ({MAX_REGRESSION_ECE}) or invalid")

        # Per-class coverage
        per_class = fold.get("per_class_metrics", {})
        if set(per_class.keys()) != EXPECTED_CLASSES:
            raise ValueError(f"Fold {fold_num} ({signer}): Class coverage mismatch: missing {EXPECTED_CLASSES - set(per_class.keys())}")

        for c_name, c_metric in per_class.items():
            for m_key in ["precision", "recall", "f1_score"]:
                m_val = c_metric.get(m_key)
                if not is_valid_finite_float(m_val) or m_val < 0.0 or m_val > 1.0:
                    raise ValueError(f"Fold {fold_num} ({signer}), Class '{c_name}': Invalid {m_key} value '{m_val}'")
            if c_metric.get("samples") != 15:
                raise ValueError(f"Fold {fold_num} ({signer}), Class '{c_name}': Expected samples == 15, got {c_metric.get('samples')}")

        # Confusion matrix validation
        cm = fold.get("confusion_matrix", [])
        if len(cm) != 10 or any(len(row) != 10 for row in cm):
            raise ValueError(f"Fold {fold_num} ({signer}): Confusion matrix must be 10x10, got {len(cm)}x{len(cm[0]) if cm else 0}")
        for r_idx, row in enumerate(cm):
            for c_idx, cell in enumerate(row):
                if cell is None or isinstance(cell, bool) or not isinstance(cell, int) or cell < 0:
                    raise ValueError(f"Fold {fold_num} ({signer}): Confusion matrix cell at [{r_idx}][{c_idx}] must be a non-negative integer, got {cell!r}")
            row_sum = sum(row)
            if row_sum != 15:
                raise ValueError(f"Fold {fold_num} ({signer}): Confusion matrix row {r_idx} sum is {row_sum}, expected 15 (samples per class)")
        cm_sum = sum(sum(row) for row in cm)
        if cm_sum != 150:
            raise ValueError(f"Fold {fold_num} ({signer}): Confusion matrix total elements sum to {cm_sum}, expected 150")

    if seen_held_out != EXPECTED_SIGNERS:
        raise ValueError(f"Not all signers were held out: missing {EXPECTED_SIGNERS - seen_held_out}")

    # 3. Training Procedure LOSO Summary Validation
    summary = d.get("training_procedure_loso_summary", {})
    mean_acc = summary.get("mean_accuracy")
    if not is_valid_finite_float(mean_acc) or mean_acc < 0.0 or mean_acc > 1.0:
        raise ValueError(f"Summary mean_accuracy must be in range [0.0, 1.0], got {mean_acc}")
    if mean_acc < MIN_REGRESSION_ACCURACY:
        raise AssertionError(f"Summary mean_accuracy {mean_acc} below internal regression floor ({MIN_REGRESSION_ACCURACY})")

    mean_f1 = summary.get("mean_macro_f1")
    if not is_valid_finite_float(mean_f1) or mean_f1 < 0.0 or mean_f1 > 1.0:
        raise ValueError(f"Summary mean_macro_f1 must be in range [0.0, 1.0], got {mean_f1}")
    if mean_f1 < MIN_REGRESSION_MACRO_F1:
        raise AssertionError(f"Summary mean_macro_f1 {mean_f1} below internal regression floor ({MIN_REGRESSION_MACRO_F1})")

    mean_brier = summary.get("mean_calibrated_brier")
    if not is_valid_finite_float(mean_brier) or mean_brier < 0.0 or mean_brier > MAX_REGRESSION_BRIER:
        raise ValueError(f"Summary mean_calibrated_brier must be in range [0.0, {MAX_REGRESSION_BRIER}], got {mean_brier}")

    mean_ece = summary.get("mean_calibrated_top_label_ece")
    if not is_valid_finite_float(mean_ece) or mean_ece < 0.0 or mean_ece > MAX_REGRESSION_ECE:
        raise ValueError(f"Summary mean_calibrated_top_label_ece must be in range [0.0, {MAX_REGRESSION_ECE}], got {mean_ece}")

    runtime = summary.get("total_runtime_sec")
    if not is_valid_finite_float(runtime) or runtime <= 0.0:
        raise ValueError(f"Summary total_runtime_sec {runtime} is invalid")

    # 4. Kinematic Similarity Diagnostics Validation
    sim_diag = d.get("kinematic_similarity_diagnostics", {})
    counts = sim_diag.get("comparison_count_audit", {})
    ord_c = counts.get("ordered_comparisons", {})
    unord_c = counts.get("unordered_unique_pairs", {})

    if ord_c.get("total_cross_signer_comparisons") != 1260000:
        raise ValueError(f"Ordered cross-signer comparisons mismatch: {ord_c.get('total_cross_signer_comparisons')} != 1,260,000")
    if ord_c.get("same_class_cross_signer_comparisons") != 126000:
        raise ValueError(f"Ordered same-class comparisons mismatch: {ord_c.get('same_class_cross_signer_comparisons')} != 126,000")
    if ord_c.get("diff_class_cross_signer_comparisons") != 1134000:
        raise ValueError(f"Ordered diff-class comparisons mismatch: {ord_c.get('diff_class_cross_signer_comparisons')} != 1,134,000")

    if unord_c.get("total_cross_signer_pairs") != 630000:
        raise ValueError(f"Unordered cross-signer pairs mismatch: {unord_c.get('total_cross_signer_pairs')} != 630,000")
    if unord_c.get("same_class_cross_signer_pairs") != 63000:
        raise ValueError(f"Unordered same-class pairs mismatch: {unord_c.get('same_class_cross_signer_pairs')} != 63,000")
    if unord_c.get("diff_class_cross_signer_pairs") != 567000:
        raise ValueError(f"Unordered diff-class pairs mismatch: {unord_c.get('diff_class_cross_signer_pairs')} != 567,000")

    # Top confusable class pairs validation (Phase 16 & 17 pairwise mathematics & uniqueness)
    conf_pairs = sim_diag.get("most_confusable_class_pairs", [])
    if len(conf_pairs) != 10:
        raise ValueError(f"Expected 10 top confusable class pairs, got {len(conf_pairs)}")
    seen_confusable_pairs = set()
    for p_idx, pair in enumerate(conf_pairs):
        c1, c2 = pair.get("class_1"), pair.get("class_2")
        if c1 not in EXPECTED_CLASSES:
            raise ValueError(f"Pair #{p_idx + 1}: Invalid class_1 label '{c1}'")
        if c2 not in EXPECTED_CLASSES:
            raise ValueError(f"Pair #{p_idx + 1}: Invalid class_2 label '{c2}'")
        if c1 == c2:
            raise ValueError(f"Pair #{p_idx + 1}: Class labels must be distinct, got {c1} == {c2}")
        if c1 >= c2:
            raise ValueError(f"Pair #{p_idx + 1} ({c1}-{c2}): Inconsistent class ordering, expected class_1 < class_2 alphabetically ({c1} >= {c2})")

        pair_key = frozenset([c1, c2])
        if pair_key in seen_confusable_pairs:
            raise ValueError(f"Pair #{p_idx + 1} ({c1}-{c2}): Repeated confusable class pair")
        seen_confusable_pairs.add(pair_key)

        ord_cnt = pair.get("ordered_comparisons_count")
        unord_cnt = pair.get("unordered_pairs_count")
        if ord_cnt != 25200:
            raise ValueError(f"Pair #{p_idx + 1} ({c1}-{c2}): Ordered count must be exactly 25,200 across both directions, got {ord_cnt}")
        if unord_cnt != 12600:
            raise ValueError(f"Pair #{p_idx + 1} ({c1}-{c2}): Unordered count must be exactly 12,600, got {unord_cnt}")
        if ord_cnt != 2 * unord_cnt:
            raise ValueError(f"Pair #{p_idx + 1} ({c1}-{c2}): Ratio violation {ord_cnt} != 2 * {unord_cnt}")

        for sim_key in ["mean_cosine_similarity", "median_cosine_similarity", "p95_cosine_similarity", "max_cosine_similarity"]:
            sim_val = pair.get(sim_key)
            if not is_valid_finite_float(sim_val) or sim_val < 0.0 or sim_val > 1.0:
                raise ValueError(f"Pair #{p_idx + 1} ({c1}-{c2}): Invalid {sim_key} '{sim_val}', must be finite float in [0.0, 1.0]")

    # Statistical distribution overlap validation
    ovl_meta = sim_diag.get("statistical_distribution_overlap", {})
    ovl_val = ovl_meta.get("ovl_value")
    if not is_valid_finite_float(ovl_val) or ovl_val < 0.0 or ovl_val > 1.0:
        raise ValueError(f"Invalid Weitzman OVL value: '{ovl_val}'")

    print(f"[VERIFY PASS] BdSL LOSO Report '{report_path}' conforms to Phase 16 contract.")
    print(f"              Mean Accuracy: {mean_acc:.4f} (Internal Floor: {MIN_REGRESSION_ACCURACY:.2f})")
    print(f"              Mean Macro F1: {mean_f1:.4f} (Internal Floor: {MIN_REGRESSION_MACRO_F1:.2f})")
    print(f"              Mean Calibrated Brier: {mean_brier:.4f} (Max Gate: {MAX_REGRESSION_BRIER:.2f})")
    print(f"              Mean Calibrated ECE:   {mean_ece:.4f} (Max Gate: {MAX_REGRESSION_ECE:.2f})")
    print(f"              Weitzman OVL Overlap:  {ovl_val * 100:.2f}% shared density mass")
    print(f"              All 8 folds and 45 pairwise combinatorial dimensions validated.")
    return d


if __name__ == "__main__":
    target_path = sys.argv[1] if len(sys.argv) > 1 else "artifacts/bdsl_loso_evaluation_report.json"
    try:
        verify_loso_report(target_path)
        sys.exit(0)
    except Exception as exc:
        print(f"[VERIFY FAIL] {exc}", file=sys.stderr)
        sys.exit(1)
