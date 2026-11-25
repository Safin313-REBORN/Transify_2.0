# Transify 2.0 System Architecture Specification (V2)

**Document Version:** 2.0.0  
**Status:** Approved & Implemented  
**Author:** Team Alpha Nexus  
**Last Updated:** 2026-11-25  
**Runtime Platform:** Linux (x86_64), Python 3.11, FastAPI, Vanilla Modern ES6+, SQLite 3  

---

## 1. High-Level System Architecture Diagram

```
+----------------------------------------------------------------------------------------------------+
|                                         CLIENT BROWSER (EDGE / PWA)                                |
|                                                                                                    |
|  +--------------------+  +----------------------+  +---------------------+  +-------------------+  |
|  |  Sign Translation  |  | Optical Braille (OBR)|  | Neural Voice & TTS  |  | Transify Care CDS |  |
|  |  MediaPipe Hands   |  | 6-Dot Matrix Canvas  |  | Captions & Stt     |  | Triage & Insulin  |  |
|  +---------+----------+  +----------+-----------+  +----------+----------+  +---------+---------+  |
|            |                        |                         |                       |            |
|  +---------+------------------------+-------------------------+-----------------------+---------+  |
|  |           Client Runtime Core: Zero Auto-Audio Privacy Guard, Offline Service Worker         |  |
|  |           WCAG 2.1 AAA Accessibility Layer, Dark/Light Theming, Keyboard Trap Focus          |  |
|  +----------------------------------------------+-----------------------------------------------+  |
+-------------------------------------------------|--------------------------------------------------+
                                                  | HTTPS / WSS / JSON-RPC
                                                  v
+----------------------------------------------------------------------------------------------------+
|                                    TRANSIFY FASTAPI BACKEND SERVER                                 |
|                                                                                                    |
|  +-------------------------+  +--------------------------+  +-----------------------------------+  |
|  |   API Gateway & CSP     |  |  Session & CSRF Guard    |  |       Rate Limiting & Telemetry   |  |
|  +------------+------------+  +------------+-------------+  +-----------------+-----------------+  |
|               |                            |                                  |                    |
|  +------------v----------------------------v----------------------------------v-----------------+  |
|  |                                APPLICATION & ROUTING LAYER                                   |  |
|  |  - /api/v1/sign/*       : WebSocket & REST Sign Recognition (BdSL, ASL)                       |  |
|  |  - /api/v1/braille/*    : Image OCR & UEB Grade 1 / Bharati Bengali Translation               |  |
|  |  - /api/care/triage     : 5-Tier Clinical Triage Matrix (WHO, MIMIC-IV)                       |  |
|  |  - /api/care/insulin    : Bolus Calculator, Meal Analysis & Hypoglycemia Guards               |  |
|  |  - /api/care/polypharm  : Drug-Drug Interaction Screen (OpenFDA, ChEMBL)                      |  |
|  |  - /api/mcp, /mcp       : Model Context Protocol (MCP v1.0 / JSON-RPC 2.0 Engine)            |  |
|  +------------+----------------------------+----------------------------------+-----------------+  |
|               |                            |                                  |                    |
|  +------------v------------+  +------------v-------------+  +-----------------v-----------------+  |
|  |     DOMAIN ENGINES      |  |    EXTERNAL SERVICES     |  |      PERSISTENCE LAYER (SQLITE)   |  |
|  | - Sign Translation Net  |  | - OpenFDA Adverse Events |  | - data/transify.db (Immutable     |  |
|  | - Braille Dot Clusterer |  | - ChEMBL Bioactivities   |  |   hash: 9e5ec945a0450f87705c...) |  |
|  | - Triage Clinical Rule  |  | - Zipline Drone Dispatch |  | - Audit Trail Tables             |  |
|  | - Assistive Chatbot Rag |  | - OpenStreetMap Facilities| - Telemetry & Interaction Logs      |  |
|  +-------------------------+  +--------------------------+  +-----------------------------------+  |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Layered Component Decomposition

### 2.1 Presentation & Client Runtime Layer
- **HTML5/ES6+ Architecture:** Modular architecture without heavy frontend build tool overhead, guaranteeing instantaneous page rendering and zero hydration delays.
- **Strict Content Security Policy (CSP):** Enforced via HTTP headers `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; ...`.
- **Zero Auto-Audio Enforcement:** Browser Web Audio API and SpeechSynthesis are wrapped in explicit user gesture checks (`isUserGestureActive()`). Direct background audio invocation throws runtime exceptions and logs privacy violations.

### 2.2 Model Context Protocol (MCP) Server Layer
- **Specification:** Compliant with Model Context Protocol (MCP) v1.0 standard.
- **Transports:** HTTP POST with JSON-RPC 2.0 envelopes at `/api/mcp` and `/mcp`.
- **RPC Methods Supported:**
  - `initialize`: Protocol negotiation, returns server capabilities and metadata (`transify-care-mcp`, v2.0.0).
  - `tools/list`: Dynamic discovery returning JSON Schema representations for all exposed clinical tools.
  - `tools/call`: Executes sandboxed domain methods (`resolve_sign_ambiguity`, `resolve_braille_ambiguity`, `triage_symptom`, `calculate_insulin_correction`, `check_polypharmacy`, `chat_assistive_agent`).
  - `ping`: Health verification.

### 2.3 Domain Services & Clinical Engine
- **Clinical Triage Service (`src/care/triage.py`):** Multi-factorial acuity evaluation mapping chief complaints against Manchester/Emergency Severity Index (ESI) standards. Red-flag logic overrides confidence bounds to guarantee patient safety.
- **Diabetic Chronic Care Service (`src/care/chronic_care.py`):** Calculates bolus units:
  $$\text{Bolus} = \left(\frac{\text{Carbs}}{\text{CIR}}\right) + \left(\frac{\text{BG} - \text{Target}}{\text{ISF}}\right) - \text{IOB}$$
  Includes hard caps at $\le 15 \text{ units}$ without confirmed clinician sign-off.
- **Polypharmacy & Safety Engine (`src/care/clinical_evidence.py`):** Caches OpenFDA and ChEMBL query vectors to perform offline-resilient contraindication warnings.

### 2.4 Persistence Layer
- **Primary Store:** SQLite 3 database at `data/transify.db`.
- **Integrity Invariant:** Cryptographic SHA-256 checksum:
  `9e5ec945a0450f87705c3702790da675777f7eef3d64e1dfe64221c99e097cac`.
  This file remains immutable during runtime tests and migrations to ensure zero database corruption across deploy cycles.

---

## 3. Communication Protocols & Interfaces

| Protocol | Endpoint | Message Format | Purpose |
| :--- | :--- | :--- | :--- |
| **HTTP REST** | `/api/v1/braille/translate` | JSON (base64 image) | Optical Braille Recognition |
| **HTTP REST** | `/api/care/triage` | JSON payload | Clinical symptom risk scoring |
| **HTTP REST** | `/api/care/insulin` | JSON payload | Carbohydrate and blood glucose bolus titration |
| **WebSocket** | `/ws/sign` | Binary / JSON frame | Continuous streaming sign gesture landmarks |
| **JSON-RPC 2.0** | `/api/mcp` | MCP Envelope | Multi-agent tool execution and context injection |
| **HTTP REST** | `/api/health` | JSON status | Production monitoring and Railway container liveness |
