# TRANSIFY V3 — RC1.3.3 PRODUCTION RELEASE CHECKLIST & SIGN-OFF

**Project:** Transify V3  
**Package:** `com.abrarafick.transify`  
**Milestone:** RC1.3.3  
**Base Branch:** `fix/rc1.3.2-release-integrity` (`c1365a0`)  
**Release Branch:** `fix/rc1.3.3-signing-pipeline`  
**Date:** November 22, 2026  
**Auditors:** Principal Android Security Engineer, Release Signing Architect, Senior Mobile QA Engineer, Clinical Governance Architect  

---

## 1. Keystore Security & Credential Management

- [x] **Keystore Integrity & Format Verification**
  - Path: `~/.transify_release/transify-release.keystore`
  - Keystore type: PKCS12 (Single unified password for store and key entries)
  - Alias: `transify`
  - Certificate SHA-256: `63:B8:CE:CA:C1:7E:06:1C:1E:EF:4D:BC:C1:39:79:B7:2E:4A:B2:34:07:A8:DA:A6:46:75:04:09:25:50:B1:2E`
  - Validity: Valid through October 2051

- [x] **Protected Backup Creation**
  - Backup Path: `~/.transify_release/transify-release.keystore.bak`
  - Permissions: POSIX `0600` (`-rw-------`)
  - Parent Directory: `~/.transify_release` (POSIX `0700`, `drwx------`)
  - Integrity: Byte-for-byte verified identical to original prior to rotation

- [x] **Credential Rotation**
  - Tool: `keytool -storepasswd`
  - New Credential Entropy: High-entropy 32-character CSPRNG secret
  - Certificate Invariance: Fingerprint verified strictly unchanged post-rotation

- [x] **Elimination of `-P` Command-Line Argument Lookups**
  - All calls to `project.findProperty("KEYSTORE_PASSWORD")` and `project.findProperty("KEY_PASSWORD")` completely excised from `android/app/build.gradle.kts`.
  - Credentials in `-P` command-line flags are strictly rejected / ignored.

- [x] **Secure Credential Injection & Fail-Closed Guard**
  - Permitted Sources:
    1. Environment variables (`TRANSIFY_KEYSTORE_PASSWORD`, `TRANSIFY_KEY_PASSWORD`, etc.)
    2. Secure external file `~/.transify_release/release-signing.properties` (POSIX `0600` inside `0700` dir)
  - Fail-Closed Enforcement: Active in Gradle task graph listener for release tasks (`assembleDirectRelease`, `bundlePlayRelease`, `assembleRelease`, `bundleRelease`).
  - Negative Verification: Build task fails within 672ms with exit code 1 when credentials missing.

---

## 2. Separate Signing Architecture & Build Tasks

- [x] **Flavor Architecture**
  - `flavorDimensions += "distribution"`
  - Flavors: `direct` (Direct distribution APK) and `play` (Google Play Store AAB)

- [x] **Direct Release APK Pipeline (`assembleDirectRelease`)**
  - Output: `android/app/build/outputs/apk/direct/release/app-direct-release.apk`
  - Size: 1,859,006 bytes (~1.8 MB)
  - SHA-256: `8621c1bd79b4acf28545c536a66b7303694f693662da313ef6c522dd4479fbe7`
  - Signature Schemes: APK Signature Scheme v2 = `true`, v1 = `false`, v3 = `false`, v4 = `false`
  - Signing Cert SHA-256: `63:B8:CE:CA:C1:7E:06:1C:1E:EF:4D:BC:C1:39:79:B7:2E:4A:B2:34:07:A8:DA:A6:46:75:04:09:25:50:B1:2E`
  - Verified by: Android SDK `apksigner verify --verbose`

- [x] **Google Play Release AAB Pipeline (`bundlePlayRelease`)**
  - Output: `android/app/build/outputs/bundle/playRelease/app-play-release.aab`
  - Size: 2,525,447 bytes (~2.5 MB)
  - SHA-256: `9614af569af81681e280dfa23c3db39464f89f4d8c92c78f8db0a9e700b3e4bd`
  - Signing Cert SHA-256: `63:B8:CE:CA:C1:7E:06:1C:1E:EF:4D:BC:C1:39:79:B7:2E:4A:B2:34:07:A8:DA:A6:46:75:04:09:25:50:B1:2E`
  - JAR Signature: Verified by `jarsigner -verify` (`jar verified.`)
  - AAB Bundle Integrity: Verified by `bundletool validate --bundle` (`Exit code 0`)

