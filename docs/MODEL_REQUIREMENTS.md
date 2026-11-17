# Transify — AI Model Requirements & Architectural Specifications (Revised)

## 1. Architectural Philosophy and Independence Principle

Transify enforces the **Principle of Model Independence**:
- **Module 01 (Sign Language Translator)** and **Module 02 (Braille Image Translator)** operate on distinct data modalities (video stream vs. document images) with decoupled training pipelines, loss functions, and inference runtime artifacts.
- In accordance with the Phase 1 Review Directive, **Module 01 prioritizes Bangladesh Sign Language (BdSL)**, generating English text through a structured gloss-translation pipeline. **Module 02 targets Unified English Braille (UEB) Grade 1** based on the **ICEB Rules of Unified English Braille, Third Edition (2024)**, adopting a robust two-stage localization-and-classification architecture.

---

## 2. Module 01: Live Sign Language Recognition Engine (BdSL-First)

```
                         MODULE 01 ARCHITECTURAL PIPELINE (BDSL)
                          
   [ Webcam Frame ] (640x480 @ 30 FPS)
          |
          v
   [ MediaPipe Holistic Backbone ]
   (Tracks Left Hand [21], Right Hand [21], and Upper-Body Pose [33])
          |
          v
   [ Anatomical Normalization & Relative Quantization Layer ]
   - Centering: Translate hand coordinates relative to chest / shoulder center (Landmarks 11, 12)
   - Scaling: Scale by inter-shoulder distance || L_11 - L_12 ||_2 to ensure distance invariance
   - Feature Vector: Left Hand (63D) + Right Hand (63D) + Upper Pose (36D) = 162D per frame
          |
          +-----------------------+-----------------------+
          |                                               |
     [ Level A: Alphabet ]                           [ Level B: Word Signs ]
   (Static BdSL Letters / Digits)                  (Dynamic Lexical Signs)
          |                                               |
   Input: 162D Feature Vector                      Input: Sliding Window Buffer
          |                                        T = 30 frames (30 x 162 = 4,860D)
          v                                               |
   [ Deep MLP Classifier (ONNX) ]                         v
   (Trained on BdSL-D1500 / BdSL36)                [ 1D-CNN + BiLSTM Sequencer (ONNX) ]
          |                                        (Trained on BdSLW60 / SignBD-Word)
          +-----------------------+-----------------------+
                                  |
                                  v
                   [ Softmax Probability Vector ]
                   P(c | X) >= threshold (Target: 0.80)
                                  |
                                  v
                   [ Temporal Debounce / Hysteresis Filter ]
                   (Sustained consensus across >= 6 frames)
                                  |
                                  v
                   [ Bengali Sign Gloss Buffer ]
                   (e.g., [আমি], [পানি], [খাওয়া])
                                  |
                                  v
                   [ Semantic Cross-Lingual Translation Engine ]
                   (Gloss-to-English Mapping & SVO Reordering)
                                  |
                                  v
                   [ Fluent English Text: "I drink water" ] ---> [ Text-to-Speech (TTS) ]
```

### 2.1 Input and Output Specifications

| Specification | Parameter | Details |
|---|---|---|
| **Input Modality** | Continuous RGB Video Stream | Client webcam ($640 \times 480$ at target $\ge 30\text{ FPS}$). |
| **Skeletal Feature Extraction** | MediaPipe Holistic | Left hand ($21 \times 3$), Right hand ($21 \times 3$), Upper-body pose ($12 \times 3$ key landmarks: shoulders, elbows, wrists, nose, ears). |
| **Feature Representation** | Normalized Anatomical Vector | $X_t \in \mathbb{R}^{162}$ per frame, centered on mid-shoulder midpoint and scaled by inter-shoulder distance. |
| **Target Task 1 (Level A)** | Static BdSL Characters | 36 basic alphabet letters + 10 digits (from `BdSL-D1500` and `Ishara-Lipi`). |
| **Target Task 2 (Level B)** | Isolated BdSL Words | 60 high-utility daily communication sign words (from `BdSLW60`). |
| **Output Representation** | Class Prediction + Semantic Gloss | `(predicted_gloss: str, confidence: float, translated_english: str)`. |
| **Target Latency Budget** | End-to-End Processing Goal | Proposed engineering target: $\le 30\text{ ms}$ on standard consumer CPU. |

### 2.2 Mathematical Feature Normalization for Two-Handed BdSL

Because BdSL features two-handed alphabets and signs localized relative to the chest and face, landmarks cannot be centered purely on a single wrist:

1. **Anatomical Reference Origin:**
   Let $L_{\text{l\_sh}}$ (Landmark 11) and $L_{\text{r\_sh}}$ (Landmark 12) be the left and right shoulder landmarks:
   $$L_{\text{chest}} = \frac{L_{\text{l\_sh}} + L_{\text{r\_sh}}}{2}$$

2. **Translation Centering:**
   Center all hand and upper-body landmarks relative to the chest midpoint:
   $$L'_i = L_i - L_{\text{chest}}, \quad \forall i \in \{\text{Hands, Pose}\}$$

