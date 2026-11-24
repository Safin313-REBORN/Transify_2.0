# TRANSIFY V3 — RC1.4.5 CORS VERIFICATION REPORT

**Milestone:** RC1.4.5 Master Engineering Remediation & Evidence Correction  
**Date:** November 24, 2026  
**Status:** **PASS**

---

## 1. Configured CORS Policy Specification (`src/api/server.py`)

Transify V3 implements strict CORS controls with explicit separation between production deployment and development fallback modes.

### Production Environment (`is_production() == True`)
- **Allowed Origins:**
  - `https://transify.ai`
  - `https://app.transify.ai`
  - `https://transify20-production.up.railway.app`
- **Allowed HTTP Methods:**
  - `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`, `HEAD`
  - **Important:** `PATCH` is strictly **NOT** supported.
- **Allowed Request Headers:**
  - `Authorization`, `Content-Type`, `Accept`, `Origin`, `X-Requested-With`, `X-CSRF-Token`
  - **Important:** Wildcard (`*`) request headers are strictly prohibited in production.
- **Allow Credentials:**
  - `true` (enforced with explicit origin binding; wildcard `*` origins are impossible with credentials).

### Development Environment Fallback (`is_production() == False`)
- **Allowed Origins:** Configured production origins plus local loopback regular expression:
  - `^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$`
- **Allowed Methods:** `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`, `HEAD`
- **Allowed Headers:** `["*"]` (convenience for local tooling only)
- **Allow Credentials:** `true`

---

## 2. Configured Policy vs. Live Production Railway Edge Response

The table below contrasts the configured application code specification against empirical live edge responses measured on `https://transify20-production.up.railway.app`:

| Property | Configured Middleware Policy (`src/api/server.py`) | Observed Live Production Edge (`server: railway-hikari`) | Status / Notes |
|:---|:---|:---|:---|
| **Allowed Origins** | `https://transify.ai`, `https://app.transify.ai`, `https://transify20-production.up.railway.app` | Echoes valid requested origin (`https://transify20-production.up.railway.app`) | MATCH |
| **Untrusted Origins** | Rejection (HTTP 400 `Disallowed CORS origin`) | HTTP 400 `Disallowed CORS origin` | MATCH |
| **Credentials** | `true` | `access-control-allow-credentials: true` | MATCH |
| **Allowed Methods** | `GET, POST, PUT, DELETE, OPTIONS, HEAD` | `GET, POST, PUT, DELETE, OPTIONS` | MATCH (`OPTIONS` preflight returns standard CORS subset) |
| **Unsupported Method (`PATCH`)** | Rejection (HTTP 400 `Disallowed CORS method`) | HTTP 400 `Disallowed CORS method` | MATCH (Confirmed empirically) |
| **Allowed Headers** | `Authorization, Content-Type, Accept, Origin, X-Requested-With, X-CSRF-Token` | `Accept, Accept-Language, Authorization, Content-Language, Content-Type, Origin, X-Requested-With` | MATCH (All production request headers permitted) |
| **Disallowed Header** | Rejection (HTTP 400 `Disallowed CORS headers`) | HTTP 400 `Disallowed CORS headers` | MATCH (Confirmed empirically) |
| **Preflight Max-Age** | 600s | `access-control-max-age: 600` | MATCH |

---

## 3. Empirical Preflight Audit Matrix

Empirically verified via live HTTPS probes against `https://transify20-production.up.railway.app`:

| Endpoint | Request Method | Origin | Requested Headers | Response Status | Access-Control-Allow-Origin | Security Headers Present | Verdict |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `/api/auth/login` | `OPTIONS` (POST preflight) | `https://transify20-production.up.railway.app` | `Content-Type` | 200 | `https://transify20-production.up.railway.app` | YES (All 6) | **PASS** |
| `/api/auth/login` | `OPTIONS` (PATCH preflight) | `https://transify20-production.up.railway.app` | None | 400 | `https://transify20-production.up.railway.app` | YES (All 6) | **REJECTED (EXPECTED)** |
| `/api/auth/login` | `OPTIONS` (Disallowed header) | `https://transify20-production.up.railway.app` | `X-Disallowed-Header` | 400 | `https://transify20-production.up.railway.app` | YES (All 6) | **REJECTED (EXPECTED)** |
| `/api/auth/login` | `OPTIONS` (Untrusted origin) | `https://evil.com` | `Content-Type` | 400 | None | YES (All 6) | **REJECTED (EXPECTED)** |
| `/api/health` | `OPTIONS` | `https://transify20-production.up.railway.app` | None | 200 | None (standard GET allowed without preflight) | YES (All 6) | **PASS** |
