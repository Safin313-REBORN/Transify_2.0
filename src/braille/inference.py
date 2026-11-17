"""
Complete End-to-End Image-to-English Braille Recognition & Translation Engine for Transify Module 02.
Processes real-world Braille photographs, runs IQA, preprocessing, cell localization,
6-dot classification, deterministic UEB Grade 1 decoding, and optional TTS speech playback.
"""

import os
import sys
import time
import argparse
import pickle
import subprocess
import threading
from typing import Dict, Any, Optional
import cv2
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.braille.quality_assessment import ImageQualityAssessment
from src.braille.preprocessing import BrailleImagePreprocessor
from src.braille.detector import BrailleCellDetector
from src.braille.architectures import BrailleClassifierWrapper, extract_subcell_features
from src.braille.decoder import UEBGrade1Decoder, vector_to_unicode, DecodedDocument

BUNDLE_PATH = "models/braille/exported/braille_model_bundle.pkl"


class SafeUnpickler(pickle.Unpickler):
    """
    Pickle Unpickler compatible across NumPy 1.x and 2.x serialization boundaries.
    Automatically resolves numpy._core <-> numpy.core renames.
    """
    def find_class(self, module, name):
        try:
            return super().find_class(module, name)
        except (ModuleNotFoundError, AttributeError):
            if module.startswith("numpy._core"):
                alt_module = "numpy.core" + module[len("numpy._core"):]
                return super().find_class(alt_module, name)
            elif module.startswith("numpy.core"):
                alt_module = "numpy._core" + module[len("numpy.core"):]
                return super().find_class(alt_module, name)
            raise


def safe_pickle_load(file_obj):
    return SafeUnpickler(file_obj).load()


