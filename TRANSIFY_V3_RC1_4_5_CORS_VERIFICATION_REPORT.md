# TRANSIFY V3 — RC1.4.5 CORS VERIFICATION REPORT

**Milestone:** RC1.4.5.3.1 Final CORS Evidence & PR Metadata Cleanup  
**Date:** November 24, 2026  
**Status:** **PASS (SOURCE POLICY VERIFIED / PRODUCTION DEPLOYMENT PENDING)**

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
  - **Important:** Wildcard (`*`) request headers are strictly prohibited and rejected in production validation.
- **Allow Credentials:**
  - `true` (enforced with explicit origin binding; wildcard `*` origins are impossible with credentials).

### Development Environment Fallback (`is_production() == False`)
- **Allowed Origins:** Configured production origins plus local loopback regular expression:
  - `^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$`
- **Allowed Methods:** `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`, `HEAD`
- **Allowed Headers:** `["*"]` (convenience for local tooling only)
- **Allow Credentials:** `true`

---

## 2. Configured Policy vs. Observed Live Production Railway Edge Response

The table below contrasts the configured branch specification against empirical live edge responses measured on `https://transify20-production.up.railway.app`:

| Property | Configured Branch Policy (`src/api/server.py`) | Observed Current Railway Policy (`server: railway-hikari`) | Status / Deployment State |
|:---|:---|:---|:---|
| **Allowed Origins** | `https://transify.ai`, `https://app.transify.ai`, `https://transify20-production.up.railway.app` | Echoes valid requested origin (`https://transify20-production.up.railway.app`, `https://transify.ai`) | **MATCH** |
| **Untrusted Origins** | Rejection (HTTP 400 `Disallowed CORS origin`) | HTTP 400 `Disallowed CORS origin` | **MATCH** |
| **Credentials** | `true` | `access-control-allow-credentials: true` | **MATCH** |
| **Allowed Methods** | `GET, POST, PUT, DELETE, OPTIONS, HEAD` | `GET, POST, PUT, DELETE, OPTIONS` | **PARTIAL MATCH** (`HEAD` is verified in branch tests; unverified on live edge pending release deployment) |
| **Unsupported Method (`PATCH`)** | Rejection (HTTP 400 `Disallowed CORS method`) | HTTP 400 `Disallowed CORS method` | **MATCH** (Empirically verified) |
| **Allowed Headers** | `Authorization, Content-Type, Accept, Origin, X-Requested-With, X-CSRF-Token` | `Accept, Accept-Language, Authorization, Content-Language, Content-Type, Origin, X-Requested-With` | **PARTIAL MATCH** (`X-CSRF-Token` is verified in branch tests; unverified on live edge pending release deployment) |
| **Disallowed Header** | Rejection (HTTP 400 `Disallowed CORS headers`) | HTTP 400 `Disallowed CORS headers` | **MATCH** (Empirically verified) |
| **Preflight Max-Age** | 600s | `access-control-max-age: 600` | **MATCH** |

---

## 3. Empirical Preflight & Control Audit Matrix

Empirically verified via live HTTPS probes against `https://transify20-production.up.railway.app` and in-memory branch verification:

### A. Live Production Edge Probes (`https://transify20-production.up.railway.app`)

| Type | Endpoint | Sent Method / Headers | Sent Origin | Status | Captured Response Body | Observed Access-Control Headers | Verdict |
|:---|:---|:---|:---|:---:|:---|:---|:---:|
| **Positive CORS Preflight** | `/api/auth/login` | `POST` / `Content-Type` | `https://transify20-production.up.railway.app` | 200 | (empty) | Allow-Origin: prod URL, Allow-Methods: 5 methods, Credentials: true | **PASS** |
| **Positive CORS Preflight** | `/login` (SPA) | `GET` / `Content-Type` | `https://transify20-production.up.railway.app` | 200 | (empty) | Allow-Origin: prod URL, Allow-Methods: 5 methods, Credentials: true | **PASS** |
| **Negative Rejection (Method)** | `/api/auth/login` | `PATCH` / `Content-Type` | `https://transify20-production.up.railway.app` | 400 | `Disallowed CORS method` | Allow-Origin: None, Rejected | **REJECTED (EXPECTED)** |
| **Negative Rejection (Header)** | `/api/auth/login` | `POST` / `X-Disallowed-Custom-Header` | `https://transify20-production.up.railway.app` | 400 | `Disallowed CORS headers` | Allow-Origin: None, Rejected | **REJECTED (EXPECTED)** |
| **Negative Rejection (Origin)** | `/api/auth/login` | `POST` / `Content-Type` | `https://untrusted-attacker-origin.example.com` | 400 | `Disallowed CORS origin` | Allow-Origin: None, Rejected | **REJECTED (EXPECTED)** |
| **Plain OPTIONS Control** | `/api/health` | (Plain OPTIONS, no CORS headers) | None | 405 | `{"detail":"Method Not Allowed"}` | Allow: GET. Not a CORS preflight. | **CONTROL VERIFIED** |

### B. In-Memory Branch Verification (`src/api/server.py` Production Policy)

| Type | Endpoint | Sent Method / Headers | Sent Origin | Status | Result / Allowed Values | Verdict |
|:---|:---|:---|:---|:---:|:---|:---:|
| **Branch Positive Probe** | `/api/auth/login` | `HEAD` preflight | `https://transify.ai` | 200 | `Access-Control-Allow-Methods` includes `HEAD` | **PASS (VERIFIED IN BRANCH)** |
| **Branch Positive Probe** | `/api/auth/login` | `POST` / `X-CSRF-Token` | `https://transify.ai` | 200 | `Access-Control-Allow-Headers` includes `X-CSRF-Token`, zero wildcard `*` | **PASS (VERIFIED IN BRANCH)** |

---

## 4. Expected State After Release Deployment

Following the merge of PR #1 and subsequent automated deployment to Railway:
1. `HEAD` method support in CORS preflights will be active across all production origins.
2. `X-CSRF-Token` header support in CORS preflights will be active across all production origins.
3. Content-Security-Policy will strictly enforce `script-src 'self'` without legacy `'unsafe-inline'`.
