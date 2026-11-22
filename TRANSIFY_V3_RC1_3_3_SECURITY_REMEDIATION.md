# TRANSIFY V3 — RC1.3.3 SECURITY REMEDIATION REPORT
## Keystore Password Rotation, Protected Backup, & -P Credential Elimination

**Project:** Transify V3 — Assistive Health & Multimodal Communication Platform  
**Target Milestone:** Release Candidate RC1.3.3 (Security Hardening Continuation)  
**Package:** `com.abrarafick.transify`  
**Repository:** `Safin313-REBORN/Transify_2.0`  
**Branch:** `fix/rc1.3.3-signing-pipeline`  
**Base Commit:** `c1365a0`  
**Audit Roles:** Principal Android Security Engineer, Release Signing Architect, Senior Build Engineer, Git Security Auditor, and Independent QA Lead  
**Audit Date:** November 22, 2026  

---

## 1. EXECUTIVE SUMMARY

The RC1.3.3 security milestone completes the critical credential remediation and signing pipeline separation initiated in RC1.3.2:

1. **Keystore Password Rotation (Verified):**
   - The exposed passwords on the production keystore (`transify-release.keystore`) were successfully rotated using `keytool -storepasswd` to a cryptographically strong 32-character secret.
   - The original direct APK certificate identity (`SHA-256: 63:B8:CE:CA:C1:7E:06:1C:1E:EF:4D:BC:C1:39:79:B7:2E:4A:B2:34:07:A8:DA:A6:46:75:04:09:25:50:B1:2E`) was **100% preserved**, maintaining signature lineage and seamless update compatibility on hospital test tablets.
2. **Protected Keystore Backup:**
   - A protected backup of the keystore was created prior to rotation:
     `/home/safin313/.transify_release/transify-release.keystore.bak` (filesystem mode `0600`).
   - Parent directory permissions enforced at `0700` (`chmod 700 /home/safin313/.transify_release`).
3. **Elimination of `-P` Command-Line Credential Resolution:**
   - Gradle `project.findProperty()` credential lookups were completely excised.
   - Supplying passwords via `-P` CLI flags (which leak into process listings via `ps aux` and shell history) is strictly forbidden.
   - Credentials are now resolved exclusively via environment variables (`KEYSTORE_PASSWORD`, `KEY_PASSWORD`) or the untracked external file `~/.transify_release/release-signing.properties` (mode `0600`).
4. **Fail-Closed Architecture:**
   - When required credentials are absent, release builds fail closed within < 700 ms with an explicit diagnostic error and zero secret exposure.

---

## 2. PRIORITY 1 — KEYSTORE INSPECTION, BACKUP, & PASSWORD ROTATION

### 2.1 Pre-Rotation Keystore Audit
The local keystore was inspected and verified using `keytool`:
- **Keystore Path:** `/home/safin313/.transify_release/transify-release.keystore`
- **Keystore Format:** PKCS12 (Standard SUN Provider)
- **Primary Alias:** `transify`
- **Algorithm:** 2048-bit RSA with SHA384withRSA signature
- **Validity:** November 22, 2026 to April 9, 2054 (10,000 days)
- **Subject DN:** `CN=Transify Release, OU=Transify Assistive Health, O=Safin313, L=Dhaka, ST=Dhaka, C=BD`
- **Certificate SHA-256 Fingerprint:**
  `63:B8:CE:CA:C1:7E:06:1C:1E:EF:4D:BC:C1:39:79:B7:2E:4A:B2:34:07:A8:DA:A6:46:75:04:09:25:50:B1:2E`

### 2.2 Creation of Protected Backup
Before performing any modification, an immutable backup was created:
- **Backup File:** `/home/safin313/.transify_release/transify-release.keystore.bak`
- **Filesystem Mode:** `0600` (`-rw-------`)
- **Integrity Check:** Checksum matches pre-rotation keystore.

### 2.3 Password Rotation Execution
Password rotation was performed using the JDK `keytool` utility:
```bash
keytool -storepasswd \
    -keystore /home/safin313/.transify_release/transify-release.keystore \
    -storepass "<COMPROMISED_OLD_PASSWORD>" \
    -new "<SECURE_ROTATED_32_CHAR_SECRET>"
```
- **Post-Rotation Verification:** The keystore was re-opened and inspected using the new password. The certificate fingerprint and public key hash remained identical (`63:B8:CE...`), confirming that the cryptographic key pair and X.509 certificate were untouched while the access passphrase was rotated.
- **Properties Update:** `~/.transify_release/release-signing.properties` was updated with the new rotated credentials and secured with `chmod 600`.

---

## 3. PRIORITY 3 — EXCISION OF `-P` CREDENTIAL PASSING

### 3.1 Security Hazard of Gradle `-P` CLI Arguments
Passing credentials via `-PKEYSTORE_PASSWORD=...` on the terminal command line exposes secrets to:
1. Shell history files (`~/.bash_history`).
2. Global OS process tables (`/proc/*/cmdline`, visible to any local user via `ps aux`).
3. CI/CD build runner logs and process monitors.

### 3.2 Implemented Refactoring in `android/app/build.gradle.kts`
```kotlin
// Secure credential resolution: ONLY environment variables or secure external properties file (mode 0600)
// project.findProperty() lookups for passwords have been completely eliminated.
val externalSigningPropsFile = (
    System.getenv("SIGNING_PROPERTIES_PATH")
        ?: "${System.getProperty("user.home")}/.transify_release/release-signing.properties"
).let { File(it) }

val signingFileProperties = Properties()
if (externalSigningPropsFile.exists()) {
    externalSigningPropsFile.inputStream().use { signingFileProperties.load(it) }
}

fun resolveSigningProperty(name: String): String? {
    return System.getenv(name) ?: signingFileProperties.getProperty(name)
}
```

### 3.3 Fail-Closed Test Verification
An empirical negative verification test was executed:
- **Command:** `SIGNING_PROPERTIES_PATH=/tmp/empty.properties ./gradlew assembleDirectRelease`
- **Result:** Build aborted in 672 ms:
  ```text
  Direct release build failed: Required signing credentials are absent or keystore file does not exist.
  Credentials must be supplied strictly via environment variables (KEYSTORE_PASSWORD, KEY_PASSWORD)
  or ~/.transify_release/release-signing.properties (mode 0600). Command-line -P arguments are forbidden.
  ```

---

## 4. DUAL SIGNING PIPELINE ARCHITECTURE

Transify V3 implements genuinely separate release pipelines via Gradle product flavors:

1. **`assembleDirectRelease` (Direct APK Distribution Pipeline):**
   - Output: `android/app/build/outputs/apk/direct/release/app-direct-release.apk`
   - Signing Config: `directRelease` (uses `transify-release.keystore` with rotated password).
   - Signer Certificate SHA-256: `63b8cecac17e061c1eef4dbcc13979b72e4ab23407a8daa6467504092550b12e`.
   - Update Compatibility: Maintained for existing hospital pilot tablet deployments.
2. **`bundlePlayRelease` (Google Play Ingestion Pipeline):**
   - Output: `android/app/build/outputs/bundle/playRelease/app-play-release.aab`
   - Signing Config: `playRelease` (uses the currently registered Google Play upload key in `transify-release.keystore`).
   - Replacement Upload Key Status: Staged locally (`transify-upload-replacement.keystore`, 4096-bit RSA, SHA-256: `9A:A3:EB...`); will be switched only after Google Play confirms upload key reset completion.
