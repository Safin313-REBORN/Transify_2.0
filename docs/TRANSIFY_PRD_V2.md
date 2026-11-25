# Transify 2.0 Product Requirements Document (PRD V2)

**Document Version:** 2.0.0  
**Status:** Approved & Implemented  
**Author:** Team Alpha Nexus  
**Last Updated:** 2026-11-25  
**Target Environment:** Production (Railway Cloud + Offline PWA Edge)  

---

## 1. Executive Summary & Vision

**Transify** is an enterprise-grade, multimodal assistive health and communications platform engineered for individuals with sensory, motor, and environmental communication barriers. By integrating computer vision (Bangla & American Sign Language recognition, Optical Braille Recognition), clinical decision support (evidence-based emergency triage, insulin titration guidance, polypharmacy interaction checking), and decentralized agent protocols (Model Context Protocol - MCP), Transify democratizes inclusive healthcare and real-time translation across low-bandwidth, rural, and clinical settings.

### Core Mission
To eliminate sensory and physical communication barriers in healthcare and everyday life through zero-latency on-device processing, privacy-first offline operation, and medically verified conversational assistance.

---

## 2. User Personas & Clinical Scenarios

### Persona 1: Deaf & Hard-of-Hearing (BdSL / ASL Communicator)
- **Name:** Rafiq (Age 24, Rural Sylhet / Urban Dhaka)
- **Profile:** Native Bangla Sign Language (BdSL) signer. Visits medical clinics where doctors and triage nurses do not understand sign language.
- **Needs:** Real-time sign-to-text and sign-to-speech translation with visual feedback, zero lag, gesture stabilization, and offline capability.
- **Safety Invariant:** Zero unauthorized auto-audio emissions to prevent embarrassing or privacy-violating loud speaker triggers in crowded clinics.

### Persona 2: Visually Impaired Individual (Braille Reader)
- **Name:** Ananya (Age 31, College Lecturer)
- **Profile:** Reads Grade 1 & Grade 2 Unified English Braille (UEB) and Bharati Bengali Braille. Relies on tactile documents, medication boxes, and textbooks.
- **Needs:** Fast optical Braille recognition from phone camera with instant dot matrix visualization, TTS read-aloud (on explicit demand), and export to text or `.brf` embossable format.

### Persona 3: Rural Patient with Chronic Comorbidities
- **Name:** Abdul (Age 58, Kurigram District)
- **Profile:** Type 2 Diabetes Mellitus patient with hypertension. Limited internet connectivity. Requires insulin dose adjustments based on carb intake and blood glucose readings.
- **Needs:** Instant meal-to-bolus calculator, hypoglycemia early warning, local offline caching of clinical guidelines, emergency medical drone dispatch capability (Zipline integration).

### Persona 4: Clinic Triage Nurse / Healthcare Worker
- **Name:** Dr. Nasrin (Age 39, Community Health Clinic)
- **Profile:** Evaluates high patient volumes. Manages polypharmacy prescriptions and acute symptom triage under high stress.
- **Needs:** Rapid Manchester/ESI-aligned symptom triage matrix, automated drug-drug interaction screening via OpenFDA/ChEMBL, and structured EHR data exports.

---

## 3. Platform Functional Dimensions & Modules

Transify 2.0 is partitioned into 6 primary operational modules:

```
+-------------------------------------------------------------------------------+
|                                TRANSIFY PLATFORM                              |
+-----------------------+-------------------------------+-----------------------+
| 1. Vision & Gesture   | 2. Tactile & Document Vision  | 3. Care Decision      |
|    - 40+ BdSL Signs   |    - 6-Dot UEB Grade 1 Braille|    - Emergency Triage |
|    - 26 ASL Alphabets |    - Bharati Bengali Braille  |    - Insulin Bolus    |
|    - Real-time MediaPipe- Interactive Dot Matrix Grid |    - Polypharmacy API |
+-----------------------+-------------------------------+-----------------------+
| 4. MCP Agent Protocol | 5. Remote Care & Logistics    | 6. Inclusive UX & PWA |
|    - JSON-RPC 2.0 API |    - Zipline Drone Dispatch   |    - Zero Auto-Audio  |
|    - Tool Calling     |    - Low-bandwidth Fallback   |    - WCAG 2.1 AAA     |
|    - Ambiguity Agents |    - Offline Local Caching    |    - Keyboard Nav     |
+-----------------------+-------------------------------+-----------------------+
```

