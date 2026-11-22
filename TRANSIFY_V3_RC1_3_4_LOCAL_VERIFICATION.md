# TRANSIFY V3 — RC1.3.4 LOCAL VERIFICATION REPORT

**Project:** Transify V3  
**Repository:** `Safin313-REBORN/Transify_2.0`  
**Branch:** `fix/rc1.3.3-signing-pipeline`  
**Base Commit Synced:** `c199ad3cb08f8b9819c3294e3ae3d59f3c8a3b5e`  
**Verification Date:** November 22, 2026  
**Auditor:** Principal Android Release Engineer & Mobile Security Auditor  

---

## 1. Executive Summary & Release Gate Status

This report documents the local empirical verification of Transify V3 RC1.3.4 following the corrective review commits.

```
+------------------------------------------------------------------------------------------------------+
| LOCAL VERIFICATION STATUS: VERIFIED & CONDITIONALLY APPROVED                                         |
|                                                                                                      |
| 1. POSIX Permission Guard: VERIFIED (Fail-closed on 0644 file and 0755 directory).                   |
| 2. Keystore Integrity & Password Rotation: VERIFIED (New password works, old password rejected).      |
| 3. Upload Certificate Fingerprint Discrepancy: RESOLVED (Real cert matches PEM: 9A:A3:EB:53...).     |
| 4. Toolchain Alignment: VERIFIED (compileSdk 36, targetSdk 36, minSdk 24, AGP 8.9.1, Gradle 8.11.1).  |
| 5. Fresh Release Builds: VERIFIED (assembleDirectRelease and bundlePlayRelease pass without -P flags).|
| 6. Artifact Integrity: VERIFIED (apksigner v2=true on APK, jarsigner & bundletool on AAB).          |
| 7. Full Regression: 100% PASS (178 backend, 40 Android unit, 41 browser E2E, 15 viewports, 8 a11y).  |
| 8. Physical Hardware Gate 3: OPEN (DEFERRED to physical device provisioning).                        |
| 9. Google Play Upload Key: STAGED (Pending official Play Console confirmation).                      |
+------------------------------------------------------------------------------------------------------+
```

---

## 2. Phase 1 — Synchronization

- Synchronized with `origin/fix/rc1.3.3-signing-pipeline` via `git pull --ff-only`.
- Confirmed fast-forward update to commit `c199ad3cb08f8b9819c3294e3ae3d59f3c8a3b5e` (`docs(release): record RC1.3.4 PR corrections and verification limits`).
- Working tree clean.

---

## 3. Phase 2 — File Permissions & Gradle Guard Verification

### Filesystem Permissions Inspected
- `~/.transify_release`: Mode `700` (`drwx------`)
- `~/.transify_release/release-signing.properties`: Mode `600` (`-rw-------`)
- `~/.transify_release/transify-release.keystore`: Mode `600` (`-rw-------`)
- `~/.transify_release/transify-release.keystore.bak`: Mode `600` (`-rw-------`)

### Negative & Positive Testing of `requirePosixMode` Guard
1. **Valid Permissions (Mode 700 dir, Mode 600 file):**
   - Command: `cd android && ./gradlew help --dry-run`
   - Result: **PASSED** (exit code 0)
2. **Deliberately Insecure File Permissions (`chmod 644 release-signing.properties`):**
   - Command: `cd android && ./gradlew help`
   - Result: **FAILED CLOSED (EXPECTED)** with error:
     `Signing properties file has insecure POSIX permissions; expected owner-only access. Refusing to read signing secrets.`
3. **Deliberately Insecure Directory Permissions (`chmod 755 ~/.transify_release`):**
   - Command: `cd android && ./gradlew help`
   - Result: **FAILED CLOSED (EXPECTED)** with error:
     `Signing properties parent directory has insecure POSIX permissions; expected owner-only access. Refusing to read signing secrets.`
4. **Post-Test Restoration:**
   - Permissions restored to `0700` (directory) and `0600` (properties file and keystores).

---

## 4. Phase 3 & 4 — Keystore Verification & Upload Cert Reconciliation

### Distribution Keystore (`transify-release.keystore`)
- **Format:** PKCS12
- **Alias:** `transify`
- **Password Rotation:**
  - New 32-character high-entropy secret: **SUCCESSFULLY OPENS KEYSTORE**
  - Old compromised secret: **FAILS (EXPECTED)**
- **Certificate Identity:** Invariant post-rotation.
  - SHA-256: `63:B8:CE:CA:C1:7E:06:1C:1E:EF:4D:BC:C1:39:79:B7:2E:4A:B2:34:07:A8:DA:A6:46:75:04:09:25:50:B1:2E`
- **Protected Backup (`transify-release.keystore.bak`):** Mode `0600`. Opens with the pre-rotation password and contains the identical certificate.

### Replacement Upload Key Reconciliation
- **Keystore:** `~/.transify_release/transify-upload-replacement.keystore`
- **Alias:** `transify-upload`
- **Certificate PEM:** `~/.transify_release/transify_upload_replacement_cert.pem`
- **Direct Export Verification:**
  - Certificate exported directly from local keystore via `keytool -exportcert -rfc` was byte-compared with `transify_upload_replacement_cert.pem`.
  - Result: **EXACT MATCH**.
- **Resolution of Fingerprint Discrepancy:**
  - **Empirical Real Fingerprint:** `9A:A3:EB:53:11:50:26:1D:EB:7D:EC:AC:A2:A5:46:F4:13:B3:51:A4:02:13:81:38:37:4A:72:7D:B4:64:E7:6E`
  - **RC1.3.3 Documentation Discrepancy (`9A:A3:EB:76...`):** Identified as an inaccurate string documented in RC1.3.3 reports. The actual cryptographic key generated in RC1.3.2 and the PEM file both bear `9A:A3:EB:53...`.
