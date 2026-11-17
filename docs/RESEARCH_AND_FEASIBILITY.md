# Transify — Master Research & Feasibility Study (Revised)

## 1. Introduction and Scope of Investigation

Assistive communication systems designed to bridge the gap between sensory-impaired individuals and the hearing/sighted public require a rigorous synthesis of computer vision (CV), deep learning (DL), natural language processing (NLP), and domain-specific linguistic knowledge. 

In response to the Phase 1 Review Directive, this updated study establishes:
1. **Module 01: Vision-Based Bangladesh Sign Language Recognition (SLR) and English Translation:** Prioritizing BdSL for the initial Minimum Viable Product (MVP), evaluating multi-modal skeletal tracking (MediaPipe Holistic), separating the 5 distinct sign language tasks, and formalizing the cross-lingual translation pipeline ($\text{BdSL} \rightarrow \text{Bengali Gloss} \rightarrow \text{English Text}$).
2. **Module 02: Optical Braille Recognition (OBR) and Standard-Compliant Decoding:** Prioritizing Unified English Braille (UEB) Grade 1 in strict accordance with the **ICEB Rules of Unified English Braille, Third Edition (2024)**, and comparatively evaluating single-stage versus two-stage cell localization and pattern decoding architectures.

---

## 2. Module 01: Sign Language Recognition — Academic Literature Review

### 2.1 The Five Distinct Computational Tasks in Sign Language Processing

Sign language processing is not a monolithic classification task. Rigorous research mandates decoupling five distinct engineering stages:

```
[Task 1: Static Alphabet] --------> Isolated manual characters / digits (e.g. 36 BdSL basic letters).
                                    Spatial handshape & joint angles. Single frame.
                                    
[Task 2: Dynamic Fingerspelling] -> Rapid spelling transitions with co-articulation.
                                    Frame sequences. Requires CTC sequence decoders.
                                    
[Task 3: Isolated Word Signs] ----> Single lexical vocabulary signs (e.g. 60 words in BdSLW60).
                                    Handshape + 3D motion trajectory + body location.
                                    
[Task 4: Continuous SLR (CSLR)] --> Fluent sentence signing without pauses.
                                    Severe co-articulation, spatial verbs, grammar.
                                    
[Task 5: Sign Translation (SLT)] -> End-to-end mapping from sign video / glosses to spoken language text.
                                    Cross-lingual syntax reordering (e.g. BdSL SOV -> English SVO).
```

- **Scope Boundary for Transify MVP:** The Phase 2 MVP targets **Task 1 (Static Alphabet Recognition)** and **Task 3 (Isolated Word Signs)**. Tasks 2, 4, and 5 (Dynamic fingerspelling sequences, continuous sentence signing, and full neural sign translation) require multi-modal parallel video-text corpora and heavy spatial-temporal transformers; they are formally categorized as **Phase 3 and Phase 4 Research Goals**.

---

### 2.2 Foundational Benchmark Studies

