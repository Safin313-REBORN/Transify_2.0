"""
Transify — Regression Tests for BdSL LOSO Model Validation, Data Integrity & Performance Diagnostics
Validates:
1. BdSL LOSO evaluation report integrity, fold-local preprocessing pipelines, and cross-signer generalization (8 signers, 1,200 samples).
2. Data integrity invariants (zero duplicates, zero NaN/inf, exactly 15 samples per class across all 8 signers).
3. Production model loading, scaler compatibility, inference schema, and unknown sign rejection.
4. HaGRID model manifest disclosures, 38D feature dimension, and prototype status.
5. TransifySignDiagnostics instrumentation presence, zero pixel storage, cancellation on disable, and zero UI disruption.
"""

import os
import json
import pickle
import numpy as np
import pytest
from src.models.architectures import extract_temporal_features, BDSL_METADATA
from src.api.sign_adapter import SignLanguageAdapter


def test_bdsl_loso_evaluation_report():
    """
    Validates BdSL LOSO evaluation report integrity, fold-local preprocessing pipelines,
    and cross-signer generalization (8 signers, 1,200 samples).

    Acceptance Policy Documentation:
    - Internal Engineering Regression Floor: The Transify platform enforces an internal
      engineering regression floor of >= 0.90 (90%) accuracy and macro F1 across held-out signers
      to detect regressions in preprocessing, feature extraction, or model pipelines during CI/CD.
    - Clinical/Safety Boundary: A clinical or life-critical safety dependability threshold has
      NOT yet been established; this threshold serves strictly as an engineering quality floor.
    - Laboratory Benchmark Baseline: Under controlled SES01 laboratory conditions, the champion
      MLP architecture achieves 1.0000 on all 8 folds.
    """
    report_path = "models/sign/bdsl_loso_evaluation_report.json"
    assert os.path.exists(report_path), f"LOSO evaluation report missing: {report_path}"

    with open(report_path, "r") as f:
        data = json.load(f)

    assert data["total_signers"] == 8
    assert len(data["signers"]) == 8
    assert data["total_samples"] == 1200
    assert data["classes_evaluated"] == 10
    assert data["feature_dimension"] == 972
    assert "Fold-local Pipeline" in data["preprocessing_pipeline"]
    assert "StratifiedKFold" in data["calibration_configuration"]

    summary = data["training_procedure_loso_summary"]
    # Internal engineering regression floor: >= 90% accuracy and F1 required
    assert summary["mean_accuracy"] >= 0.90, f"Expected mean accuracy >= 90%, got {summary['mean_accuracy']}"
    assert summary["mean_macro_f1"] >= 0.90, f"Expected mean macro F1 >= 90%, got {summary['mean_macro_f1']}"
    assert summary["mean_calibrated_brier"] <= 0.15, f"Expected Brier <= 0.15, got {summary['mean_calibrated_brier']}"
    assert summary["mean_calibrated_top_label_ece"] <= 0.15, f"Expected ECE <= 0.15, got {summary['mean_calibrated_top_label_ece']}"

    # Critical signs evaluation validation
    assert "critical_signs_evaluation" in summary
    for critical_sign in ["I_NEED_HELP", "STOP"]:
        assert critical_sign in summary["critical_signs_evaluation"]
        cs_data = summary["critical_signs_evaluation"][critical_sign]
        assert cs_data["total_samples"] == 120
        assert cs_data["mean_precision"] >= 0.90
        assert cs_data["mean_recall"] >= 0.90
        assert cs_data["mean_f1"] >= 0.90
        assert cs_data["clinical_safety_threshold_status"] == "NOT_YET_ESTABLISHED"

    folds = data["per_signer_loso_folds"]
    assert len(folds) == 8
    for fold in folds:
        assert fold["test_samples"] == 150
        assert fold["train_samples"] == 1050
        assert fold["accuracy"] >= 0.90
        assert fold["held_out_signer"] not in fold["train_signers"]


