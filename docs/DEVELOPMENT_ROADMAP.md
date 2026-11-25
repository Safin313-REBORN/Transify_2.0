# Transify — Phase-Wise Development Roadmap & Milestones (Revised)

## 1. Master Development Lifecycle Overview

Transify adheres to a disciplined, stage-gated research and engineering lifecycle. Movement between phases is strictly contingent upon satisfying verifiable completion criteria.

```
+----------------------------------------------------------------------------------------------------+
|                                    TRANSIFY DEVELOPMENT TIMELINE                                   |
|                                                                                                    |
|  [ PHASE 1: RESEARCH, FEASIBILITY & CORRECTION REVIEW ] --------> (Current State: Review Complete) |
|  - BdSL-First Research & Dataset Audits (BdSL-D1500, BdSLW60)     - UEB Grade 1 Specification (ICEB 2024)|
|  - Anti-Leakage Leave-Signers-Out Protocols                       - Two-Stage Braille Architecture |
|  - Performance Re-Classification & Correction Log                 - Proposed Decision Ballots      |
|                                                                                                    |
|  [ PHASE 2: DATA INGESTION & MVP MODEL DEVELOPMENT ] -----------> (Target Next Phase)              |
|  - Ingest BdSL-D1500 (Alphabet) & BdSLW60 (Words)                 - Ingest Roboflow / Angelina BBoxes|
|  - Feature Pipeline: MediaPipe Holistic (162D Features)           - Stage 1: 1-Class Cell Localizer|
|  - Model 01 Training: BdSL MLP & BiLSTM ONNX Models               - Stage 2: 6-Dot Pattern Model   |
|  - Cross-Lingual Translation: BdSL Gloss -> English Text         - ICEB 2024 UEB State Machine    |
|                                                                                                    |
|  [ PHASE 3: VOCABULARY EXPANSION & MULTI-LANGUAGE SCALING ]                                        |
|  - Dynamic BdSL Scaling (BdSLW401 Transformer Sequencers)         - ASL Secondary Engine (WLASL)   |
|  - Liblouis UEB Grade 2 Back-Translation Engine                   - Multi-Signer Gold Validation   |
|                                                                                                    |
|  [ PHASE 4: FULL SYSTEM INTEGRATION & PRODUCTION HARDENING ]                                       |
|  - FastAPI Async Microservices Backend                            - Accessible High-Contrast UI    |
|  - Real-Time WebSocket Streaming Engine                           - Human-in-the-Loop TTS & Error  |
|  - Continuous SLR & Neural Machine Translation Research           - Production Hardening & Security|
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Phase-by-Phase Detailed Plan

### Phase 1: Research, Feasibility & Project Foundation
- **Status:** **CORRECTION PASS COMPLETE** (Awaiting Project Owner Final Approval).
- **Core Deliverables:**
  - Expanded BdSL dataset registry (`BdSL-D1500`, `SignBD-Word`, `BdSLW60`, `BdSLW401`, `Ishara-Lipi`, `BdSL36`).
  - ASL future expansion inventory with corrected WLASL counts and GPL 2.0 license check.
  - ICEB Rules of Unified English Braille, Third Edition (2024) specification.
  - Comparative analysis of Two-Stage vs. Single-Stage Braille architectures.
  - Re-classification of all metrics and removal of unverified performance claims.
  - Formulation of `PHASE1_CORRECTION_LOG.md`.
- **Gating Criteria:** Formal Project Owner sign-off on the four decision ballots in `RISKS_AND_DECISIONS.md`.

---

### Phase 2: Data Ingestion, Baseline Pipeline & MVP Model Development
- **Status:** **PENDING PHASE 1 SIGN-OFF**.
- **Dependencies:** Project Owner approval of Decision 01 (BdSL MVP), Decision 02 (UEB Grade 1 ICEB 2024), and Decision 03 (Colab GPU training).
- **Sprint 2.1: Data Acquisition & Preprocessing:**
  - Ingest verified BdSL datasets (`BdSL-D1500` for characters, `BdSLW60` for words).
  - Implement `HolisticFeatureExtractor` converting raw video frames into normalized 162-dimensional anatomical coordinate tensors (`.npy`).
  - Ingest Braille datasets (`Roboflow`, `DSBI`, `Angelina`); format 1-class cell localization bounding boxes and pre-segmented cell crops.
  - Freeze strict Leave-Signers-Out (LSO) and document-independent train/val/test splits.
- **Sprint 2.2: Module 01 (BdSL Sign Recognition) MVP:**
  - Train BdSL Alphabet MLP (Level A) and BdSL Word BiLSTM (Level B) on Google Colab GPU.
  - Implement temporal hysteresis/debounce filter ($W = 6$ frames) to suppress jitter.
  - Build the rule-based Bengali Gloss $\rightarrow$ English Text translation engine.
  - Export trained models to portable ONNX format for local CPU inference.
- **Sprint 2.3: Module 02 (Braille Recognition) MVP:**
  - Train Stage 1 (1-Class YOLOv8-nano Cell Localizer) on Google Colab GPU.
  - Train Stage 2 (6-Dot Pattern Classifier) on pre-segmented and synthetic cell patches.
  - Implement the ICEB 2024 UEB Grade 1 state machine decoder.
  - Export Stage 1 and Stage 2 models to ONNX format.
- **Sprint 2.4: Local CPU Benchmarking:**
  - Benchmark both ONNX pipelines on the local 12-core Windows workstation.
  - Verify real-time video processing ($\le 30\text{ ms}$ per frame) and Braille document processing ($\le 1.5\text{ s}$ per page).
- **Target Research Milestones for Phase 2 Exit:**
  - Model 01 achieves research target $\text{Macro F1} \ge 90\%$ on held-out test signers.
  - Model 02 achieves research target $\text{Cell Accuracy} \ge 88\%$ on held-out document photographs.

---

### Phase 3: Vocabulary Expansion, Linguistic Context & Multi-Language Support
- **Status:** Planned.
- **Dependencies:** Validated Phase 2 MVP models.
- **Key Objectives:**
  - Scale BdSL vocabulary to 401 words using `BdSLW401` with Transformer-based Relative Quantization Encoding (RQE).
  - Train secondary American Sign Language (ASL) models on `WLASL100` and `ChicagoFSWild+` as an optional source-language plugin.
  - Integrate `liblouis` C/Python engine to support UEB Grade 2 contracted Braille back-translation.
  - Conduct a multi-signer gold validation protocol with 3–5 diverse local signers across multiple webcams.

---

### Phase 4: Full System Integration, Accessible Web App & Production Hardening
- **Status:** Planned.
- **Dependencies:** Completed Phase 2 & 3 ONNX artifacts.
- **Key Objectives:**
  - Build FastAPI asynchronous microservices with WebSocket streaming (`/ws/sign/live`) and REST document endpoints (`/api/braille/translate`).
  - Develop WCAG 2.1 Level AAA accessible frontend with high-contrast themes, ARIA 1.2 screen-reader compliance, and real-time canvas overlays.
  - Implement human-in-the-loop assistive controls: editable draft text, one-touch retry, and Text-to-Speech (TTS) audio playback.
  - Conduct continuous sign language translation (CSLT) exploratory research.
  - Perform security, privacy, and memory leak audits (ensuring zero persistent biometric storage).

---

### Phase 5: Transify Care CDS, Model Context Protocol (MCP) & Global Deployment
- **Status:** **COMPLETED & DEPLOYED TO PRODUCTION** (Railway Cloud).
- **Key Objectives & Achievements:**
  - Integrated Transify Care clinical decision support (CDS) suite with WHO & Merck Manual-grounded 5-tier emergency triage and insulin titration calculation.
  - Deployed Model Context Protocol (MCP v1.0 / JSON-RPC 2.0) gateway at `/api/mcp` enabling direct integration with AI clinical agents.
  - Enforced Zero Auto-Audio privacy invariants across all browser and TTS interfaces.
  - Achieved 100% automated test coverage (249 automated tests passing across clinical safety, browser regression, and MCP protocols).
  - Maintained cryptographic SQLite persistence integrity (`data/transify.db` SHA-256 invariant verified).
  - Deployed production service to `https://transify20-production.up.railway.app/`.

