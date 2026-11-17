# Transify — Project Charter

## Official Identity

- **Project Name:** Transify
- **Official Title:** An AI-Powered Assistive Communication Platform for Sign Language Recognition and Braille-to-Text Translation
- **Tagline:** *Breaking Communication Barriers.*
- **Phase:** Phase 1 — Research, Feasibility & Project Foundation
- **Document Version:** 1.0.0
- **Status:** Approved Baseline for Review

---

## Executive Summary

**Transify** is a unified assistive communication software platform designed to bridge critical accessibility gaps for individuals who are Deaf, hard-of-hearing, blind, or visually impaired. The platform integrates two independent, dedicated Artificial Intelligence (AI) recognition engines into a single accessible web and desktop application:
1. **Module 01 (Live Sign Language Translator — BdSL-First):** A real-time computer vision system that captures continuous webcam input, extracts 3D skeletal landmarks via MediaPipe Holistic (dual hands + upper-body pose), classifies Bangladesh Sign Language (BdSL) manual alphabets and lexical signs, and translates recognized Bengali sign glosses into coherent English sentences and audible Text-to-Speech (TTS) audio.
2. **Module 02 (Braille Image Translator — UEB Grade 1):** An optical Braille recognition (OBR) system that accepts uploaded or camera-captured photographs of embossed Braille documents, preprocesses the image under variable lighting, localizes Braille cells via a robust two-stage pipeline, decodes 6-dot patterns in strict compliance with the **ICEB Rules of Unified English Braille, Third Edition (2024)**, and reconstructs English text.

Transify rejects superficial wrappers or generic multi-modal commercial chat APIs as substitutes for core recognition. Instead, the project commits to training, validating, and deploying two independent, purpose-built machine learning models trained on verified, publicly documented, and academically peer-reviewed datasets.

---

## Vision and Core Objectives

### Vision
To create an open, mathematically grounded, accessible, and privacy-preserving bridge between sensory-impaired communities and the wider society, enabling natural, autonomous, and barrier-free communication through state-of-the-art computer vision and machine learning.

### Core Objectives
1. **Develop an Independent Live Sign Language Recognition Engine (BdSL Priority):**
   - Real-time skeletal tracking (dual hands and upper-body pose) on consumer-grade CPU hardware.
   - Robust classification of static manual alphabet characters (one-handed and two-handed) and core lexical sign words.
   - Intelligent temporal debounce filtering, semantic gloss accumulation, and grammatical translation into natural English text.
   - Native bi-directional communication aids, including Text-to-Speech (TTS) and manual human-in-the-loop review controls.

2. **Develop an Independent Optical Braille Recognition (OBR) Engine (UEB Grade 1):**
   - Accurate localization and decoding of 6-dot Braille cells from unconstrained photographs (accounting for perspective skew, non-uniform illumination, and page bowing) using a two-stage architecture.
   - Full compliance with established Braille standards, targeting Unified English Braille (UEB) Grade 1 (uncontracted) according to the official **ICEB Rules of Unified English Braille, Third Edition (2024)**.
   - Reconstruction of character sequences into structured English text with line-break awareness and confidence scoring.

3. **Maintain Strict Modularity and Architectural Decoupling:**
   - Ensure the Sign Language model and the Braille model operate as separate microservices or independent pipeline workers with dedicated training, validation, and inference boundaries.
   - Ensure neither model's failure degrades the availability of the other.

---

## Detailed Module Scope

### Module 01: Live Sign Language Translator (BdSL)

```
+---------------------------------------------------------------------------------------------------+
|                           MODULE 01: LIVE SIGN TRANSLATOR (BDSL-FIRST)                            |
|                                                                                                   |
|  [ Live Video ] ---> [ MediaPipe Holistic ] ---> [ Anatomical Coord ] ---> [ MLP / BiLSTM     ]   |
|  [   Webcam   ]      [ (Dual Hands + Pose)]      [ Normalization    ]      [ Classifiers      ]   |
|                                                  (Chest-centered,          (Level A / Level B)    |
|                                                   Shoulder-scaled)                                |
|                                                                                   |               |
|                                                                                   v               |
|  [ English TTS ] <-- [ Semantic Translator ] <-- [ Debounce Filter ] <--- [ Bengali Sign Gloss]   |
|  [ Audio / UI  ]     [ (SOV -> SVO English)]     [ & Consensus     ]      [ Stream + Conf.    ]   |
+---------------------------------------------------------------------------------------------------+
```

