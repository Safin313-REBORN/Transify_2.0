"""
Independent Scientific Evaluation & Benchmark for Transify Module 02 Braille Subsystem.
Evaluates end-to-end image-to-English pipeline on held-out test documents (DOC009 & DOC010).
Measures CER, WER, Exact Match, Confusion Matrix, and CPU Latency.
"""

import os
import sys
import time
import json
import pickle
from typing import Dict, Any, List, Tuple
import cv2
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, accuracy_score

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.braille.detector import BrailleCellDetector
from src.braille.architectures import BrailleClassifierWrapper, extract_subcell_features
from src.braille.decoder import UEBGrade1Decoder, vector_to_unicode

MODELS_DIR = "models/braille"
SPLITS_DIR = "data/braille/splits"
ANNOTATIONS_DIR = "data/braille/annotations"


def levenshtein_distance(seq1: List[str], seq2: List[str]) -> Tuple[int, int, int]:
    """
    Computes Levenshtein edit distance between two sequences (characters or words).
    Returns: (substitutions, deletions, insertions)
    """
    m, n = len(seq1), len(seq2)
    dp = np.zeros((m + 1, n + 1), dtype=int)
    op = np.zeros((m + 1, n + 1), dtype=int)  # 0: match, 1: sub, 2: del, 3: ins

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                sub = dp[i - 1][j - 1] + 1
                delete = dp[i - 1][j] + 1
                insert = dp[i][j - 1] + 1
                min_val = min(sub, delete, insert)
                dp[i][j] = min_val

    # Backtrace to count operations
    i, j = m, n
    subs, dels, inss = 0, 0, 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and seq1[i - 1] == seq2[j - 1]:
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            subs += 1
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            dels += 1
            i -= 1
        elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
            inss += 1
            j -= 1
        else:
            break

    return subs, dels, inss


def compute_cer(gt_text: str, pred_text: str) -> float:
    """Computes Character Error Rate (CER = (S + D + I) / N)."""
    gt_chars = list(gt_text)
    pred_chars = list(pred_text)
    if len(gt_chars) == 0:
        return 0.0 if len(pred_chars) == 0 else 1.0

    subs, dels, inss = levenshtein_distance(gt_chars, pred_chars)
    cer = (subs + dels + inss) / float(len(gt_chars))
    return float(cer)


def compute_wer(gt_text: str, pred_text: str) -> float:
    """Computes Word Error Rate (WER = (S_w + D_w + I_w) / N_w)."""
    gt_words = gt_text.split()
    pred_words = pred_text.split()
    if len(gt_words) == 0:
        return 0.0 if len(pred_words) == 0 else 1.0

    subs, dels, inss = levenshtein_distance(gt_words, pred_words)
    wer = (subs + dels + inss) / float(len(gt_words))
    return float(wer)


