# Transify — Project Evaluation & Panel Documentation Package

> **Breaking Communication Barriers**  
> *A Multi-Modal Assistive AI Translation Platform for Sign Language, Optical Braille, STT & TTS*  
> **Academic Year 2026 • Evaluation Panel & Project Defense Package**  
> **Repository:** [https://github.com/Abrarafick/transify](https://github.com/Abrarafick/transify)  

---

## 📁 Package Deliverables Manifest

This directory (`Panel/`) contains all required technical documentation, presentation decks, architectural diagrams, and application screenshots prepared for the project defense and evaluation committee.

| File / Folder | Type | Description |
| :--- | :--- | :--- |
| 📊 **`Project_Presentation.pptx`** | Presentation | 16:9 widescreen presentation deck (12 slides) covering project motivation, problem statement, architecture, ML engines (98.7% ASL & 99.4% Braille), UI/UX accessibility, benchmarks, live demo walkthrough, and roadmap. |
| 📄 **`Project_Report.pdf`** | Technical Report | Publication-quality project documentation including executive summary, literature review, mathematical landmark formulations, algorithm benchmarks, database schema, and test results. |
| 📘 **`README.md`** | Overview | Package manifest, system setup, prerequisite installation, execution guide, demo credentials, and technical verification instructions. |
| 📋 **`EXECUTIVE_SUMMARY.md`** | Executive Summary | High-level problem statement, business case, UN SDG alignment (SDG 3, 4, 10), and key quantitative engineering milestones. |
| 🏗️ **`SYSTEM_ARCHITECTURE.md`** | Architecture | Detailed multi-tier design specification covering presentation, FastAPI gateway, 98% Decision Gateway, and SQLite persistence. |
| 🔌 **`API_DOCUMENTATION.md`** | API Reference | Complete REST API specification with endpoint contracts, payload schemas, and example JSON responses. |
| 📖 **`USER_MANUAL.md`** | User Manual | End-user operational guide with step-by-step instructions for Deaf, Blind, Speech-Impaired, and Hearing communicators. |
| 🧪 **`TESTING_AND_VERIFICATION_REPORT.md`** | QA Audit | Audit report detailing all 34 automated unit and integration tests passing with 100% green status. |
| 🧠 **`DATASET_AND_MODEL_CARD.md`** | Model Card | Provenance of ASL, HaGRID, and 50-document Braille datasets, ExtraTrees/Random Forest architectures, and metrics. |
| 🚀 **`DEPLOYMENT_AND_SETUP_GUIDE.md`** | DevOps | Bare-metal local setup, Docker containerization, `.env` configuration, and Nginx production reverse proxy guide. |
| 🎓 **`PROJECT_DEFENSE_FAQ.md`** | Viva Voce | Comprehensive defense panel Q&A addressing ML trade-offs, 98% Decision Gateway, privacy, and accessibility. |
| 🤝 **`CONTRIBUTING.md`** | Guidelines | Developer standards, zero-Bengali constraint in `src/`, WCAG 2.1 AAA mandate, and Git workflow. |
| 🏗️ **`System_Architecture.png`** | Diagram | High-resolution 300 DPI multi-tier architecture diagram. |
| 👥 **`Use_Case_Diagram.png`** | Diagram | High-resolution 300 DPI UML Use Case Diagram illustrating user interactions. |
| 🗄️ **`ER_Diagram.png`** | Diagram | High-resolution 300 DPI Entity-Relationship (ER) Diagram detailing SQLite relational entities. |
| 🔄 **`Flowchart.png`** | Diagram | High-resolution 300 DPI End-to-End System Workflow Flowchart. |
| 🖼️ **`Screenshots/`** | Directory | High-fidelity device-frame application screenshots highlighting every core viewport. |

---

## 🖼️ Application Screenshots Catalog (`Panel/Screenshots/`)

| Screenshot | Screen Name | Key Highlights |
| :--- | :--- | :--- |
| **`01_Onboarding_Welcome.png`** | Welcome Onboarding Screen | First-time visitor view showcasing Transify brand artwork, lavender background, and `Register`, `Login`, and `Continue without registration` actions. |
| **`02_SlideUp_Authentication.png`** | Slide-Up Authentication Sheet | Hardware-accelerated frosted glass bottom sheet with spring physics animation, dual tab switching, and password eye toggles. |
| **`03_Dashboard_Home.png`** | Central Assistive Dashboard | Uncluttered feature cards for Sign Language, Braille OCR, Voice Hub, and Accessibility Center. |
| **`04_Live_Sign_Translator.png`** | Live Sign Translator | Real-time 30 FPS webcam feed, MediaPipe 162-D landmark overlay, confidence meter, and recognized gloss output. |
| **`05_Braille_Image_Translator.png`** | Optical Braille Reader | Pre-flight Image Quality Assessment (IQA), contour grid alignment, and 99.4% ExtraTrees UEB Grade 1 decoding. |
| **`06_Speech_TTS_STT.png`** | Two-Way Voice & Audio Hub | Bidirectional communication interface with audio ripple pulse recording animation and phonetic TTS speech playback. |
| **`07_Accessibility_Preferences.png`** | Accessibility Center | WCAG 2.1 AAA high-contrast mode toggles, dynamic text scaling (14px–22px), and voice calibrations. |
| **`08_System_Analytics.png`** | System Analytics & Telemetry | Live accuracy meters (98.7% & 99.4%), 34/34 automated test confirmation, and persistent audit trails. |

---

## ⚙️ System Requirements & Prerequisites

- **Operating System:** Windows 10/11, macOS 12+, or Ubuntu 20.04+ Linux
- **Python Version:** Python 3.10, 3.11, 3.12, 3.13, or 3.14
- **Web Browser:** Google Chrome, Microsoft Edge, or Mozilla Firefox (with WebRTC camera and Web Audio API support)
- **Hardware:** Standard consumer laptop or desktop with built-in or USB webcam and microphone (No discrete GPU required; all models run efficiently on CPU).

---

## 🚀 Quick Setup & Installation Guide

### Step 1: Open Terminal in Project Root
```bash
cd "C:\Users\HP\Desktop\Transify"
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Launch the Transify Application Server
```bash
python run_server.py --host 0.0.0.0 --port 8000
```
When successfully started, the console displays:
```text
======================================================================
  TRANSIFY — Breaking Communication Barriers
  Assistive Sign Language & Braille AI Translation Platform
======================================================================
  [+] Platform Status:  Online & Ready
  [+] Sign AI Engine:   ASL & HaGRID Ensemble (98.7% Accuracy)
  [+] Braille AI Engine: UEB Grade 1 ExtraTrees (99.4% Accuracy)
  [+] Decision Gateway: 98% Confidence Gate + MCP Server Fallback
  [+] Database Layer:   SQLite Persistent Storage (Local Privacy)
  [+] Speech Audio:     Web Speech API + PCM Audio Fallback
  [+] Accessibility:    WCAG 2.1 AAA High-Contrast & Screen-Reader Ready

  🌐 Accessible Web Application: http://localhost:8000/
  📊 Assistive Dashboard:         http://localhost:8000/dashboard
  🤟 Live Sign Translator:       http://localhost:8000/sign
  ⠃ Braille Image Translator:    http://localhost:8000/braille
  📖 Interactive API Docs:        http://localhost:8000/docs
======================================================================
```

---

## 🎯 Live Demonstration & Evaluator Walkthrough

### 1. Two-Step Onboarding Gateway
1. Open your browser and navigate to **[http://localhost:8000/](http://localhost:8000/)**.
2. **Step 1 (Welcome Screen):** Notice the clean Transify brand illustration, header logo, and 3 action options.
3. **Step 2 (Slide-Up Bottom Sheet):** Click **`Login`** or **`Register`**. Observe the smooth upward spring slide animation (`translateY(105%)` to `translateY(0)`).
4. Click **`← Back`** or tap the dimmed background to watch the sheet smoothly glide back down.
5. **Instant Demo Access:** Click **`Continue without registration`** to immediately bypass credentials and trigger the splash experience into the main dashboard.

### 2. Demo Credentials
If logging in through the form:
- **Email:** `demo@transify.ai`
- **Password:** `transify2026`
- **Or:** Click the **`⚡ One-Click Demo Access`** pill to auto-populate and authenticate in 0.4 seconds.

### 3. Live Sign Language & Gesture Translator
- Navigate to the **Hand Signal** card or visit `http://localhost:8000/sign`.
- Grant webcam permission to activate the 30 FPS MediaPipe tracking.
- Toggle between **Live Expressions**, **A–Z Alphabet Speller**, and **Common Vocabulary**.
- Test gestures (`CALL`, `LIKE`, `STOP`, `PEACE`, `HELLO`) to observe instant recognition and continuous sentence assembly.

### 4. Optical Braille Image Translator
- Navigate to the **Braille** card or visit `http://localhost:8000/braille`.
- Upload or drag-and-drop an embossed dot photograph.
- Inspect the Pre-Flight Image Quality Assessment (IQA) and confidence status badge.
- Review the decoded English text (UEB Grade 1, 99.4% precision) and click **`🔊 Listen to Text (TTS)`**.

### 5. Speech-to-Text & Text-to-Speech Hub
- Open **Speech to Text** to view real-time voice captioning. Click **`🔊 Speak Back (TTS)`** to forward captions to the voice synthesizer.
- Open **Text to Speech** to type or click 1-tap quick phrases with custom speed scaling.

---

## 🧪 Automated Testing & Verification

The project includes an end-to-end regression test suite covering all machine learning pipelines, REST endpoints, database transactions, and accessibility preference services.

To run the automated test suite:
```bash
python -m unittest tests/test_full_system.py
```

### Verified Test Output:
```text
..................................
----------------------------------------------------------------------
Ran 34 tests in 2.854s

OK
```
**All 34/34 automated tests pass with 100% green status and zero regressions.**

---

## 📊 Technical Specifications Summary

| Feature Parameter | Specification |
| :--- | :--- |
| **Sign Feature Dimension** | 162 Normalized Landmarks (Hands 42 x 3, Pose 12 x 3) |
| **Sign Classification Algorithm** | Random Forest Ensemble & HaGRID Geometric Classifier |
| **Sign Recognition Accuracy** | **98.7%** (ASL) & **98.2%** (HaGRID) |
| **Braille OCR Model** | ExtraTrees Classifier (UEB Grade 1 Dot Matrix) |
| **Braille OCR Accuracy** | **99.4%** Character Accuracy across 2,471 Cells |
| **Decision Gateway** | Local Model ($\ge 98\%$) / MCP Fallback ($< 98\%$) |
| **Pre-Flight IQA Latency** | < 35 ms (Laplacian Variance + Histogram Dispersion) |
| **Inference Latency** | < 30 ms Per Frame CPU Execution |
| **Web Accessibility Standard** | **WCAG 2.1 AAA Compliant** (High Contrast & Aria Modals) |
| **Memory Footprint** | < 220 MB RAM at Peak 30 FPS Video Processing |

---

## 🏛️ Project Defense & Submission Committee Information

- **Project Title:** Transify — Breaking Communication Barriers
- **Domain:** Assistive Artificial Intelligence & Multi-Modal Human-Computer Interaction
- **Academic Year:** 2026
- **Package Location:** `C:\Users\HP\Desktop\Transify\Panel\`

*All files in this directory are final, validated, and ready for panel evaluation.*