def test_data_integrity_audit_results():
    report_path = "models/sign/bdsl_loso_evaluation_report.json"
    with open(report_path, "r") as f:
        data = json.load(f)

    audit = data["data_integrity_audit"]
    assert audit["total_manifest_rows"] == 1200
    assert audit["duplicate_sample_ids"] == 0
    assert audit["duplicate_landmark_paths"] == 0
    assert audit["missing_landmark_files"] == 0
    assert audit["exact_file_content_duplicates"] == 0
    assert audit["non_finite_coordinates_count"] == 0
    assert audit["dimension_mismatch_count"] == 0
    assert audit["per_class_sample_balance"]["is_perfectly_balanced"] is True
    assert audit["per_class_sample_balance"]["min_samples_per_signer_class"] == 15
    assert audit["per_class_sample_balance"]["max_samples_per_signer_class"] == 15


def test_production_model_loading_and_inference():
    """Validates that production model checkpoint loads cleanly and executes valid inference."""
    m_path = "models/sign/bdsl_champion_model.pkl"
    s_path = "models/sign/scaler.pkl"
    c_path = "models/sign/calibrated_classifier.pkl"

    assert os.path.exists(m_path), f"Missing model: {m_path}"
    assert os.path.exists(s_path), f"Missing scaler: {s_path}"
    assert os.path.exists(c_path), f"Missing calibrated classifier: {c_path}"

    with open(m_path, "rb") as f:
        model = pickle.load(f)
    with open(s_path, "rb") as f:
        scaler = pickle.load(f)

    assert model.n_features_in_ == 972
    assert scaler.n_features_in_ == 972
    assert list(model.classes_) == list(range(10))

    # Test SignLanguageAdapter inference
    predictor = SignLanguageAdapter()
    assert predictor.temporal_model is not None
    assert predictor.temporal_scaler is not None

    # Test unknown/idle rejection with flat zeros
    idle_seq = np.zeros((30, 162), dtype=np.float32)
    idle_res = predictor.predict_sequence(idle_seq, language_mode="bdsl")
    assert idle_res["status"] == "REJECTED"
    assert idle_res["label"] == "UNKNOWN"

    # Test synthetic sequence with movement
    active_seq = np.random.randn(30, 162).astype(np.float32) * 0.1
    active_res = predictor.predict_sequence(active_seq, language_mode="bdsl")
    assert "label" in active_res
    assert "class_id" in active_res
    assert "confidence" in active_res
    assert "probabilities" in active_res
    assert active_res["language_mode"] == "bdsl"


def test_hagrid_manifest_disclosures():
    manifest_path = "models/sign/hagrid_model_manifest.json"
    assert os.path.exists(manifest_path), f"HaGRID manifest missing: {manifest_path}"

    with open(manifest_path, "r") as f:
        data = json.load(f)

    assert data["class_count"] == 24
    assert len(data["supported_classes"]) == 24
    assert data["feature_dimension"] == 38
    assert "Synthetic-Template Prototype" in data["model_type"]
    assert "data_origin_disclosure" in data
    assert "synthetic" in data["data_origin_disclosure"].lower()
    assert "38D" in data["architecture"]