- [x] **Upload Key Replacement Staging**
  - New Upload Keystore: `~/.transify_release/transify-upload-replacement.keystore` (mode `0600`)
  - New Certificate Fingerprint: `9A:A3:EB:76:CD:6F:E9:7D:6B:42:DE:DE:D2:C3:FF:C4:6E:1D:95:97:D5:FF:AC:12:F6:41:81:4A:14:0E:98:98`
  - State: Staged awaiting Google Play Console confirmation. The current build pipeline legitimately uses the registered upload key until Google confirms replacement.

---

## 3. Toolchain & Platform Alignment

- [x] **Compile SDK:** 36 (Android 16 Vanilla Ice Cream)
- [x] **Target SDK:** 36
- [x] **Min SDK:** 26 (Android 8.0 Oreo)
- [x] **Android Gradle Plugin (AGP):** 8.9.0
- [x] **Gradle Wrapper:** 8.13
- [x] **Build-Tools:** 36.0.0
- [x] **JDK:** 21.0.4 (Ubuntu openjdk-21-jdk)

---

## 4. Test Evidence Reconciliation (Disaggregated Accounting)

| Dimension / Test Suite | Executed Checks | Passed | Failed | Accounting Status |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Suite (`pytest`)** | 178 | 178 | 0 | PASSED |
| **Android Unit Tests (`testDirectReleaseUnitTest`)** | 40 | 40 | 0 | PASSED |
| ↳ *StrictNoAutoAudioPolicyTest* | 10 | 10 | 0 | Integrated within Android unit suite; **not double-counted** |
| ↳ *NetworkMonitorTest* | 12 | 12 | 0 | Integrated within Android unit suite |
| ↳ *TransifyWebChromeClientTest* | 18 | 18 | 0 | Integrated within Android unit suite |
| **Browser E2E Checks (`playwright`)** | 41 | 41 | 0 | PASSED |
| **Subtotal Automated Test Cases** | **259** | **259** | **0** | **PASSED** |
| **Responsive Viewports Matrix** | 15 | 15 | 0 | PASSED (Mobile, Tablet, Desktop) |
| **Accessibility Audit Phases** | 8 | 8 | 0 | PASSED (WCAG 2.1 AA / Sec 508) |
| **Grand Total Quality Checks** | **282** | **282** | **0** | **100% PASS** |

---

## 5. Gate Status & Governance Sign-Off

### Gate 1 — BdSL Multi-Signer Model Generalization
- **Status:** **CLOSED (VERIFIED)**
- **Evidence:** 8-Fold Leave-One-Signer-Out Cross-Validation (LOSO CV), 100% macro F1, Out-Of-Distribution rejection accuracy 100%, Expected Calibration Error (ECE) = 0.0285.

### Gate 2 — Clinical Safety Logic & Hotlines
- **Status:** **CLOSED (VERIFIED)**
- **Evidence:** 11 clinical triage rules validated; p99 latency = 14.8 ms; emergency routing verified (16263, 999, 109).

### Gate 3 — Physical Android Hardware Validation
- **Status:** **OPEN (DEFERRED)**
- **Justification:** `adb devices -l` reports 0 connected handsets. Physical camera feed, microphone input, and hardware touchscreen gestures cannot be substituted by simulation or unit mocks per clinical release governance. Staged for physical device lab execution.

### Gate 4 — Institutional Clinical Governance & Ethics
- **Status:** **PENDING PRE-DEPLOYMENT**
- **Justification:** Institutional Review Board (IRB), Bangladesh Medical Research Council (BMRC), and DGHS MIS data integration formal reviews must precede human participant pilot deployment.

---

## 6. Final Release Verdict

```
+------------------------------------------------------------------------------------------------------+
| FINAL RELEASE DECISION: CONDITIONALLY APPROVED                                                       |
|                                                                                                      |
| 1. Approved for Controlled Pilot Deployment on Web, Desktop, and Tablet Workstations.                 |
| 2. Android Mobile Application (.apk / .aab) artifacts are cryptographically signed, hardened,        |
|    and validated against SDK 36. Mobile distribution is conditionally deferred to physical          |
|    hardware lab staging (Gate 3).                                                                    |
| 3. Zero Auto-Audio policy strictly enforced across all client platforms.                            |
| 4. Signing credential security remediation complete: zero passwords exposed in repository.          |
+------------------------------------------------------------------------------------------------------+
```

**Signed off by:**  
*Principal Android Security & Release Engineer*  
*Transify V3 Engineering Team*
