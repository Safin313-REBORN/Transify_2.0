# Roadmap: Transify 2.0 Production Hardening

## High-Level Milestones

- **Phase 1: Project Identity & Android JavaScript Bridge Security**
  - Verify project identity, remove insecure `addJavascriptInterface` fallback, harden AndroidX `WebMessageListener` with exact origin matching, main-frame restriction, payload size limits, and action allowlisting.

- **Phase 2: Confidence Integrity & Model Attribution**
  - Fix SpeechRecognizer confidence fallbacks (eliminate fabricated 1.0).
  - Eliminate fabricated 0.99/0.95 confidence scores in MCP sign/braille resolvers and frontend.
  - Decompose model status reporting into separate components (SignFrame, HaGRID, MediaPipe, Braille) with truthful metrics.

- **Phase 3: Healthcheck, Readiness & CORS Hardening**
  - Separate `/api/health` (process liveness) from `/api/ready` (production readiness with 503 on model/db failure).
  - Restrict CORS to explicit production origins + optional env var.
  - Update `railway.json` and `Dockerfile` to use `/api/ready`.
  - Truthful startup banner and documentation updates.

- **Phase 4: Comprehensive Test Suite & Verification**
  - Backend pytest regression suite covering `/api/ready`, model attribution, CORS, and confidence integrity.
  - Android unit test suite (`./gradlew testDebugUnitTest`).
  - Android debug APK assembly with production URL.

- **Phase 5: Git Push, Railway Redeploy & Live Production Verification**
  - Stage, commit, and push verified changes to `origin/main`.
  - Trigger and monitor Railway deployment to `SUCCESS`.
  - Validate live HTTPS production endpoints (`/`, `/api/health`, `/api/ready`, `/api/models/status`).
  - Final Android APK generation and delivery.
