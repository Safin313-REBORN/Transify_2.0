# Transify 2.0 — Product Requirements Document (PRD)

**Project Name:** Transify 2.0  
**Tagline:** *Breaking Communication Barriers through Artificial Intelligence.*  
**Target Audience:** Individuals who are Deaf, hard-of-hearing, blind, visually impaired, non-verbal, and their families, educators, and healthcare providers.  
**Platform Scope:** Responsive Progressive Web Application (PWA), Native Android Client (WebView Bridge), and Headless REST/MCP API.  
**Version:** 2.0.0 (Production Ready)  
**Date:** November 19, 2026

---

## 1. Problem Statement & Market Need

Over 1.5 billion people globally live with hearing loss, and 2.2 billion people experience vision impairment. In Bangladesh and other South Asian regions, standardized assistive tools for regional sign languages (such as Bangladesh Sign Language — BdSL) and unified Braille (UEB Grade 1) are virtually non-existent or fragmented into commercial, privacy-invasive cloud silos.

Transify 2.0 addresses this systemic communication divide by delivering an accessible, privacy-preserving, zero-cloud-lock-in multi-modal communication platform that runs on consumer hardware.

---

## 2. Target User Personas

| Persona | Primary Needs | Key Transify Capabilities |
| :--- | :--- | :--- |
| **Afsana (Deaf / BdSL Native)** | Expressive communication in BdSL; wants text & speech translation for non-signing peers. | Real-time BdSL 10-Class Temporal Sign Translator, HaGRID ASL, visual feedback, Communication Hub. |
| **Rahim (Visually Impaired Student)** | Access printed Braille handouts and books; requires high-contrast tactile UI. | Optical Braille Recognition (UEB Grade 1 ICEB 2024), text reconstruction, manual TTS on demand. |
| **Tanvir (Non-Verbal Stroke Survivor)** | Quick conversational communication without physical strain or keyboard exhaustion. | Quick Phraseboard (Bilingual EN/BN), single-tap speech playback, customizable phrasebook. |
| **Dr. Nusrat (Caregiver / Educator)** | Monitor communication sessions across modalities; export clean records. | Multi-modal Communication Hub feed, session history filtering, zero-XSS chat transcript export. |

---

## 3. Functional Requirements (FR)

### FR-01: Live Hand Sign & Gesture Recognition
- **FR-01.1 (BdSL Temporal Sequences):** 10-Class temporal pipeline analyzing 30 consecutive video frames across dual-hand landmarks.
- **FR-01.2 (HaGRID ASL Communicative Gestures):** Real-time recognition of 24+ communicative gestures (`HELLO`, `THANK_YOU`, `HELP`, `YES`, `NO`, `CALL`, etc.).
- **FR-01.3 (Target Box Containment):** Hand landmarks outside the designated Camera Guide Box trigger an amber warning and reset temporal buffers to prevent spurious inference.
- **FR-01.4 (98% Decision Gateway):** Confidence $\ge 0.98$ resolves immediately (<15 ms). Ambiguous gestures ($< 0.98$) engage the MCP Disambiguation Agent.

### FR-02: Optical Braille Recognition (OBR - UEB Grade 1)
- **FR-02.1 (ICEB 2024 Standard):** Accurate 6-dot cell localization and decoding compliant with the **Rules of Unified English Braille (Third Edition, 2024)**.
- **FR-02.2 (Illumination Invariance):** Adaptive CLAHE contrast enhancement for shadowed, skewed, or uneven paper captures.
- **FR-02.3 (Output Actions):** Text display first, clipboard copy, formatted `.txt` download, and optional on-demand TTS.

### FR-03: Real-Time Speech-to-Text (STT)
- **FR-03.1:** Continuous microphone captioning supporting English (US/UK) and Bengali (`bn-BD`).
- **FR-03.2:** Visual concentric pulsing ring indicator during active recording state.

### FR-04: Natural Text-to-Speech (TTS) & Strict No-Auto-Audio Rule
- **FR-04.1:** Multi-lingual speech synthesis via native Web Speech API with pitch, speed, and volume controls.
- **FR-04.2 (Strict Non-Negotiable):** Audio playback NEVER starts automatically upon translation or transcription. The translated text must be rendered visually first; audio plays strictly upon an explicit user click on a speaker icon (`🔊`).

