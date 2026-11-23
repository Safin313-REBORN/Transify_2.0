# TRANSIFY V3 — RC1.4.4 CONTENT SECURITY POLICY COMPATIBILITY REPORT

**Project:** Transify V3  
**Evaluator:** Principal Application Security Architect  
**Milestone:** RC1.4.4 Production Security Verification  
**Enforced Header:** `Content-Security-Policy`  
**Timestamp:** 2026-11-23T16:40:27.122076+00:00  
**Verdict:** **PASSED (COMPATIBILITY VERIFIED WITH ZERO APPLICATION REGRESSIONS)**

---

## 1. Enforced Policy Directives

```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob:; media-src 'self' blob: data:; connect-src 'self' https://transify20-production.up.railway.app; frame-ancestors 'none'; base-uri 'self'; form-action 'self';
```

---

## 2. Directive Rationale & Application Dependency Analysis

| Directive | Allowed Sources | Legitimate Application Dependency |
| :--- | :--- | :--- |
| `default-src` | `'self'` | Fallback default restricting unclassified resources to the application origin. |
| `script-src` | `'self' 'unsafe-inline'` | Required for inline boot/auth script blocks (`index.html`) and 108 inline DOM event handlers (`onclick`). Refactoring roadmap detailed below. |
| `style-src` | `'self' 'unsafe-inline' https://fonts.googleapis.com` | Loads Google Fonts stylesheet link and component inline style attributes. |
| `font-src` | `'self' https://fonts.gstatic.com data:` | Downloads Google Fonts binary files (`Outfit`, `Plus Jakarta Sans`, `Hind Siliguri`) and inline data URIs. |
| `img-src` | `'self' data: blob:` | Required for SVG icons in styles, canvas snapshot frames, and Braille OCR file previews (`URL.createObjectURL(file)`). |
| `media-src` | `'self' blob: data:` | Required for Web Audio API PCM buffers, offline synthetic TTS playback, and speech recording audio playback. |
| `connect-src` | `'self' https://transify20-production.up.railway.app` | Required for REST API calls (`/api/auth/*`, `/api/care/*`, `/api/translate/*`). |
| `frame-ancestors` | `'none'` | Forbids framing by any site, including same-origin, to guarantee complete clickjacking immunity. |
| `base-uri` | `'self'` | Restricts `<base>` tag injection attacks. |
| `form-action` | `'self'` | Enforces form submissions strictly to same-origin. |

---

## 3. Playwright Automated Browser Regression Evidence

Automated Playwright browser tests in `tests/test_csp_browser_regression.py` verified the policy against a live headless Chromium instance:

1. `test_csp_no_unexpected_violations`: **PASSED** (0 `securitypolicyviolation` events recorded during full page boot and route navigation).
2. `test_csp_blocks_unauthorized_external_script`: **PASSED** (Synthetic injection of `<script src="https://evil-attacker.com/malicious.js">` was blocked by the browser and triggered a `securitypolicyviolation` event).
3. `test_permissions_policy_allows_camera_and_mic_for_self`: **PASSED** (Browser confirmed permissions API grants camera and microphone to the application origin).
4. `test_csp_allows_braille_blob_and_data_urls`: **PASSED** (Blob image preview loads successfully without CSP image blocks).
5. `test_csp_api_connectivity_under_connect_src`: **PASSED** (Fetch calls to `/api/health` succeed under `connect-src 'self'`).

---

## 4. Staged Migration Plan for `'unsafe-inline'` Elimination

While `'unsafe-inline'` is currently necessary to preserve the functionality of 108 inline `onclick` event attributes and the authentication boot script in `src/frontend/index.html`, Transify has established a 3-stage migration plan:

- **Stage A (Completed):** Scoped compatibility CSP deployed and verified. Input sanitization with DOMPurify active on all user content.
- **Stage B (Planned RC2.0):** Refactor inline event handlers (`onclick="showView('sign')"`) into declarative `data-route="sign"` attributes with centralized event delegation in `src/frontend/static/app.js`.
- **Stage C (Planned RC2.1):** Transition to strict CSP with dynamic per-response cryptographic nonces (`script-src 'self' 'nonce-...'`).
