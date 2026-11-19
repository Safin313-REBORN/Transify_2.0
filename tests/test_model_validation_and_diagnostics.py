"""
Transify — Regression Tests for BdSL LOSO Model Validation & Performance Diagnostics
Validates:
1. BdSL LOSO evaluation report integrity and cross-signer generalization (8 signers, 1,200 samples).
2. HaGRID model manifest disclosures, 38D feature dimension, and prototype status.
3. TransifySignDiagnostics instrumentation presence and zero UI disruption in app.js.
"""

import os
import json
import pytest


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

    summary = data["summary_metrics"]
    assert summary["mean_accuracy"] >= 0.99, f"Expected mean accuracy >= 99%, got {summary['mean_accuracy']}"
    assert summary["mean_macro_f1"] >= 0.99, f"Expected mean macro F1 >= 99%, got {summary['mean_macro_f1']}"
    assert summary["mean_calibrated_brier"] <= 0.05, f"Expected Brier <= 0.05, got {summary['mean_calibrated_brier']}"
    assert summary["mean_calibrated_ece"] <= 0.05, f"Expected ECE <= 0.05, got {summary['mean_calibrated_ece']}"

    folds = data["per_signer_folds"]
    assert len(folds) == 8
    for fold in folds:
        assert fold["test_samples"] == 150
        assert fold["train_samples"] == 1050
        assert fold["accuracy"] >= 0.99
        assert fold["held_out_signer"] not in fold["train_signers"]


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


def test_diagnostics_instrumentation_in_app_js():
    app_js_path = "src/frontend/static/app.js"
    assert os.path.exists(app_js_path), f"app.js missing: {app_js_path}"

    with open(app_js_path, "r") as f:
        content = f.read()

    assert "TransifySignDiagnostics" in content
    assert "requestVideoFrameCallback" in content
    assert "getSummary" in content
    assert "recordPipelineCycle" in content
    assert "canvasDrawMs" in content
    assert "jpegEncodeMs" in content
    assert "serverInferenceMs" in content
