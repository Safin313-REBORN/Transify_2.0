# Optical Braille Recognition Annotation Specification
## Data Structures, Schemas, Validation Rules, and Reading Order Standards

---

## 1. Overview and Core Philosophy

In Optical Braille Recognition (OBR), annotations must capture both **low-level spatial geometry** (bounding boxes, individual dot coordinates) and **high-level semantic structure** (reading order, lines, cells, spaces, UEB indicators).

To ensure complete reproducibility and compatibility with modern computer vision frameworks, Transify defines a dual annotation standard:
1. **Hierarchical Document JSON Schema:** Captures document metadata, line groupings, cell bounding boxes, 6-dot binary arrays, Unicode Braille glyphs, and target English text transcriptions.
2. **YOLO Detection Format:** Standard normalized text files (`class_id x_center y_center width height`) for training Stage 1 cell localization models.

---

## 2. Hierarchical Document JSON Schema

Every annotated document page possesses a master metadata record:

```json
{
  "document_id": "DOC_UEB_001",
  "source_dataset": "Transify-Benchmark-2026",
  "image_filename": "DOC_UEB_001_L1.png",
  "image_dimensions": {
    "width": 1920,
    "height": 1080,
    "channels": 3
  },
  "physical_properties": {
    "substrate": "heavy_braille_paper_140gsm",
    "embossing_type": "single_sided_recto",
    "lighting_condition": "oblique_directional_side",
    "capture_device": "iPhone 14 Pro, 24mm f/1.78"
  },
  "linguistic_metadata": {
    "standard": "Unified English Braille (UEB)",
    "grade": "Grade 1 (Uncontracted)",
    "ground_truth_text": "Hello, world.\nThis is a test of Braille recognition."
  },
  "lines": [
    {
      "line_index": 0,
      "bounding_box": [120, 150, 240, 1750],
      "cells": [
        {
          "cell_id": "DOC001_L00_C00",
          "column_index": 0,
          "bbox": [125, 160, 235, 220],
          "dots": [0, 0, 0, 0, 0, 1],
          "unicode_braille": "⠠",
          "character_meaning": "Capital Indicator",
          "is_space": false,
          "reading_order": 0
        },
        {
          "cell_id": "DOC001_L00_C01",
          "column_index": 1,
          "bbox": [125, 230, 235, 290],
          "dots": [1, 1, 0, 0, 1, 0],
          "unicode_braille": "⠓",
          "character_meaning": "h",
          "is_space": false,
          "reading_order": 1
        }
      ]
    }
  ]
}
```

---

## 3. Cell-Level Field Definitions

| Field Name | Type | Allowed Values / Constraints | Description |
|---|---|---|---|
| `cell_id` | String | Unique string matching `DOC[0-9]{3}_L[0-9]{2}_C[0-9]{2}` | Traceable cell identifier. |
| `line_index` | Integer | $\ge 0$ | Vertical line index in reading order (top to bottom). |
| `column_index`| Integer | $\ge 0$ | Horizontal position along the current line (left to right). |
| `bbox` | Array[4] | `[ymin, xmin, ymax, xmax]` in integer pixels | Absolute spatial bounds encompassing all 6 dot positions of the cell. |
| `dots` | Array[6] | Exactly 6 binary values: $d_i \in \{0, 1\}$ | Six-dot state $(d_1, d_2, d_3, d_4, d_5, d_6)$. |
| `unicode_braille`| String | Glyphs in Unicode range `U+2800` through `U+283F` | Corresponding Braille glyph. |
| `is_space` | Boolean | `true` or `false` | Indicates whether cell represents an intentional word-spacing gap. |
| `reading_order`| Integer | $\ge 0$, strictly monotonic within document | Global sequence index for text reconstruction. |

---

## 4. Multi-Line Reading Order Rules

1. **Top-to-Bottom Line Traversal:**
   - Lines must be ordered by the vertical centroid of their constituent cells:
     $$\bar{y}_{\text{line}} = \frac{1}{N} \sum_{k=1}^{N} \frac{y_{\min}^{(k)} + y_{\max}^{(k)}}{2}$$
   - A new line is registered whenever a cell's vertical centroid exceeds the previous line by $\ge 0.6 \times \text{cell\_height}$.
2. **Left-to-Right Cell Traversal:**
   - Within each line, cells are sorted monotonically by their horizontal coordinate: $x_{\min}^{(1)} < x_{\min}^{(2)} < \dots < x_{\min}^{(N)}$.
3. **Inter-Cell vs Inter-Word Space Classification:**
   - Given horizontal gap $\Delta x = x_{\min}^{(k+1)} - x_{\max}^{(k)}$:
     - If $\Delta x \le 0.8 \times \text{cell\_width}$: Intra-word adjacent cells (no space).
     - If $0.8 \times \text{cell\_width} < \Delta x \le 2.2 \times \text{cell\_width}$: Single word space (`" "`).
     - If $\Delta x > 2.2 \times \text{cell\_width}$: Multiple blank cell spaces or indentation.

---

## 5. Automated Annotation Integrity Validation Rules

An automated validation script (`src/braille/validate_annotations.py`) validates every annotation file against five strict invariants:

1. **Geometry Invariant:** For every bounding box, $x_{\max} > x_{\min}$ and $y_{\max} > y_{\min}$, and coordinates lie strictly within image boundaries.
2. **Overlap Invariant:** No two cells on the same line may have an Intersection-over-Union (IoU) exceeding $0.15$.
3. **Monotonicity Invariant:** Within each line, horizontal centers must be strictly increasing: $x_c^{(k+1)} > x_c^{(k)}$.
4. **Encoding Invariant:** The 6-dot vector $\mathbf{d}$ must match the `unicode_braille` character exactly according to ICEB standard bitmask $0\text{x}2800 + \sum_{i=1}^6 d_i 2^{i-1}$.
5. **Decodability Invariant:** Reconstructing the text via the UEB Grade 1 decoder must match the `ground_truth_text` with zero unhandled exceptions.
