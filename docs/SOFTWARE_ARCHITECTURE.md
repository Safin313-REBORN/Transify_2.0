# Transify — Software Architecture & System Integration Blueprint (Revised)

## 1. System Overview and Architectural Principles

Transify is engineered as a modular, accessible, service-oriented communication platform. The core engineering mandate is **Architectural Independence**: the Live Sign Language Recognition service (prioritizing BdSL) and the Braille Recognition service (prioritizing UEB Grade 1) operate as decoupled microservices sharing a unified FastAPI backend gateway and accessible frontend interfaces.

```
+----------------------------------------------------------------------------------------------------+
|                                    TRANSIFY SYSTEM ARCHITECTURE                                    |
|                                                                                                    |
|  +----------------------------------------------------------------------------------------------+  |
|  |                             PRESENTATION LAYER (Web / Desktop UI)                            |  |
|  |  [ Accessible React / Web Client ] <---> [ Web Audio API / Native Speech Synthesis (TTS) ]    |  |
|  |  - High Contrast / ARIA 1.2 Access       - Real-Time Webcam Video Canvas + Holistic Overlay   |  |
|  |  - Manual Confirmation & Retry Dialogs   - Braille Image Uploader & Interactive BBox Inspector|  |
|  +----------------------------------------------------------------------------------------------+  |
|                               |                                      |                             |
|                    WebSocket (30 FPS Stream)              REST API (Multipart Upload)              |
|                               v                                      v                             |
|  +----------------------------------------------------------------------------------------------+  |
|  |                           GATEWAY & API ORCHESTRATION LAYER (FastAPI)                        |  |
|  |  - Route: /ws/sign/live (Holistic Coords)       - Route: /api/braille/translate (Images)       |  |
|  |  - Auth & Rate Limiting                         - Input Validation & Image Sanitization       |  |
|  +----------------------------------------------------------------------------------------------+  |
|                |                                                     |                             |
|                v                                                     v                             |
|  +------------------------------------+             +------------------------------------+         |
|  |   MODULE 01: SIGN RECOGNITION      |             |   MODULE 02: BRAILLE RECOGNITION   |         |
|  |         SERVICE (BdSL-First)       |             |        SERVICE (Two-Stage UEB)     |         |
|  |  - MediaPipe Holistic Pipeline     |             |  - Image Quality & Blur Assessor   |         |
|  |  - Anatomical Normalizer (162D)    |             |  - CLAHE Preprocessing Engine      |         |
|  |  - BdSL Alphabet MLP Model (ONNX)  |             |  - Stage 1: Cell Localizer (ONNX)  |         |
|  |  - BdSL Word BiLSTM Model (ONNX)   |             |  - Stage 2: 6-Dot Classifier (ONNX)|         |
|  |  - Debounce & State Filter         |             |  - Line Clustering & Sorter        |         |
|  |  - Gloss-to-English Translator     |             |  - ICEB 2024 UEB State Machine     |         |
|  +------------------------------------+             +------------------------------------+         |
|                \                                                     /                             |
|                 \                                                   /                              |
|                  v                                                 v                               |
|  +----------------------------------------------------------------------------------------------+  |
|  |                           SHARED SERVICES & INFRASTRUCTURE LAYER                             |  |
|  |  [ Text-to-Speech (TTS) Engine ]      [ Model Registry & Storage ]   [ Telemetry & Logging ]    |  |
|  |  - Client Web Speech API (Primary)    - ONNX Runtime Engine          - Structured Loguru        |  |
|  |  - Server-Side edge-tts / pyttsx3     - Versioned Artifact Manifests - Latency & Error Profiling|  |
|  +----------------------------------------------------------------------------------------------+  |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Component Deconstruction

### 2.1 Independent Recognition Services

#### Service 01: BdSL Sign Language Recognition Engine (`sign_service`)
- **Process Isolation:** Runs as an independent worker process or asynchronous thread pool worker.
- **Internal Pipeline Modules:**
  1. `HolisticLandmarkExtractor`: Wraps MediaPipe Holistic C++/Python bindings to track dual hands (42 points) and upper-body pose (12 points).
  2. `AnatomicalNormalizer`: Performs vectorized chest-centering and inter-shoulder distance scaling, outputting a 162-dimensional normalized float tensor.
  3. `GestureClassifier`: Executes an ONNX Runtime session for the trained BdSL Alphabet MLP (Level A) or 1D-CNN-LSTM Lexical Sequencer (Level B).
  4. `TemporalDebounceFilter`: Enforces a sliding consensus window ($W = 6$ frames at $\ge 0.80$ confidence) to eliminate gesture jitter.
  5. `GlossToEnglishTranslator`: Translates recognized Bengali sign glosses into grammatically structured English sentences (applying SOV to SVO reordering).

#### Service 02: Braille Recognition Engine (`braille_service`)
- **Process Isolation:** Completely decoupled from `sign_service`.
- **Internal Pipeline Modules:**
  1. `ImageQualityAssessor`: Rejects blurred images (Laplacian variance $< 100$) with descriptive feedback.
  2. `ImagePreprocessor`: Applies CLAHE illumination normalization and deskewing.
  3. `Stage1_CellLocalizer`: Executes a 1-class YOLOv8-nano ONNX session detecting physical `braille_cell` bounding boxes $[x_1, y_1, x_2, y_2, \text{conf}]$.
  4. `SpatialLineSorter`: Clusters detected boxes into horizontal reading lines based on vertical overlap and sorts left-to-right.
  5. `Stage2_PatternClassifier`: Ingests cropped cell patches and classifies the 6-dot binary state $[d_1, \dots, d_6] \in \{0, 1\}^6$.
  6. `UEBGrade1Decoder`: Decodes binary cell patterns into English text according to the **ICEB Rules of Unified English Braille, Third Edition (2024)**.

---

## 3. Data Flow Blueprints

### 3.1 Live BdSL Data Flow

```
[User BdSL Gesture] 
        |
        v
