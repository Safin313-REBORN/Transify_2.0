# Transify 2.0 — AI-Powered Accessible Multi-Modal Communication & Clinical Triage Platform

> **Tagline:** *Breaking Communication Barriers through Artificial Intelligence.*  
> **Status:** Production Ready · 6 Modules Deployed · 62+ Automated Tests Passing  
> **Live Deployment:** [https://transify20-production.up.railway.app](https://transify20-production.up.railway.app)

---

## 🌟 Executive Overview

**Transify 2.0** is an all-in-one, multi-modal assistive communication and clinical decision-support platform engineered to empower individuals who are Deaf, hard-of-hearing, blind, visually impaired, non-verbal, or managing chronic conditions.

Transify 2.0 integrates **six dedicated AI and clinical modules** with zero cloud lock-in and a strict **Zero Auto-Audio privacy invariant**:
1. **Live Hand Sign & Gesture Translator (ASL & BdSL):** Real-time computer vision engine recognizing 24+ communicative words, full manual A-Z fingerspelling, and Bengali Sign Language (BdSL) with Camera Target Box containment, 3-frame rolling consensus, and an ultra-fast 98% Decision Gateway.
2. **Optical Braille Recognition & Generator (UEB Grade 1):** Optical Braille Recognition (OBR) pipeline powered by a 99.4% accuracy ExtraTrees classifier, CLAHE normalizer, strict ICEB 2024 compliance, an interactive 6-dot tactile matrix explorer, and bidirectional text-to-Braille synthesis.
3. **Real-Time Speech-to-Text (STT):** Live continuous voice captioning with real-time interim display and one-click copy or speech playback.
4. **Natural Text-to-Speech (TTS):** Multi-lingual speech synthesis via Web Speech API with automatic audio fallback and user-gesture activation.
5. **Transify Care & Clinical Decision Support:** Safety-first triage engine adhering to WHO Interagency Integrated Triage protocols, Merck Manuals clinical guidelines, emergency red-flag escalations, Zipline medical drone delivery integration, ChronicCare insulin dosage safety calculators (with non-negative correction bounds), and OpenFDA polypharmacy interaction alerts.
6. **Multimodal AI Chatbot Agent & MCP Server:** Offline-first trained assistive knowledge agent with semantic intent classification, domain fine-tuning, and full compliance with the **Model Context Protocol (MCP)** specification (JSON-RPC 2.0).

---

## 🎯 Main Features & Capabilities

### 1. ✋ Hand Sign Recognition Engine (ASL & BdSL)
- **24+ Communicative Classes:** `CALL`, `DISLIKE`, `FIST`, `FOUR`, `HELLO`, `HELP`, `I_LOVE_YOU`, `LIKE`, `MUTE`, `NO`, `OK`, `ONE`, `PALM`, `PEACE`, `PEACE_INVERTED`, `ROCK`, `STOP`, `STOP_INVERTED`, `THANK_YOU`, `THREE`, `THREE2`, `TWO_UP`, `TWO_UP_INVERTED`, `YES`.
- **BdSL & ASL Bilingual Toggle:** Native support for both American Sign Language and Bangladesh Sign Language gloss translation.
- **Manual Alphabet Fingerspelling (A-Z):** Full 26-letter fingerspelling recognizer with live word assembler and auto-space detection.
- **Strict Target Box (ROI) Containment:** Inference only executes when hands are inside the guide box.
- **98% Decision Gateway:**
  - Confidence $\ge 0.98$: Local trained model answers directly ($< 15\text{ ms}$).
  - Confidence $< 0.98$: Automatically engages the **MCP Server Disambiguation Agent** to resolve candidate clashes.

### 2. ⠃⠗ Optical Braille Translation (OBR - UEB Grade 1)
- **High-Accuracy Vision Pipeline:** 99.4% dot pattern recognition on embossed paper documents.
- **Interactive 6-Dot Tactile Matrix:** Real-time dot toggle explorer mapping tactile pins to Unicode Braille, ASCII, and Bengali Bharati equivalents.
- **Bidirectional Text-to-Braille Generator:** Generates formatted UEB Grade 1 Braille cells and BRF downloadable files from English or Bengali text.
- **Direct Output Actions:** Spoken text (TTS), 1-click clipboard copy, and formatted `.txt` / `.brf` download.

### 3. 🎙️ Speech-to-Text (STT) & 🔊 Text-to-Speech (TTS)
- **Live Captions Hub:** Real-time speech recognition supporting English (US/UK) and Bengali (`bn-BD`).
- **Zero Auto-Audio Guarantee:** Strict compliance ensuring audio never plays automatically without explicit, deliberate user interaction.

### 4. 🏥 Transify Care & Clinical Decision Support
- **WHO & DGHS Emergency Triage:** Multi-tier clinical triage prioritizing RED emergency red flags > YELLOW urgent symptoms > ROUTINE GREEN.
- **Bangladesh Emergency Escalation:** Direct one-touch links for National Emergency (`999`) and Health Helpline (`16263`).
- **Zipline Medical Drone Delivery:** Coordinates emergency cold-chain aerial logistics for antivenom, O-negative blood, and vaccines.
- **ChronicCare Insulin Dosage Safeguards:** Net carb and ISF calculation with mandatory ability-to-swallow assessments, mild/severe hypoglycemia lockouts, and non-negative correction bounds.
- **OpenFDA Polypharmacy Alerts:** Automated drug-drug interaction warning checks.

### 5. 🤖 Multimodal AI Chatbot & MCP Server
- **Standard Model Context Protocol (MCP):** JSON-RPC 2.0 endpoints at `/api/mcp` and `/mcp` supporting `initialize`, `tools/list`, `tools/call`, and `ping`.
- **Exposed MCP Tools:**
  - `resolve_sign_ambiguity`: Kinematic sign disambiguation.
  - `resolve_braille_ambiguity`: Optical Braille state resolution.
  - `triage_symptom`: WHO-guided clinical symptom evaluation.
  - `calculate_insulin_correction`: Clinically safe bolus calculation.
  - `check_polypharmacy`: OpenFDA medication contraindication check.
  - `chat_assistive_agent`: Multimodal offline knowledge retrieval.

---

## 🛠️ Technology Stack

- **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/) (ASGI) & [Uvicorn](https://www.uvicorn.org/) for async real-time endpoints.
- **Data Validation & Settings:** [Pydantic v2](https://docs.pydantic.dev/) for robust payload serialization.
- **Machine Learning & Vision:**
  - [Google MediaPipe](https://developers.google.com/mediapipe) (`HandLandmarker`) for 3D landmark localization.
  - [Scikit-learn](https://scikit-learn.org/) (ExtraTrees and Random Forest classifiers).
  - [OpenCV](https://opencv.org/) (`opencv-python-headless`) for image preprocessing and CLAHE.
  - [NumPy](https://numpy.org/) & [Pandas](https://pandas.pydata.org/) for vector mathematics.
- **Security & Authentication:**
  - [Argon2id](https://pypi.org/project/argon2-cffi/) password hashing with cryptographically secure salts.
  - HttpOnly, SameSite=Lax session management.
  - CSRF header protection (`X-Transify-CSRF`) and rate limiting.
  - GDPR Article 17 permanent account deletion endpoint.
- **Frontend & Accessibility:**
  - Semantic HTML5 & responsive modular CSS3 with WCAG 2.1 AAA high-contrast theme support.
  - Zero heavy frontend frameworks: Pure Vanilla JavaScript (ES6+).
  - Web Speech API for native browser speech synthesis and recognition.
- **Local Persistence:** SQLite (`data/transify.db`) with SHA-256 integrity validation.
- **Testing:** [pytest](https://docs.pytest.org/) suite covering clinical safety, audio privacy regressions, and MCP protocols.

---

## 🏛️ System Architecture

```
+------------------------------------------------------------------------------------+
|                               TRANSIFY 2.0 PLATFORM                                |
|                                                                                    |
|  +----------------+  +----------------+  +---------------+  +--------------------+ |
|  | 1. HAND SIGN AI|  | 2. BRAILLE OBR |  | 3. SPEECH-TEXT|  | 5. TRANSIFY CARE   | |
|  | MediaPipe 3D   |  | CLAHE Preproc  |  | Web Speech STT|  | WHO/Merck Triage   | |
|  | 24 ASL/BdSL    |  | 6-Dot Explorer |  | Live Captions |  | Zipline Drone Med | |
|  | Target Box Gate|  | UEB Grade 1 Gen|  | TTS Audio Out |  | ChronicCare Safe| |
|  +--------+-------+  +--------+-------+  +-------+-------+  +---------+----------+ |
|           |                   |                  |                    |            |
|           v                   v                  v                    v            |
|  +-------------------------------------------------------------------------------+ |
|  |               MODEL CONTEXT PROTOCOL (MCP) & 98% DECISION GATEWAY             | |
|  |   - Local Model Direct Answer (Confidence >= 98%)                             | |
|  |   - MCP Server Agent Disambiguation (Confidence < 98% / Ambiguity)            | |
|  |   - JSON-RPC 2.0 Endpoints: /api/mcp, /mcp, /api/mcp/tools                    | |
|  +---------------------------------------+---------------------------------------+ |
|                                          |                                         |
|                                          v                                         |
|  +-------------------------------------------------------------------------------+ |
|  |                  FastAPI ASGI Backend & Argon2 Secure Auth                    | |
|  |                SQLite Local Storage (Verified SHA-256 Invariant)              | |
|  |               Responsive WCAG 2.1 AAA High-Contrast Web Interface            | |
|  +-------------------------------------------------------------------------------+ |
+------------------------------------------------------------------------------------+
```

---

## 🚀 Quickstart & Installation

### Prerequisites
- Python 3.10+ (Tested on Python 3.11, 3.12)
- Modern web browser (Chrome, Edge, Firefox, Safari)
- Webcam and microphone (for Sign Language and STT modules)

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/Safin313-REBORN/Transify_2.0.git
cd Transify_2.0

# Create and activate virtual environment
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

#### Available Environment Variables:
- `SIGN_CONFIDENCE_THRESHOLD`: Confidence cutoff (default `0.98`). Predictions below route to MCP resolver.
- `BRAILLE_CONFIDENCE_THRESHOLD`: Cutoff for optical Braille recognition.
- `OPENAI_API_KEY`: *(Optional)* API key for cloud LLM vision models.
- `GEMINI_API_KEY`: *(Optional)* API key for Google Gemini model disambiguation.
- `MCP_SERVER_URL`: *(Optional)* Custom endpoint URL for external MCP server resolvers.

### 3. Run the Application Locally

```bash
python run_server.py --host 0.0.0.0 --port 8000
```

Navigate to:
- **Main Application:** [http://localhost:8000/](http://localhost:8000/)
- **Live Sign Translator:** [http://localhost:8000/#sign](http://localhost:8000/#sign)
- **Braille Document Translator:** [http://localhost:8000/#braille](http://localhost:8000/#braille)
- **Transify Care Portal:** [http://localhost:8000/#care](http://localhost:8000/#care)
- **Speech to Text:** [http://localhost:8000/#stt](http://localhost:8000/#stt)
- **Text to Speech:** [http://localhost:8000/#tts](http://localhost:8000/#tts)
- **Interactive API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **MCP Server Endpoints:** [http://localhost:8000/api/mcp](http://localhost:8000/api/mcp)

---

## 💻 Automated Testing & Verification

Run the comprehensive pytest test suite (62+ tests):

```bash
pytest tests/ -v
```

Test Coverage Includes:
- `test_zero_auto_audio_regression.py`: Enforces zero automated audio playback without explicit user consent.
- `test_care_browser.py`: Verifies browser triage, XSS sanitization, and offline safety.
- `test_chatbot.py`: Verifies emergency red-flag handling, fine-tuning, and domain retrieval.
- `test_clinical_safety_matrix.py`: Verifies clinical bounds, IDOR prevention, and CSRF protection.
- `test_mcp_protocol.py`: Verifies Model Context Protocol (MCP) JSON-RPC 2.0 handshake and tools.

---

## 📂 Repository Structure

```
Transify_2.0/
├── data/                       # Datasets, annotations, SQLite database (SHA-256 verified)
│   ├── braille/                # Braille character samples and splits
│   ├── sign/                   # Sign landmark data and splits
│   └── transify.db             # Local SQLite database
├── docs/                       # Technical documentation, PRDs, and architecture specs
├── models/                     # Trained model artifacts and manifests
│   ├── braille/                # Braille cell localizer & 6-dot classifier
│   └── sign/                   # HaGRID & ASL 24-class models
├── src/                        # Core source code
│   ├── api/                    # FastAPI endpoints, MCP routers, TTS engines
│   ├── braille/                # OBR vision pipeline and UEB decoder
│   ├── care/                   # WHO/Merck clinical triage, ChronicCare, RAG
│   ├── chatbot/                # Multi-domain trained AI chatbot agent
│   ├── database/               # SQLite schemas, Argon2 auth, and backups
│   ├── frontend/               # Accessible single-page web app (HTML/CSS/JS)
│   └── sign/                   # MediaPipe tracker, fingerspelling, MCP resolver
├── tests/                      # Automated test suites
├── Dockerfile                  # Application container definition
├── requirements.txt            # Python dependencies
├── run_server.py               # Standalone production server launcher
└── README.md                   # Platform documentation
```

---

## ♿ Accessibility Compliance (WCAG 2.1 AAA)

- **Theme Palette:** High-contrast purple aesthetic (`#8338ec`) and sunshine gold (`#ffcb05`) with full dark/light mode toggle.
- **Screen Reader Announcements:** Dedicated `aria-live="polite"` regions for real-time auditory notifications.
- **Zero Heavy Frameworks:** Pure vanilla JavaScript and modular CSS for lightweight, zero-latency execution.
- **Privacy-First:** Translations, medical inquiries, and sessions remain strictly protected.

---

## 📄 License & Acknowledgments

- **License:** MIT License. Free for educational, research, and assistive deployment.
- **HaGRID Dataset:** Kapitanov et al. (HAnd Gesture Recognition Image Dataset).
- **ICEB Standards:** Unified English Braille (UEB) Rules, 3rd Edition (2024).
- **MediaPipe:** Google MediaPipe HandLandmarker.
- **Clinical Sources:** WHO Interagency Integrated Triage & Merck Manuals Consumer Edition.
