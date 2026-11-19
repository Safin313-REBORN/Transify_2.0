# Transify 2.0 — AI-Powered Accessible Multi-Modal Communication Platform

> **Tagline:** *Breaking Communication Barriers through Artificial Intelligence.*  
> **Status:** Production Ready · 4 Modules Deployed · 187/187 Automated Tests Passing · CI Verified

---

## 🌟 Executive Overview

**Transify 2.0** is an all-in-one, multi-modal assistive communication platform engineered to empower individuals who are Deaf, hard-of-hearing, blind, visually impaired, or non-verbal.

Transify 2.0 integrates **four dedicated AI modules**, an accessible **Communication Hub**, a rapid **Phraseboard**, and a hardened production authentication and security infrastructure with zero external cloud lock-in:
1. **Live Hand Sign & Gesture Translator (ASL, HaGRID & BdSL):** Real-time computer vision engine recognizing 24+ communicative sign language words and gestures with strict Camera Target Box containment, 30-frame temporal sequence analysis, and an ultra-fast 98% Decision Gateway.
2. **Optical Braille Translator (UEB Grade 1):** Optical Braille Recognition (OBR) pipeline powered by an ExtraTrees classifier (100% exact-cell test accuracy on heldout data), CLAHE contrast normalizer, and strict compliance with the **ICEB Rules of Unified English Braille (2024)**.
3. **Real-Time Speech-to-Text (STT):** Live continuous microphone voice captioning with real-time interim display and one-click copy or speech playback.
4. **Natural Text-to-Speech (TTS):** Instant multi-lingual speech synthesis via Web Speech API with automatic audio fallback and strictly user-initiated audio playback (zero auto-audio).
5. **Accessible Communication Hub & Phraseboard:** Conversational cross-modal feed linking Sign Language, Optical Braille, STT voice captions, and typed messages with visual status badges (Saved, Guest, Unsaved) and complete DOM XSS immunity.
6. **Hardened Production Security:** Argon2id password hashing, HttpOnly session cookies, atomic SQLite rate limiting, exact-origin CSRF validation, mandatory Terms of Service consent, configurable SMTP password reset adapter, and versioned database migrations (1–7).

---

## 🎯 Main Features & Capabilities

### 1. ✋ Hand Sign Recognition Engine (ASL, HaGRID & BdSL)
- **24+ Communicative Classes:** `CALL`, `DISLIKE`, `FIST`, `FOUR`, `HELLO`, `HELP`, `I_LOVE_YOU`, `LIKE`, `MUTE`, `NO`, `OK`, `ONE`, `PALM`, `PEACE`, `PEACE_INVERTED`, `ROCK`, `STOP`, `STOP_INVERTED`, `THANK_YOU`, `THREE`, `THREE2`, `TWO_UP`, `TWO_UP_INVERTED`, `YES`.
- **Strict Target Box (ROI) Containment:** Inference and predictions only execute when the user's hand is inside the designated guide box on camera. Outside hands trigger an amber safety warning and reset history.
- **30-Frame Temporal Analysis Before Decision:** Gestures are stabilized across consensus frames before confirming the translation and displaying text.
- **98% Decision Gateway:**
  - Confidence $\ge 0.98$: Local trained ExtraTrees / Random Forest model answers directly ($< 15\text{ ms}$).
  - Ambiguity or Confidence $< 0.98$: Automatically engages the **MCP Server Disambiguation Agent** to resolve candidate clashes.

### 2. ⠃⠗ Optical Braille Translation (OBR - UEB Grade 1)
- **High-Accuracy Vision Pipeline:** 99.4% dot pattern recognition on embossed paper documents.
- **Illumination-Invariant Preprocessing:** Adaptive CLAHE enhancement handles variable room lighting and shadows.
- **Direct Output Actions:** Spoken text (TTS via explicit speaker click), 1-click clipboard copy, and formatted `.txt` download.

### 3. 🎙️ Speech-to-Text (STT) & 🔊 Text-to-Speech (TTS)
- **Live Captions:** Real-time speech recognition supporting English (US/UK) and Bengali.
- **Strict No-Auto-Audio Rule:** Translations and transcripts never start audio playback automatically. Text appears first; playback occurs strictly and only when the user explicitly clicks the speaker button (🔊).

### 4. 💬 Accessible Communication Hub & Quick Phraseboard
- **Multimodal Conversation Feed:** Seamlessly imports translations from Sign Language, Optical Braille, and Voice Captions into a unified chronological chat stream.
- **Visual Storage Distinction:** Distinct status chips clearly differentiate cloud-saved messages (`✓ Saved`), temporary guest sessions (`Temporary Guest`), and offline connection errors (`⚠️ Unsaved`).
- **DOM-Based XSS Immunity:** Built strictly with `document.createElement`, `textContent`, and native event listeners—neutralizing script tag injection, `<img>`/`<svg>` handlers, and attribute breakout attacks.
- **Quick Phraseboard:** Grid of essential everyday expressions in English and Bengali with personal phrasebook addition, deletion, and favorite filtering.

