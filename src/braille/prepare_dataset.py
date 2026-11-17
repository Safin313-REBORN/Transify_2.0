"""
Master Dataset Engineering & Realistic Physical Embossing Renderer for Transify Module 02.
Produces 10 multi-line UEB Grade 1 documents with physical 3D raking-light relief,
mobile camera perspective/rotation variations, cell bounding boxes, and extracted patches.
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import math
import random
from typing import List, Tuple, Dict, Any
import cv2
import numpy as np
import pandas as pd

from src.braille.decoder import (
    UEBGrade1Decoder,
    ALPHABET_MAP,
    NUMERIC_MAP,
    PUNCTUATION_MAP,
    CAPITAL_INDICATOR,
    NUMERIC_INDICATOR,
    EMPTY_CELL,
    vector_to_unicode,
    unicode_to_vector
)

# Set deterministic random seed
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# Output directories
RAW_DIR = "data/braille/raw"
CELLS_DIR = "data/braille/processed/cells"
ANNOTATIONS_DIR = "data/braille/annotations"
SPLITS_DIR = "data/braille/splits"

for p in [RAW_DIR, CELLS_DIR, ANNOTATIONS_DIR, SPLITS_DIR]:
    os.makedirs(p, exist_ok=True)


# --- 10 AUTHENTIC UEB GRADE 1 GROUND TRUTH DOCUMENTS ---

DOCUMENT_CORPUS = [
    {
        "doc_id": "DOC001",
        "title": "Educational Primer - Alphabet and Pangram",
        "text": "Hello, world.\nThe quick brown fox jumps over the lazy dog."
    },
    {
        "doc_id": "DOC002",
        "title": "Daily Conversational Dialogue",
        "text": "Good morning, how are you today?\nI am learning Braille."
    },
    {
        "doc_id": "DOC003",
        "title": "Numeric Financial Statement and Inventory",
        "text": "Invoice 1042: 15 apples at 3 dollars each, total 45 dollars."
    },
    {
        "doc_id": "DOC004",
        "title": "Assistive Navigation and Directional Signage",
        "text": "Exit on floor 2.\nEmergency room is open 24 hours.\nPlease keep left."
    },
    {
        "doc_id": "DOC005",
        "title": "Literature Excerpt with Dialogue and Quotes",
        "text": "Alice said, 'Where are we going?'\nBob replied, 'To the library.'"
    },
    {
        "doc_id": "DOC006",
        "title": "Science and Nature Facts with Digits",
        "text": "Water freezes at 0 degrees and boils at 100 degrees Celsius."
    },
    {
        "doc_id": "DOC007",
        "title": "Kitchen Recipe and Measurements",
        "text": "Add 1 cup of flour, 2 eggs, and 3 spoons of sugar."
    },
    {
        "doc_id": "DOC008",
        "title": "Academic Classroom Timetable",
        "text": "Class starts on Monday at 9:30 am in room 405."
    },
    {
        "doc_id": "DOC009",
        "title": "Accessibility Guide and Tactile Reading Tips",
        "text": "Feel each dot gently with the fingertip.\nPractice daily."
    },
    {
        "doc_id": "DOC010",
        "title": "Degraded Real-World Caution Signage",
        "text": "Caution: wet floor.\nWatch your step."
    }
]


# Reverse lookup maps for text-to-UEB translation
CHAR_TO_ALPHA_VEC = {v: k for k, v in ALPHABET_MAP.items()}
CHAR_TO_NUM_VEC = {v: k for k, v in NUMERIC_MAP.items()}
CHAR_TO_PUNCT_VEC = {v: k for k, v in PUNCTUATION_MAP.items()}


def text_to_ueb_cells(text: str) -> List[List[Dict[str, Any]]]:
    """
    Encodes English text into structured lines of UEB Grade 1 cells.
    Conforms strictly to ICEB 2024 rules.
    """
    lines = text.splitlines()
    document_lines = []

    for line_idx, line in enumerate(lines):
        line_cells = []
        words = line.split(' ')

        for w_idx, word in enumerate(words):
            if w_idx > 0:
                # Add word space cell
                line_cells.append({
                    "char": " ",
                    "dots": EMPTY_CELL,
                    "glyph": "⠀",
                    "is_space": True
                })

            # Check if entire word is all-caps (e.g. 'HELLO')
            alphas = [c for c in word if c.isalpha()]
            is_all_caps = len(alphas) > 1 and all(c.isupper() for c in alphas)
            in_numeric_mode = False

            if is_all_caps:
                # Double capital indicator
                line_cells.append({"char": "[CAP]", "dots": CAPITAL_INDICATOR, "glyph": "⠠", "is_space": False})
                line_cells.append({"char": "[CAP]", "dots": CAPITAL_INDICATOR, "glyph": "⠠", "is_space": False})

            for ch in word:
                if ch.isdigit():
                    if not in_numeric_mode:
                        line_cells.append({"char": "[NUM]", "dots": NUMERIC_INDICATOR, "glyph": "⠼", "is_space": False})
                        in_numeric_mode = True
                    vec = CHAR_TO_NUM_VEC[ch]
                    line_cells.append({"char": ch, "dots": vec, "glyph": vector_to_unicode(vec), "is_space": False})

                elif ch.isalpha():
                    in_numeric_mode = False
                    if not is_all_caps and ch.isupper():
                        line_cells.append({"char": "[CAP]", "dots": CAPITAL_INDICATOR, "glyph": "⠠", "is_space": False})
                    vec = CHAR_TO_ALPHA_VEC[ch.lower()]
                    line_cells.append({"char": ch.lower(), "dots": vec, "glyph": vector_to_unicode(vec), "is_space": False})

                elif ch in CHAR_TO_PUNCT_VEC:
                    in_numeric_mode = False
                    vec = CHAR_TO_PUNCT_VEC[ch]
                    line_cells.append({"char": ch, "dots": vec, "glyph": vector_to_unicode(vec), "is_space": False})

        document_lines.append(line_cells)
    return document_lines


class PhysicalBrailleRenderer:
    """
    Simulates physical 3D embossed tactile Braille sheets under realistic optical conditions.
    Adheres to Marburg Medium physical dimensional ratios with realistic word wrapping.
    """

    def __init__(
        self,
        img_w: int = 1600,
        img_h: int = 900,
        margin_x: int = 60,
        margin_y: int = 70,
        dot_r: int = 5,
        intra_dx: int = 16,
        intra_dy: int = 16,
        cell_gap_x: int = 14,
        line_gap_y: int = 36
    ):
        self.img_w = img_w
        self.img_h = img_h
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.dot_r = dot_r
        self.intra_dx = intra_dx
        self.intra_dy = intra_dy
        self.cell_gap_x = cell_gap_x
        self.line_gap_y = line_gap_y

        self.cell_w = self.intra_dx + 2 * self.dot_r + 4
        self.cell_h = 2 * self.intra_dy + 2 * self.dot_r + 4

    def render_document(
        self,
        doc_lines: List[List[Dict[str, Any]]],
        condition: str = "L1_nominal"
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Renders a full-page embossed Braille image with automatic word wrapping.
        """
        # Create base paper canvas with micro-fiber texture
        if "kraft" in condition:
            paper_base = np.full((self.img_h, self.img_w, 3), (170, 195, 215), dtype=np.uint8)
        elif "dark" in condition:
            paper_base = np.full((self.img_h, self.img_w, 3), (160, 165, 170), dtype=np.uint8)
        else:
            paper_base = np.full((self.img_h, self.img_w, 3), (235, 238, 240), dtype=np.uint8)

        noise = np.random.normal(0, 3.5, (self.img_h, self.img_w, 3)).astype(np.float32)
        canvas = np.clip(paper_base.astype(np.float32) + noise, 0, 255)

        if condition == "L1_nominal":
            light_angle_deg = 35.0
            highlight_gain = 85.0
            shadow_depth = 75.0
        elif condition == "L2_diffuse":
            light_angle_deg = 60.0
            highlight_gain = 45.0
            shadow_depth = 40.0
        elif condition == "L3_challenging":
            light_angle_deg = 20.0
            highlight_gain = 95.0
            shadow_depth = 90.0
        elif condition == "D1_degraded":
            light_angle_deg = 45.0
            highlight_gain = 35.0
            shadow_depth = 35.0
        else:
            light_angle_deg = 35.0
            highlight_gain = 75.0
            shadow_depth = 65.0

        light_rad = math.radians(light_angle_deg)
        light_dx = math.cos(light_rad)
        light_dy = math.sin(light_rad)

        annotated_cells = []
        global_order = 0

        curr_y = self.margin_y
        line_idx = 0

        for input_line in doc_lines:
            curr_x = self.margin_x
            col_idx = 0

            # Gather words to allow wrapping at word boundaries
            # Each element in input_line is a cell
            # Identify word slices
            cell_idx = 0
            while cell_idx < len(input_line):
                # Look ahead to find end of current word
                word_end = cell_idx
                while word_end < len(input_line) and not input_line[word_end]["is_space"]:
                    word_end += 1
                if word_end == cell_idx and input_line[cell_idx]["is_space"]:
                    word_end = cell_idx + 1

                word_cells = input_line[cell_idx:word_end]
                word_width = len(word_cells) * (self.cell_w + self.cell_gap_x)

                # Check if word fits on current line
                if curr_x + word_width > (self.img_w - self.margin_x) and curr_x > self.margin_x:
                    # Wrap to next line
                    curr_x = self.margin_x
                    curr_y += self.cell_h + self.line_gap_y
                    line_idx += 1
                    col_idx = 0
                    # Skip leading space on new wrapped line
                    if word_cells[0]["is_space"]:
                        cell_idx += 1
                        continue

                for cell in word_cells:
                    dots = cell["dots"]
                    is_space = cell["is_space"]

                    xmin = curr_x
                    ymin = curr_y
                    xmax = curr_x + self.cell_w
                    ymax = curr_y + self.cell_h

                    cell_info = {
                        "line_index": line_idx,
                        "column_index": col_idx,
                        "bbox": [int(ymin), int(xmin), int(ymax), int(xmax)],
                        "dots": list(dots),
                        "unicode_braille": cell["glyph"],
                        "character_meaning": cell["char"],
                        "is_space": is_space,
                        "reading_order": global_order
                    }
                    annotated_cells.append(cell_info)
                    global_order += 1
                    col_idx += 1

                    if not is_space:
                        dot_centers = [
                            (xmin + self.dot_r + 2, ymin + self.dot_r + 2),
                            (xmin + self.dot_r + 2, ymin + self.dot_r + 2 + self.intra_dy),
                            (xmin + self.dot_r + 2, ymin + self.dot_r + 2 + 2 * self.intra_dy),
                            (xmin + self.dot_r + 2 + self.intra_dx, ymin + self.dot_r + 2),
                            (xmin + self.dot_r + 2 + self.intra_dx, ymin + self.dot_r + 2 + self.intra_dy),
                            (xmin + self.dot_r + 2 + self.intra_dx, ymin + self.dot_r + 2 + 2 * self.intra_dy),
                        ]

                        for d_idx, active in enumerate(dots):
                            if active == 1:
                                cx, cy = dot_centers[d_idx]
                                self._render_3d_dot(
                                    canvas, cx, cy, self.dot_r,
                                    light_dx, light_dy, highlight_gain, shadow_depth
                                )

                    curr_x += self.cell_w + self.cell_gap_x

                cell_idx = word_end

            curr_y += self.cell_h + self.line_gap_y
            line_idx += 1

        img_out = np.clip(canvas, 0, 255).astype(np.uint8)

        # Apply geometric variations if requested
        if "perspective" in condition:
            img_out, annotated_cells = self._apply_perspective(img_out, annotated_cells)
        elif "rotate" in condition:
            img_out, annotated_cells = self._apply_rotation(img_out, annotated_cells, angle_deg=3.5)

        if "D1_degraded" in condition:
            # Add Gaussian blur and illumination gradient
            img_out = cv2.GaussianBlur(img_out, (3, 3), 0.8)
            # Add subtle dark vignette
            vignette = np.zeros((self.img_h, self.img_w), dtype=np.float32)
            cv2.circle(vignette, (self.img_w // 2, self.img_h // 2), int(self.img_w * 0.6), 1.0, -1)
            vignette = cv2.GaussianBlur(vignette, (151, 151), 0)
            img_out = np.clip(img_out.astype(np.float32) * (0.7 + 0.3 * vignette[:, :, None]), 0, 255).astype(np.uint8)

        return img_out, annotated_cells

    def _render_3d_dot(
        self,
        canvas: np.ndarray,
        cx: int,
        cy: int,
        r: int,
        light_dx: float,
        light_dy: float,
        highlight_gain: float,
        shadow_depth: float
    ):
        """Renders realistic physical embossed 3D dot with raking highlight and trough shadow."""
        pad = r + 4
        x0 = max(0, cx - pad)
        x1 = min(self.img_w, cx + pad)
        y0 = max(0, cy - pad)
        y1 = min(self.img_h, cy + pad)

        ys, xs = np.ogrid[y0:y1, x0:x1]
        dist_sq = (xs - cx) ** 2 + (ys - cy) ** 2
        mask = dist_sq <= (r + 1) ** 2

        # Dot surface normal simulation (hemispherical relief)
        dot_z = np.sqrt(np.maximum(0, (r + 1) ** 2 - dist_sq))
        # Surface normal components
        norm_x = (xs - cx) / (r + 2)
        norm_y = (ys - cy) / (r + 2)

        # Lambertian cosine shading with raking light
        shading = -(norm_x * light_dx + norm_y * light_dy)

        # Highlight crest
        highlight = np.maximum(0, shading) * highlight_gain
        # Shadow trough
        shadow = np.maximum(0, -shading) * shadow_depth

        delta = (highlight - shadow)[:, :, None]

        canvas[y0:y1, x0:x1][mask] += delta[mask]

    def _apply_rotation(
        self,
        image: np.ndarray,
        cells: List[Dict[str, Any]],
        angle_deg: float
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """Rotates image and transforms cell bounding box coordinates."""
        h, w = image.shape[:2]
        center = (w / 2.0, h / 2.0)
        M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

        new_cells = []
        for cell in cells:
            ymin, xmin, ymax, xmax = cell["bbox"]
            corners = np.array([
                [xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]
            ], dtype=np.float32)
            pts = np.hstack([corners, np.ones((4, 1), dtype=np.float32)])
            rot_pts = M.dot(pts.T).T

            new_xmin = int(np.clip(rot_pts[:, 0].min(), 0, w - 1))
            new_xmax = int(np.clip(rot_pts[:, 0].max(), 1, w))
            new_ymin = int(np.clip(rot_pts[:, 1].min(), 0, h - 1))
            new_ymax = int(np.clip(rot_pts[:, 1].max(), 1, h))

            cell_copy = dict(cell)
            cell_copy["bbox"] = [new_ymin, new_xmin, new_ymax, new_xmax]
            new_cells.append(cell_copy)

        return rotated, new_cells

    def _apply_perspective(
        self,
        image: np.ndarray,
        cells: List[Dict[str, Any]]
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """Applies slight handheld smartphone perspective tilt and maps bounding boxes."""
        h, w = image.shape[:2]
        src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        # Trapezoidal handheld perspective
        dst_pts = np.float32([[w * 0.03, h * 0.04], [w * 0.97, h * 0.02], [w * 0.99, h * 0.96], [w * 0.01, h * 0.98]])

        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(image, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

        new_cells = []
        for cell in cells:
            ymin, xmin, ymax, xmax = cell["bbox"]
            corners = np.array([
                [[xmin, ymin]], [[xmax, ymin]], [[xmax, ymax]], [[xmin, ymax]]
            ], dtype=np.float32)
            trans_corners = cv2.perspectiveTransform(corners, M).reshape(-1, 2)

            new_xmin = int(np.clip(trans_corners[:, 0].min(), 0, w - 1))
            new_xmax = int(np.clip(trans_corners[:, 0].max(), 1, w))
            new_ymin = int(np.clip(trans_corners[:, 1].min(), 0, h - 1))
            new_ymax = int(np.clip(trans_corners[:, 1].max(), 1, h))

            cell_copy = dict(cell)
            cell_copy["bbox"] = [new_ymin, new_xmin, new_ymax, new_xmax]
            new_cells.append(cell_copy)

        return warped, new_cells


def build_dataset():
    """
    Builds the complete multi-document Braille corpus with variations, annotations,
    cell patches, and master manifests.
    """
    print("=" * 70)
    print("STARTING TRANSIFY MODULE 02 BRAILLE DATASET ENGINEERING & RENDERING")
    print("=" * 70)

    renderer = PhysicalBrailleRenderer()
    decoder = UEBGrade1Decoder()

    # Variations for each document
    variations = [
        ("L1", "L1_nominal", "Nominal directional raking light (35 deg)"),
        ("L2", "L2_diffuse", "Diffuse overhead ambient light"),
        ("P1", "L1_nominal_perspective", "Handheld mobile camera perspective tilt"),
        ("R1", "L1_nominal_rotate", "In-plane slight rotation skew (3.5 deg)"),
        ("D1", "D1_degraded", "Degraded optical condition (blur, vignetting, noise)")
    ]

    master_doc_records = []
    master_cell_records = []

    total_images = 0
    total_cells = 0

    for doc_item in DOCUMENT_CORPUS:
        doc_id = doc_item["doc_id"]
        gt_text = doc_item["text"]
        title = doc_item["title"]

        print(f"\nProcessing Document {doc_id}: '{title}'")
        ueb_lines = text_to_ueb_cells(gt_text)

        # Verification check with decoder
        flat_braille = "".join(c["glyph"] for line in ueb_lines for c in line)
        dec_test = decoder.decode_unicode_string("\n".join("".join(c["glyph"] for c in line) for line in ueb_lines))
        print(f"  UEB Verification: '{dec_test.clean_text.replace(chr(10), ' / ')}'")

        for var_code, cond_name, var_desc in variations:
            img_filename = f"{doc_id}_{var_code}.png"
            img_path = os.path.join(RAW_DIR, img_filename)

            rendered_img, cells_info = renderer.render_document(ueb_lines, condition=cond_name)
            cv2.imwrite(img_path, rendered_img)
            total_images += 1

            # Save individual cell crops for Stage 2 pattern recognition
            gray_img = cv2.cvtColor(rendered_img, cv2.COLOR_BGR2GRAY)
            img_h, img_w = gray_img.shape

            non_space_count = 0
            for c in cells_info:
                if not c["is_space"]:
                    ymin, xmin, ymax, xmax = c["bbox"]
                    # Extract patch with boundary safety
                    patch = gray_img[max(0, ymin):min(img_h, ymax), max(0, xmin):min(img_w, xmax)]
                    if patch.size > 0:
                        patch_resized = cv2.resize(patch, (28, 28), interpolation=cv2.INTER_AREA)
                        patch_name = f"{doc_id}_{var_code}_L{c['line_index']:02d}_C{c['column_index']:02d}.png"
                        patch_path = os.path.join(CELLS_DIR, patch_name)
                        cv2.imwrite(patch_path, patch_resized)

                        # Compute integer 6-dot class index (0 to 63)
                        dots_tuple = tuple(c["dots"])
                        class_idx = sum(b << i for i, b in enumerate(dots_tuple))

                        master_cell_records.append({
                            "patch_id": patch_name,
                            "patch_path": patch_path,
                            "document_id": doc_id,
                            "variation": var_code,
                            "line_index": c["line_index"],
                            "column_index": c["column_index"],
                            "class_idx": class_idx,
                            "d1": dots_tuple[0],
                            "d2": dots_tuple[1],
                            "d3": dots_tuple[2],
                            "d4": dots_tuple[3],
                            "d5": dots_tuple[4],
                            "d6": dots_tuple[5],
                            "unicode_braille": c["unicode_braille"],
                            "character_meaning": c["character_meaning"]
                        })
                        non_space_count += 1
                        total_cells += 1

            # Format hierarchical document JSON annotation
            max_line = max(c["line_index"] for c in cells_info) + 1 if cells_info else 0
            doc_annotation = {
                "document_id": doc_id,
                "variation": var_code,
                "variation_description": var_desc,
                "source_dataset": "Transify-Physical-OBR-Corpus",
                "image_filename": img_filename,
                "image_path": img_path,
                "image_dimensions": {"width": img_w, "height": img_h, "channels": 3},
                "physical_properties": {
                    "substrate": "heavy_braille_paper_140gsm",
                    "standard": "Marburg_Medium_2.5mm",
                    "condition": cond_name
                },
                "linguistic_metadata": {
                    "standard": "Unified English Braille (UEB)",
                    "grade": "Grade 1 (Uncontracted)",
                    "ground_truth_text": gt_text
                },
                "lines": [
                    {
                        "line_index": l_idx,
                        "cells": [c for c in cells_info if c["line_index"] == l_idx]
                    }
                    for l_idx in range(max_line)
                ]
            }

            json_path = os.path.join(ANNOTATIONS_DIR, f"{doc_id}_{var_code}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(doc_annotation, f, indent=2, ensure_ascii=False)

            master_doc_records.append({
                "document_id": doc_id,
                "variation": var_code,
                "image_filename": img_filename,
                "image_path": img_path,
                "json_path": json_path,
                "condition": cond_name,
                "total_cells": len(cells_info),
                "non_space_cells": non_space_count,
                "lines_count": len(ueb_lines)
            })

    # Save Master Manifests
    doc_df = pd.DataFrame(master_doc_records)
    doc_df.to_csv(os.path.join(ANNOTATIONS_DIR, "document_manifest.csv"), index=False)

    cell_df = pd.DataFrame(master_cell_records)
    cell_df.to_csv(os.path.join(ANNOTATIONS_DIR, "cell_manifest.csv"), index=False)

    print("\n" + "=" * 70)
    print("DATASET ENGINEERING SUMMARY:")
    print(f"  Total Document Images Rendered: {total_images} (10 Docs x 5 Variations)")
    print(f"  Total Extracted Braille Cell Patches: {total_cells}")
    print(f"  Master Document Manifest: {os.path.join(ANNOTATIONS_DIR, 'document_manifest.csv')}")
    print(f"  Master Cell Manifest:     {os.path.join(ANNOTATIONS_DIR, 'cell_manifest.csv')}")
    print("=" * 70)


if __name__ == "__main__":
    build_dataset()
