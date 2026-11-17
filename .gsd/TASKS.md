# Task Backlog: Transify 2.0 Hardening

## Phase 1: Android Security & JavaScript Bridge Hardening
- [x] Task 1.1: Audit `MainActivity.kt` and remove insecure `registerFallbackJavascriptInterfaces()` and `addJavascriptInterface` fallback `[Done]`
- [x] Task 1.2: Harden AndroidX `WebMessageListener` implementation with strict exact-origin checks, `isMainFrame` check, payload limit, action allowlist, and graceful UI degradation on unsupported WebViews `[Done]`
- [x] Task 1.3: Audit and update Android unit tests for `MainActivity` / bridge security `[Done]`

## Phase 2: Confidence Integrity & Model Attribution
- [x] Task 2.1: Remove fabricated 1.0 speech confidence fallback in `TransifySpeechBridge.kt` and `src/frontend/static/app.js` `[Done]`
- [x] Task 2.2: Remove fabricated 0.99/0.95 confidence values across `src/sign/mcp_sign_resolver.py`, `src/braille/mcp_chatbot_resolver.py`, `src/api/sign_adapter.py`, `src/api/braille_adapter.py`, and `src/frontend/static/app.js` `[Done]`
- [x] Task 2.3: Deconstruct `/api/models/status` into separate components (SignFrame ASL, HaGRID, MediaPipe, Braille) with truthful metrics in `src/api/server.py` `[Done]`

## Phase 3: Healthcheck, Readiness, CORS & Startup Hardening
- [x] Task 3.1: Implement separate `/api/health` (liveness: 200) and `/api/ready` (readiness: 200/503) endpoints in `src/api/server.py` `[Done]`
- [x] Task 3.2: Restrict CORS middleware to exact production origin `https://transify20-production.up.railway.app` and dev mode localhost in `src/api/server.py` `[Done]`
- [x] Task 3.3: Update `railway.json` and `Dockerfile` to use `/api/ready` for healthchecks `[Done]`
- [x] Task 3.4: Remove hardcoded accuracy claims from startup banner in `run_server.py` and truthful documentation updates in `README.md` and `Panel/` `[Done]`

## Phase 4: Verification & Automated Tests
- [x] Task 4.1: Add backend unit and integration tests in `tests/test_full_system.py` for `/api/ready` (200 & 503), CORS, model attribution, and confidence handling `[Done]`
- [x] Task 4.2: Execute `python -m compileall src run_server.py` and `pytest tests/` `[Done]`
- [x] Task 4.3: Execute Android tests `./gradlew testDebugUnitTest` and assemble debug APK `[Done]`

## Phase 5: Git Push, Railway Redeployment & Production Verification
- [ ] Task 5.1: Review diffs, stage verified source files, and commit to `main` `[Pending]`
- [ ] Task 5.2: Push commit to GitHub `origin/main` `[Pending]`
- [ ] Task 5.3: Trigger Railway redeploy and monitor build and container logs to `SUCCESS` `[Pending]`
- [ ] Task 5.4: Verify live endpoints on `https://transify20-production.up.railway.app` (`/`, `/api/health`, `/api/ready`, `/api/models/status`) `[Pending]`
- [ ] Task 5.5: Build final verified Android APK and compile final 20-point report `[Pending]`
