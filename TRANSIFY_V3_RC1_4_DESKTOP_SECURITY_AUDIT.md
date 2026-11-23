# TRANSIFY V3 — RC1.4 DESKTOP WEBVIEW SECURITY AUDIT REPORT

**Project:** Transify V3  
**Package:** `com.abrarafick.transify`  
**Milestone:** RC1.4 Desktop Audit Correction & Evidence Reconciliation  
**Date:** November 23, 2026  
**Auditor:** Principal Mobile & Application Security Architect  
**Evaluated Environment:** Browser-based Chromium Desktop Testing (Playwright / Chromium 130.0.0.0, Linux x86_64)  
**Data Provenance:** Extracted programmatically from `TRANSIFY_V3_RC1_4_DESKTOP_VIEWPORT_MATRIX.json`  

---

## 1. Executive Summary & Audit Scope

This audit evaluates application security controls for Transify V3 across live production infrastructure (`https://transify20-production.up.railway.app`) and local desktop browser workstation environments.

```
+======================================================================================================+
| DESKTOP SECURITY AUDIT STATUS: RECONCILED WITH EMPIRICAL EVIDENCE                                    |
+======================================================================================================+
| • Live Production Probe: HTTP/2 200 OK via Railway Hikari Edge Proxy                                 |
| • Edge Security Headers: Missing Strict-Transport-Security (HSTS) and Content-Security-Policy (CSP)  |
| • Script-Src CSP Directives: 'unsafe-inline' is functionally required due to index.html inline logic  |
| • Authentication Token Transport: Dual emission (HttpOnly Cookie for Web + JSON token for Android)    |
| • Native Bridge IPC Security: NOT APPLICABLE / NOT TESTED (No desktop wrapper implemented)           |
| • Zero Auto-Audio Policy: VERIFIED ENFORCED (0 unprompted calls; explicit user click required)       |
+======================================================================================================+
```

---

## 2. Live Production Infrastructure Probe

A live HTTP probe against the production URL (`https://transify20-production.up.railway.app/`) captured empirical edge headers:

```http
HTTP/2 200
server: railway-hikari
content-type: text/html; charset=utf-8
date: Mon, 23 Nov 2026 06:28:04 GMT
vary: accept-encoding
x-railway-request-id: T88RfmLZToKC3KZnlt7tkg
x-railway-edge: sin1
```

### Critical Security Findings on Edge Proxy:
1. **Strict-Transport-Security (HSTS):** **ABSENT**. The Railway edge proxy terminates TLS but does not inject HSTS headers (`max-age=31536000; includeSubDomains; preload`). Previous reports claiming HSTS enforcement were inaccurate.
2. **Content-Security-Policy (CSP):** **ABSENT** on production edge responses.
3. **Missing Protective Headers:** strict-transport-security, content-security-policy, x-content-type-options, x-frame-options, referrer-policy, permissions-policy.
4. **Remediation Recommendation:** Configure custom middleware in `src/api/server.py` or Railway edge routing rules to inject HSTS, CSP, `X-Content-Type-Options: nosniff`, and `X-Frame-Options: DENY`.

---

## 3. Content Security Policy (CSP) & `unsafe-inline` Implications

- **Current Architecture Requirement:** Transify's frontend (`src/frontend/index.html`) relies on inline JavaScript blocks (lines 29–79 for auth modal open/close and routing helpers) and inline DOM event attributes (`onclick="event.stopPropagation()"`).
- **Security Implications:** When CSP is enforced, the `script-src` directive must explicitly allow `'unsafe-inline'` unless these blocks are refactored into external bundled scripts or assigned cryptographic sha256 nonces.
- **Risk Assessment:** While `'unsafe-inline'` broadens the theoretical XSS attack surface, all dynamic user text in Chat and Care is actively sanitized through DOMPurify and strictly escaped before DOM insertion. Refactoring inline scripts is logged as a Post-RC1 hardening item.

---

## 4. Authentication Session Handling & Dual-Token Emission

- **Dual-Token Architecture:** During user login (`POST /api/v1/auth/login`), the backend server executes two simultaneous actions:
  1. Sets an `HttpOnly`, `SameSite=Lax`, `Secure` cookie named `transify_session`.
  2. Returns the raw bearer token in the JSON response payload (`"token": "..."`).
- **Architectural Rationale:**
  - The `HttpOnly` cookie secures browser-based desktop sessions against JavaScript credential theft.
  - The JSON response token is **strictly required for Android mobile client compatibility** (`MainActivity.kt` and OkHttp client), which operates in an isolated native network context where cookies are not automatically shared across Android WebView and native background services.
- **Client Storage Hygiene:** Verified in `tests/test_care_security.py` that desktop browser code never stores the raw token in unencrypted persistent `localStorage`.

---

## 5. Native Desktop Bridge IPC Security

- **Status:** **NOT APPLICABLE / NOT TESTED**.
- **Evidence:** This repository does NOT contain an Electron main process (`ipcMain`/`ipcRenderer`), a Tauri Rust backend (`tauri::command`), a Windows WebView2 host object (`AddHostObjectToScript`), or a WebKitGTK extension.
- Testing is strictly performed in standard Chromium desktop browser contexts. No native desktop operating system APIs (raw filesystem, child process execution) are exposed to the DOM.

---

## 6. Zero Auto-Audio Policy Verification

- **Empirical Test Result:** **PASSED**.
- Unprompted audio playback attempts across all 10 views: **0**
- Unprompted speech synthesis attempts across all 10 views: **0**
- Explicit user button click speech attempts: **1**
- Enforces clinical acoustic safety in hospital and office environments.