[Webcam Capture (30 FPS)]
        |
        v
[MediaPipe Holistic (Dual Hands + Pose)] 
        | (Extracts 54 3D Keypoints: 162 Floats)
        v
[WebSocket Message: Float32 ArrayBuffer] ---> Network (< 5 ms)
        |
        v
[FastAPI WebSocket Handler]
        |
        v
[Anatomical Normalization (NumPy)] 
        | (Chest Centered, Shoulder-Distance Scaled)
        v
[ONNX Runtime Session: BdSL Classifier] ---> Logits (< 5 ms)
        |
        v
[Debounce Consensus Filter]
        |
    [Did prediction remain stable for >= 6 frames?]
       /                                      \
     YES                                       NO
     /                                          \
  Commit Sign to Gloss Stream             Continue Buffering
     |
  Semantic Translation: Bengali Gloss -> English Text
     |
     v
[Emit JSON Payload over WebSocket]
     |
     v
[Frontend UI Update (Audio TTS Available on Explicit User Click — Strict No Auto-Audio)]
```

### 3.2 Braille Image Translation Data Flow

```
[User Document Upload / Capture]
        |
        v
[REST POST /api/braille/translate]
        |
        v
[Blur & Resolution Assessment] ---> If blurry: Return HTTP 422 with tips
        |
        v
[CLAHE & Geometric Preprocessing]
        |
        v
[Stage 1: 1-Class YOLOv8-nano Cell Localizer] ---> Bounding Boxes
        |
        v
[Line Clustering & Horizontal Sorting Algorithm]
        |
        v
[Stage 2: 6-Dot Pattern Classifier on Cell Crops] ---> 6-Bit Binary Vectors
        |
        v
[ICEB 2024 UEB Grade 1 State Machine Decoder]
        |
        v
[Construct Structured JSON: Text, Confidence, Bounding Boxes]
        |
        v
[Frontend Display: Editable Text Editor + BBox Overlay + On-Demand TTS Button]
```

---

## 4. Human-in-the-Loop Assistive Controls

Assistive tools must avoid presenting speculative guesses as verified translations:
- **Tentative vs. Confirmed States:** Predictions between $60\%$ and $80\%$ confidence are rendered with a tentative visual indicator, requiring user confirmation or pause before audio readout.
- **One-Touch Correction:** Sighted or blind users can tap/select any word in the UI editor to inspect confidence, edit text, or re-read via TTS.
- **Strict No-Auto-Audio Rule:** Audio synthesis NEVER triggers automatically upon translation. Text is rendered first; audio playback requires an explicit user click on the speaker icon (`🔊`).
- **Privacy-by-Design:** All video frames and document images are processed ephemerally in-memory. No biometric video feeds or personal documents are retained on server disks.

---

## 5. Accessible Communication Hub & Phraseboard

```
[Sign Frame / Braille / Voice / Typed Text]
                  |
                  v
       [Communication Hub Engine]
                  |
        +---------+---------+
        |                   |
        v                   v
[Safe DOM Builder]  [FastAPI Backend]
(textContent/Node)  (Cookie Auth Check)
        |                   |
        v                   v
[Visual Feed Card]  [SQLite Persistence]
(Saved/Guest/Retry) (WAL / Immediate Tx)
```

- **Cross-Modal Synchronization:** Unifies Sign Language, Braille OCR, STT captions, and manual text into a single chronological stream.
- **DOM-Based XSS Immunity:** Built exclusively with safe native DOM methods (`textContent`, `replaceChildren`), preventing script injection from malicious payloads.
- **Storage Status Reflection:** Visual chips differentiate cloud-persisted messages (`✓ Saved`), ephemeral guest interactions (`Temporary Guest`), and network retry states (`⚠️ Unsaved`).

---

## 6. Hardened Security Architecture

- **Password Cryptography:** Argon2id (`time_cost=2`, `memory_cost=65536`) with automatic transparent upgrade from PBKDF2 (600,000 iterations).
- **Session Lifecycle:** Cryptographically random 32-byte tokens hashed with SHA-256 in SQLite; stored strictly in secure, HttpOnly, SameSite=Lax cookies.
- **CSRF Exact-Origin Enforcement:** Validates normalized origin and referer headers against explicit production whitelists; blocks cross-origin state mutation.
- **Persistent Rate Limiting:** High-concurrency atomic rate limiting on authentication and reset endpoints backed by SQLite WAL mode.
- **Disaster Recovery:** Online non-blocking database backup (`scripts/backup_db.py`) and rollback (`scripts/restore_db.py`) utilities with automated integrity verification.

---

## 7. Android Client Architecture

```
[Android Native App (Kotlin 1.9.24 / AndroidX)]
        |
  [Hardware-Accelerated WebView Engine]
        |
  [WebChromeClient / WebViewClient Bridge]
        | (Grants WebRTC camera & microphone permissions)
        v
  [Transify Responsive Web Application]
```
- Hardware-accelerated WebView rendering with zero iframe latency.
- Seamless bridge granting camera (`CAMERA`) and microphone (`RECORD_AUDIO`) permissions natively without popup interruptions.
- Verified debug APK build pipeline (`./gradlew assembleDebug`).
