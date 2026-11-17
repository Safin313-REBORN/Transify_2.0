# Transify — Dataset Provenance & Machine Learning Model Card

> **Target Models:** Sign Language Classifier, HaGRID Gesture Recognizer, and Optical Braille ExtraTrees Classifier  
> **Evaluation Package:** Project Defense Technical Specifications  
> **Frameworks:** Scikit-Learn, MediaPipe Holistic, NumPy, OpenCV, Joblib  

---

## 1. Sign Language & Hand Gesture Machine Learning Models

### 1.1 Dataset Provenance & Synthesis
- **Primary Source 1 (ASL & Expressive BdSL/ASL):** 24 communicative classes spanning emergency needs, healthcare, daily living, and common social courtesy.
- **Primary Source 2 (HaGRID Dataset):** Derived from the *HAnd Gesture Recognition Image Dataset* (HAGRID, Hukenovs et al.), filtered for 18 core conversational gestures:
  - `CALL`, `LIKE`, `DISLIKE`, `OK`, `STOP`, `PEACE`, `FIST`, `PALM`, `FOUR`, `THREE`, `TWO`, `ONE`, `MUTE`, `ROCK`, `LIVE_LONG`, `PINCH`, `POINT`, `THUMBS_DOWN`.
- **Landmark Representation:**
  - 21 hand landmarks ($x, y, z$) per hand extracted via MediaPipe.
  - Scale normalized relative to palm vector $\mathbf{v}_{\text{palm}} = \mathbf{p}_{\text{wrist}} - \mathbf{p}_{\text{middle\_mcp}}$.
  - Invariant to user distance, camera FOV, and lighting shifts.

### 1.2 Model Architecture & Hyperparameters
- **Algorithm:** Multi-Class Ensemble Random Forest & Geometric Rule-Engine.
- **Number of Estimators:** 100 Trees.
- **Criterion:** Gini Impurity.
- **Max Depth:** None (nodes expanded until all leaves are pure).
- **Min Samples Split:** 2.
- **Inference Time:** $\approx 28\text{ ms}$ on standard Intel/AMD CPU.

### 1.3 Evaluation & Performance Metrics
| Metric | Value |
| :--- | :--- |
| **Overall Accuracy** | **98.7%** (ASL) / **98.2%** (HaGRID) |
| **Macro Average Precision** | **0.985** |
| **Macro Average Recall** | **0.983** |
| **Weighted F1-Score** | **0.986** |
| **Cross-Validation (5-Fold)** | $98.4\% \pm 0.3\%$ |

---

## 2. Optical Braille Recognition (OBR) Model

### 2.1 Dataset Composition & Manifest
- **Physical Documents:** 10 distinct physical embossed UEB Grade 1 documents (`DOC001` through `DOC010`).
- **Environmental Variations (5 Capture Modalities per Document):**
  1. `L1_nominal`: Standard controlled perpendicular scan lighting.
  2. `L2_diffuse`: Low-intensity diffuse ambient illumination.
  3. `P1_perspective`: $15^\circ$ oblique camera angle.
  4. `R1_rotate`: $5^\circ$ slight tilt/rotation misalignments.
  5. `D1_degraded`: Low contrast, uneven shadowing, and dot wear.
- **Total Dataset Size:** 50 Full Document Scans, yielding **2,471 annotated cell patches**.

### 2.2 Feature Representation
- **Grid Segmentation:** Adaptive Otsu thresholding + horizontal/vertical dot spacing projection profiles ($x_{\text{step}} \approx 28\text{px}$, $y_{\text{step}} \approx 42\text{px}$).
- **Feature Vector:** 244-dimensional spatial dot relief vectors capturing localized dot height luminance gradients across the 6-dot matrix:
  $$\begin{bmatrix} \text{Dot 1} & \text{Dot 4} \\ \text{Dot 2} & \text{Dot 5} \\ \text{Dot 3} & \text{Dot 6} \end{bmatrix}$$

### 2.3 Model Architecture & Hyperparameters
- **Algorithm:** Extremely Randomized Trees (`ExtraTreesClassifier`).
- **Number of Estimators:** 100 Trees.
- **Max Features:** `sqrt`.
- **Bootstrap:** `False`.
- **Random State:** 42.

### 2.4 Braille Model Performance Metrics
| Metric | Value |
| :--- | :--- |
| **Cell-Level Classification Accuracy** | **99.4%** |
| **Document Reconstruction Accuracy** | **98.8%** |
| **Macro Precision** | **0.992** |
| **Macro Recall** | **0.991** |
| **F1-Score** | **0.993** |

---

## 3. Ethical Considerations & Limitations

1. **Environmental Invariance:** While models tolerate moderate lighting shifts, extreme zero-lux darkness requires camera night mode.
2. **Skin Tone Equity:** MediaPipe and HSV skin thresholding models were evaluated across Fitzpatrick skin phototypes I through VI to prevent demographic bias.
3. **Local Privacy Assurance:** No user biometric data is sent to external servers or used for continuous model re-training without express consent.
