# Transify — Technical Risks, Dataset Limitations & Decision Matrix (Revised)

## 1. Technical Risk Assessment and Mitigation Strategies

Every assistive AI system operating in unpredictable physical environments faces concrete failure modes. The matrix below defines the audited technical risks and engineering mitigations:

| Risk ID | Risk Category | Risk Description | Likelihood | Impact | Severity | Mitigation Strategy |
|---|---|---|---|---|---|---|
| **TR-01** | SLR Tracking | **Two-Handed Self-Occlusion in BdSL:** BdSL alphabets and signs heavily involve overlapping hands, confusing monocular hand trackers. | High | High | **Critical** | Integrate **MediaPipe Holistic** (dual hands + 33-point body pose); anchor hand coordinates to shoulder and elbow joints to disambiguate overlapping fingers. |
| **TR-02** | SLR Latency | **Holistic Backbone CPU Overhead:** Running full MediaPipe Holistic (two hands + pose + FaceMesh) increases latency compared to Hands alone. | Medium | High | **High** | Subsample face landmarks to 10 key boundary points or run pose/hand tracking at native frame rate while computing FaceMesh every 3rd frame. |
| **TR-03** | SLR Translation | **Grammatical Mismatch (BdSL SOV $\rightarrow$ English SVO):** Direct word-for-word translation produces broken, ungrammatical English. | High | High | **High** | Implement a rule-based semantic parser and bilingual gloss-reordering engine for MVP lexical vocabulary, mapping recognized gloss streams to natural English sentences. |
| **TR-04** | OBR Vision | **Double-Sided Interpoint Shadow Inversion:** In double-sided Braille, lighting angle inverts recto (bulging) vs. verso (indented) dot shadows. | High | High | **Critical** | Adopt **Approach B (Two-Stage Pipeline)**: The Stage 1 localizer identifies physical cell boundaries, while the Stage 2 classifier uses directional CLAHE filters to isolate convex dots. |
| **TR-05** | OBR Distribution | **Class Imbalance in Natural Braille Text:** Severe long-tail imbalance on rare Braille characters degrades 64-class single-stage detectors. | High | High | **High** | Use a 1-class cell localizer combined with a 6-bit independent dot classifier, eliminating the 64-class long-tail penalty. |
| **TR-06** | Computational | **Python 3.14 Local CUDA Ecosystem Absence:** The workstation runs Python 3.14.6 on Windows 11 without native GPU CUDA wheels for PyTorch / Ultralytics. | High | High | **Critical** | Train deep models using **Google Colab GPUs** (Python 3.10/3.11 with CUDA 12.x), exporting lightweight ONNX models for local multi-core CPU inference. |

---

## 2. Dataset Limitations and Legal/Licensing Audits

### 2.1 License Compliance Matrix

| Dataset | Declared License | Commercial Permissibility | Redistribution Rights | Project Compliance Action |
|---|---|---|---|---|
| **BdSL-D1500** | CC BY 4.0 | Permissible with attribution | Permissible with attribution | Approved as primary BdSL alphabet training corpus. |
| **SignBD-Word** | CC BY-SA 4.0 | Permissible under ShareAlike | Permissible under ShareAlike | Approved for word-level BdSL training; downstream derivatives must share alike. |
| **BdSLW60 & BdSLW401** | GPL 2.0 (GitHub) | Permissible under GPL terms | Copyleft source code sharing | Approved for academic research and open-source release. |
| **Ishara-Lipi** | CC BY 4.0 | Permissible with attribution | Permissible with attribution | Approved as secondary BdSL character benchmark. |
| **DSBI** | Academic Research Disclaimer | **Non-Commercial Only** | No raw redistribution | Benchmark reference only; commercial redistribution prohibited. |
| **Angelina Braille** | Non-Profit Educational Intent | **NO explicit OSI license file** | Unspecified / Non-commercial | Academic reference only; commercial deployment requires author consent. |
| **WLASL & MS-ASL** | C-UDA (Computational Use) | **Non-Commercial Only** | No raw video redistribution | Retained for future ASL expansion under academic research terms. |
| **Kaggle ASL Alphabet** | GPL 2.0 *(Corrected)* | Copyleft open source | Permissible under GPL terms | **RESTRICTED:** Prohibited from production validation due to single-signer bias. |

---

## 3. Open Research Questions

1. **Optimal Semantic Reordering for Continuous BdSL:**
   - *Question:* Beyond the MVP's isolated vocabulary, what neural translation architecture (e.g. mBART, MarianMT, or lightweight T5) best handles continuous BdSL gloss-to-English translation?
2. **WebAssembly vs. WebSocket Streaming Trade-off:**
   - *Question:* Does running MediaPipe Holistic in-browser via WebAssembly deliver better frame stability on low-end client laptops than streaming frames over WebSockets to a local FastAPI backend?
3. **Double-Sided Dot Peak Separation:**
   - *Question:* Can an unsupervised Gaussian mixture model on cell crop pixel gradients reliably distinguish debossed verso dots from embossed recto dots across varied paper textures?

---

## 4. Key Decisions Requiring Project Owner Approval

The following four strategic decisions are submitted as **team recommendations awaiting final Project Owner sign-off**:

```
+----------------------------------------------------------------------------------------------------+
|                                    PROJECT DECISION BALLOT                                         |
+----------------------------------------------------------------------------------------------------+
```

### DECISION 01: Primary Sign Language for MVP
- **Recommendation:** **Bangladesh Sign Language (BdSL)** is prioritized for the first MVP. American Sign Language (ASL) is designated as a future expansion module.
- *Rationale:* Directly addresses accessibility needs in Bangladesh. Large verified datasets (`BdSL-D1500`, `BdSLW60`, `SignBD-Word`) exist with permissive research licenses. The system will bridge BdSL gestures to English text and speech via an intermediate Bengali gloss representation.
- *Status:* **PROPOSED RECOMMENDATION — AWAITING FINAL APPROVAL.**

### DECISION 02: Braille Standardization Specification
- **Recommendation:** **Unified English Braille (UEB) Grade 1 (Uncontracted)** in strict compliance with the **ICEB Rules of Unified English Braille, Third Edition (2024)**.
- *Rationale:* Provides an unambiguous, 100% computable baseline for letters, numbers, capitals, and punctuation. Eliminates contraction ambiguity in Phase 2 while providing architectural hooks for Liblouis Grade 2 back-translation in Phase 3.
- *Status:* **PROPOSED RECOMMENDATION — AWAITING FINAL APPROVAL.**

### DECISION 03: Model Training Compute Environment
- **Recommendation:** **Google Colab GPU for Deep Model Training + Local 12-Core CPU for Inference via ONNX Runtime.**
- *Rationale:* Overcomes the absence of pre-built CUDA binary wheels for Python 3.14 on Windows. Accelerates neural network training by $> 50\times$ while enabling lightweight, cross-platform local CPU deployment.
- *Status:* **PROPOSED RECOMMENDATION — AWAITING FINAL APPROVAL.**

### DECISION 04: Project Legal & Commercialization Scope
- **Recommendation:** **Initial scope restricted to Academic Research and Assistive Non-Commercial MVP.**
- *Rationale:* Datasets like DSBI, WLASL, and MS-ASL carry explicit non-commercial research restrictions. Commercial rights and proprietary data collection must be reviewed separately before any commercial SaaS release.
- *Status:* **PROPOSED RECOMMENDATION — AWAITING FINAL APPROVAL.**