### FR-05: Accessible Communication Hub
- **FR-05.1:** Unified chronological feed combining Sign Language, Braille, Voice Captions, and typed messages.
- **FR-05.2:** Visual status badges clearly differentiating saved cloud records (`✓ Saved`), guest mode (`Temporary Guest`), and network retries (`⚠️ Unsaved`).
- **FR-05.3:** Safe DOM rendering using `textContent` and `replaceChildren` ensuring complete immunity against stored and DOM-based XSS attacks.

### FR-06: Quick Phraseboard
- **FR-06.1:** Categorized grid (General, Emergency, Daily Needs, Social) in English and Bengali.
- **FR-06.2:** Custom phrase addition, deletion, and favorite toggling scoped to authenticated accounts.

### FR-07: Production Authentication & Session Lifecycle
- **FR-07.1:** Argon2id password hashing (`time_cost=2`, `memory_cost=65536`) with transparent upgrade from PBKDF2 (600k iterations).
- **FR-07.2:** Secure, HttpOnly, SameSite=Lax cookie authentication. Raw tokens are never stored in `localStorage`.
- **FR-07.3:** Timing-decoupled password reset anti-enumeration via background worker dispatch, SHA-256 hashed single-use tokens, and URL fragment deep-linking (`#reset_token=`).
- **FR-07.4:** Mandatory explicit Terms of Service and Privacy Policy consent checkbox (`consent_terms: true`).

### FR-08: Model Context Protocol (MCP) & Autonomous Agents
- **FR-08.1:** RESTful `/api/mcp/sign-resolve` endpoint enabling AI agent systems to disambiguate multi-candidate gestures with motion energy and context hints.

---

## 4. Non-Functional Requirements (NFR)

- **NFR-01 (Latency):** Static gesture inference $\le 20\text{ ms}$; temporal BdSL inference $\le 45\text{ ms}$; MCP resolution $\le 1.8\text{ s}$.
- **NFR-02 (Accessibility):** WCAG 2.1 AAA compliance; all touch targets $\ge 48 \times 48\text{ px}$; contrast ratio $\ge 7:1$; full keyboard navigability with visible focus rings.
- **NFR-03 (Motion Comfort):** Strict `@media (prefers-reduced-motion: reduce)` and `body.reduced-motion` enforcement disabling all CSS keyframes and spring transforms.
- **NFR-04 (Security Perimeter):** Exact-Origin CSRF validation, persistent SQLite atomic rate limiting on sensitive endpoints, zero dynamic f-string SQL queries, and hardened security headers (HSTS, nosniff, SAMEORIGIN).
- **NFR-05 (Availability & Fault Isolation):** Decoupled AI modules; a failure in the Braille classifier does not degrade sign tracking or speech services.
- **NFR-06 (Disaster Recovery):** Automated zero-downtime online SQLite backups (`backup_db.py`) and verified restore/rollback tools (`restore_db.py`).
- **NFR-07 (SEO & Social Sharing):** Standards-compliant Open Graph tags for WhatsApp rich link previews (< 300KB image, HTTPS URL), `robots.txt`, and XML `sitemap.xml`.
- **NFR-08 (Zero External Cloud Dependency):** Complete offline execution capability on local consumer CPU without third-party API dependencies.

---

## 5. Acceptance Criteria

1. **Sign Language:** Recognizes 24+ HaGRID classes and 10 BdSL temporal classes with $>95\%$ test accuracy on heldout data.
2. **Braille Translation:** Successfully decodes 100% of standard ICEB 2024 uncontracted English Braille characters from test documents.
3. **Audio Safety:** Zero automatic audio playback in automated browser regression runs.
4. **Security Auditing:** Zero hardcoded API keys, zero unhashed passwords, zero SQL injection paths, zero IDOR leaks, and zero CSRF bypasses.
5. **Test Suite:** 100% passing across all 187 Pytest unit/integration tests, 19 Playwright browser tests, and Android unit tests.
