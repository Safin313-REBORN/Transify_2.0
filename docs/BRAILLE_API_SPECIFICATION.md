# Optical Braille Recognition API Specification
## REST & WebSocket Gateway Schemas for Transify Module 02

---

## 1. Overview and Architecture

The Transify Braille AI API provides production-grade endpoints for image quality assessment, full-page Braille image translation, single-cell pattern classification, and text-to-speech audio synthesis.

**Base URL:** `/v1/braille`  
**Protocol:** HTTP/1.1 and HTTP/2 over TLS (WebSocket supported for streaming captures)  
**Authentication:** Standard Bearer API Key via header: `Authorization: Bearer <API_TOKEN>`

---

## 2. Endpoints Specification

### 2.1 Translate Braille Image
- **Endpoint:** `POST /v1/braille/translate`
- **Content-Type:** `multipart/form-data` or `application/json` (Base64 payload)
- **Description:** Ingests a full-page Braille photograph, executes IQA, preprocessing, cell localization, 6-dot classification, and returns formatted English text.

#### Request Schema (Multipart Form)
| Parameter | Type | Required? | Description |
|---|---|:---:|---|
| `file` | Binary File | Required | JPG, PNG, or WebP image file ($\le 15\text{ MB}$). |
| `speak_tts` | Boolean | Optional (Default: `false`) | If `true`, includes synthesized TTS audio URL/base64 in response. |
| `confidence_threshold` | Float | Optional (Default: `0.65`) | Threshold below which cells are flagged as uncertain. |

#### Response Schema (JSON)
```json
{
  "success": true,
  "status_code": 200,
  "data": {
    "text": "Feel each dot gently with the fingertip.\nPractice daily.",
    "clean_text": "Feel each dot gently with the fingertip. Practice daily.",
    "mean_confidence": 0.9985,
    "total_cells": 57,
    "classified_cells_count": 48,
    "spaces_count": 9,
    "uncertain_cells": [],
    "grade2_warnings": [],
    "diagnostics": {
      "iqa_ms": 32.4,
      "detection_ms": 78.1,
      "classification_ms": 115.6,
      "decoding_ms": 0.15,
      "total_latency_ms": 226.25
    },
    "qa_metrics": {
      "resolution": "1600x900",
      "blur_variance": 133.56,
      "mean_brightness": 237.68,
      "contrast_std": 3.57,
      "glare_pct": 0.45,
      "quality_flags": []
    }
  }
}
```

---

### 2.2 Image Quality Assessment (IQA Pre-Flight)
- **Endpoint:** `POST /v1/braille/iqa`
- **Description:** Fast pre-flight check evaluated in $< 35\text{ ms}$ on client or server to ensure image is sharp and properly illuminated before running full recognition.

#### Response Schema (When Image is Rejected)
```json
{
  "success": false,
  "status_code": 422,
  "error": {
    "code": "IMAGE_QUALITY_INSUFFICIENT",
    "rejection_reason": "Image is too blurry (Laplacian variance 5.5 < threshold 30.0). Hold camera steady.",
    "quality_flags": ["BLURRY", "LOW_CONTRAST"],
    "metrics": {
      "resolution": "1600x900",
      "blur_variance": 5.48,
      "mean_brightness": 237.75,
      "contrast_std": 1.43,
      "glare_pct": 0.14
    },
    "user_guidance": "Please hold the camera steady, ensure adequate side lighting, and avoid direct perpendicular flash."
  }
}
```

---

### 2.3 Text-to-Speech Synthesis
- **Endpoint:** `POST /v1/braille/tts`
- **Content-Type:** `application/json`
- **Description:** Converts translated English text to audio waveform.

#### Request Schema
```json
{
  "text": "Feel each dot gently with the fingertip. Practice daily.",
  "voice": "en-US",
  "speed": 1.0,
  "format": "wav"
}
```

#### Response Schema
```json
{
  "success": true,
  "audio_format": "audio/wav",
  "duration_seconds": 3.42,
  "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEA..."
}
```

---

## 3. Standard HTTP Error Codes

| Error Code | HTTP Status | Meaning & Troubleshooting |
|---|:---:|---|
| `IMAGE_QUALITY_INSUFFICIENT` | 422 | Image failed blur, illumination, or glare check. User must retake photo. |
| `NO_BRAILLE_CELLS_DETECTED` | 422 | Image does not appear to contain recognizable 6-dot Braille patterns. |
| `UNSUPPORTED_IMAGE_FORMAT` | 415 | File format must be JPEG, PNG, or WebP. |
| `PAYLOAD_TOO_LARGE` | 413 | Uploaded image exceeds 15 MB limit. |
| `INTERNAL_INFERENCE_ERROR` | 500 | Exception occurred in vision pipeline; details recorded in server log. |