- **Input:** Continuous RGB video stream via standard client webcam ($640 \times 480$ at target $\ge 30\text{ FPS}$).
- **Processing Pipeline:**
  1. Skeletal detection and tracking isolating dual hands (42 landmarks) and upper-body pose (key torso and arm points).
  2. Spatial normalization: translation centering relative to the chest midpoint and scale normalization via inter-shoulder distance.
  3. Feature vector construction (162-dimensional normalized coordinates per frame).
  4. Hybrid classification:
     - Level A (Static BdSL Alphabet): Supervised deep MLP classification on normalized coordinate vectors.
     - Level B (Dynamic Lexical Signs): Temporal sequence modeling over a sliding window ($T = 30$ frames) using a 1D-CNN + BiLSTM architecture.
  5. Temporal smoothing via sliding-window consensus (hysteresis thresholding) to eliminate jitter.
  6. Semantic translation: mapping recognized Bengali sign glosses into natural English text with grammatical reordering.
  7. English text generation with full Text-to-Speech (TTS) audio playback controls.
  8. Human-in-the-loop confirmation, editing, and retry mechanisms.

### Module 02: Braille Image Translator (UEB Grade 1)

```
+---------------------------------------------------------------------------------------------------+
|                        MODULE 02: BRAILLE IMAGE TRANSLATOR (TWO-STAGE)                            |
|                                                                                                   |
|  [ Uploaded / ] ---> [ Quality & Blur   ] ---> [ Illumination-   ] ---> [ Stage 1: Cell Localizer]|
|  [ Captured   ]      [ Assessment       ]      [ Invariant Prep  ]      [ (1-Class YOLOv8-nano)   ]|
|  [ Document   ]      (Laplacian Var.)          (Adaptive CLAHE)                                   |
|                                                                                   |               |
|                                                                                   v Cell Crops    |
|  [ English TTS ] <-- [ ICEB 2024 UEB    ] <--- [ Line Clustering & ] <-- [ Stage 2: 6-Dot Pattern ]|
|  [ Audio / UI  ]     [ Grade 1 Decoder  ]      [ Reading-Order Sort]     [ Classifier (CNN)       ]|
+---------------------------------------------------------------------------------------------------+
```

- **Input:** Single or multi-page digital images of embossed paper Braille (JPEG, PNG, WebP) uploaded via browser or snapped using device camera.
- **Processing Pipeline:**
  1. Image quality assessment (Laplacian variance blur detection, minimum resolution checks).
  2. Image preprocessing: grayscale conversion, Contrast Limited Adaptive Histogram Equalization (CLAHE), and deskewing.
  3. Stage 1 Cell Localization: 1-class deep object detection (YOLOv8-nano) identifying physical `braille_cell` bounding boxes.
  4. Spatial layout reconstruction: line clustering via vertical overlap and horizontal sorting in reading order.
  5. Stage 2 Pattern Classification: lightweight CNN classifying the 6-dot binary state $[d_1, \dots, d_6] \in \{0, 1\}^6$ on cell crops.
  6. Character decoding: deterministic state machine compliant with the **ICEB Rules of Unified English Braille, Third Edition (2024)**.
  7. Editable review panel displaying the reconstructed English text with character-level confidence scores.
  8. Optional English Text-to-Speech (TTS) playback.
  4. 6-dot matrix extraction: mapping each cell into a 6-bit binary state $[d_1, d_2, d_3, d_4, d_5, d_6] \in \{0, 1\}^6$.
  5. Reading order reconstruction: horizontal sorting within clustered lines based on y-coordinate projection.
  6. Character decoding against Unified English Braille (UEB) Grade 1 rules (including capital indicators, numerical prefixes, and punctuation).
  7. Editable review panel displaying the reconstructed English text with character-level confidence scores.
  8. Optional English Text-to-Speech (TTS) playback.

---

## Critical Scientific Distinctions & Boundaries

