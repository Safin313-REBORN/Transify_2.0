"""
Stage 1: Braille Cell Detection and Layout Analyzer for Transify Module 02.
Extracts reading lines, cell bounding boxes, inter-word spaces, and normalized 28x28 patches.
"""

from typing import List, Tuple, Dict, Any, Optional
import cv2
import numpy as np

from src.braille.quality_assessment import ImageQualityAssessment
from src.braille.preprocessing import BrailleImagePreprocessor
from src.braille.decoder import RecognizedCell, EMPTY_CELL


class BrailleCellDetector:
    """
    Stage 1 detector that localizes Braille cells and reconstructs document reading order.
    """

    def __init__(
        self,
        min_dot_area: int = 8,
        max_dot_area: int = 250,
        nominal_cell_w: int = 28,
        nominal_cell_h: int = 44,
        line_cluster_dist: int = 28,
        space_threshold_ratio: float = 0.85
    ):
        self.iqa = ImageQualityAssessment()
        self.preprocessor = BrailleImagePreprocessor()
        self.min_dot_area = min_dot_area
        self.max_dot_area = max_dot_area
        self.nominal_cell_w = nominal_cell_w
        self.nominal_cell_h = nominal_cell_h
        self.line_cluster_dist = line_cluster_dist
        self.space_threshold_ratio = space_threshold_ratio

    def detect_and_crop_cells(
        self,
        image: np.ndarray,
        known_boxes: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Processes image through IQA, preprocessing, and cell detection.
        If known_boxes is provided (from annotations or Stage 1 YOLO), crops directly.
        Otherwise, runs contour grid clustering.
        """
        # 1. Quality Assessment
        qa_result = self.iqa.assess(image)
        if not qa_result["is_usable"]:
            return {
                "success": False,
                "rejection_reason": qa_result["rejection_reason"],
                "qa_metrics": qa_result["metrics"],
                "lines": [],
                "preprocessed": None
            }

        # 2. Image Preprocessing & Deskewing
        prep = self.preprocessor.process(image)
        gray = prep.get("deskewed_raw_gray", prep["gray"])
        binary = prep["binary"]
        h_img, w_img = gray.shape

        # 3. Cell Extraction
        if known_boxes is not None and len(known_boxes) > 0:
            lines = self._extract_from_known_boxes(gray, known_boxes)
        else:
            lines = self._detect_cells_from_contours(gray, binary)

        return {
            "success": True,
            "rejection_reason": None,
            "qa_metrics": qa_result["metrics"],
            "preprocessed": prep,
            "lines": lines,
            "total_lines": len(lines),
            "total_cells": sum(len(l) for l in lines)
        }

    def _extract_from_known_boxes(
        self,
        gray: np.ndarray,
        boxes_data: List[Dict[str, Any]]
    ) -> List[List[RecognizedCell]]:
        """Groups given boxes into lines and crops 28x28 patches."""
        h_img, w_img = gray.shape
        # Group by line_index
        lines_dict: Dict[int, List[Dict[str, Any]]] = {}
        for b in boxes_data:
            l_idx = b.get("line_index", 0)
            if l_idx not in lines_dict:
                lines_dict[l_idx] = []
            lines_dict[l_idx].append(b)

        result_lines = []
        for l_idx in sorted(lines_dict.keys()):
            line_cells = []
            # Sort cells horizontally
            cells_in_line = sorted(lines_dict[l_idx], key=lambda c: c["bbox"][1])

            for c_idx, c in enumerate(cells_in_line):
                ymin, xmin, ymax, xmax = c["bbox"]
                is_space = c.get("is_space", False)

                if is_space:
                    patch = np.full((28, 28), 240, dtype=np.uint8)
                else:
                    crop = gray[max(0, ymin):min(h_img, ymax), max(0, xmin):min(w_img, xmax)]
                    if crop.size == 0:
                        patch = np.full((28, 28), 240, dtype=np.uint8)
                    else:
                        patch = cv2.resize(crop, (28, 28), interpolation=cv2.INTER_AREA)

                r_cell = RecognizedCell(
                    cell_id=f"L{l_idx:02d}_C{c_idx:02d}",
                    line_idx=l_idx,
                    col_idx=c_idx,
                    dot_vector=tuple(c.get("dots", EMPTY_CELL)),
                    unicode_char=c.get("unicode_braille", "⠀"),
                    confidence=1.0,
                    bbox=(int(xmin), int(ymin), int(xmax), int(ymax)),
                    is_space=is_space
                )
                # Attach patch for downstream classification
                setattr(r_cell, "patch", patch)
                line_cells.append(r_cell)

            result_lines.append(line_cells)

        return result_lines

    def _detect_cells_from_contours(
        self,
        gray: np.ndarray,
        binary: np.ndarray
    ) -> List[List[RecognizedCell]]:
        """
        Adaptive grid clustering on binary dot contours.
        Dynamically estimates dot scale, line clusters, and 6-dot cell occupancy.
        """
        h_img, w_img = gray.shape
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        dot_centers = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 3.0 <= area <= 3500.0:
                # Discard non-dot linear borders or thin noise
                bx, by, bw, bh = cv2.boundingRect(cnt)
                ar = float(bw) / float(bh)
                if 0.2 <= ar <= 5.0:
                    M = cv2.moments(cnt)
                    if M["m00"] > 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        dot_centers.append((cx, cy))

        if not dot_centers:
            return []

        # Dynamic estimation of inter-dot spacing
        if len(dot_centers) >= 4:
            pts = np.array(dot_centers)
            diff_y = []
            diff_x = []
            for i in range(min(len(pts), 80)):
                dxs = np.abs(pts[:, 0] - pts[i, 0])
                dys = np.abs(pts[:, 1] - pts[i, 1])
                valid_y = dys[(dys > 3) & (dys < 120) & (dxs < 30)]
                if len(valid_y) > 0:
                    diff_y.append(np.min(valid_y))
                valid_x = dxs[(dxs > 3) & (dxs < 120) & (dys < 30)]
                if len(valid_x) > 0:
                    diff_x.append(np.min(valid_x))

            est_dy = float(np.median(diff_y)) if len(diff_y) >= 2 else 14.0
            est_dx = float(np.median(diff_x)) if len(diff_x) >= 2 else 14.0
        else:
            est_dy = 14.0
            est_dx = 14.0

        line_cluster_dist = max(32.0, est_dy * 2.8)
        nominal_cell_w = max(22.0, est_dx * 2.0)
        nominal_cell_h = max(34.0, est_dy * 3.0)
        max_intra_cell_dx = est_dx * 1.55
        space_threshold = est_dx * 2.3

        # Sort dots by Y to cluster lines
        dot_centers = sorted(dot_centers, key=lambda p: p[1])

        # Cluster into horizontal lines
        line_groups = []
        current_line = [dot_centers[0]]

        for pt in dot_centers[1:]:
            min_y = min(p[1] for p in current_line)
            max_y = max(p[1] for p in current_line)
            if (pt[1] - min_y) < line_cluster_dist:
                current_line.append(pt)
            else:
                line_groups.append(current_line)
                current_line = [pt]
        if current_line:
            line_groups.append(current_line)

        # Sort lines from top to bottom
        line_groups = sorted(line_groups, key=lambda grp: np.mean([p[1] for p in grp]))

        result_lines = []
        for l_idx, grp in enumerate(line_groups):
            # Sort dots along line horizontally
            grp_x = sorted(grp, key=lambda p: p[0])
            line_y_mean = float(np.mean([p[1] for p in grp]))
            ymin = max(0, int(line_y_mean - nominal_cell_h / 2.0))
            ymax = min(h_img, int(line_y_mean + nominal_cell_h / 2.0))

            # Cluster dots into cells based on dynamic spacing
            cells_in_line = []
            c_start = 0
            while c_start < len(grp_x):
                c_end = c_start + 1
                while c_end < len(grp_x) and (grp_x[c_end][0] - grp_x[c_end - 1][0]) <= max_intra_cell_dx:
                    c_end += 1

                cell_dots = grp_x[c_start:c_end]
                cell_min_x = min(p[0] for p in cell_dots)
                cell_max_x = max(p[0] for p in cell_dots)
                cell_cx = (cell_min_x + cell_max_x) / 2.0
                xmin = max(0, int(cell_cx - nominal_cell_w / 2.0))
                xmax = min(w_img, int(cell_cx + nominal_cell_w / 2.0))

                cells_in_line.append((xmin, xmax, cell_dots))
                c_start = c_end

            line_cells = []
            prev_xmax = -1

            for c_idx, (xmin, xmax, cell_dots) in enumerate(cells_in_line):
                # Check for space between cells
                if prev_xmax != -1:
                    gap = xmin - prev_xmax
                    if gap > space_threshold:
                        # Insert Space cell
                        sp_cell = RecognizedCell(
                            cell_id=f"L{l_idx:02d}_C{len(line_cells):02d}",
                            line_idx=l_idx,
                            col_idx=len(line_cells),
                            dot_vector=EMPTY_CELL,
                            unicode_char="⠀",
                            confidence=1.0,
                            bbox=(prev_xmax, ymin, xmin, ymax),
                            is_space=True
                        )
                        setattr(sp_cell, "patch", np.full((28, 28), 240, dtype=np.uint8))
                        setattr(sp_cell, "geometric_dots", EMPTY_CELL)
                        line_cells.append(sp_cell)

                crop = gray[ymin:ymax, xmin:xmax]
                patch = cv2.resize(crop, (28, 28), interpolation=cv2.INTER_AREA) if crop.size > 0 else np.full((28, 28), 240, dtype=np.uint8)

                # Determine 6-dot occupancy directly from detected dot coordinates
                min_dot_x = min(p[0] for p in cell_dots)
                max_dot_x = max(p[0] for p in cell_dots)
                has_two_cols = (max_dot_x - min_dot_x) > (est_dx * 0.45)
                col_split_x = (min_dot_x + max_dot_x) / 2.0 if has_two_cols else min_dot_x + est_dx * 0.5

                d1, d2, d3, d4, d5, d6 = 0, 0, 0, 0, 0, 0
                for px, py in cell_dots:
                    col = 1 if (has_two_cols and px > col_split_x) else 0
                    y_off = py - line_y_mean
                    row = 0 if y_off < -est_dy * 0.45 else (2 if y_off > est_dy * 0.45 else 1)
                    if col == 0:
                        if row == 0: d1 = 1
                        elif row == 1: d2 = 1
                        else: d3 = 1
                    else:
                        if row == 0: d4 = 1
                        elif row == 1: d5 = 1
                        else: d6 = 1

                geom_dots = (d1, d2, d3, d4, d5, d6)

                r_cell = RecognizedCell(
                    cell_id=f"L{l_idx:02d}_C{len(line_cells):02d}",
                    line_idx=l_idx,
                    col_idx=len(line_cells),
                    dot_vector=EMPTY_CELL,
                    unicode_char="⠀",
                    confidence=1.0,
                    bbox=(xmin, ymin, xmax, ymax),
                    is_space=False
                )
                setattr(r_cell, "patch", patch)
                setattr(r_cell, "geometric_dots", geom_dots)
                line_cells.append(r_cell)
                prev_xmax = xmax

            if line_cells:
                result_lines.append(line_cells)

        return result_lines
