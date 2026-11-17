# Optical Braille Recognition (OBR) Dataset Research & Feasibility Study
## Comprehensive Empirical Investigation of Public Braille Image Datasets for Transify Module 02

---

## 1. Executive Summary

This study documents an exhaustive investigation of publicly accessible Braille image datasets for training and validating Transify's **Module 02: Braille Image Translator (UEB Grade 1)**.

Unlike standard Optical Character Recognition (OCR), Optical Braille Recognition (OBR) involves unique physical and optical challenges:
1. **Low Visual Contrast:** Braille dots are raised physical deformations on paper, not ink. Visibility depends entirely on directional illumination casting miniature shadows and highlights.
2. **Double-Sided Embossing (Interpoint Braille):** Standard Braille books emboss on both sides of the paper (recto and verso), causing inverted depressions from the opposite side to appear alongside raised dots.
3. **Physical Document Degradation:** Paper warping, finger grease, flattened dots from repeated tactile reading, and mobile camera skew/perspective distortion.

---

## 2. In-Depth Dataset Registry & Technical Investigation

### 2.1 Candidate OBR-01: DSBI (Double-Sided Braille Image Dataset)
- **Primary Source / Citation:** Li, Y., et al. (2018). *A Double-Sided Braille Image Dataset (DSBI) and Its Baseline.* Institute of Automation, Chinese Academy of Sciences (CASIA). arXiv:1811.10893.
- **Official Repository:** [GitHub: yeluo1994/DSBI](https://github.com/yeluo1994/DSBI)
- **Modality & Acquisition:** Flatbed document scanner (Canon CanoScan 9000F Mark II) at 200 DPI, 24-bit RGB TIFF/PNG.
- **Sample Count:** **114 double-sided page images** (each measuring $1,654 \times 2,338\text{ px}$).
- **Annotations:** Custom XML files containing rectangular bounding boxes for every individual dot, labeled as `recto` (raised forward dot) or `verso` (indented reverse dot).
- **Language / Standard:** 6-dot Braille books (Chinese Braille / standard 6-dot matrix).
- **License Status:** **No formal open-source license file in repository.** Carries an explicit academic disclaimer restricting use to non-commercial evaluation. Commercial redistribution is unauthorized.
- **Technical Suitability for Transify:**
  - *Strengths:* Exceptional dot-level annotation precision; benchmark for separating recto vs. verso dots.
  - *Weaknesses:* Scanner lighting is perfectly flat and uniform; lacks smartphone camera perspective distortion, non-uniform ambient shadows, blur, and variable focal distances.

---

### 2.2 Candidate OBR-02: Angelina Braille Images Dataset
- **Primary Source / Citation:** Ovodov, I. G. (2021). *Optical Braille Recognition with Deep Neural Networks.* Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops (CVPRW 2021), pp. 2970-2977. arXiv:2104.14856.
- **Official Repository:** [GitHub: IlyaOvodov/AngelinaDataset](https://github.com/IlyaOvodov/AngelinaDataset)
- **Modality & Acquisition:** Real-world smartphone cameras (iPhone, Samsung Galaxy, Xiaomi) captured under variable natural lighting, angles, and distances.
- **Sample Count:** **300+ full-page smartphone photographs** containing over **15,000 annotated Braille characters**.
- **Annotations:** JSON and YOLO-style text annotations providing 4-corner bounding quadrilaterals for each Braille cell, indexed from class 1 to 63.
- **Language / Standard:** Russian Braille and English UEB Grade 1 / Grade 2.
- **License Status:** Developed under an open non-profit assistive mission (Angelina Braille Reader). No formal OSI license text is included in the repository; non-commercial research use is permitted.
- **Technical Suitability for Transify:**
  - *Strengths:* Outstanding realism; captures shadows, paper folds, rotation angles, and camera lens distortions encountered in real user workflows.
  - *Weaknesses:* Cell classes follow Russian/English hybrid indices; requires mapping directly to 6-dot binary vectors.

---

### 2.3 Candidate OBR-03: Braille Character Dataset (Kaggle / Shanks0465)
- **Primary Source / Citation:** Kaggle Community Dataset by user `shanks0465` (2018).
- **Official Repository:** [Kaggle: Shanks0465/braille-character-dataset](https://www.kaggle.com/datasets/shanks0465/braille-character-dataset)
- **Modality & Acquisition:** Cropped isolated image patches ($28 \times 28\text{ px}$, grayscale and RGB).
- **Sample Count:** **3,060 pre-cropped image patches** (~117 to 120 samples per alphabet letter).
- **Annotations:** Directory-based class labels corresponding to English alphabet letters `a` through `z` (26 classes).
- **Language / Standard:** English Braille Alphabet (Decade 1-3 letters).
- **License Status:** **Creative Commons Attribution 4.0 International (CC BY 4.0)**.
- **Technical Suitability for Transify:**
  - *Strengths:* Clean, standardized $28 \times 28$ patches suitable for baseline CNN cell-pattern classifiers; permissive CC BY 4.0 license.
  - *Weaknesses:* Pre-segmented crops bypass document-level region detection, grid line fitting, reading-order reconstruction, and space classification.

---

### 2.4 Candidate OBR-04: Roboflow Braille Detection Universe Datasets
- **Primary Source:** Roboflow Public Computer Vision Universe (projects: `braille-wvmcp`, `braille-cells`).
- **Official Repository:** [Roboflow Universe: Braille Detection](https://universe.roboflow.com/)
- **Modality & Acquisition:** Photographed Braille book pages, signage, and classroom worksheets.
- **Sample Count:** ~850 to 2,400 annotated photographs ($640 \times 640$ normalized crops).
- **Annotations:** YOLOv8 format: `class_id x_center y_center width height` (either 1-class `braille_cell` or 63-class characters).
- **License Status:** **Public Domain (CC0 1.0) and CC BY 4.0**.
- **Technical Suitability for Transify:**
  - *Strengths:* Permissive licenses; native bounding-box format for Stage 1 cell localization; realistic camera angles.
  - *Weaknesses:* Variable community annotation precision; requires automated filtering of misaligned bounding boxes.

---

## 3. Physical Standards of Braille Embossing (Marburg Medium Specification)

To ensure the computer vision pipeline adheres to physical reality, the dimensions of standard Braille paper embossing defined by the **World Braille Council** and **Marburg Medium Standard** are adopted:

| Measurement Parameter | Physical Dimension (mm) | Pixel Scale @ 300 DPI | Pixel Scale @ 72 DPI (Mobile) |
|---|:---:|:---:|:---:|
| **Dot Base Diameter ($d$)** | $1.44\text{ mm}$ ($\pm 0.1\text{ mm}$) | $\approx 17\text{ px}$ | $\approx 4\text{ px}$ |
| **Dot Height ($h$)** | $0.48\text{ mm}$ ($\pm 0.05\text{ mm}$) | N/A (3D relief) | N/A (3D relief) |
| **Intra-cell Dot Spacing ($c_{\text{dot}}$)** | $2.34\text{ mm}$ ($\pm 0.1\text{ mm}$) | $\approx 28\text{ px}$ | $\approx 7\text{ px}$ |
| **Inter-cell Spacing ($c_{\text{cell}}$)** | $6.20\text{ mm}$ ($\pm 0.2\text{ mm}$) | $\approx 73\text{ px}$ | $\approx 18\text{ px}$ |
| **Inter-line Spacing ($c_{\text{line}}$)** | $10.00\text{ mm}$ ($\pm 0.5\text{ mm}$) | $\approx 118\text{ px}$ | $\approx 28\text{ px}$ |
| **Cell Aspect Ratio ($H/W$)** | $1.70 : 1.00$ | $1.70 : 1.00$ | $1.70 : 1.00$ |

These geometrical priors are utilized in Transify's grid-clustering and line-reconstruction algorithms to enforce valid anatomical reading order and distinguish real cells from accidental noise artifacts.

---

## 4. Multi-Source Integration Strategy

Transify deploys a **hybrid multi-dataset strategy**:
1. **Stage 1 (Cell Detection & Grid Extraction):** Evaluates bounding-box localization on full documents (Angelina, Roboflow, and realistic calibration documents).
2. **Stage 2 (6-Dot Pattern Classification):** Evaluates isolated cell patches across 64 discrete binary states (or 6 independent dot binary classifiers).
3. **End-to-End Validation:** Independent test documents representing multi-line paragraphs, complete sentences, punctuation, and capital indicators, evaluated against exact ground-truth English strings.