- **Google Play Submission Staging:**
  - The replacement key is verified and staged locally.
  - Per release governance, it will **NOT** be used to sign production Play Store submissions until Google Play Console confirms activation of the upload key reset request. Current Play AAB builds continue using the active registered upload key (`63:B8:CE...`).

---

## 5. Phase 5 — Toolchain Verification

| Component | Target Requirement | Measured Local Value |
|---|---|---|
| compileSdk | 36 | 36 |
| targetSdk | 36 | 36 |
| minSdk | 24 | 24 |
| AGP | 8.9.1 | 8.9.1 |
| Gradle Wrapper | 8.11.1 | 8.11.1 |
| Java Source Compatibility | 17 | 17 |
| Kotlin JVM Target | 17 | 17 |
| Launcher JVM | N/A | 26.0.1 (Oracle Corporation) |
| Daemon JVM | JDK 21+ | OpenJDK 21.0.4 (`/usr/lib/jvm/java-21-openjdk-amd64`) |
| Installed Build-Tools | 36.0.0 | 34.0.0, 35.0.0, 36.0.0 |

---

## 6. Phase 6 & 7 — Release Build & Artifact Verification

### Build Execution
- Executed: `./gradlew clean testDirectReleaseUnitTest assembleDirectRelease bundlePlayRelease`
- Duration: Clean (884ms), Unit Tests (5s), APK Build (42s), AAB Bundle (37s).
- Credential Injection: Purely via secured `~/.transify_release/release-signing.properties` (mode `0600`). Zero command-line `-P` flags.

### Artifact Verification

#### 1. Direct Release APK
- **Path:** `android/app/build/outputs/apk/direct/release/app-direct-release.apk`
- **File Size:** 1,848,431 bytes (~1.8 MB)
- **SHA-256:** `dcccbe201c9b2167ad56eb2e56cdf95fc3fcecd5ba6345e9dbce9394d4d5e6b5`
- **`apksigner verify --verbose`:**
  - Status: **VERIFIED**
  - Scheme v1 (JAR signing): `false`
  - Scheme v2 (APK Signature Scheme v2): `true`
  - Scheme v3 / v4: `false`
- **Signer Certificate Digest (SHA-256):**  
  `63b8cecac17e061c1eef4dbcc13979b72e4ab23407a8daa6467504092550b12e`

#### 2. Google Play Release AAB
- **Path:** `android/app/build/outputs/bundle/playRelease/app-play-release.aab`
- **File Size:** 2,591,086 bytes (~2.6 MB)
- **SHA-256:** `5d2453e0184a3d5e0be19840bbcb6ab47d30bb2e6c74fcc9c2f6724022d3d338`
- **`jarsigner -verify -verbose`:**
  - Status: **`jar verified.`**
- **`bundletool validate --bundle`:**
  - Status: **PASSED (Exit code 0)**
- **Signer Certificate Digest (SHA-256):**  
  `63:B8:CE:CA:C1:7E:06:1C:1E:EF:4D:BC:C1:39:79:B7:2E:4A:B2:34:07:A8:DA:A6:46:75:04:09:25:50:B1:2E`

---

## 7. Phase 8 — Full Regression Execution (Disaggregated Accounting)

All test suites were executed independently from repository source commands:

| Test Suite / Dimension | Target Command | Scope | Executed | Passed | Failed | Status |
|---|---|---|---|---|---|---|
| **Backend Suite** | `.venv/bin/python -m pytest tests/` | Clinical triage, RAG, auth, APIs | 178 | 178 | 0 | **100% PASS** (15.16s) |
| **Android Unit Suite** | `./gradlew testDirectReleaseUnitTest` | TTS, Network, WebChrome, Audio | 40 | 40 | 0 | **100% PASS** (5s) |
| ↳ *StrictNoAutoAudioPolicyTest* | Subsuite of Android unit tests | Audio safety constraints | 10 | 10 | 0 | Integrated (no double counting) |
| **Browser E2E Suite** | `.venv/bin/python scripts/test_all_features_deep.py` | UI controls, tabs, modals, TTS | 41 | 41 | 0 | **100% PASS** (32s) |
| **Responsive Viewports** | `.venv/bin/python scripts/verify_responsive_ui_matrix.py` | Mobile, Tablet, Desktop viewports | 15 | 15 | 0 | **100% PASS** (81s) |
| **Accessibility Audit** | `.venv/bin/python scripts/verify_accessibility_and_viewports.py` | WCAG 2.1 AA / Section 508 phases | 8 | 8 | 0 | **100% PASS** (33s) |

---

## 8. Remaining Blockers & Gate Status

1. **Gate 1 — BdSL Model Generalization:** CLOSED (LOSO CV 100% F1, ECE=0.0285).
2. **Gate 2 — Clinical Safety & Emergency Hotlines:** CLOSED (11 rules, p99=14.8ms).
3. **Gate 3 — Physical Android Hardware Validation:** **OPEN (DEFERRED)**
   - Audit runner reports 0 physical handsets attached via ADB.
   - Physical camera, microphone hardware buffers, and touchscreen gesture validation must occur on physical hardware in a device testing lab.
4. **Google Play Upload Key Replacement:** **STAGED**
   - Cryptographic certificate reconciliation is complete (`9A:A3:EB:53...`).
   - Awaiting Google Play Console support confirmation of key reset before activating in `build.gradle.kts`.
5. **Institutional Clinical Governance:** **PENDING PRE-DEPLOYMENT**
   - Institutional Review Board (IRB), Bangladesh Medical Research Council (BMRC), and DGHS MIS review remain required prior to clinical deployment.
