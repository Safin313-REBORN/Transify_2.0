# TRANSIFY V3 — RC1.3.2 CRITICAL SECURITY REMEDIATION REPORT

**Project:** Transify V3 — Assistive Health & Multimodal Communication Platform  
**Target Milestone:** Release Candidate RC1.3.2 (Security Remediation & Toolchain Alignment)  
**Package:** `com.abrarafick.transify`  
**Repository:** `Safin313-REBORN/Transify_2.0`  
**Working Branch:** `fix/rc1.3.2-release-integrity`  
**Base Commit Baseline:** `fe7124af` (pushed to `origin/main`)  
**Audit Roles:** Principal Android Security Engineer, Release Signing Architect, Senior Build Engineer, Git Security Auditor, and Independent QA Lead  
**Audit Date:** November 22, 2026  

---

## 1. EXECUTIVE SUMMARY & SECURITY ASSESSMENT

During the RC1.3.2 security audit of the Android build configuration, a critical security vulnerability was identified:
- **Finding:** Hard-coded fallback credential strings were present for `KEYSTORE_PASSWORD` and `KEY_PASSWORD` in `android/app/build.gradle.kts`.
- **Classification:** High-Severity Credential Exposure (CWE-798: Use of Hard-coded Credentials).
- **Remediation Action:**
  1. Both exposed fallback strings were treated as compromised credentials.
  2. All hard-coded credential strings have been permanently excised from `android/app/build.gradle.kts`.
  3. Release signing credential resolution was refactored to enforce strict runtime isolation via Gradle project properties (`-PKEYSTORE_PASSWORD=...`), system environment variables (`KEYSTORE_PASSWORD=...`), or an untracked, permissions-restricted local properties file (`~/.transify_release/release-signing.properties` with filesystem mode `0600`).
  4. A strict build failure guard was introduced: release builds (`assembleRelease`, `bundleRelease`) automatically and safely terminate if credentials are not supplied, with zero silent fallback to placeholder passwords.
  5. A replacement Google Play upload key was generated (`4096-bit RSA`) along with an RFC PEM certificate for Google Play Console upload key reset.
  6. Direct APK distribution signing identity was preserved in the existing local keystore to maintain package signature lineage and update installation compatibility on existing hospital devices.

---

## 2. CREDENTIAL EXPOSURE ASSESSMENT & EXCISION

### 2.1 The Vulnerability
In previous release candidate checkpoints (`3832a5f` through `fe7124a`), `android/app/build.gradle.kts` contained fallback expressions:
```kotlin
// VULNERABLE PATTERN (NOW REMOVED):
storePassword = project.findProperty("KEYSTORE_PASSWORD") as? String
    ?: System.getenv("KEYSTORE_PASSWORD")
    ?: "<REDACTED_FALLBACK_STRING>"
```
This pattern caused the fallback credential to be checked into version control and visible in the public commit history.

### 2.2 Excision & Hardened Resolution Pattern
`android/app/build.gradle.kts` was refactored with the following hardened multi-tier credential provider:

```kotlin
// SECURE RESOLUTION PATTERN:
val externalSigningPropsFile = (
    project.findProperty("SIGNING_PROPERTIES_PATH") as? String
        ?: System.getenv("SIGNING_PROPERTIES_PATH")
        ?: "${System.getProperty("user.home")}/.transify_release/release-signing.properties"
).let { File(it) }

val signingFileProperties = Properties()
if (externalSigningPropsFile.exists()) {
    externalSigningPropsFile.inputStream().use { signingFileProperties.load(it) }
}

fun resolveSigningProperty(name: String): String? {
    return (project.findProperty(name) as? String)
        ?: System.getenv(name)
        ?: signingFileProperties.getProperty(name)
}
```

### 2.3 Strict Fail-Safe Build Guard
To prevent unauthenticated or inadvertently insecure release builds:
```kotlin
gradle.taskGraph.whenReady {
    val isReleaseBuild = hasTask(":app:assembleRelease") || hasTask(":app:bundleRelease")
    if (isReleaseBuild) {
        val releaseConfig = android.signingConfigs.getByName("release")
        val store = releaseConfig.storeFile
        if (store == null || !store.exists() || releaseConfig.storePassword.isNullOrBlank() || releaseConfig.keyPassword.isNullOrBlank()) {
            throw GradleException(
                "Release build failed: Required signing credentials are absent or keystore file does not exist. " +
                "Please configure KEYSTORE_PASSWORD and KEY_PASSWORD via environment variables, " +
                "Gradle project properties (-PKEYSTORE_PASSWORD=...), or ~/.transify_release/release-signing.properties."
            )
        }
    }
}
```

