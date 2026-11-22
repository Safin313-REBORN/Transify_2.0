# TRANSIFY V3 — RC1.3.4 PR Corrections & Independent Release Verification

**Repository:** `Safin313-REBORN/Transify_2.0`  
**Branch:** `fix/rc1.3.3-signing-pipeline`  
**Base:** `main`  
**Scope:** Corrective review of RC1.3.3 before merge  
**Status:** **CONDITIONALLY READY FOR LOCAL VALIDATION — NOT APPROVED FOR MERGE**

## 1. Repository Corrections Applied

The following changes were committed to the existing draft PR branch:

1. Added POSIX permission enforcement in `android/app/build.gradle.kts`. If the external signing-properties file exists, Gradle now requires a regular file, exact owner-only directory permissions (`0700`), and exact owner-only file permissions (`0600`) before loading it. Filesystems that cannot expose POSIX permissions fail closed.
2. Corrected `TRANSIFY_V3_RC1_3_3_RELEASE_CHECKLIST.md` to match tracked configuration: `compileSdk 36`, `targetSdk 36`, `minSdk 24`, AGP `8.9.1`, Gradle `8.11.1`, Java source compatibility 17 and Kotlin JVM target 17. Runtime JDK and locally installed Build-Tools are left for host verification.
3. Corrected `TRANSIFY_V3_RC1_3_3_TEST_RESULTS.json`: automated test cases (259), viewport configurations (15), and accessibility phases (8) are represented as separate dimensions. No mixed-unit grand total is reported. Runtime JDK is not claimed from repository source.
4. Added explicit disclosure of the difference between local keystore claims and evidence independently observable from GitHub.
5. Documented the conflicting replacement upload-key certificate fingerprints found between RC1.3.2 and RC1.3.3. The later value is not treated as verified until the local keystore and PEM are compared.

## 2. Source Configuration Checked

| Setting | Tracked source value |
|---|---:|
| compileSdk | 36 |
| targetSdk | 36 |
| minSdk | 24 |
| AGP | 8.9.1 |
| Gradle wrapper | 8.11.1 |
| Java source compatibility | 17 |
| Kotlin JVM target | 17 |

The actual runtime JDK and SDK Build-Tools installation must be captured from the build host.

## 3. Metrics Accounting

| Dimension | Reported result | Unit |
|---|---:|---|
| Backend tests | 178 passed | Test cases |
| Android tests | 40 passed | Test cases |
| Browser E2E | 41 passed | Checks |
| **Automated test cases/checks** | **259 passed** | Test cases/checks |
| Responsive validation | 15 passed | Viewport configurations |
| Accessibility validation | 8 passed | Verification phases |

The 10 Zero Auto-Audio assertions are included inside the 40 Android tests and are not added again.

These figures are recorded from the RC1.3.3 test report; this repository correction did not execute the test suites.

## 4. Local Verification Still Required

The following operations cannot be completed by reading GitHub source alone:

- Verify the rotated PKCS12 keystore opens with the new credential and fails with the old credential, without printing either.
- Verify backup permissions and checksum; verify active keystore, backup, properties file and parent directory ownership/modes.
- Export the replacement upload certificate from the actual local keystore and compare its SHA-256 fingerprint against the PEM. Resolve the RC1.3.2 vs RC1.3.3 fingerprint discrepancy.
- Capture `./gradlew -version` and `sdkmanager --list_installed`.
- Execute Gradle permission-guard negative tests, `testDirectReleaseUnitTest`, `assembleDirectRelease`, and `bundlePlayRelease`.
- Re-run backend, Playwright, viewport and accessibility suites using the actual repository commands.
- Re-run `apksigner`, `jarsigner`, `bundletool validate`, and artifact SHA-256 checksums against the newly generated files.
- Confirm Google Play upload-key reset activation in Play Console before signing a Play submission with the replacement key.

## 5. Release Gates

- **Signing-source hardening:** Implemented in source; local permission and key rotation verification pending.
- **Direct APK signer identity:** Reported fingerprint remains `63:B8:CE:...`; local artifact re-verification required.
- **Play upload key:** Existing registered key remains in use until replacement acceptance; replacement certificate fingerprint reconciliation pending.
- **Physical Android Gate 3:** OPEN / DEFERRED; physical handset validation still required.
- **Clinical governance:** Applicable institutional and ethics approvals remain separate prerequisites before human clinical research or patient-facing ward deployment.

## 6. Decision

**CONDITIONALLY APPROVED FOR CONTINUED REVIEW. NOT APPROVED FOR MERGE OR GENERAL AVAILABILITY.**

This milestone corrects repository-visible inconsistencies and hardens the secret-file permission check. It does not claim local keystore operations, artifact rebuilding, test execution, physical hardware testing, or external approvals that were not performed during this repository review.
