# Project: Transify 2.0

## Overview
Transify is an assistive multimodal AI translation platform for hand gesture/sign language and optical Braille recognition (OBR), wrapped in a secure native Android WebView application. The backend is powered by FastAPI, SQLite, and scikit-learn / MediaPipe inference models, deployed on Railway.

## Architecture
- **Web Frontend**: Vanilla HTML5, CSS3, JavaScript (no framework rewrite, strict visual preservation).
- **Mobile Container**: Android WebView application (`com.abrarafick.transify`) with AndroidX `WebMessageListener` native bridges for SpeechRecognizer, file picking, and Blob downloads.
- **Backend API**: FastAPI serving the unified web client and REST endpoints.
- **AI Models**:
  - SignFrame ASL Fingerspelling Predictor (PyTorch / NumPy CNN fallback)
  - HaGRID Gesture Classifier (scikit-learn Random Forest, 24 classes, 86.83% test accuracy)
  - MediaPipe Hand Landmarker (21 landmarks)
  - Braille OCR (scikit-learn ExtraTrees, UEB Grade 1, 100% held-out cell accuracy)
- **Deployment**: Railway production container with persistent SQLite volume (`/app/data`).

## Target Environments & Identifiers
- **Repository**: `Safin313-REBORN/Transify_2.0` (branch: `main`)
- **Railway Project ID**: `cf17911b-4222-431e-87cd-666aabf88422`
- **Railway Service ID**: `8b4fd318-c669-49ca-bdc2-516cf229211d`
- **Railway Environment**: `production` (`496ab9d9-b582-4d6b-82db-058b425eb4b8`)
- **Production URL**: `https://transify20-production.up.railway.app`
- **Android Package**: `com.abrarafick.transify`