To preserve research integrity and prevent over-promising, Transify formally defines the following technical boundaries:

### Sign Language: Linguistic Reality vs. Engineering Granularity
1. **Fingerspelling (Alphabet Recognition):**
   - Letter-by-letter manual representation of written orthography.
   - *Transify MVP Scope:* Fully supported in real time for static and low-motion letters (A–Z, numbers, space, delete).
2. **Isolated Sign Recognition (Lexical Signs):**
   - Single vocabulary words expressed through comprehensive hand shapes, motion trajectories, and locations.
   - *Transify MVP Scope:* Supported for a targeted core dictionary of 50–100 high-utility daily communication glosses.
3. **Continuous Sign Language Recognition (CSLR) & Translation (SLT):**
   - Fluent, unrestricted sentence signing characterized by grammatical non-manual markers (facial expressions, mouthings, head tilts), directional verbs, spatial reference indexing, and strong co-articulation.
   - *Transify Boundary:* Continuous translation of unconstrained deaf-to-deaf discourse requires extensive multi-modal parallel corpora (e.g., PHOENIX-Weather 2014T) and heavy spatial-temporal transformers that exceed consumer client capabilities. It is explicitly categorized as a **Phase 4 Research Goal**, not an MVP deliverable.

### Braille: Standardization Reality
1. **English Braille Grade 1 (Uncontracted):**
   - Exact one-to-one mapping between embossed 6-dot cells and English characters.
   - *Transify Scope:* Primary foundation for Phase 1 and Phase 2 MVP.
2. **Unified English Braille (UEB):**
   - Standardized international code established by the International Council on English Braille (ICEB). Incorporates unambiguous prefixes for capitals (Dot 6), numbers (Dots 3-4-5-6), and standardized technical symbols.
   - *Transify Scope:* Standard to which all Grade 1 character decoders must strictly adhere.
3. **English Braille Grade 2 (Contracted):**
   - Highly compressed system containing 189 contractions, abbreviations, and single-cell whole-word signs (e.g., cell for "the", "and", "ing").
   - *Transify Boundary:* Decoding Grade 2 requires a contextual natural language back-translation grammar engine (such as the open-source Liblouis engine). The vision model will output raw 6-dot cell configurations; UEB Grade 2 parsing is architected as an external rule plugin to be finalized in Phase 3.

---

## Target Audience and User Personas

| Persona | Primary Need | Transify Feature Utilization |
|---|---|---|
| **Alex (Deaf Professional)** | Communicating directly with non-signing colleagues in face-to-face settings without an interpreter. | Module 01 Live Sign Language Translator, real-time caption display, Text-to-Speech output. |
| **Priya (Blind Student)** | Reading physical handouts, printed Braille notices, and peer notes independently. | Module 02 Braille Image Translator, camera capture, audio TTS readout, screen-reader accessible UI. |
| **David (Special Educator)** | Assessing Braille literacy worksheets and teaching sign alphabet to young children. | Module 01 fingerspelling practice validator; Module 02 batch Braille verification and visual character overlay. |
| **Maria (Hearing & Sighted Caregiver)** | Understanding signs performed by an elderly relative with late-onset speech loss. | Module 01 Live Sign Translator, word-by-word accumulation, audio readout. |

---

## Operating Principles and Quality Criteria

1. **Empirical Truth over Marketing:** We report exact evaluation metrics (WER, CER, Macro F1, Latency in ms) derived strictly from held-out test splits. Training accuracy is never cited as proof of real-world efficacy.
2. **Zero Synthetic Hallucination:** Under no circumstances are training datasets, citations, benchmark numbers, or license permissions invented.
3. **Generalization over Memorization:** Models must be validated using strictly signer-independent splits (for sign recognition) and document-independent splits (for Braille recognition) to ensure robustness against unseen users and lighting conditions.
4. **Privacy-by-Design:** All webcam frames and Braille images are processed either in-memory on the client or within an isolated, ephemeral backend buffer. No user biometric video or personal documents are stored without explicit, authenticated consent.
5. **Human-in-the-Loop Assistive Design:** Recognizing the safety-critical nature of assistive tools, the UI provides unambiguous confidence indicators, editable draft text, and one-touch retry buttons before emitting finalized audio or text.