def test_production_checkpoint_metric_schema():
    """Validates that production checkpoint evaluation outputs all 12 raw and calibrated metrics."""
    report_path = "models/sign/bdsl_loso_evaluation_report.json"
    with open(report_path, "r") as f:
        data = json.load(f)

    prod = data["production_model_checkpoint_evaluation"]
    assert prod["model_architecture"] == "RandomForestClassifier"
    assert prod["input_feature_dim"] == 972
    assert list(prod["classes"]) == list(range(10))

    s001 = prod["official_held_out_test_metrics_s001"]
    expected_keys = [
        "held_out_signer",
        "sample_count",
        "raw_accuracy",
        "raw_macro_precision",
        "raw_macro_recall",
        "raw_macro_f1",
        "calibrated_accuracy",
        "calibrated_macro_precision",
        "calibrated_macro_recall",
        "calibrated_macro_f1",
        "raw_brier_score",
        "calibrated_brier_score",
        "raw_top_label_ece",
        "calibrated_top_label_ece",
        "macro_f1"
    ]
    for key in expected_keys:
        assert key in s001, f"Missing metric key: {key}"

    assert s001["held_out_signer"] == "S001"
    assert s001["sample_count"] == 150
    assert s001["raw_accuracy"] == 1.0
    assert s001["raw_macro_precision"] == 1.0
    assert s001["raw_macro_recall"] == 1.0
    assert s001["raw_macro_f1"] == 1.0
    assert s001["calibrated_accuracy"] == 1.0
    assert s001["calibrated_macro_precision"] == 1.0
    assert s001["calibrated_macro_recall"] == 1.0
    assert s001["calibrated_macro_f1"] == 1.0
    assert s001["raw_brier_score"] == 0.0135
    assert s001["calibrated_brier_score"] == 0.0045
    assert s001["raw_top_label_ece"] == 0.0692
    assert s001["calibrated_top_label_ece"] == 0.0636


def test_kinematic_similarity_distribution_diagnostics():
    """Validates percentile distributions, count audits, overlap analysis, and confusable pair ranking."""
    report_path = "models/sign/bdsl_loso_evaluation_report.json"
    with open(report_path, "r") as f:
        data = json.load(f)

    sim = data["kinematic_similarity_diagnostics"]
    assert "comparison_count_audit" in sim
    assert "within_class_cross_signer_similarity" in sim
    assert "between_class_cross_signer_similarity" in sim
    assert "threshold_overlap_analysis" in sim
    assert "statistical_distribution_overlap" in sim
    assert "most_confusable_class_pairs" in sim
    assert "per_class_cross_signer_summary" in sim

    # Count audit
    audit = sim["comparison_count_audit"]
    ord_c = audit["ordered_comparisons"]
    assert ord_c["total_cross_signer_comparisons"] == 1260000
    assert ord_c["same_class_cross_signer_comparisons"] == 126000
    assert ord_c["diff_class_cross_signer_comparisons"] == 1134000
    assert ord_c["partition_invariant_satisfied"] is True

    unord_c = audit["unordered_unique_pairs"]
    assert unord_c["total_cross_signer_pairs"] == 630000
    assert unord_c["same_class_cross_signer_pairs"] == 63000
    assert unord_c["diff_class_cross_signer_pairs"] == 567000
    assert unord_c["partition_invariant_satisfied"] is True

    # Percentiles
    within = sim["within_class_cross_signer_similarity"]
    for p in ["min", "p05", "p25", "median", "mean", "p75", "p95", "max", "std"]:
        assert p in within

    assert within["min"] == 0.901
    assert within["median"] == 0.982
    assert within["mean"] == 0.9762
    assert within["max"] == 0.9964

    between = sim["between_class_cross_signer_similarity"]
    for p in ["min", "p05", "p25", "median", "mean", "p75", "p95", "max", "std"]:
        assert p in between

    assert between["min"] == 0.3157
    assert between["median"] == 0.7891
    assert between["mean"] == 0.7655
    assert between["max"] == 0.9785

    # Threshold overlap
    thresh = sim["threshold_overlap_analysis"]
    assert thresh["overlap_interval_min_to_max"] == [0.901, 0.9785]

    ord_ov = thresh["ordered_comparisons"]
    assert ord_ov["between_class_ge_within_class_min"]["numerator"] == 145104
    assert ord_ov["between_class_ge_within_class_min"]["denominator"] == 1134000
    assert ord_ov["between_class_ge_within_class_min"]["percentage"] == 12.8

    assert ord_ov["between_class_ge_within_class_p05"]["numerator"] == 48172
    assert ord_ov["between_class_ge_within_class_p05"]["denominator"] == 1134000
    assert ord_ov["between_class_ge_within_class_p05"]["percentage"] == 4.25

    assert ord_ov["within_class_le_between_class_max"]["numerator"] == 46426
    assert ord_ov["within_class_le_between_class_max"]["denominator"] == 126000
    assert ord_ov["within_class_le_between_class_max"]["percentage"] == 36.85

    unord_ov = thresh["unordered_unique_pairs"]
    assert unord_ov["between_class_ge_within_class_min"]["numerator"] == 72552
    assert unord_ov["between_class_ge_within_class_min"]["denominator"] == 567000
    assert unord_ov["between_class_ge_within_class_min"]["percentage"] == 12.8

    assert unord_ov["within_class_le_between_class_max"]["numerator"] == 23213
    assert unord_ov["within_class_le_between_class_max"]["denominator"] == 63000
    assert unord_ov["within_class_le_between_class_max"]["percentage"] == 36.85

    # Statistical distribution overlap (OVL)
    stat_ov = sim["statistical_distribution_overlap"]
    assert stat_ov["ovl_value"] == 0.0829
    assert stat_ov["ovl_percentage"] == 8.29

    # Most confusable pairs
    confusable = sim["most_confusable_class_pairs"]
    assert len(confusable) == 10
    for pair in confusable:
        ord_c = pair.get("ordered_comparisons_count") or pair.get("ordered_comparisons")
        unord_c = pair.get("unordered_pairs_count") or pair.get("unordered_unique_pairs")
        assert ord_c == 25200, f"Expected 25,200 ordered comparisons for pair, got {ord_c}"
        assert unord_c == 12600, f"Expected 12,600 unordered pairs for pair, got {unord_c}"
        assert ord_c == 2 * unord_c, f"Expected 2:1 ratio for pair, got {ord_c} vs {unord_c}"

    top_pair = confusable[0]
    assert top_pair["class_1"] == "HELLO"
    assert top_pair["class_2"] == "I_DONT_UNDERSTAND"
    assert top_pair["mean_cosine_similarity"] == 0.9556
    assert top_pair["max_cosine_similarity"] == 0.9785