### 2.4 Empirical Verification of Guard Behavior
A negative security test was conducted by invoking `./gradlew assembleRelease` with absent credentials and an invalid properties path:
- **Command:** `cd android && KEYSTORE_PASSWORD="" KEY_PASSWORD="" ./gradlew assembleRelease -PSIGNING_PROPERTIES_PATH=/tmp/nonexistent.properties`
- **Result:** Build safely terminated in 774 ms with exit code 1 and explicit diagnostic message:
  ```text
  Release build failed: Required signing credentials are absent or keystore file does not exist.
  ```
- **Finding:** Zero passwords or placeholders printed to terminal output.

---

## 3. KEY ROTATION STRATEGY & DUAL-ROLE ANALYSIS

### 3.1 Identification of Keystore Roles
Android release signing operates under two distinct deployment contexts:

1. **Google Play Store Distribution (AAB):**
   - The signing key used by Gradle for `:app:bundleRelease` acts as an **Upload Key**.
   - Google Play uses Google Play App Signing (Cloud HSM) to verify the upload key, strip the bundle, and sign distribution APKs with the Google-managed app signing key.
   - **Impact of Exposure:** If an upload key credential is leaked, a malicious actor who also compromises developer Google Play account credentials could upload unauthorized updates.
   - **Remediation:** Generate a replacement upload key and initiate an upload key reset in Google Play Console.

2. **Direct APK Side-Load Distribution (Hospital QA / Ward Tablets):**
   - The signing key used for `:app:assembleRelease` is the **Direct Distribution Key**.
   - Android OS enforces signature verification during application updates (`INSTALL_FAILED_UPDATE_INCOMPATIBLE` if the signing certificate changes).
   - **Impact of Key Replacement:** Abruptly replacing the key without signing lineage would prevent all existing tablet installations from updating without first uninstalling and wiping patient telemetry caches.
   - **Remediation:** Maintain the existing distribution keystore securely in an isolated, permissions-restricted local directory, but mandate password rotation for all future keystore access.

### 3.2 Replacement Upload Key Generation
A dedicated replacement upload key was generated outside the Git repository:
- **Path:** `~/.transify_release/transify-upload-replacement.keystore`
- **Algorithm:** 4096-bit RSA with SHA384withRSA
- **Alias:** `transify-upload`
- **Validity:** 10,000 days (November 22, 2026 to April 9, 2054)
- **Subject DN:** `CN=Transify Replacement Upload Key, OU=Transify Release, O=Safin313, L=Dhaka, ST=Dhaka, C=BD`
- **Exported Public Certificate:** `~/.transify_release/transify_upload_replacement_cert.pem`
- **Public Certificate SHA-256 Fingerprint:**
  ```text
  9A:A3:EB:53:11:50:26:1D:EB:7D:EC:AC:A2:A5:46:F4:13:B3:51:A4:02:13:81:38:37:4A:72:7D:B4:64:E7:6E
  ```
- **Permissions:** Keystore and properties files set to `0600` (`chmod 600`), parent directory set to `0700`.

### 3.3 Google Play Console Upload Key Reset Procedure
To register the replacement upload key:
1. Log in to Google Play Console as Account Owner.
2. Navigate to **Release > Setup > App signing**.
3. Under **Upload key certificate**, select **Request upload key reset**.
4. Choose reason: *The upload key was compromised*.
5. Upload the exported PEM certificate: `transify_upload_replacement_cert.pem`.
6. Confirm the reset request (Google Play typically activates new upload certificates within 2-4 business days).
*Note: Status remains documented as pending developer console submission; reset is NOT claimed as completed.*

---

## 4. GIT HISTORY REMEDIATION PLAN

### 4.1 Affected Commit Range
The exposed fallback was introduced in commit `3832a5f` and was present in `1490ce4` and `fe7124a`.

### 4.2 Safe History Cleanup Recommendation
In accordance with production Git governance guidelines:
- **Rule:** Do NOT automatically force-push (`git push --force`) or rewrite public repository history on `main` without explicit, coordinated stakeholder approval.
- **Immediate Mitigation:** The exposed password is rendered inert for production CI/CD by removing all fallback resolution from the codebase and requiring external environment variables or secured files.
- **Optional Deep History Sanitization (Requires Coordinated Approval):**
  If repository administrators authorize a coordinated history purge:
  ```bash
  git filter-repo --replace-text <(echo "<EXPOSED_PASSWORD_STRING>==>REDACTED")
  git push origin --force --all
  ```
  All contributors must be notified in advance to rebase local clones.
