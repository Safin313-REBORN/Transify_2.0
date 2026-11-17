# Transify — Comprehensive REST API Specification

> **Base URL:** `http://localhost:8000`  
> **API Protocol:** REST over HTTP/1.1 & HTTP/2  
> **Format:** `application/json` (or `multipart/form-data` for file uploads)  
> **Interactive Swagger UI:** `http://localhost:8000/docs`  
> **OpenAPI Specification:** `http://localhost:8000/openapi.json`  

---

## 1. System & Telemetry Endpoints

### 1.1 Health Check
- **Endpoint:** `GET /api/health`
- **Description:** Verifies platform availability, database connection, and core sub-modules.
- **Response `200 OK`:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "subsystems": {
    "sign_recognition": "online",
    "braille_ocr": "online",
    "database": "connected",
    "audio_tts": "online"
  }
}
```

### 1.2 Model Telemetry & Accuracy Status
- **Endpoint:** `GET /api/models/status`
- **Description:** Returns live accuracy benchmarks, champion architectures, and supported classes.
- **Response `200 OK`:**
```json
{
  "signframe_asl": {
    "architecture": "SignFrame CNN",
    "supported_classes": 26,
    "status": "LOADED"
  },
  "hagrid_gestures": {
    "test_accuracy": 0.8683,
    "supported_classes": 24,
    "status": "LOADED"
  },
  "mediapipe_landmarker": {
    "keypoints": 21,
    "status": "LOADED"
  },
  "braille_obr": {
    "champion_model": "Multi-Output ExtraTrees",
    "test_cell_accuracy": 1.0,
    "metric_scope": "cell-level",
    "standard": "UEB Grade 1",
    "status": "LOADED"
  }
}
```

---

## 2. Sign Language & Gesture Endpoints

### 2.1 Predict from Landmark Vector
- **Endpoint:** `POST /api/sign/predict`
- **Content-Type:** `application/json`
- **Request Body:**
```json
{
  "landmarks": [0.52, 0.41, 0.0, "... 162 normalized coordinates ..."],
  "language_mode": "asl"
}
```
- **Response `200 OK`:**
```json
{
  "prediction": "HELLO",
  "gloss": "Hello / Greeting",
  "confidence": 0.992,
  "is_fallback": false,
  "engine_source": "SignFrame AI (ASL)"
}
```

### 2.2 Process Live Camera Frame
- **Endpoint:** `POST /api/sign/process_frame`
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `file`: Raw image frame (JPEG/PNG).
  - `roi_mode`: `"right"` | `"center"` | `"left"`.
- **Response `200 OK`:**
```json
{
  "has_hand": true,
  "in_roi": true,
  "prediction": "LIKE",
  "confidence": 0.985,
  "consensus_count": 3
}
```

### 2.3 Fingerspelling Word Assembly
- **Endpoint:** `POST /api/sign/fingerspell`
- **Request Body:** `{"action": "append", "letter": "A"}`
- **Response `200 OK`:**
```json
{
  "current_word": "TRANS",
  "committed_sentence": ["HELLO"]
}
```

### 2.4 AI Sentence Smoothing
- **Endpoint:** `POST /api/sign/sentence/smooth`
- **Request Body:**
```json
{
  "tokens": ["I", "NEED", "WATER"]
}
```
- **Response `200 OK`:**
```json
{
  "raw_gloss": "I NEED WATER",
  "synthesized_sentence": "I need some water, please."
}
```

---

## 3. Optical Braille Recognition (OBR) Endpoints

### 3.1 Pre-Flight Image Quality Assessment (IQA)
- **Endpoint:** `POST /api/braille/iqa`
- **Content-Type:** `multipart/form-data`
- **Parameters:** `file` (Image binary).
- **Response `200 OK`:**
```json
{
  "accepted": true,
  "metrics": {
    "sharpness": 448.3,
    "min_sharpness": 25.0,
    "brightness": 245.6,
    "resolution": "934x544"
  },
  "is_usable": true
}
```

### 3.2 Full Document Braille Translation
- **Endpoint:** `POST /api/braille/translate`
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `file`: Image binary (PNG, JPG, WebP).
  - `speak_tts`: `"true"` | `"false"`.
- **Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "text": "Hello world.",
    "braille_ascii": ",hello world.",
    "cell_count": 14,
    "line_count": 1,
    "mean_confidence": 0.989,
    "engine_info": {
      "is_fallback": false,
      "source": "Local Custom ExtraTrees Model (>= 98% Confidence)",
      "badge": "CUSTOM AI MODEL (>= 98%)"
    },
    "read_coverage": {
      "percentage": 100.0,
      "confident_cells": 14,
      "total_cells": 14,
      "summary": "All Braille cells decoded (14 cells)."
    }
  }
}
```

---

## 4. Audio Text-to-Speech (TTS) Endpoint

- **Endpoint:** `POST /api/tts`
- **Content-Type:** `application/json`
- **Request Body:**
```json
{
  "text": "Welcome to Transify Assistive Platform.",
  "speed": 1.0,
  "lang": "en-US"
}
```
- **Response `200 OK`:**
```json
{
  "status": "success",
  "audio_format": "audio/wav",
  "data_url": "data:audio/wav;base64,UklGRi...",
  "character_count": 39
}
```

---

## 5. History & Feedback Endpoints

- `GET /api/history`: Returns the list of recent translation logs.
- `DELETE /api/history`: Clears user audit logs.
- `POST /api/history/{id}/feedback`: Accepts thumbs up (`rating: 5`) or correction feedback (`rating: 1`).
