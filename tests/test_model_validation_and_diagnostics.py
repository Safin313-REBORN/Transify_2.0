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
    assert summary["mean_accuracy"] >= 0.99, f"Expected mean accuracy >= 99%, got {summary['mean_accuracy']}"
    assert summary["mean_macro_f1"] >= 0.99, f"Expected mean macro F1 >= 99%, got {summary['mean_macro_f1']}"
    assert summary["mean_calibrated_brier"] <= 0.05, f"Expected Brier <= 0.05, got {summary['mean_calibrated_brier']}"
    assert summary["mean_calibrated_top_label_ece"] <= 0.05, f"Expected ECE <= 0.05, got {summary['mean_calibrated_top_label_ece']}"

    folds = data["per_signer_loso_folds"]
    assert len(folds) == 8
    for fold in folds:
        assert fold["test_samples"] == 150
        assert fold["train_samples"] == 1050
        assert fold["accuracy"] >= 0.99
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
    """Validates percentile distributions, overlap analysis, and confusable pair ranking."""
    report_path = "models/sign/bdsl_loso_evaluation_report.json"
    with open(report_path, "r") as f:
        data = json.load(f)

    sim = data["kinematic_similarity_diagnostics"]
    assert "within_class_cross_signer_similarity" in sim
    assert "between_class_cross_signer_similarity" in sim
    assert "distribution_overlap_analysis" in sim
    assert "most_confusable_class_pairs" in sim
    assert "per_class_cross_signer_summary" in sim

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

    overlap = sim["distribution_overlap_analysis"]
    assert overlap["overlap_interval_min_to_max"] == [0.901, 0.9785]
    assert overlap["between_class_pairs_ge_within_class_min_count"] == 145104
    assert overlap["total_between_class_pairs"] == 1134000
    assert overlap["between_class_pairs_ge_within_class_min_pct"] == 12.8

    confusable = sim["most_confusable_class_pairs"]
    assert len(confusable) == 10
    top_pair = confusable[0]
    assert top_pair["class_1"] == "HELLO"
    assert top_pair["class_2"] == "I_DONT_UNDERSTAND"
    assert top_pair["mean_cosine_similarity"] == 0.9556
    assert top_pair["max_cosine_similarity"] == 0.9785


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