3. **Scale Invariance:**
   Compute inter-shoulder Euclidean distance $D_{\text{shoulder}} = \|L_{\text{l\_sh}} - L_{\text{r\_sh}}\|_2$. Normalize:
   $$L''_i = \frac{L'_i}{\max(D_{\text{shoulder}}, 10^{-6})}$$
   This guarantees invariance to camera zoom, user distance, and torso dimensions.

### 2.3 Cross-Lingual Semantic Translation Architecture

```
[Recognized BdSL Sign] ---> [Bengali Gloss] ---> [Cross-Lingual Dictionary / Rule Engine] ---> [English Output]
 "পানি" (Water)               "পানি"               Lookup: "water", Rule: Noun                  "Water"
 "আমি পানি খাওয়া"            "আমি", "পানি", "খাওয়া" Rule: [Subj] + [Obj] + [Verb] -> SVO         "I drink water"
```
- For static alphabet fingerspelling, an unambiguous 1-to-1 transliteration table converts Bengali letters to Romanized English spelling.
- For lexical sign words, a bilingual gloss lexicon with rule-based grammatical reordering maps BdSL SOV structures into natural English SVO sentences.

---

## 3. Module 02: Braille Recognition Engine (UEB Grade 1)

```
                         MODULE 02 ARCHITECTURAL PIPELINE (TWO-STAGE)
                          
   [ Input Braille Image ] (Smartphone Photo / Document Scan)
          |
          v
   [ Image Quality & Blur Assessor ]
   (Reject if Laplacian Variance Var(ΔI) < 100)
          |
          v
   [ Illumination Normalization & CLAHE Preprocessing ]
          |
          v
   [ STAGE 1: BRAILLE CELL LOCALIZER ]
   (1-Class YOLOv8-nano trained exclusively to detect `braille_cell` boxes)
          |
          |--> Outputs bounding boxes: B_k = [x_1, y_1, x_2, y_2, conf]
          v
   [ Spatial Layout & Reading-Order Sorter ]
   - Line Clustering: Group bounding boxes into horizontal lines by y-overlap
   - Horizontal Sorting: Sort boxes within each line by x-coordinate
   - Space Detection: If gap Δx > 1.8 * median_cell_width => inject cell space ' '
          |
          v
   [ STAGE 2: CELL-PATTERN / 6-DOT CLASSIFIER ]
   (Lightweight CNN / Binary 6-Dot Classifier on cropped cell patches)
          |
          |--> Outputs 6-bit binary vector: [d_1, d_2, d_3, d_4, d_5, d_6] in {0, 1}^6
          v
   [ Braille ASCII & UEB Grade 1 State Machine Decoder ]
   (Compliant with ICEB Rules of Unified English Braille, 3rd Edition, 2024)
          |
          |-- Rule 6: Number Indicator (⠼) toggles digits 1-0 for subsequent a-j
          |-- Rule 8: Capital Indicator (⠠) capitalizes next character; (⠠⠠) caps word
          |-- Rules 3-5: Punctuation & Symbol Lookup Tables
          v
   [ Decoded English Text + Character Confidence Scores ] ---> [ Text-to-Speech (TTS) ]
```

### 3.1 Input and Output Specifications

| Specification | Parameter | Details |
|---|---|---|
| **Input Modality** | Digital Document Image | JPEG, PNG, WebP ($1200 \times 1600\text{ px}$ to $3000 \times 4000\text{ px}$). |
| **Decoding Standard** | Unified English Braille (UEB) Grade 1 | ICEB Rules of Unified English Braille, Third Edition (2024). |
| **Stage 1 Target** | Cell Bounding Box Localization | 1-class object detector outputting cell coordinates $[x_1, y_1, x_2, y_2]$. |
| **Stage 2 Target** | 6-Dot Pattern Decoding | 6-bit binary classification: $[d_1, d_2, d_3, d_4, d_5, d_6] \in \{0, 1\}^6$. |
| **Output Representation** | Structured Document Text | Decoded English string with line breaks, character confidences, and cell bounding box overlay coordinates. |
| **Target Latency Budget** | Full Page Processing Goal | Proposed engineering target: $\le 1.5\text{ seconds}$ on standard consumer CPU. |

### 3.2 Two-Stage vs. Single-Stage Architectural Trade-off

The decision to adopt **Approach B (Two-Stage Pipeline)** over Approach A (Direct 64-class YOLO) is justified by:
1. **Resolution of Class Imbalance:** Single-stage 64-class object detectors suffer severe performance degradation on rare Braille characters (such as `q`, `z`, and technical symbols) due to long-tail frequency distributions in natural texts. In Approach B, the Stage 1 detector trains on a single class (`braille_cell`) with $100\%$ class balance, while Stage 2 classifies 6 independent binary dots ($d_1$ through $d_6$), completely bypassing the 64-class long-tail penalty.
2. **Annotation Efficiency:** Real-world photographed training pages need only 1-class cell bounding boxes. The 6-dot pattern classifier can be trained on synthetic augmented crops and pre-segmented benchmarks (e.g. `Shanks0465`).
3. **Interpretability:** Decouples spatial localization errors from dot recognition errors, providing clear diagnostics for model refinement.

---

## 4. Performance Targets vs. Experimental Claims

To uphold scientific honesty, Transify establishes explicit research targets for Phase 2 model training without claiming unverified performance:

| Pipeline Component | Proposed Research Target (Phase 2 Goal) | Verification Benchmark |
|---|---|---|
| **BdSL Alphabet Model** | $\text{Macro F1} \ge 90.0\%$ | Held-out signer-independent test split (`BdSL-D1500`). |
| **BdSL Word Sign Model** | $\text{Top-1 Accuracy} \ge 80.0\%$ | Held-out signers on 60 dynamic words (`BdSLW60`). |
| **Braille Cell Localizer** | $\text{mAP@0.50} \ge 92.0\%$ | Held-out document test split (Roboflow / Angelina). |
| **Braille Cell Decoder** | $\text{Cell Accuracy} \ge 88.0\%$ | Held-out smartphone captures under natural lighting. |
| **End-to-End Latency** | $\le 30\text{ ms}$ live sign / $\le 1.5\text{ s}$ Braille page | Local 12-core CPU benchmark suite. |
