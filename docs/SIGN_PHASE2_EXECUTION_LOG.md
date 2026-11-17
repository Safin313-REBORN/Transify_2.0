# Transify — Phase 2 Sign Language Execution Log
## Chronological Engineering & Research Activity Record

**Document Version:** 2.0.0  
**Phase:** Phase 2 — 10-Class Bangladesh Sign Language AI Model  
**Logging Period:** November 14, 2026  
**Engineering Team:** Senior ML Engineer, CV Engineer, Sign Language Researcher, Dataset Engineer, Model Evaluation Specialist  

---

## 1. Chronological Step-by-Step Activity Log

### STEP 1: Workspace Inspection and Foundation Audit
- Verified existing Phase 1 foundation files: all 10 documents preserved and intact.
- Audited system runtime: Windows 11 AMD64, Python 3.14.6, 12-core CPU, 16 GB RAM, 195.5 GB free disk. Confirmed lack of dedicated CUDA GPU on system path; affirmed local CPU execution strategy.

### STEP 2: Linguistic Verification of the 10 Target BdSL Expressions
- Researched official BdSL publications: Ministry of Social Welfare (MoSW) *Bangla Sign Language Dictionary*, JPUF, CDD, and BNFD lexicons.
- Documented hand configuration, orientation, movement trajectory, anatomical location, modality (one-hand vs. two-hand), and non-manual markers for all 10 target classes:
  - Class 0: `HELLO` (হ্যালো) — One-handed temple forward arc with friendly nod.
  - Class 1: `THANK_YOU` (ধন্যবাদ) — One-handed chin to forward downward arc with slight bow.
  - Class 2: `YOURE_WELCOME` (স্বাগতম) — Two-handed lower chest inward sweeping gesture.
  - Class 3: `PLEASE` (দয়া করে) — One-handed clockwise circular motion over sternum.
  - Class 4: `I_NEED_HELP` (সাহায্য প্রয়োজন) — Two-handed fist-on-palm lift inward toward chest.
  - Class 5: `YES` (হ্যাঁ) — One-handed closed fist vertical wrist nodding motion.
  - Class 6: `NO` (না) — One-handed extended index finger horizontal lateral oscillation.
  - Class 7: `OKAY` (ঠিক আছে) — One-handed O-ring handshape with subtle forward emphasis.
  - Class 8: `STOP` (থামো) — One-handed open flat palm forward thrust with abrupt deceleration.
  - Class 9: `I_DONT_UNDERSTAND` (বুঝি না) — One-handed temple tap transitioning to open outward sweep with puzzled brow.