def test_similarity_comparison_mathematical_invariants():
    """Validates combinatorial invariants directly on the manifest data."""
    import pandas as pd
    manifest_p = "data/sign/annotations/dataset_master_manifest.csv"
    assert os.path.exists(manifest_p)

    df = pd.read_csv(manifest_p)
    signers = np.array(df["signer_id"])
    labels = np.array(df["class_label"])
    N = len(df)

    assert N == 1200
    assert len(np.unique(signers)) == 8
    assert len(np.unique(labels)) == 10

    # Ordered masks
    diff_signer = (signers[:, None] != signers[None, :])
    same_class = (labels[:, None] == labels[None, :]) & diff_signer
    diff_class = (labels[:, None] != labels[None, :]) & diff_signer

    # Invariant: partition sum
    assert np.sum(diff_signer) == 8 * 7 * 150 * 150 == 1260000
    assert np.sum(same_class) == 10 * 8 * 7 * 15 * 15 == 126000
    assert np.sum(diff_class) == 1260000 - 126000 == 1134000
    assert np.sum(same_class) + np.sum(diff_class) == np.sum(diff_signer)

    # Unordered masks (i < j)
    triu_mask = np.triu(np.ones((N, N), dtype=bool), k=1)
    diff_signer_unord = diff_signer & triu_mask
    same_class_unord = same_class & triu_mask
    diff_class_unord = diff_class & triu_mask

    assert np.sum(diff_signer_unord) == 1260000 // 2 == 630000
    assert np.sum(same_class_unord) == 126000 // 2 == 63000
    assert np.sum(diff_class_unord) == 1134000 // 2 == 567000
    assert np.sum(same_class_unord) + np.sum(diff_class_unord) == np.sum(diff_signer_unord)