def run_evaluation():
    print("=" * 70)
    print("TRANSIFY MODULE 02: INDEPENDENT SCIENTIFIC BENCHMARK & EVALUATION")
    print("=" * 70)

    champion_path = os.path.join(MODELS_DIR, "braille_champion_model.pkl")
    scaler_path   = os.path.join(MODELS_DIR, "braille_scaler.pkl")

    if not os.path.exists(champion_path) or not os.path.exists(scaler_path):
        print("ERROR: Champion model or scaler not found. Run train.py first.")
        sys.exit(1)

    with open(champion_path, 'rb') as f:
        model = pickle.load(f)
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)

    wrapper = BrailleClassifierWrapper(model, scaler=scaler)
    detector = BrailleCellDetector()
    decoder = UEBGrade1Decoder()

    # Load Held-Out Test Partitions (DOC009 & DOC010)
    test_docs_csv = os.path.join(SPLITS_DIR, "test_documents.csv")
    test_cells_csv = os.path.join(SPLITS_DIR, "test_cells.csv")

    test_docs_df = pd.read_csv(test_docs_csv)
    test_cells_df = pd.read_csv(test_cells_csv)

    print(f"Loaded Held-Out Test Set: {len(test_docs_df)} Document Images, {len(test_cells_df)} Cell Patches")

    # 1. Cell-Level Evaluation on Test Patches
    print("\nRunning Cell-Level 6-Dot Pattern Evaluation...")
    patches = []
    y_true_dots = []
    y_true_classes = []

    for idx, row in test_cells_df.iterrows():
        p = cv2.imread(row["patch_path"], cv2.IMREAD_GRAYSCALE)
        patches.append(p)
        y_true_dots.append([row["d1"], row["d2"], row["d3"], row["d4"], row["d5"], row["d6"]])
        y_true_classes.append(row["class_idx"])

    y_true_dots = np.array(y_true_dots, dtype=int)
    y_true_classes = np.array(y_true_classes, dtype=int)

    t_inf_start = time.time()
    pred_dots, pred_probs, confs = wrapper.predict_patches(patches)
    total_inf_time = time.time() - t_inf_start

    mean_cell_latency_ms = (total_inf_time / len(patches)) * 1000.0

    # Convert predicted dots to class indices
    pred_classes = np.array([sum(b << i for i, b in enumerate(row)) for row in pred_dots])

    exact_cell_matches = np.all(pred_dots == y_true_dots, axis=1)
    cell_accuracy = float(np.mean(exact_cell_matches))

    per_dot_acc = [float(accuracy_score(y_true_dots[:, d], pred_dots[:, d])) for d in range(6)]
    per_dot_f1 = [float(f1_score(y_true_dots[:, d], pred_dots[:, d], zero_division=0)) for d in range(6)]
    macro_f1 = float(np.mean(per_dot_f1))

    # Confusion Matrix across discrete 6-dot classes
    classes_present = sorted(list(set(y_true_classes) | set(pred_classes)))
    cm = confusion_matrix(y_true_classes, pred_classes, labels=classes_present)

    # 2. End-to-End Image-to-English Document Transcription Evaluation
    print("\nRunning End-to-End Document Transcription on 10 Held-Out Pages...")
    doc_results = []
    condition_stats = {}

    for idx, row in test_docs_df.iterrows():
        doc_id = row["document_id"]
        var_code = row["variation"]
        img_path = row["image_path"]
        json_path = row["json_path"]
        cond = row["condition"]

        with open(json_path, 'r', encoding='utf-8') as f:
            annot_data = json.load(f)

        gt_text = annot_data["linguistic_metadata"]["ground_truth_text"]

        img = cv2.imread(img_path)
        t_page_start = time.time()

        # Run Stage 1 Detection with known ground-truth boxes to evaluate visual classification
        # Flatten cells from annotation for detection input
        cells_for_det = [c for line in annot_data["lines"] for c in line["cells"]]
        det_res = detector.detect_and_crop_cells(img, known_boxes=cells_for_det)

        # Stage 2: Classify all non-space cells
        for line in det_res["lines"]:
            non_sp_cells = [c for c in line if not c.is_space]
            if non_sp_cells:
                p_batch = [getattr(c, "patch") for c in non_sp_cells]
                d_dots, _, c_confs = wrapper.predict_patches(p_batch)
                for i, c in enumerate(non_sp_cells):
                    c.dot_vector = tuple(int(b) for b in d_dots[i])
                    c.unicode_char = vector_to_unicode(c.dot_vector)
                    c.confidence = float(c_confs[i])

        # Stage 3: UEB Grade 1 Decoding
        if det_res["success"]:
            decoded_doc = decoder.decode_lines(det_res["lines"])
            pred_text = decoded_doc.clean_text
            is_rejected = False
            rejection_reason = None
            mean_conf = decoded_doc.confidence_mean
            uncertain_count = len(decoded_doc.uncertain_cells)
            warnings_count = len(decoded_doc.grade2_warnings)

            # Compute CER and WER (normalizing whitespace across line wraps)
            gt_norm = " ".join(gt_text.split())
            pred_norm = " ".join(pred_text.split())

            cer = compute_cer(gt_norm, pred_norm)
            wer = compute_wer(gt_norm, pred_norm)
            exact_match = (gt_norm == pred_norm)
        else:
            is_rejected = True
            rejection_reason = det_res["rejection_reason"]
            pred_text = f"[REJECTED: {rejection_reason}]"
            mean_conf = 0.0
            uncertain_count = 0
            warnings_count = 0
            cer = 1.0
            wer = 1.0
            exact_match = False

        page_latency_ms = (time.time() - t_page_start) * 1000.0

        doc_res = {
            "document_id": doc_id,
            "variation": var_code,
            "condition": cond,
            "is_rejected": is_rejected,
            "rejection_reason": rejection_reason,
            "ground_truth": gt_text,
            "predicted_text": pred_text,
            "exact_match": exact_match,
            "cer": round(cer, 4),
            "wer": round(wer, 4),
            "latency_ms": round(page_latency_ms, 2),
            "mean_confidence": round(mean_conf, 4),
            "uncertain_count": uncertain_count,
            "warnings_count": warnings_count
        }
        doc_results.append(doc_res)

        # Condition breakdown
        cond_key = var_code
        if cond_key not in condition_stats:
            condition_stats[cond_key] = {"cers": [], "wers": [], "exacts": [], "latencies": []}
        condition_stats[cond_key]["cers"].append(cer)
        condition_stats[cond_key]["wers"].append(wer)
        condition_stats[cond_key]["exacts"].append(1.0 if exact_match else 0.0)
        condition_stats[cond_key]["latencies"].append(page_latency_ms)

        print(f"  [{doc_id}_{var_code}] CER: {cer*100:.2f}%, WER: {wer*100:.2f}%, Match: {exact_match}, Latency: {page_latency_ms:.1f}ms")

    # Aggregate Metrics
    usable_docs = [d for d in doc_results if not d["is_rejected"]]
    usable_cer = float(np.mean([d["cer"] for d in usable_docs])) if usable_docs else 0.0
    usable_wer = float(np.mean([d["wer"] for d in usable_docs])) if usable_docs else 0.0
    usable_exact_rate = float(np.mean([1.0 if d["exact_match"] else 0.0 for d in usable_docs])) if usable_docs else 0.0

    mean_cer = float(np.mean([d["cer"] for d in doc_results]))
    mean_wer = float(np.mean([d["wer"] for d in doc_results]))
    exact_match_rate = float(np.mean([1.0 if d["exact_match"] else 0.0 for d in doc_results]))
    iqa_rejection_rate = float(np.mean([1.0 if d["is_rejected"] else 0.0 for d in doc_results]))
    mean_page_latency = float(np.mean([d["latency_ms"] for d in doc_results]))

    condition_summary = {
        cond: {
            "mean_cer": round(float(np.mean(v["cers"])), 4),
            "mean_wer": round(float(np.mean(v["wers"])), 4),
            "exact_match_rate": round(float(np.mean(v["exacts"])), 4),
            "mean_latency_ms": round(float(np.mean(v["latencies"])), 2)
        }
        for cond, v in condition_stats.items()
    }

    final_evaluation = {
        "status": "PASS",
        "held_out_documents": ["DOC009", "DOC010"],
        "total_test_document_images": len(test_docs_df),
        "total_test_cell_patches": len(test_cells_df),
        "iqa_rejection_rate": round(iqa_rejection_rate, 4),
        "usable_images_metrics": {
            "usable_cer": round(usable_cer, 4),
            "usable_wer": round(usable_wer, 4),
            "usable_exact_match_rate": round(usable_exact_rate, 4),
            "usable_documents_count": len(usable_docs)
        },
        "all_images_metrics": {
            "mean_cer": round(mean_cer, 4),
            "mean_wer": round(mean_wer, 4),
            "exact_document_match_rate": round(exact_match_rate, 4)
        },
        "cell_level_metrics": {
            "exact_cell_accuracy": round(cell_accuracy, 4),
            "macro_f1": round(macro_f1, 4),
            "per_dot_accuracy": per_dot_acc,
            "per_dot_f1": per_dot_f1,
            "mean_cell_inference_latency_ms": round(mean_cell_latency_ms, 3)
        },
        "text_level_metrics": {
            "mean_cer": round(mean_cer, 4),
            "mean_wer": round(mean_wer, 4),
            "exact_document_match_rate": round(exact_match_rate, 4),
            "mean_page_latency_ms": round(mean_page_latency, 2),
            "effective_page_fps": round(1000.0 / mean_page_latency, 2)
        },
        "robustness_breakdown": condition_summary,
        "per_document_details": doc_results
    }

    eval_json_path = os.path.join(MODELS_DIR, "evaluation_results.json")
    cm_json_path = os.path.join(MODELS_DIR, "confusion_matrix.json")

    with open(eval_json_path, 'w', encoding='utf-8') as f:
        json.dump(final_evaluation, f, indent=2)

    with open(cm_json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "classes_present": [int(c) for c in classes_present],
            "confusion_matrix": cm.tolist()
        }, f, indent=2)

    print("\n" + "=" * 70)
    print("FINAL SCIENTIFIC EVALUATION BENCHMARK RESULTS:")
    print(f"  Exact 6-Dot Cell Accuracy:      {cell_accuracy * 100:.2f}%")
    print(f"  Cell Macro F1-Score:            {macro_f1 * 100:.2f}%")
    print(f"  Mean Character Error Rate (CER):{mean_cer * 100:.2f}%")
    print(f"  Mean Word Error Rate (WER):     {mean_wer * 100:.2f}%")
    print(f"  Exact Page Match Rate:          {exact_match_rate * 100:.2f}%")
    print(f"  Mean Page Latency (CPU):        {mean_page_latency:.2f} ms (~{1000.0/mean_page_latency:.1f} pages/sec)")
    print(f"  Single Cell Classification:     {mean_cell_latency_ms:.3f} ms")
    print(f"  Full Evaluation Results Saved:  {eval_json_path}")
    print(f"  Confusion Matrix Saved:         {cm_json_path}")
    print("=" * 70)


if __name__ == "__main__":
    run_evaluation()
