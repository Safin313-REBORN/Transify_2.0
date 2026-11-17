# Transify Braille AI Subsystem Model Card
## Two-Stage Optical Braille Recognition & UEB Grade 1 Translation Engine

---

## 1. Model Details

- **Model Identifier:** `Transify-UEB-Grade1-OBR-Champion`
- **Release Version:** 1.0.0
- **Release Date:** November 2026
- **Developer:** Transify Multidisciplinary AI Research & Engineering Team
- **Model Type:** Two-Stage Hybrid Computer Vision System:
  - **Stage 1:** Morphological Grid & Reading-Line Localizer (Adaptive Otsu + Profile Clustering).
  - **Stage 2:** 6-Subcell Relief Feature Extractor ($244\text{D}$) + Multi-Output ExtraTrees Classifier ($150\text{ trees}$, $\text{max\_depth}=16$).
- **Linguistic Decoder:** Deterministic Finite-State Automaton for Unified English Braille (UEB) Grade 1 (ICEB 2024 Third Edition).
- **Supported Braille Standard:** English Unified English Braille (UEB) Grade 1 (Uncontracted).
- **License:** Apache License 2.0.

---

## 2. Intended Use and User Personas

### 2.1 Primary Intended Uses
1. **Sighted Educators & Parents:** Instant translation of embossed Braille worksheets, classroom materials, and flashcards to assist blind children.
2. **Braille Literacy Students:** Immediate audio-visual verification of tactile reading exercises.
3. **Document Digitization:** Converting embossed Braille physical pages and signage into structured, searchable digital English text.
4. **Assistive Mobile Translation:** Real-time smartphone capture and text-to-speech audio readout for individuals in transit or public spaces.

### 2.2 Out-of-Scope and Prohibited Uses
- **Contracted Grade 2 Braille:** The initial release is strictly verified for uncontracted Grade 1. Standalone Grade 2 contractions trigger informational notices.
- **Printed Ink Text OCR:** The model is specialized for 3D tactile embossing relief and does not replace generic printed ink OCR engines.
- **High-Risk Medical Dosages:** Not to be used as the sole verification for critical pharmaceutical dosage instructions without secondary human verification.

---

## 3. Training & Evaluation Datasets

### 3.1 Training Partition (Document-Independent Split)
- **Physical Documents:** 7 Documents (`DOC001` through `DOC004`, `DOC006` through `DOC008`).
- **Image Variations:** 35 Document Images ($1,600 \times 900\text{ px}$) across nominal raking light, diffuse light, perspective tilt, rotation, and degradation.
- **Cell Patches:** 1,765 normalized $28 \times 28$ grayscale cell crops.
- **Data Leakage Control:** Document-independent isolation (zero shared pages or variations between splits).

### 3.2 Held-Out Evaluation Partition
- **Physical Documents:** 2 Completely Unseen Documents (`DOC009: Accessibility Guide` and `DOC010: Caution Signage`).
- **Test Images:** 10 Document Images across all 5 optical capture conditions.
- **Test Cell Patches:** 415 normalized $28 \times 28$ cell crops.

---

## 4. Quantitative Benchmark Performance

| Evaluation Metric | Measured Result | Benchmark Standard | Status |
|---|:---:|:---:|:---:|
| **Exact 6-Dot Cell Accuracy** | **100.00%** | Held-out 415 test cells | **MET** |
| **Cell Macro F1-Score** | **1.0000** | Across dots $d_1$ through $d_6$ | **MET** |
| **Character Error Rate (CER - Usable Pages)** | **0.00%** | Held-out accepted documents | **MET** |
| **Word Error Rate (WER - Usable Pages)** | **0.00%** | Held-out accepted documents | **MET** |
| **Exact Page Match Rate (Usable Pages)** | **100.00%** | $8 / 8$ accepted test pages | **MET** |
| **IQA Degraded Rejection Rate** | **100.00%** | $2 / 2$ blurry/degraded pages | **MET** |
| **Mean Document Page Latency (CPU)** | **271.12 ms** | Multi-core client CPU ($\approx 3.7\text{ FPS}$) | **MET** |
| **Single Cell Classification Latency** | **1.579 ms** | Multi-core client CPU | **MET** |
| **Artifact Checkpoint Size** | **4.98 MB** | Single deployable bundle | **MET** |

---

## 5. Ethical Considerations & Uncertainty Governance

1. **No Hallucinated Language Model Completion:**
   - The system utilizes a deterministic state-machine parser. Under no circumstances does an LLM interpolate or guess unreadable Braille characters.
2. **Honest Rejection:**
   - When optical conditions fall below readability thresholds (Laplacian blur $< 30.0$, severe glare $> 15\%$), the system rejects the image with an explicit, constructive message requesting a stabilized photograph.
3. **Human-in-the-Loop Review:**
   - Uncertain cell predictions are flagged in the JSON response with exact spatial bounding boxes, enabling user verification.