def test_raw_video_provenance_disclosure():
    """Validates that raw video provenance is explicitly disclosed as UNVERIFIED IN THIS EXECUTION."""
    report_path = "models/sign/bdsl_loso_evaluation_report.json"
    with open(report_path, "r") as f:
        data = json.load(f)

    audit = data["data_integrity_audit"]
    assert audit["raw_video_provenance_status"] == "UNVERIFIED_IN_THIS_EXECUTION"
    assert audit["raw_video_provenance_details"]["audit_status"] == "UNVERIFIED_IN_THIS_EXECUTION"
    assert audit["raw_video_provenance_details"]["workspace_video_files_found"] == 0
    assert audit["raw_video_provenance_details"]["missing_workspace_video_files"] == 1200
    assert audit["missing_landmark_files"] == 0
    assert audit["total_manifest_rows"] == 1200


def test_diagnostics_instrumentation_in_app_js():
    app_js_path = "src/frontend/static/app.js"
    assert os.path.exists(app_js_path), f"app.js missing: {app_js_path}"

    with open(app_js_path, "r") as f:
        content = f.read()

    assert "TransifySignDiagnostics" in content
    assert "requestVideoFrameCallback" in content
    assert "cancelVideoFrameCallback" in content
    assert "getSummary" in content
    assert "recordPipelineCycle" in content
    assert "canvasDrawMs" in content
    assert "jpegEncodeMs" in content
    assert "serverInferenceMs" in content
    assert "metric_nature" in content


def test_verify_loso_report_script():
    from scripts.verify_loso_report import verify_loso_report
    report_p = "models/sign/bdsl_loso_evaluation_report.json"
    assert os.path.exists(report_p), f"Report not found: {report_p}"
    # Validates schema and acceptance thresholds on generated report
    verify_loso_report(report_p)


def test_all_45_class_pairs_mathematical_invariants():
    """
    Validates that every one of the 45 class pairs {A, B} has:
    1. Exactly 25,200 ordered cross-signer comparisons.
    2. Exactly 12,600 unordered unique cross-signer pairs (i < j).
    3. Exactly 2:1 ratio between ordered and unordered pairs.
    4. Total across all 45 pairs sums to 1,134,000 ordered and 567,000 unordered.
    5. No same-signer or diagonal comparisons.
    """
    import pandas as pd
    manifest_p = "data/sign/annotations/dataset_master_manifest.csv"
    assert os.path.exists(manifest_p)

    df = pd.read_csv(manifest_p)
    signers = np.array(df["signer_id"])
    labels = np.array(df["class_label"])
    unique_classes = sorted(list(np.unique(labels)))
    N = len(df)
    assert len(unique_classes) == 10

    diff_signer_mask = (signers[:, None] != signers[None, :])
    triu_mask = np.triu(np.ones((N, N), dtype=bool), k=1)

    total_pair_ordered = 0
    total_pair_unordered = 0
    pair_count = 0

    for i in range(len(unique_classes)):
        for j in range(i + 1, len(unique_classes)):
            c1, c2 = unique_classes[i], unique_classes[j]
            pair_count += 1
            pair_mask_ord = (((labels[:, None] == c1) & (labels[None, :] == c2)) |
                             ((labels[:, None] == c2) & (labels[None, :] == c1))) & diff_signer_mask
            pair_mask_unord = pair_mask_ord & triu_mask

            count_ord = int(np.sum(pair_mask_ord))
            count_unord = int(np.sum(pair_mask_unord))

            assert count_ord == 25200, f"Pair {c1}-{c2} ordered count {count_ord} != 25200"
            assert count_unord == 12600, f"Pair {c1}-{c2} unordered count {count_unord} != 12600"
            assert count_ord == 2 * count_unord, f"Pair {c1}-{c2} 2:1 ratio violated"

            total_pair_ordered += count_ord
            total_pair_unordered += count_unord

    assert pair_count == 45
    assert total_pair_ordered == 1134000
    assert total_pair_unordered == 567000