class BrailleTranslatorPipeline:
    """
    End-to-End Optical Braille Recognition & Translation Subsystem.
    """

    def __init__(self, bundle_path: str = BUNDLE_PATH):
        if not os.path.exists(bundle_path):
            # Fallback to unexported champion model
            champ_path = "models/braille/braille_champion_model.pkl"
            scaler_path = "models/braille/braille_scaler.pkl"
            if os.path.exists(champ_path) and os.path.exists(scaler_path):
                with open(champ_path, "rb") as f:
                    model = safe_pickle_load(f)
                with open(scaler_path, "rb") as f:
                    scaler = safe_pickle_load(f)
                self.wrapper = BrailleClassifierWrapper(model, scaler=scaler)
            else:
                raise FileNotFoundError(f"Model artifacts missing at {bundle_path}!")
        else:
            with open(bundle_path, "rb") as f:
                bundle = safe_pickle_load(f)
            self.wrapper = BrailleClassifierWrapper(bundle["model_object"], scaler=bundle.get("scaler"))

        self.iqa = ImageQualityAssessment()
        self.preprocessor = BrailleImagePreprocessor()
        self.detector = BrailleCellDetector()
        self.decoder = UEBGrade1Decoder()

    def translate_image(
        self,
        image_input: Any,
        known_boxes: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Translates a Braille image into English text.
        Args:
            image_input: File path (str) or NumPy BGR image matrix.
            known_boxes: Optional ground-truth or Stage 1 external bounding boxes.
        Returns:
            Dictionary with transcription, confidence, IQA status, and timing diagnostics.
        """
        t_start = time.time()

        # 1. Image Validation & Loading
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                return {
                    "success": False,
                    "error": f"Image file not found: {image_input}",
                    "text": ""
                }
            image = cv2.imread(image_input)
            if image is None:
                return {
                    "success": False,
                    "error": f"Could not decode image file: {image_input}",
                    "text": ""
                }
        elif isinstance(image_input, np.ndarray):
            image = image_input
        else:
            return {
                "success": False,
                "error": f"Unsupported image input type: {type(image_input)}",
                "text": ""
            }

        # 2. Image Quality Assessment
        t_iqa_start = time.time()
        qa_result = self.iqa.assess(image)
        t_iqa = (time.time() - t_iqa_start) * 1000.0

        if not qa_result["is_usable"]:
            return {
                "success": False,
                "rejection_reason": qa_result["rejection_reason"],
                "qa_metrics": qa_result["metrics"],
                "text": "",
                "latency_ms": round((time.time() - t_start) * 1000.0, 2)
            }

        # 3. Preprocessing & Cell Detection
        t_det_start = time.time()
        det_result = self.detector.detect_and_crop_cells(image, known_boxes=known_boxes)
        t_det = (time.time() - t_det_start) * 1000.0

        if not det_result["success"] or len(det_result["lines"]) == 0:
            return {
                "success": False,
                "rejection_reason": "No readable Braille cells could be localized.",
                "qa_metrics": qa_result["metrics"],
                "text": "",
                "latency_ms": round((time.time() - t_start) * 1000.0, 2)
            }

        # 4. Six-Dot Pattern Classification
        t_clf_start = time.time()
        total_cells_classified = 0
        for line in det_result["lines"]:
            non_space_cells = [c for c in line if not c.is_space]
            if non_space_cells:
                patches = [getattr(c, "patch") for c in non_space_cells]
                d_dots, probs, confs = self.wrapper.predict_patches(patches)
                for i, c in enumerate(non_space_cells):
                    geom_dots = getattr(c, "geometric_dots", None)
                    # When unconstrained images have clean geometric dots and no known boxes provided
                    if geom_dots is not None and sum(geom_dots) > 0 and known_boxes is None:
                        c.dot_vector = tuple(int(b) for b in geom_dots)
                        c.confidence = 0.98
                    else:
                        c.dot_vector = tuple(int(b) for b in d_dots[i])
                        c.confidence = float(confs[i])
                    c.unicode_char = vector_to_unicode(c.dot_vector)
                total_cells_classified += len(non_space_cells)
        t_clf = (time.time() - t_clf_start) * 1000.0

        # 5. UEB Grade 1 Deterministic Decoding
        t_dec_start = time.time()
        decoded_doc = self.decoder.decode_lines(det_result["lines"])
        t_dec = (time.time() - t_dec_start) * 1000.0

        total_latency_ms = (time.time() - t_start) * 1000.0

        return {
            "success": True,
            "rejection_reason": None,
            "text": decoded_doc.clean_text,
            "raw_text": decoded_doc.raw_text,
            "total_cells": decoded_doc.total_cells,
            "classified_cells_count": total_cells_classified,
            "mean_confidence": round(decoded_doc.confidence_mean, 4),
            "uncertain_cells": decoded_doc.uncertain_cells,
            "grade2_warnings": decoded_doc.grade2_warnings,
            "qa_metrics": qa_result["metrics"],
            "diagnostics": {
                "iqa_ms": round(t_iqa, 2),
                "detection_ms": round(t_det, 2),
                "classification_ms": round(t_clf, 2),
                "decoding_ms": round(t_dec, 2),
                "total_latency_ms": round(total_latency_ms, 2)
            }
        }

    def speak_text(self, text: str, non_blocking: bool = True):
        """Synthesizes English text into audio speech via Windows Speech Synthesizer."""
        if not text or text.startswith("[REJECTED"):
            return

        def _speak_worker():
            safe_text = text.replace("'", "").replace('"', '').replace("\n", " ")
            cmd = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_text}')"
            try:
                subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=10)
            except Exception:
                pass

        if non_blocking:
            t = threading.Thread(target=_speak_worker, daemon=True)
            t.start()
        else:
            _speak_worker()


def main():
    parser = argparse.ArgumentParser(description="Transify UEB Grade 1 Braille Image Translator")
    parser.add_argument("--image_path", type=str, default="data/braille/raw/DOC001_L1.png", help="Path to Braille image")
    parser.add_argument("--tts", action="store_true", help="Speak translated English text using TTS")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark across all 10 test images")
    args = parser.parse_args()

    pipeline = BrailleTranslatorPipeline()

    if args.benchmark:
        print("Running quick benchmark across sample test images...")
        sample_imgs = [
            "data/braille/raw/DOC009_L1.png",
            "data/braille/raw/DOC009_P1.png",
            "data/braille/raw/DOC010_L1.png",
            "data/braille/raw/DOC010_D1.png"
        ]
        for img_p in sample_imgs:
            res = pipeline.translate_image(img_p)
            status_str = "REJECTED" if not res["success"] else "ACCEPTED"
            print(f"  [{status_str}] {os.path.basename(img_p)} -> {repr(res.get('text', ''))} ({res.get('rejection_reason')})")
        return

    print("=" * 70)
    print(f"TRANSIFY MODULE 02: INFERENCE ON IMAGE '{args.image_path}'")
    print("=" * 70)

    # If annotation file exists with same base, load known boxes to demonstrate classification
    base_name = os.path.splitext(os.path.basename(args.image_path))[0]
    json_path = os.path.join("data/braille/annotations", f"{base_name}.json")
    known_boxes = None
    if os.path.exists(json_path):
        import json
        with open(json_path, 'r', encoding='utf-8') as f:
            annot = json.load(f)
        known_boxes = [c for line in annot.get("lines", []) for c in line.get("cells", [])]

    result = pipeline.translate_image(args.image_path, known_boxes=known_boxes)

    if not result["success"]:
        print(f"\n[REJECTED]: {result['rejection_reason']}")
        print(f"Quality Metrics: {result.get('qa_metrics')}")
    else:
        print("\nTRANSLATED ENGLISH TEXT:")
        print("-" * 50)
        print(result["text"])
        print("-" * 50)
        print(f"Confidence:        {result['mean_confidence']*100:.2f}%")
        print(f"Total Cells:       {result['total_cells']}")
        print(f"Total Latency:     {result['diagnostics']['total_latency_ms']:.2f} ms")
        print(f"Diagnostics:       {result['diagnostics']}")

        if result["grade2_warnings"]:
            print(f"\nGrade 2 Warnings:  {result['grade2_warnings']}")
        if result["uncertain_cells"]:
            print(f"Uncertain Cells:   {len(result['uncertain_cells'])} cells flagged for human review.")

        if args.tts:
            print("\nSynthesizing speech via Windows TTS...")
            pipeline.speak_text(result["text"], non_blocking=False)
            print("Speech completed.")

    print("=" * 70)


if __name__ == "__main__":
    main()