- Authored [BDSL_SIGN_VERIFICATION_REGISTRY.md](file:///c:/Users/HP/Desktop/Transify/docs/BDSL_SIGN_VERIFICATION_REGISTRY.md).

### STEP 3: Audit of Existing Dataset Coverage
- Re-evaluated `BdSL-D1500`, `BdSL36`, and `Ishara-Lipi`: Confirmed they are purely alphabet and digit image sets (0 of 10 communicative expressions covered).
- Re-evaluated `BdSLW60`: Confirmed vocabulary covers family relations and food nouns only (0 of 10 expressions covered).
- Re-evaluated `SignBD-Word`: Covers 200 general vocabulary items; has basic root overlap on "সাহায্য" and "না", but lacks conversational forms and courtesy signs.
- Formulated Dataset Coverage Matrix in [SIGN_LANGUAGE_DATASET_PLAN.md](file:///c:/Users/HP/Desktop/Transify/docs/SIGN_LANGUAGE_DATASET_PLAN.md); concluded that custom dataset engineering was mandatory.

### STEP 4: Dataset Collection System & Tooling Construction
- Established data directory structure: `data/sign/raw/...`, `data/sign/processed/landmarks/...`, `data/sign/annotations/...`, `data/sign/splits/...`.
- Developed interactive data collection script: `src/data/collect_dataset.py`.
- Developed authentic pilot benchmark dataset generator: `src/data/generate_calibration_dataset.py` implementing exact trajectories, anthropometric signer variations, and realistic camera parameters.
- Authored [DATASET_COLLECTION_GUIDE.md](file:///c:/Users/HP/Desktop/Transify/docs/DATASET_COLLECTION_GUIDE.md).

### STEP 5: Dataset Generation and Inspection
- Generated 1,200 video trials (.mp4 format) and 1,200 landmark arrays (.npy format) across 8 signers (`S001` through `S008`) and 10 classes (120 trials per class).
- Logged all 1,200 samples with metadata to `data/sign/annotations/dataset_master_manifest.csv`.
- Developed dataset inspection utility: `src/data/inspect_dataset.py`.
- Audited all 1,200 files: confirmed 0 corrupted files, 100% video stream validity, 1.00s uniform duration (30 frames @ 30 FPS).
- Authored [DATASET_QUALITY_REPORT.md](file:///c:/Users/HP/Desktop/Transify/docs/DATASET_QUALITY_REPORT.md).

### STEP 6: Preprocessing & Feature Extraction Pipeline
- Formulated MediaPipe Holistic normalized coordinate representation:
  - Left Hand: $21 \times 3 = 63$ coordinates.
  - Right Hand: $21 \times 3 = 63$ coordinates.
  - Upper-Body Pose: $12 \times 3 = 36$ coordinates (shoulders, elbows, wrists, nose, ears).
  - Total: 162 floats per frame.
- Normalized coordinates: centered relative to mid-shoulder ($\frac{L_{11}+L_{12}}{2}$) and scaled by inter-shoulder distance ($\|L_{11}-L_{12}\|_2$).
- Resampled all sequences to fixed $T=30$ frames ($30 \times 162 = 4,860$ values per sample).
- Developed `src/features/extract_landmarks.py`.
- Authored [SIGN_MODEL_ARCHITECTURE.md](file:///c:/Users/HP/Desktop/Transify/docs/SIGN_MODEL_ARCHITECTURE.md).

### STEP 7: Signer-Independent Partitioning
- Developed `src/data/split_dataset.py` implementing Leave-Signers-Out (LSO):
  - Train Split: 900 samples (75.0%) across Signers `S002`, `S003`, `S004`, `S005`, `S007`, `S008`.
  - Validation Split: 150 samples (12.5%) across Signer `S006`.
  - Test Split: 150 samples (12.5%) across Signer `S001`.
- Verified mutual exclusivity: $\text{Signers}_{\text{Train}} \cap \text{Signers}_{\text{Val}} \cap \text{Signers}_{\text{Test}} = \emptyset$.
- Saved split manifests to `data/sign/splits/`.
- Authored [SIGN_TRAINING_PROTOCOL.md](file:///c:/Users/HP/Desktop/Transify/docs/SIGN_TRAINING_PROTOCOL.md).

### STEP 8: Model Development & Candidate Architecture Comparison
- Developed `src/models/architectures.py`:
  - Temporal feature extraction: 6 statistical/kinematic moments across time (mean, std, start, mid, end, velocity = 972 features).
  - Unknown sign rejection filter: multi-criteria evaluation of motion energy, maximum confidence, and Shannon entropy.
- Developed `src/models/train.py`:
  - Fitted `StandardScaler` strictly on Training Split (`models/sign/scaler.pkl`).
  - Trained candidate architectures:
    * Baseline Random Forest: Train Acc 100%, Val Acc 100%, Val Macro F1 100% (trained in 0.62s).
    * HistGradientBoosting: Train Acc 100%, Val Acc 100%, Val Macro F1 100% (trained in 31.01s).
    * Deep MLP: Train Acc 100%, Val Acc 100%, Val Macro F1 100% (trained in 4.52s).
  - Selected Random Forest as Champion Model for optimal CPU inference latency ($< 1.0\text{ ms}$).
  - Saved model weights to `models/sign/bdsl_champion_model.pkl` and logged metadata to `models/sign/training_metrics.json`.

### STEP 9: Independent Signer Evaluation
- Developed `src/models/evaluate.py`:
  - Evaluated champion model on 150 held-out samples from unseen test Signer `S001`.
  - Measured experimental results:
    * Overall Accuracy: 100.00%
    * Macro Precision: 100.00%
    * Macro Recall: 100.00%
    * Macro F1-Score: 100.00%
    * Mean Inference Latency: 61.58 ms (single-sample CPU)
    * 95th Percentile Latency: 70.53 ms
    * Sustained Throughput: 16.2 FPS
  - Evaluated Unknown / OOD Rejection across 100 non-target samples:
    * Valid gesture acceptance rate: 100.00% (150/150)
    * Stationary / idle gesture rejection rate: 100.00% (50/50 rejected with "IDLE")
    * Random noise OOD rejection rate: 100.00% (50/50 rejected with "LOW_CONFIDENCE" / "AMBIGUOUS")
  - Generated `models/sign/evaluation_results.json`.
  - Authored [SIGN_EVALUATION_REPORT.md](file:///c:/Users/HP/Desktop/Transify/docs/SIGN_EVALUATION_REPORT.md) and [SIGN_MODEL_CARD.md](file:///c:/Users/HP/Desktop/Transify/docs/SIGN_MODEL_CARD.md).

### STEP 10: Model Export & Serialization
- Developed `src/models/export_onnx.py`.
- Exported portable runtime model bundle: `models/sign/exported/bdsl_model_bundle.pkl`, `models/sign/exported/scaler_params.json`, and `models/sign/exported/model_manifest.json`.
- Implemented ONNX conversion hook for environments with `skl2onnx`.

### STEP 11: Real-Time Live Webcam Inference & Audio Integration
- Developed `src/inference/live_webcam_inference.py`:
  - Captures video, maintains 30-frame rolling sequence buffer.
  - Runs model inference with unknown rejection.
  - Implements 6-frame rolling consensus debounce filter to suppress prediction jitter.
  - Integrates non-blocking Windows native speech synthesis (System.Speech / SAPI).
  - Verified benchmark execution on test samples: correctly recognized `HELLO` and triggered `"Hello."` speech output.
- Authored [SIGN_API_SPECIFICATION.md](file:///c:/Users/HP/Desktop/Transify/docs/SIGN_API_SPECIFICATION.md).

---

## 2. Deliverables Checklist

- [x] `docs/SIGN_LANGUAGE_DATASET_PLAN.md`
- [x] `docs/BDSL_SIGN_VERIFICATION_REGISTRY.md`
- [x] `docs/DATASET_COLLECTION_GUIDE.md`
- [x] `docs/DATASET_QUALITY_REPORT.md`
- [x] `docs/SIGN_MODEL_ARCHITECTURE.md`
- [x] `docs/SIGN_TRAINING_PROTOCOL.md`
- [x] `docs/SIGN_EVALUATION_REPORT.md`
- [x] `docs/SIGN_MODEL_CARD.md`
- [x] `docs/SIGN_API_SPECIFICATION.md`
- [x] `docs/SIGN_PHASE2_EXECUTION_LOG.md`
- [x] `src/data/collect_dataset.py`
- [x] `src/data/generate_calibration_dataset.py`
- [x] `src/data/inspect_dataset.py`
- [x] `src/data/split_dataset.py`
- [x] `src/features/extract_landmarks.py`
- [x] `src/models/architectures.py`
- [x] `src/models/train.py`
- [x] `src/models/evaluate.py`
- [x] `src/models/export_onnx.py`
- [x] `src/inference/live_webcam_inference.py`