### 5. 🛡️ Production Security & Authentication Architecture
- **Argon2id Password Hashing:** Robust password protection with transparent on-login upgrade from legacy PBKDF2.
- **Strict Cookie-Only Authentication:** Session tokens are delivered exclusively through secure, HttpOnly, SameSite=Lax cookies; raw tokens are never exposed in localStorage or response JSON.
- **Explicit Terms & Privacy Consent:** Registration strictly requires explicit consent (`consent_terms: true`), rejecting missing or false fields with HTTP 422 and recording verifiable consent timestamps.
- **Timing-Decoupled Password Reset Anti-Enumeration & Deep-Links:** Asynchronous background task execution, single-use SHA-256 hashed reset tokens with bounded 30-minute expiry, identical non-enumerating generic responses across all scenarios, automatic token invalidation on dispatch failures, canonical HTTPS URL fragment deep-linking (`#reset_token=`), legacy query-token deprecation, and configurable SMTP delivery with HTML/plain-text multipart MIME support.
- **Exact-Origin CSRF Protection:** Whitelists legitimate production origins and blocks unverified cross-origin requests on state-changing endpoints.
- **Atomic SQLite Rate Limiting:** High-concurrency transaction-safe rate limiter backed by SQLite WAL mode and `BEGIN IMMEDIATE` transactions.
- **Versioned Migrations (1–7):** Guaranteed schema evolution preserving existing users, preferences, and translation histories with full idempotency.
- **IDOR Protection:** All Hub conversations, messages, personal phrases, and history favorites enforce strict user ownership checks (`404 Not Found` for unauthorized IDs).

---

## 🛠️ Technology Stack

Transify 2.0 is built with a lightweight, high-performance architecture:

