# Transify — Sign Language Recognition API Specification
## REST and WebSocket Interfaces for 10-Class BdSL Recognition Service

**Document Version:** 2.0.0  
**Phase:** Phase 2 — System Integration & API Contract  
**Protocol Support:** RESTful HTTP/JSON & Asynchronous WebSockets  

---

## 1. Overview & Architectural Isolation

The Sign Language Recognition engine is deployed as an autonomous microservice. It operates completely independently from the Braille recognition engine, providing high-throughput WebSocket streaming and stateless REST endpoints.

---

## 2. Data Models and Enums

### 2.1 Supported Class Vocabulary Response
```json
{
  "classes": [
    {"class_id": 0, "label": "HELLO", "bdsl_gloss": "হ্যালো", "english_text": "Hello."},
    {"class_id": 1, "label": "THANK_YOU", "bdsl_gloss": "ধন্যবাদ", "english_text": "Thank you."},
    {"class_id": 2, "label": "YOURE_WELCOME", "bdsl_gloss": "স্বাগতম", "english_text": "You're welcome."},
    {"class_id": 3, "label": "PLEASE", "bdsl_gloss": "দয়া করে", "english_text": "Please."},
    {"class_id": 4, "label": "I_NEED_HELP", "bdsl_gloss": "সাহায্য প্রয়োজন", "english_text": "I need help."},
    {"class_id": 5, "label": "YES", "bdsl_gloss": "হ্যাঁ", "english_text": "Yes."},
    {"class_id": 6, "label": "NO", "bdsl_gloss": "না", "english_text": "No."},
    {"class_id": 7, "label": "OKAY", "bdsl_gloss": "ঠিক আছে", "english_text": "Okay."},
    {"class_id": 8, "label": "STOP", "bdsl_gloss": "থামো", "english_text": "Stop."},
    {"class_id": 9, "label": "I_DONT_UNDERSTAND", "bdsl_gloss": "বুঝি না", "english_text": "I don't understand."}
  ]
}
```

### 2.2 Standard Prediction Response Schema
```json
{
  "recognized": true,
  "class_id": 4,
  "label": "I_NEED_HELP",
  "bdsl_gloss": "সাহায্য প্রয়োজন",
  "english_text": "I need help.",
  "confidence": 0.942,
  "supported": true,
  "rejection_reason": null,
  "timestamp": "2026-11-14T12:00:00.123Z"
}
```

### 2.3 Unsupported / Rejected Prediction Response Schema
```json
{
  "recognized": false,
  "class_id": -1,
  "label": "UNSUPPORTED",
  "bdsl_gloss": "",
  "english_text": "Sign not recognized or not currently supported.",
  "confidence": 0.385,
  "supported": false,
  "rejection_reason": "Low confidence (0.385 < 0.700)",
  "timestamp": "2026-11-14T12:00:00.123Z"
}
```

---

## 3. Endpoints Specification

### 3.1 Get Supported Vocabulary
- **Method:** `GET`
- **Route:** `/api/sign/vocabulary`
- **Description:** Returns the closed vocabulary list of 10 supported BdSL expressions.
- **Response:** `200 OK` (Vocabulary JSON array).

---

### 3.2 Predict from Landmark Sequence
- **Method:** `POST`
- **Route:** `/api/sign/predict`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "landmarks": [
      [0.12, -0.45, 0.05, ...],  // Frame 0: 162 floats
      ...
      [0.25, 0.10, 0.20, ...]    // Frame 29: 162 floats
    ]
  }
  ```
- **Response:** `200 OK` (Standard Prediction Response JSON).
- **Errors:** `422 Unprocessable Entity` if sequence shape is not $(30, 162)$.

---

### 3.3 Predict from Video Upload
- **Method:** `POST`
- **Route:** `/api/sign/predict_video`
- **Headers:** `Content-Type: multipart/form-data`
- **Body:** `file` (MP4, AVI, or WebM video file, max $10\text{ MB}$).
- **Processing:** Server runs MediaPipe Holistic landmark extraction, normalizes to $(30, 162)$, and executes inference.
- **Response:** `200 OK` (Standard Prediction Response JSON).

---

### 3.4 Live WebSocket Streaming
- **Route:** `ws://<host>:<port>/ws/sign/live`
- **Protocol:** Bidirectional WebSocket (Text JSON or Binary Float32 ArrayBuffer).
- **Client Message (Inbound):**
  - Client sends either 162-float coordinate array per frame, OR JPEG compressed video frame.
- **Server Message (Outbound):**
  - Server sends continuous prediction status updates at 30 FPS.
  - Includes `is_committed: true` when a gesture has satisfied the 6-frame consensus threshold.
- **Heartbeat & Keep-Alive:** PING/PONG frame every 15 seconds.

---

### 3.5 Text-to-Speech (TTS) Synthesis
- **Method:** `POST`
- **Route:** `/api/sign/tts`
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "text": "I need help.",
    "voice": "en-US",
    "speed": 1.0
  }
  ```
- **Response:** `200 OK` with `Content-Type: audio/wav` or `audio/mpeg`.
