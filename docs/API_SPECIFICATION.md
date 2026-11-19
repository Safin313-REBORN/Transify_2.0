# Transify 2.0 — Unified API Specification

**Base URL (Production):** `https://transify20-production.up.railway.app`  
**Base URL (Local Development):** `http://localhost:8000`  
**Authentication:** Secure, HttpOnly `transify_session` Cookie  
**CSRF Protection:** Exact-Origin Header Validation + Double-Submit Token (`X-CSRF-Token` header / `transify_csrf` cookie)  
**Total Endpoints:** 49 Endpoints across 11 Functional Domains  
**Date:** November 19, 2026

---

## 1. Authentication & Security Headers

All state-changing requests (`POST`, `PUT`, `DELETE`, `PATCH`) require:
1. `Origin` or `Referer` matching trusted origins (`get_trusted_origins`).
2. Valid HttpOnly session cookie (`transify_session`) for protected endpoints.
3. Automated responses include:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: SAMEORIGIN`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (on HTTPS)

---

## 2. API Endpoints by Domain

### Domain 1: System Health & Monitoring
| Method | Path | Auth | Description |
| :--- | :--- | :-: | :--- |
| `GET` | `/api/health` | Public | Liveness probe; returns system version and uptime timestamp. |
| `GET` | `/api/ready` | Public | Readiness probe; verifies SQLite connectivity and AI models. |
| `GET` | `/api/models/status` | Public | Detailed AI model readiness breakdown (BdSL, HaGRID, Braille). |

### Domain 2: Authentication & Sessions
| Method | Path | Auth | Description |
| :--- | :--- | :-: | :--- |
| `POST` | `/api/auth/register` | Public | Registers a new account; enforces `consent_terms: true` and password $\ge 8$ chars. |
| `POST` | `/api/auth/login` | Public | Authenticates credentials; issues HttpOnly cookie and transparently upgrades to Argon2id. |
| `POST` | `/api/auth/forgot-password`| Public | Initiates password reset; background task delivery with anti-enumeration protection. |
| `POST` | `/api/auth/reset-password` | Public | Resets password using single-use SHA-256 token hash; invalidates all sessions. |
| `POST` | `/api/auth/guest` | Public | Creates an isolated temporary guest session. |
| `GET` | `/api/auth/me` | Public | Returns current authenticated user or `{ "authenticated": false }`. |
| `POST` | `/api/auth/logout` | Public | Revokes server session and clears client session cookies. |
| `GET` | `/api/auth/oauth/google/config` | Public | Returns Google OAuth configuration status (strictly disabled guard). |
| `GET` | `/api/auth/oauth/google/callback` | Public | Callback endpoint (strictly rejects unverified OAuth flows with HTTP 403). |

### Domain 3: Sign Language & Gesture Inference
| Method | Path | Auth | Description |
| :--- | :--- | :-: | :--- |
| `GET` | `/api/sign/classes` | Public | Returns 10-Class BdSL vocabulary labels and glosses. |
| `GET` | `/api/sign/hagrid/classes` | Public | Returns 24+ HaGRID ASL gesture labels. |
| `POST` | `/api/sign/predict` | Optional | Ingests 30-frame landmark sequences; executes 98% Decision Gateway. |
| `POST` | `/api/sign/process_frame` | Public | Processes live single webcam frame through MediaPipe. |
| `POST` | `/api/sign/reset` | Public | Clears the sliding landmark buffer and target box warnings. |
| `GET` | `/api/sign/categories` | Public | Returns categorized communicative domains (Emergency, Needs, Social). |
| `POST` | `/api/sign/fingerspell` | Public | Accumulates fingerspelling hand signs into words. |
| `POST` | `/api/sign/fingerspell/reset` | Public | Resets active fingerspelling buffer. |
| `POST` | `/api/sign/sentence/smooth` | Public | Reorders sign glosses into grammatically natural sentences. |
| `POST` | `/api/sign/sentence/reset` | Public | Clears accumulated sentence buffer. |

### Domain 4: Optical Braille Translation & TTS
| Method | Path | Auth | Description |
| :--- | :--- | :-: | :--- |
| `POST` | `/api/braille/translate` | Public | Uploads an embossed Braille image; runs ExtraTrees classifier & ICEB 2024 decoder. |

### Domain 5: Accessible Communication Hub
| Method | Path | Auth | Description |
| :--- | :--- | :-: | :--- |
| `GET` | `/api/hub/conversations` | Required | Lists active conversation sessions for the authenticated user. |
| `POST` | `/api/hub/conversations` | Required | Creates a new conversation session. |
| `GET` | `/api/hub/conversations/{id}/messages` | Required | Retrieves messages within a conversation (IDOR protected). |
| `POST` | `/api/hub/conversations/{id}/messages` | Required | Posts a new cross-modal message (Sign, Braille, Voice, Typed). |
| `DELETE`| `/api/hub/conversations/{id}` | Required | Deletes an entire conversation session and all its messages. |
| `POST` | `/api/hub/conversations/{id}/clear` | Required | Clears message history within an active session. |

### Domain 6: Quick Phraseboard
| Method | Path | Auth | Description |
| :--- | :--- | :-: | :--- |
| `GET` | `/api/phrases` | Optional | Retrieves preset and user-created custom phrases. |
| `POST` | `/api/phrases` | Required | Creates a new custom phrase (English & Bengali). |
| `POST` | `/api/phrases/{id}/favorite` | Required | Toggles favorite status on a phrase. |
| `DELETE`| `/api/phrases/{id}` | Required | Deletes a custom phrase (IDOR protected). |

### Domain 7: User Preferences & Customization
| Method | Path | Auth | Description |
| :--- | :--- | :-: | :--- |
| `GET` | `/api/preferences` | Optional | Reads user accessibility preferences (theme, font size, contrast, speed). |
| `POST` | `/api/preferences` | Required | Updates composite user preferences. |

### Domain 8: Translation History & Feedback
| Method | Path | Auth | Description |
| :--- | :--- | :-: | :--- |
| `GET` | `/api/history` | Optional | Lists recent translation history records. |
| `POST` | `/api/history/{id}/favorite` | Required | Toggles favorite status on a translation record. |
| `DELETE`| `/api/history` | Required | Clears user translation history. |
| `POST` | `/api/history/{id}/feedback` | Required | Submits user correction feedback on an inference result. |

### Domain 9: Benchmark Samples
| Method | Path | Auth | Description |
| :--- | :--- | :-: | :--- |
| `GET` | `/api/samples/sign/{name}` | Public | Returns sample landmark data for demonstration. |
| `GET` | `/api/samples/braille` | Public | Lists available benchmark Braille test images. |
| `GET` | `/api/samples/braille/{filename}`| Public | Serves test Braille image file. |

### Domain 10: Model Context Protocol (MCP) Tool
| Method | Path | Auth | Description |
| :--- | :--- | :-: | :--- |
| `POST` | `/api/mcp/sign-resolve` | Public | Agentic disambiguation tool; resolves ambiguous gesture candidates. |

### Domain 11: SEO Manifests & Frontend
| Method | Path | Auth | Description |
| :--- | :--- | :-: | :--- |
| `GET` | `/robots.txt` | Public | Crawling directives for search engines. |
| `GET` | `/sitemap.xml` | Public | XML sitemap with canonical page URLs. |
| `GET` | `/` | Public | Main application single-page canvas. |
| `GET` | `/login` | Public | Standalone login and registration page. |
| `GET` | `/dashboard` | Public | Central assistive dashboard. |
| `GET` | `/sign` | Public | Live Sign Language translator panel. |
| `GET` | `/braille` | Public | Optical Braille translator panel. |