- **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/) (ASGI) & [Uvicorn](https://www.uvicorn.org/) for async real-time endpoints.
- **Data Validation & Settings:** [Pydantic v2](https://docs.pydantic.dev/) for request parsing and field validation.
- **Machine Learning & Computer Vision:**
  - [Google MediaPipe](https://developers.google.com/mediapipe) (`HandLandmarker` task) for 3D landmark localization.
  - [Scikit-learn](https://scikit-learn.org/) (ExtraTrees and Random Forest classifiers).
  - [OpenCV](https://opencv.org/) (`opencv-python-headless`) for image preprocessing, CLAHE, and bounding box localization.
  - [NumPy](https://numpy.org/) & [Pandas](https://pandas.pydata.org/) for vector operations and dataset processing.
- **Frontend & Accessibility:**
  - Semantic HTML5 & responsive modular CSS3 with high-contrast accessibility themes (WCAG 2.1 AAA).
  - Pure Vanilla JavaScript (ES6+) for zero-dependency client execution.
  - Web Speech API for native browser Speech-to-Text (`SpeechRecognition`) and Text-to-Speech (`SpeechSynthesis`).
  - HTML5 Canvas API and `MediaDevices.getUserMedia()` for low-latency webcam processing.
- **Local Storage & Database:** SQLite (`data/transify.db`) with WAL mode and versioned schema migrations (1–7).
- **Android Client:** Native Kotlin / AndroidX WebView wrapper with hardware-accelerated rendering and camera permissions bridge.
- **Containerization & Deployment:** Docker, Docker Compose, and [Railway](https://railway.app/).

---

## ⚙️ Installation & Setup

### 1. Clone & Set Up the Python Virtual Environment

```bash
git clone https://github.com/Safin313-REBORN/Transify_2.0.git
cd Transify_2.0
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file from the provided `.env.example`:

```bash
cp .env.example .env
```

Key environment configuration variables:
- `ENVIRONMENT`: Set to `production` or `development`.
- `RAILWAY_ENVIRONMENT`: Set to `production` when running on Railway.
- `ALLOWED_ORIGINS`: Comma-separated list of allowed origins (e.g. `https://transify20-production.up.railway.app`).
- `CONFIDENCE_THRESHOLD`: Threshold for direct model inference (default `0.98`).
- `SMTP_HOST`: *(Optional)* Hostname of SMTP relay for password reset emails.
- `SMTP_PORT`: *(Optional)* SMTP port (default `587`).
- `SMTP_USER`: *(Optional)* SMTP authentication username / sender email.
- `SMTP_PASSWORD`: *(Optional)* SMTP authentication password or app token.
- `SMTP_FROM`: *(Optional)* Sender address (e.g. `no-reply@transify.ai`).
- `SMTP_USE_TLS`: *(Optional)* Enable STARTTLS (default `true`).
- `SMTP_USE_SSL`: *(Optional)* Direct SSL connection (default `false`).

### 3. Run the Application Locally

Start the ASGI server:

```bash
python run_server.py --host 0.0.0.0 --port 8000
```

Alternatively, run with Docker:

```bash
docker-compose up --build
```

Open your browser and navigate to:
- **Main Application:** [http://localhost:8000/](http://localhost:8000/)
- **Live Sign Translator:** [http://localhost:8000/#sign](http://localhost:8000/#sign)
- **Braille Document Translator:** [http://localhost:8000/#braille](http://localhost:8000/#braille)
- **Speech to Text:** [http://localhost:8000/#stt](http://localhost:8000/#stt)
- **Text to Speech:** [http://localhost:8000/#tts](http://localhost:8000/#tts)
- **Communication Hub:** [http://localhost:8000/#hub](http://localhost:8000/#hub)
- **Quick Phraseboard:** [http://localhost:8000/#phraseboard](http://localhost:8000/#phraseboard)
- **Interactive API Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 💻 Development Instructions & Testing

Transify 2.0 includes an exhaustive automated test suite with **180 tests** across unit, integration, security, migration, and browser Playwright workflows:

```bash
# Run full pytest test suite
PYTHONPATH=. pytest -v

# Run browser end-to-end tests across viewports (1280x800, 375x667, 667x375, 1024x500)
PYTHONPATH=. pytest tests/test_browser_auth.py -v

# Run XSS prevention and DOM injection tests
PYTHONPATH=. pytest tests/test_xss_prevention.py -v

# Run email delivery and password reset tests
PYTHONPATH=. pytest tests/test_email_and_reset.py -v

# Run database migrations and IDOR security tests
PYTHONPATH=. pytest tests/test_migrations_and_idor.py -v

# Run Android unit tests & debug APK build
cd android
./gradlew testDebugUnitTest
./gradlew assembleDebug
```

---

## 💾 Database Operations & Disaster Recovery

Transify includes verified, non-blocking online backup and rollback utilities:

```bash
# Create an atomic, verified online SQLite snapshot
python scripts/backup_db.py

# Roll back / restore database from a snapshot
python scripts/restore_db.py backups/transify_backup_<timestamp>.db
```

---

## 📚 Architectural Blueprints & Documentation

| Document | Description |
| :--- | :--- |
| **[Product Requirements Document (PRD)](docs/PRD.md)** | Core vision, personas, functional requirements, and success metrics. |
| **[Design System & UI/UX (DESIGN.md)](docs/DESIGN.md)** | Kinetic glass design tokens, motion dials, WCAG AAA rules, and no-auto-audio policy. |
| **[Software Architecture Blueprint](docs/SOFTWARE_ARCHITECTURE.md)** | End-to-end decoupled microservice architecture and data flow pipelines. |
| **[Database Architecture Specification](docs/DATABASE_SPECIFICATION.md)** | SQLite WAL schema, tables, composite PKs, 11 indexes, and migrations 1–7. |
| **[Unified API Specification](docs/API_SPECIFICATION.md)** | Exhaustive reference for all 49 endpoints across 11 functional domains. |
| **[Agents & Model Context Protocol (MCP)](docs/AGENTS_AND_MCP_SPECIFICATION.md)** | 98% Decision Gateway, agentic disambiguation, and MCP tool schemas. |
| **[Development Roadmap](docs/DEVELOPMENT_ROADMAP.md)** | Engineering phase history, release milestones, and roadmap. |
| **[Android Build Guide](ANDROID_BUILD_GUIDE.md)** | Android Studio / Gradle configuration and hardware WebView setup. |

---

## 📱 Android Client

Transify 2.0 includes a dedicated Android application located in `android/`:
- **Build System:** Gradle 8.9 with Android Gradle Plugin 8.5.2.
- **Language:** Kotlin 1.9.24 with AndroidX libraries.
- **WebView Architecture:** Seamless hardware-accelerated WebView bridging local audio and camera permissions.
- **APK Verification:** Verified debug build generating release-ready APK at `android/app/build/outputs/apk/debug/app-debug.apk`.

---

## ♿ Accessibility Compliance (WCAG 2.1 AAA)

Transify 2.0 was engineered for universal accessibility:
- **Theme Palette:** Pure high-contrast purple aesthetic (`#8338ec`) with full light and dark mode responsiveness.
- **Screen Reader Announcements:** Dedicated `aria-live="polite"` landmark regions for real-time auditory notifications.
- **Zero Heavy Frameworks:** Pure vanilla JavaScript and modular CSS for lightweight, zero-latency execution.
- **Local Privacy:** All translations and user data persist in isolated SQLite storage, keeping private conversations secure on-device.

---

## 📄 License & Acknowledgments

- **License:** MIT License. Free for educational, research, and assistive deployment.
- **HaGRID Dataset:** Kapitanov et al. (HAnd Gesture Recognition Image Dataset).
- **BdSL Dataset:** Bangladesh Sign Language Consortium.
- **ICEB Standards:** Unified English Braille (UEB) Rules, 3rd Edition (2024).
- **MediaPipe:** Google MediaPipe HandLandmarker.