### Module 1: Gesture & Sign Translation
- **Input:** High-speed video stream via WebRTC / WebSocket (`/ws/sign`).
- **Processing:** 21-landmark 3D hand pose estimation via MediaPipe/TensorFlow.js.
- **Lexicon:** 40+ standardized BdSL medical and conversational signs + ASL alphabets A-Z.
- **Confidence Filter:** Dynamic sliding-window temporal smoothing with threshold $\tau = 0.78$.

### Module 2: Optical Braille Recognition (OBR)
- **Input:** Image upload or live camera capture (`POST /api/v1/braille/translate`).
- **Processing:** Bilateral filtering, morphological dot extraction, spatial grid clustering.
- **Interactive Component:** 6-dot virtual Braille matrix enabling bidirectional tactile inspection and character lookup.
- **Standards:** UEB Grade 1 and Bharati Bengali Braille mapping.

### Module 3: Transify Care & Clinical Decision Support (CDS)
- **Emergency Triage Engine (`/api/care/triage`):** 5-level acuity stratification (Resuscitation, Emergent, Urgent, Less Urgent, Non-Urgent) with red-flag detection (chest pain, stroke signs, dyspnea).
- **Insulin & Nutrition Calculator (`/api/care/insulin`):** Validated carbohydrate-to-insulin ratio (CIR) and insulin sensitivity factor (ISF) calculation with strict hypo/hyperglycemia safety guards.
- **Polypharmacy Checker (`/api/care/polypharmacy`):** Multi-drug interaction screening against live FDA adverse event databases and ChEMBL.

### Module 4: Model Context Protocol (MCP v1.0)
- **Protocol:** Standardized JSON-RPC 2.0 over HTTP (`POST /api/mcp` and `POST /mcp`).
- **Discovery:** `GET /api/mcp/tools` returning full JSON Schema for agent tooling.
- **Registered Tools:**
  1. `resolve_sign_ambiguity`: Clinical/conversational sign disambiguation.
  2. `resolve_braille_ambiguity`: OCR confidence correction.
  3. `triage_symptom`: Multi-factorial clinical symptom acuity triage.
  4. `calculate_insulin_correction`: Diabetic bolus and meal calculation.
  5. `check_polypharmacy`: Multi-agent drug interaction auditing.
  6. `chat_assistive_agent`: Evidence-based conversational medical assistant.

### Module 5: Remote Care & Emergency Logistics
- **Zipline Medical Drone Dispatch:** Simulated and integrated API for urgent anti-venom, insulin, and blood delivery to remote coordinates.
- **Network Resilience:** Progressive Web App (PWA) with Service Worker caching and automatic offline degradation.

### Module 6: Inclusive Accessible User Experience
- **WCAG 2.1 AAA Compliance:** 7:1+ contrast ratios across light and dark modes.
- **Zero Auto-Audio Invariant:** No speech synthesis, audio cues, or sound effects without an explicit, verifiable user click/tap gesture.
- **Navigation:** Complete keyboard trapping, skip links, aria-live announcements for screen readers, and zero horizontal scrolling on mobile viewports.

---

## 4. Non-Functional Requirements (NFRs)

| Category | Requirement | Target Metric | Verification Method |
| :--- | :--- | :--- | :--- |
| **Latency** | Sign gesture recognition inference | $< 45 \text{ ms}$ | WebSocket benchmark |
| **Latency** | REST API P99 response time | $< 120 \text{ ms}$ | Automated load testing |
| **Audio Privacy** | Zero Auto-Audio execution | $0 \text{ unauthorized triggers}$ | Playwright browser automated regression |
| **Database** | SQLite integrity & immutability | SHA-256 constant | SHA-256 hash checking pre/post test suite |
| **Security** | OWASP Top 10 mitigation | 0 vulnerabilities | Strict CSP, CSRF tokens, input validation |
| **Accessibility** | Color contrast & navigation | WCAG 2.1 AAA | Axe core & manual tab audit |
| **Bundle Size** | Frontend JS bundle | $< 250 \text{ KB}$ gzipped | Webpack/esbuild analyzer |

---

## 5. Security & Privacy Guarantees

1. **Client-Side Data Isolation:** Patient drafts and real medical complaints are never cached in unencrypted `localStorage` unless explicitly marked as synthetic demo data.
2. **Content Security Policy (CSP):** Strict nonce/hash script controls disallowing inline evaluations, unvetted external CDNs, or unsafe DOM injections.
3. **CSRF & Rate Limiting:** All state-changing endpoints enforce anti-CSRF token verification and sliding-window IP rate limiting (100 req/min for public APIs, 30 req/min for AI endpoints).
4. **Zero-Trust Clinical Advice:** All AI-generated healthcare suggestions feature mandatory medical disclaimers and require human clinician sign-off.