#### Study 1: Bangla Sign Language (BdSL) Alphabets and Numerals Classification Using a Deep Learning Model
- **Authors:** Kanchon Kanti Podder, Muhammad E. H. Chowdhury, Anas M. Tahir, et al.
- **Publication / DOI:** *Sensors* (MDPI), 2022, 22(3), 974 / [DOI: 10.3390/s22030974](https://doi.org/10.3390/s22030974)
- **Objective:** Classify complex one-handed and two-handed BdSL alphabets and numerals under variable backgrounds and diverse skin tones.
- **Dataset Evaluated:** `BdSL-D1500` (132,061 images across 87 classes: 38 one-hand, 36 two-hand, 10 digits, compound numerals).
- **Published Benchmark Results:** The authors reported that a fine-tuned ResNet18 achieved up to $99.99\%$ test accuracy on their segmented image crop evaluation set.
- **Limitations:** Evaluated on isolated cropped images; does not address temporal video transitions or continuous signing.
- **Relevance to Transify:** Establishes that BdSL alphabets have high intra-class discriminability when both hands are captured with clean feature representations.

#### Study 2: BdSLW60: A Word-Level Bangla Sign Language Dataset
- **Authors:** Husne Ara Rubaiyeat, Hasan Mahmud, Ahsan Habib, Md. Kamrul Hasan
- **Preprint / Identifier:** arXiv:2402.10098 (Feb 2024) / [GitHub: hasanssl/RQE](https://github.com/hasanssl/RQE)
- **Objective:** Address the acute shortage of unconstrained word-level BdSL video benchmarks.
- **Dataset Evaluated:** `BdSLW60` (9,307 video trials, 60 sign words, 18 signers, checked by 60 annotators).
- **Key Contribution:** Relative Quantization Encoding (RQE) anchoring landmarks to anatomical reference points.
- **Relevance to Transify:** Provides the verified, peer-reviewed video benchmark required to train our Phase 3 isolated word recognition model.

#### Study 3: SignBD-Word: Video-Based Bangla Word-Level Sign Language and Pose Translation
- **Authors:** Ataher Sams, Ahsan Habib Akash, S. M. M. Rahman
- **Conference / Repository:** IEEE ICCCNT 2023 / [Zenodo DOI: 10.5281/zenodo.6779843](https://doi.org/10.5281/zenodo.6779843)
- **Dataset Evaluated:** `SignBD-Word` (6,000 video clips, 200 unique lexical words, full-body and upper-body views + 2D pose data).
- **Relevance to Transify:** Confirms that upper-body pose information is essential to disambiguate BdSL signs performed at different anatomical locations (head, chest, shoulder).

#### Study 4: Word-Level Deep Sign Language Recognition from Video (WLASL)
- **Authors:** Dongxu Li, Cristian Rodriguez, Xin Yu, Hongdong Li
- **Conference / DOI:** IEEE/CVF WACV 2020 / [arXiv:1910.11006](https://arxiv.org/abs/1910.11006)
- **Dataset Evaluated:** WLASL (2,000 glosses, 21,083 indexed video instances, 119 signers).
- **Published Benchmark Results:** I3D achieved $65.89\%$ Top-1 Accuracy on WLASL100, dropping to $32.48\%$ on WLASL2000.
- **Relevance to Transify:** Illustrates the severe long-tail scaling penalty when expanding vocabulary beyond 100 classes in video sign recognition.

---

## 3. Linguistic Architecture & Cross-Lingual Pipeline for BdSL

### 3.1 Grammatical Reality: Sign Language Syntax vs. English

A common engineering misconception is assuming sign languages follow English spoken grammar. They do not:
- **English Syntax:** Strict Subject-Verb-Object (SVO) word order ("I drink water").
- **BdSL Syntax:** Predominantly Subject-Object-Verb (SOV) or Topic-Comment structure ("I water drink").
- **Spatial Inflection & Directionality:** In BdSL, verb direction indicates subject and object; tense is indicated by time markers rather than grammatical verb conjugation.
- **Non-Manual Markers (NMMs):** Negation, questioning, and emotional intensity are conveyed via head tilts, eyebrow furrowing, and mouth morphemes.

### 3.2 The Transify Cross-Lingual Pipeline

Because the source language is BdSL and the target software output is English, Transify adopts a staged semantic translation pipeline:

```
+----------------------------------------------------------------------------------------------------+
|                                    TRANSIFY BDSL-TO-ENGLISH PIPELINE                               |
|                                                                                                    |
|  [ Live Video Stream ]                                                                             |
|          |                                                                                         |
|          v                                                                                         |
|  [ Vision Feature Extraction: MediaPipe Holistic (Dual Hands + Upper-Body Pose + Face) ]           |
|          |                                                                                         |
|          v                                                                                         |
|  [ Coordinate Normalization: Anatomical Anchor Centering (Torso / Wrist) ]                         |
|          |                                                                                         |
|          v                                                                                         |
|  [ Recognition Model: Classification of BdSL Alphabet / Lexical Sign Gloss ]                       |
|          |                                                                                         |
|          v                                                                                         |
|  [ Semantic Representation: Bengali Sign Gloss Stream (e.g. [আমি] [পানি] [খাওয়া]) ]              |
|          |                                                                                         |
|          v                                                                                         |
|  [ Cross-Lingual Translation Engine: Gloss-to-English Mapping & Syntax Reordering ]                |
|     - Level A (Fingerspelling): Bengali character transliteration / direct English spelling        |
|     - Level B (Lexical Words): Lexicon lookup & rule-based template reordering (SOV -> SVO)       |
|          |                                                                                         |
|          v                                                                                         |
|  [ Fluent English Text: "I drink water" ] ---> [ Text-to-Speech (TTS) Audio Output ]               |
+----------------------------------------------------------------------------------------------------+
```

### 3.3 MediaPipe Hands vs. MediaPipe Holistic Evaluation

Our review investigated whether MediaPipe Hands alone is sufficient for BdSL:

| Dimension | MediaPipe Hands Alone | MediaPipe Holistic (Hands + Pose + FaceMesh) |
|---|---|---|
| **Tracking Scope** | Single or dual hand landmarks (21 points per hand) | Dual hands (42 pts) + Upper-body pose (33 pts) + FaceMesh (468 pts) |
| **Two-Handed BdSL Alphabets** | High vulnerability to finger swapping and self-occlusion | Resolves spatial ambiguity by referencing wrist to elbow/shoulder bones |
| **Anatomical Body Anchoring** | **Fails completely.** Cannot determine if hand is at chest, chin, or forehead | **Succeeds.** Directly measures distance between hand landmarks and facial/torso anchor points |
| **Non-Manual Facial Signals** | Zero facial information | Captures eyebrow position, mouth openness, and head orientation |
| **CPU Computational Load** | Very light ($\sim 14\text{ ms}$ on CPU) | Moderate ($\sim 28–35\text{ ms}$ on 12-core CPU; optimized via pose subsampling) |
| **Engineering Verdict** | **INSUFFICIENT for general BdSL** | **SELECTED ARCHITECTURAL FOUNDATION** |

---

## 4. Module 02: Braille Standards & Architectural Re-Evaluation

### 4.1 Braille Standards: Unified English Braille (UEB) Grade 1

The decoding specification for Transify is formally aligned with:
> **The Rules of Unified English Braille, Third Edition (2024)**  
> *Published by the International Council on English Braille (ICEB)*

Key Rules Governing the Transify Decoder:
1. **Uncontracted (Grade 1) Scope:** Spells out every word letter-by-letter, eliminating the 189 contractions of Grade 2.
2. **Numeric Indicator (Rule 6):** Dots 3-4-5-6 (`⠼`) sets numeric mode for subsequent letters `a`–`j` ($1$–$0$). Numeric mode is terminated by a space, hyphen, or explicit letter indicator (Dots 5-6 `⠰`).
3. **Capital Indicators (Rule 8):**
   - Single capital prefix: Dot 6 (`⠠`) capitalizes the immediately following letter.
   - Word capital prefix: Double Dot 6 (`⠠⠠`) capitalizes the entire word.
4. **Punctuation & Quotation Marks (2024 Rule Revisions):** Strict decoding of unambiguous UEB multi-cell symbols for brackets, slashes, quotation marks, and currency signs.

---

### 4.2 Architectural Re-Evaluation: Approach A vs. Approach B

The Phase 1 review requested a detailed comparative evaluation between:
- **Approach A:** YOLO-based direct 64-class cell classification.
- **Approach B:** Separate Braille cell localization followed by cell-pattern classification (Two-Stage Pipeline).

```
+----------------------------------------------------------------------------------------------------+
|                               BRAILLE ARCHITECTURAL COMPARISON                                     |
|                                                                                                    |
|  APPROACH A: Single-Stage Direct YOLO Classification                                               |
|  [ Braille Image ] ---> [ YOLOv8-nano (64 Classes) ] ---> [ Line Sorter ] ---> [ UEB Decoder ]     |
|                                                                                                    |
|  APPROACH B: Two-Stage Pipeline (Localization + Pattern Classification)                            |
|  [ Braille Image ] ---> [ Cell Localizer (1-Class YOLO / Morph) ]                                  |
|                                      |                                                             |
|                                      v Localized Cell Crops                                        |
|                         [ 6-Dot Pattern Classifier (Lightweight CNN) ]                             |
|                                      |                                                             |
|                                      v Decoded 6-Bit Vectors                                       |
|                         [ Line Sorter ] ---> [ UEB Decoder ]                                       |
+----------------------------------------------------------------------------------------------------+
```

#### Detailed Trade-Off Matrix

| Evaluation Dimension | Approach A: Direct 64-Class YOLO | Approach B: Two-Stage Localization + Classification |
|---|---|---|
| **Class Imbalance Resilience** | **Poor.** Extreme long-tail imbalance in natural text (e.g. thousands of 'e', 't', 'a' cells, but few 'q', 'z', or rare punctuation cells in training images). | **Exceptional.** Localization model trains on a single class (`braille_cell`), completely invariant to character frequencies. The pattern classifier can be balanced via data augmentation. |
| **Annotation Burden** | Very High. Every cell in every training photo must be manually annotated with its correct 64-class label. | Low. Real photographs only need 1-class bounding boxes; pattern classifier can be trained on pre-segmented crops (e.g. Shanks0465 Kaggle) and synthetic dot grids. |
| **Localization Precision** | Bound to class prediction logits; misclassification often causes bounding box suppression via NMS. | High. Localization focuses purely on detecting cell physical boundaries. |
| **Interpretability & Error Diagnosis** | Black-box. Difficult to determine if an error was due to missing box detection or dot pattern confusion. | Highly modular. Errors can be isolated to either localization failure or pattern classification failure. |
| **Inference Latency** | Single forward pass ($\sim 350\text{ ms}$ on CPU). | Two passes: Localization ($\sim 250\text{ ms}$) + batched crop classification ($\sim 100\text{ ms}$) $\approx 350\text{ ms}$ total on CPU. |
| **Recommendation** | Secondary / Experimental exploration. | **SELECTED PRIMARY ARCHITECTURE FOR TRANSFIY MVP** |

---

## 5. Dataset Legal Audits: Angelina Braille & DSBI

1. **Angelina Braille Images Dataset:**
   - Hosted at `IlyaOvodov/AngelinaDataset`.
   - **Audit Finding:** The repository contains **no standard open-source license file** (such as MIT, Apache 2.0, or CC BY). While developed for a non-profit assistive application, legal redistribution or commercial rights are NOT formally granted. Transify utilizes this dataset strictly as an academic research reference.
2. **DSBI (Double-Sided Braille Image Dataset):**
   - Hosted at `yeluo1994/DSBI` and OpenDataLab.
   - **Audit Finding:** Carries an explicit academic research disclaimer restricting usage to scientific evaluation and prohibiting commercial applications.
3. **Legal Compliance Mandate:** Transify will train its baseline models strictly under non-commercial academic research terms. Before any commercialization or open public deployment, either explicit written permission from the authors must be secured or independent document data collection must be executed.

---

## 6. Corrected Performance Targets & Metric Classification

All performance figures across Transify are classified into four distinct categories:

1. **Measured Experimental Results:**
   - **Status: NONE.** Transify has trained no models during Phase 1.
2. **Published External Benchmark Results (from Literature):**
   - $99.99\%$ ResNet18 accuracy reported by Podder et al. (2022) on cropped `BdSL-D1500` images.
   - $> 99.0\%$ character accuracy reported by Ovodov (2021) on the Angelina Braille reader test set.
   - $99.12\%$ precision / $98.85\%$ recall reported by Li et al. (2018) for recto dots on DSBI flatbed scans.
   - $65.89\%$ Top-1 on WLASL100 and $32.48\%$ on WLASL2000 reported by Li et al. (2020).
3. **Proposed Research Targets (Phase 2 Milestones):**
   - Module 01 (BdSL Alphabet): Target $\text{Macro F1} \ge 90.0\%$ on held-out signers.
   - Module 01 (BdSL Words): Target $\text{Top-1 Accuracy} \ge 80.0\%$ across 60 words on held-out signers.
   - Module 02 (Braille Cells): Target $\text{Cell Accuracy} \ge 88.0\%$ on held-out photographed documents.
4. **Unverified Engineering Estimates:**
   - Estimated end-to-end live video latency budget of $\sim 25–35\text{ ms}$ on a multi-core client CPU, subject to empirical measurement in Phase 2.
