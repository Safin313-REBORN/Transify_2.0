"""
Automated Dataset Integrity & Quality Auditor for Transify Module 02 Braille Subsystem.
Audits document images, annotations, extracted patches, and class balance.
"""

import os
import sys
import json
import cv2
import pandas as pd
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.braille.validate_annotations import AnnotationValidator

ANNOTATIONS_DIR = "data/braille/annotations"
RAW_DIR = "data/braille/raw"
CELLS_DIR = "data/braille/processed/cells"
AUDIT_JSON_PATH = os.path.join(ANNOTATIONS_DIR, "dataset_quality_audit.json")


def inspect_braille_dataset():
    print("=" * 70)
    print("TRANSIFY MODULE 02: BRAILLE DATASET INTEGRITY & QUALITY AUDIT")
    print("=" * 70)

    validator = AnnotationValidator()
    doc_manifest_path = os.path.join(ANNOTATIONS_DIR, "document_manifest.csv")
    cell_manifest_path = os.path.join(ANNOTATIONS_DIR, "cell_manifest.csv")

    if not os.path.exists(doc_manifest_path) or not os.path.exists(cell_manifest_path):
        print("ERROR: Master manifests missing! Run prepare_dataset.py first.")
        sys.exit(1)

    doc_df = pd.read_csv(doc_manifest_path)
    cell_df = pd.read_csv(cell_manifest_path)

    print(f"Total registered documents in manifest: {len(doc_df)}")
    print(f"Total registered cell patches in manifest: {len(cell_df)}")

    # 1. Audit Document Images & JSON Annotations
    corrupted_images = 0
    annotation_errors = 0
    total_lines = 0

    for idx, row in doc_df.iterrows():
        img_path = row["image_path"]
        json_path = row["json_path"]

        # Check image existence & read
        if not os.path.exists(img_path):
            print(f"  [ERROR] Image not found: {img_path}")
            corrupted_images += 1
            continue

        img = cv2.imread(img_path)
        if img is None or img.size == 0:
            print(f"  [ERROR] Corrupted image: {img_path}")
            corrupted_images += 1
            continue

        # Check JSON validity
        val_res = validator.validate_file(json_path)
        if not val_res["valid"]:
            print(f"  [ERROR] Annotation error in {json_path}: {val_res['errors']}")
            annotation_errors += 1
        total_lines += val_res.get("total_lines", 0)

    # 2. Audit Cell Patches
    corrupted_patches = 0
    patch_shapes = set()

    for idx, row in cell_df.iterrows():
        p_path = row["patch_path"]
        if not os.path.exists(p_path):
            corrupted_patches += 1
            continue
        patch = cv2.imread(p_path, cv2.IMREAD_GRAYSCALE)
        if patch is None or patch.size == 0:
            corrupted_patches += 1
            continue
        patch_shapes.add(patch.shape)

    # 3. Class Balance & Distribution
    unique_classes = cell_df["class_idx"].nunique()
    dot_activity = {
        "d1_active_pct": round(float((cell_df["d1"].sum() / len(cell_df)) * 100.0), 2),
        "d2_active_pct": round(float((cell_df["d2"].sum() / len(cell_df)) * 100.0), 2),
        "d3_active_pct": round(float((cell_df["d3"].sum() / len(cell_df)) * 100.0), 2),
        "d4_active_pct": round(float((cell_df["d4"].sum() / len(cell_df)) * 100.0), 2),
        "d5_active_pct": round(float((cell_df["d5"].sum() / len(cell_df)) * 100.0), 2),
        "d6_active_pct": round(float((cell_df["d6"].sum() / len(cell_df)) * 100.0), 2),
    }

    audit_summary = {
        "status": "PASS" if (corrupted_images == 0 and corrupted_patches == 0 and annotation_errors == 0) else "FAIL",
        "total_documents": len(doc_df),
        "total_cell_patches": len(cell_df),
        "corrupted_images": corrupted_images,
        "corrupted_patches": corrupted_patches,
        "annotation_errors": annotation_errors,
        "total_lines_audited": total_lines,
        "patch_shapes": [list(s) for s in patch_shapes],
        "unique_6dot_classes": unique_classes,
        "dot_activity_percentages": dot_activity
    }

    with open(AUDIT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(audit_summary, f, indent=2)

    print("\n" + "-" * 70)
    print("AUDIT SUMMARY RESULTS:")
    print(f"  Audit Status:              {audit_summary['status']}")
    print(f"  Corrupted Documents:       {corrupted_images} / {len(doc_df)}")
    print(f"  Corrupted Cell Patches:    {corrupted_patches} / {len(cell_df)}")
    print(f"  Annotation Errors:         {annotation_errors}")
    print(f"  Uniform Patch Shape:       {list(patch_shapes)}")
    print(f"  Unique 6-Dot Classes:      {unique_classes} / 64")
    print(f"  Individual Dot Activity:   {dot_activity}")
    print(f"  Full Audit Report Saved:   {AUDIT_JSON_PATH}")
    print("-" * 70)


if __name__ == "__main__":
    inspect_braille_dataset()
