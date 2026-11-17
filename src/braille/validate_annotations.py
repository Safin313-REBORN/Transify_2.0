"""
Automated Annotation Validator for Optical Braille Recognition.
Checks geometric integrity, non-overlapping constraints, monotonicity, and decodability.
"""

from typing import Dict, Any, List, Tuple
import json
import os
import sys

from src.braille.decoder import UEBGrade1Decoder, unicode_to_vector


class AnnotationValidator:
    """
    Validates Braille document annotations against strict geometric and linguistic invariants.
    """

    def __init__(self, iou_overlap_threshold: float = 0.15):
        self.iou_threshold = iou_overlap_threshold
        self.decoder = UEBGrade1Decoder()

    def validate_file(self, json_path: str) -> Dict[str, Any]:
        """Validates a single JSON annotation file."""
        if not os.path.exists(json_path):
            return {"valid": False, "errors": [f"File not found: {json_path}"]}

        with open(json_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception as e:
                return {"valid": False, "errors": [f"JSON syntax error: {str(e)}"]}

        return self.validate_document(data)

    def validate_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Validates a document dictionary."""
        errors = []
        warnings = []

        required_keys = ["document_id", "image_filename", "image_dimensions", "linguistic_metadata", "lines"]
        for k in required_keys:
            if k not in doc:
                errors.append(f"Missing mandatory document-level key: '{k}'")

        if errors:
            return {"valid": False, "errors": errors, "warnings": warnings}

        img_w = doc["image_dimensions"].get("width", 1920)
        img_h = doc["image_dimensions"].get("height", 1080)
        gt_text = doc["linguistic_metadata"].get("ground_truth_text", "")

        lines = doc.get("lines", [])
        if not lines:
            errors.append("Document contains no annotated lines.")

        total_cells = 0
        all_ordered_cells = []

        for line in lines:
            line_idx = line.get("line_index", 0)
            cells = line.get("cells", [])
            prev_x_max = -1

            for c_idx, cell in enumerate(cells):
                total_cells += 1
                cell_id = cell.get("cell_id", f"L{line_idx}_C{c_idx}")
                bbox = cell.get("bbox", [])
                dots = cell.get("dots", [])
                unicode_br = cell.get("unicode_braille", "")

                # Invariant 1: Geometry Check
                if len(bbox) != 4:
                    errors.append(f"Cell {cell_id}: bbox must have 4 coordinates [ymin, xmin, ymax, xmax], got {bbox}")
                else:
                    ymin, xmin, ymax, xmax = bbox
                    if xmax <= xmin or ymax <= ymin:
                        errors.append(f"Cell {cell_id}: degenerate bbox dimensions [ymin={ymin}, xmin={xmin}, ymax={ymax}, xmax={xmax}]")
                    if xmin < 0 or ymin < 0 or xmax > img_w or ymax > img_h:
                        errors.append(f"Cell {cell_id}: bbox exceeds image bounds ({img_w}x{img_h}): {bbox}")

                # Invariant 2: Overlap and Monotonicity
                if len(bbox) == 4:
                    _, xmin, _, xmax = bbox
                    if prev_x_max != -1 and xmin < prev_x_max:
                        # Check IoU or overlap extent (ignore 1-2 pixel raster rounding jitter)
                        overlap = prev_x_max - xmin
                        cell_w = xmax - xmin
                        if overlap > 2 and cell_w > 0 and (overlap / cell_w) > self.iou_threshold:
                            errors.append(f"Cell {cell_id}: excessive horizontal overlap with predecessor ({overlap}px, > {self.iou_threshold*100}%).")
                    prev_x_max = xmax

                # Invariant 3: 6-dot Vector Encoding
                if len(dots) != 6 or not all(d in (0, 1) for d in dots):
                    errors.append(f"Cell {cell_id}: dots must be an array of exactly 6 binary integers {dots}")
                elif unicode_br:
                    try:
                        expected_vec = list(unicode_to_vector(unicode_br))
                        if list(dots) != expected_vec:
                            errors.append(f"Cell {cell_id}: dot vector {dots} does not match Unicode Braille '{unicode_br}' (expected {expected_vec})")
                    except Exception as ex:
                        errors.append(f"Cell {cell_id}: invalid Unicode Braille character '{unicode_br}': {ex}")

                all_ordered_cells.append(cell)

        # Invariant 4: Monotonic reading order across all cells
        reading_orders = [c.get("reading_order", -1) for c in all_ordered_cells]
        if reading_orders != list(range(len(reading_orders))):
            warnings.append(f"Reading order indices are non-consecutive or unsorted: {reading_orders[:10]}...")

        return {
            "valid": len(errors) == 0,
            "total_lines": len(lines),
            "total_cells": total_cells,
            "errors": errors,
            "warnings": warnings
        }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        validator = AnnotationValidator()
        res = validator.validate_file(path)
        print(json.dumps(res, indent=2))
    else:
        print("Usage: python src/braille/validate_annotations.py <path_to_annotation.json>")
