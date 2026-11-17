"""
Document-Independent Dataset Partitioning for Transify Module 02 Braille Subsystem.
Enforces strict anti-leakage splitting: all variations of a physical document
are isolated within the same partition (Train, Validation, or Test).
"""

import os
import sys
import json
import pandas as pd

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

ANNOTATIONS_DIR = "data/braille/annotations"
SPLITS_DIR = "data/braille/splits"
os.makedirs(SPLITS_DIR, exist_ok=True)

# Document-Independent Splitting Plan
# 70% Train (7 docs), 15% Val (1 doc), 15% Test (2 docs)
TRAIN_DOC_IDS = ["DOC001", "DOC002", "DOC003", "DOC004", "DOC006", "DOC007", "DOC008"]
VAL_DOC_IDS   = ["DOC005"]
TEST_DOC_IDS  = ["DOC009", "DOC010"]


def partition_braille_dataset():
    print("=" * 70)
    print("TRANSIFY MODULE 02: DOCUMENT-INDEPENDENT DATASET SPLITTING")
    print("=" * 70)

    doc_manifest_path = os.path.join(ANNOTATIONS_DIR, "document_manifest.csv")
    cell_manifest_path = os.path.join(ANNOTATIONS_DIR, "cell_manifest.csv")

    doc_df = pd.read_csv(doc_manifest_path)
    cell_df = pd.read_csv(cell_manifest_path)

    # 1. Split Document Manifest
    train_docs = doc_df[doc_df["document_id"].isin(TRAIN_DOC_IDS)].copy()
    val_docs   = doc_df[doc_df["document_id"].isin(VAL_DOC_IDS)].copy()
    test_docs  = doc_df[doc_df["document_id"].isin(TEST_DOC_IDS)].copy()

    train_docs.to_csv(os.path.join(SPLITS_DIR, "train_documents.csv"), index=False)
    val_docs.to_csv(os.path.join(SPLITS_DIR, "val_documents.csv"), index=False)
    test_docs.to_csv(os.path.join(SPLITS_DIR, "test_documents.csv"), index=False)

    # 2. Split Cell Manifest
    train_cells = cell_df[cell_df["document_id"].isin(TRAIN_DOC_IDS)].copy()
    val_cells   = cell_df[cell_df["document_id"].isin(VAL_DOC_IDS)].copy()
    test_cells  = cell_df[cell_df["document_id"].isin(TEST_DOC_IDS)].copy()

    train_cells.to_csv(os.path.join(SPLITS_DIR, "train_cells.csv"), index=False)
    val_cells.to_csv(os.path.join(SPLITS_DIR, "val_cells.csv"), index=False)
    test_cells.to_csv(os.path.join(SPLITS_DIR, "test_cells.csv"), index=False)

    split_manifest = {
        "strategy": "Document-Independent Anti-Leakage Partitioning",
        "train": {
            "documents": TRAIN_DOC_IDS,
            "document_images": len(train_docs),
            "cell_patches": len(train_cells),
            "percentage_cells": round((len(train_cells) / len(cell_df)) * 100.0, 2)
        },
        "validation": {
            "documents": VAL_DOC_IDS,
            "document_images": len(val_docs),
            "cell_patches": len(val_cells),
            "percentage_cells": round((len(val_cells) / len(cell_df)) * 100.0, 2)
        },
        "test": {
            "documents": TEST_DOC_IDS,
            "document_images": len(test_docs),
            "cell_patches": len(test_cells),
            "percentage_cells": round((len(test_cells) / len(cell_df)) * 100.0, 2)
        }
    }

    with open(os.path.join(SPLITS_DIR, "split_summary.json"), 'w', encoding='utf-8') as f:
        json.dump(split_manifest, f, indent=2)

    print(f"Train Set: {len(TRAIN_DOC_IDS)} Documents ({len(train_docs)} Images, {len(train_cells)} Cells - {split_manifest['train']['percentage_cells']}%)")
    print(f"Val Set:   {len(VAL_DOC_IDS)} Documents ({len(val_docs)} Images, {len(val_cells)} Cells - {split_manifest['validation']['percentage_cells']}%)")
    print(f"Test Set:  {len(TEST_DOC_IDS)} Documents ({len(test_docs)} Images, {len(test_cells)} Cells - {split_manifest['test']['percentage_cells']}%)")
    print("=" * 70)


if __name__ == "__main__":
    partition_braille_dataset()