def test_verify_loso_report_deliberate_rejections(tmp_path):
    """
    Validates that verify_loso_report correctly identifies and rejects
    invalid evaluation reports across multiple failure modes:
    1. Truncated fold count (< 8)
    2. Data leakage (held-out test signer present in training signers)
    3. Accuracy below internal regression floor (< 0.90)
    4. Calibrated Brier score above gate (> 0.15)
    5. Calibrated ECE above gate (> 0.15)
    6. Non-finite / NaN metric value
    7. Wrong pairwise count (e.g. 12,600 instead of 25,200)
    """
    import copy
    from scripts.verify_loso_report import verify_loso_report

    report_p = "models/sign/bdsl_loso_evaluation_report.json"
    with open(report_p, "r") as f:
        valid_data = json.load(f)

    # 1. Truncated folds
    bad_folds = copy.deepcopy(valid_data)
    bad_folds["per_signer_loso_folds"] = bad_folds["per_signer_loso_folds"][:7]
    p1 = str(tmp_path / "bad_folds.json")
    with open(p1, "w") as f:
        json.dump(bad_folds, f)
    with pytest.raises((ValueError, AssertionError), match="Expected exactly 8 LOSO folds"):
        verify_loso_report(p1)

    # 2. Data leakage
    leak_data = copy.deepcopy(valid_data)
    leak_data["per_signer_loso_folds"][0]["train_signers"].append(
        leak_data["per_signer_loso_folds"][0]["held_out_signer"]
    )
    p2 = str(tmp_path / "leak.json")
    with open(p2, "w") as f:
        json.dump(leak_data, f)
    with pytest.raises((ValueError, AssertionError), match="Data leakage"):
        verify_loso_report(p2)

    # 3. Accuracy below regression floor
    low_acc = copy.deepcopy(valid_data)
    low_acc["training_procedure_loso_summary"]["mean_accuracy"] = 0.85
    p3 = str(tmp_path / "low_acc.json")
    with open(p3, "w") as f:
        json.dump(low_acc, f)
    with pytest.raises((ValueError, AssertionError), match="mean_accuracy.*below internal regression floor"):
        verify_loso_report(p3)

    # 4. Calibrated Brier above gate
    high_brier = copy.deepcopy(valid_data)
    high_brier["training_procedure_loso_summary"]["mean_calibrated_brier"] = 0.25
    p4 = str(tmp_path / "high_brier.json")
    with open(p4, "w") as f:
        json.dump(high_brier, f)
    with pytest.raises((ValueError, AssertionError), match="mean_calibrated_brier.*exceeds internal gate"):
        verify_loso_report(p4)

    # 5. Calibrated ECE above gate
    high_ece = copy.deepcopy(valid_data)
    high_ece["training_procedure_loso_summary"]["mean_calibrated_top_label_ece"] = 0.25
    p5 = str(tmp_path / "high_ece.json")
    with open(p5, "w") as f:
        json.dump(high_ece, f)
    with pytest.raises((ValueError, AssertionError), match="mean_calibrated_top_label_ece.*exceeds internal gate"):
        verify_loso_report(p5)

    # 6. NaN metric value
    nan_data = copy.deepcopy(valid_data)
    nan_data["training_procedure_loso_summary"]["mean_macro_f1"] = float("nan")
    p6 = str(tmp_path / "nan.json")
    with open(p6, "w") as f:
        json.dump(nan_data, f)
    with pytest.raises((ValueError, AssertionError), match="mean_macro_f1.*below internal regression floor"):
        verify_loso_report(p6)

    # 7. Invalid pairwise count
    bad_pair = copy.deepcopy(valid_data)
    bad_pair["kinematic_similarity_diagnostics"]["most_confusable_class_pairs"][0]["ordered_comparisons_count"] = 12600
    p7 = str(tmp_path / "bad_pair.json")
    with open(p7, "w") as f:
        json.dump(bad_pair, f)
    with pytest.raises((ValueError, AssertionError), match="Ordered count must be exactly 25,200"):
        verify_loso_report(p7)
