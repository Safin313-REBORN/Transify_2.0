# TRANSIFY V3 — RC1.3.4 KEYSTORE & CERTIFICATE RECONCILIATION REPORT

**Project:** Transify V3  
**Package:** `com.abrarafick.transify`  
**Milestone:** RC1.3.4 Local Verification  
**Date:** November 22, 2026  
**Auditor:** Principal Mobile Security Engineer & Release Signing Architect  

---

## 1. Scope & Security Policy

This audit covers the physical and cryptographic verification of all signing assets stored under `~/.transify_release`.

**Security Rules Strictly Followed:**
- **Zero Credential Exposure:** No keystore passwords, key passwords, or private key blocks are printed to terminal logs, markdown reports, or Git history.
- **Fail-Closed Protection:** Keystores, backups, and properties files are restricted to POSIX permissions `0600` inside a `0700` directory.
- **Certificate Invariance:** The direct APK distribution certificate identity must remain strictly invariant across password rotation.
- **Upload Key Staging Discipline:** No replacement upload key may be used for Google Play submissions without physical reconciliation between the local private key, the exported public PEM certificate, and Play Console approval.

---

## 2. Distribution Keystore Verification (`transify-release.keystore`)

### File Attributes
- **Location:** `/home/safin313/.transify_release/transify-release.keystore`
- **File Permissions:** POSIX `0600` (`-rw-------`)
- **Parent Directory:** `/home/safin313/.transify_release` (POSIX `0700`, `drwx------`)
- **Keystore Format:** `PKCS12` (standard single-password protection for store and keys)

### Authentication & Password Rotation
- **Rotated Credential (Current):** High-entropy 32-character secret loaded from `~/.transify_release/release-signing.properties`.
  - Result: **SUCCESS (Opens keystore, returncode = 0)**
- **Compromised Credential (Historical):** Pre-rotation password extracted from Git commit `3832a5f`.
  - Result: **FAILED (EXPECTED, returncode != 0)**

### Certificate Identity & Validity
- **Alias:** `transify`
- **Entry Type:** `PrivateKeyEntry`
- **Certificate Chain Length:** 1
- **Owner / Issuer:** `CN=Transify Release, OU=Transify Assistive Health, O=Safin313, L=Dhaka, ST=Dhaka, C=BD`
- **Valid From:** Sun Nov 22 17:26:40 GMT+06:00 2026 until Thu Apr 09 17:26:40 GMT+06:00 2054
- **SHA-256 Fingerprint:**  
  `63:B8:CE:CA:C1:7E:06:1C:1E:EF:4D:BC:C1:39:79:B7:2E:4A:B2:34:07:A8:DA:A6:46:75:04:09:25:50:B1:2E`
- **SHA-1 Fingerprint:** `6C:5D:2F:86:D1:5D:26:03:87:2F:EA:E4:67:12:BF:26:1C:97:F5:12`
- **MD5 Fingerprint:** `33:E0:F7:2C:99:37:FC:3A:D6:F1:95:17:2B:30:B3:13`
- **Certificate Invariance:** Verified 100% identical before and after password rotation.

### Protected Backup Keystore (`transify-release.keystore.bak`)
- **Location:** `/home/safin313/.transify_release/transify-release.keystore.bak`
- **File Permissions:** POSIX `0600` (`-rw-------`)
- **Authentication:** Verified with original historical credential (**SUCCESS**).
- **Certificate Fingerprint:** Identical SHA-256 `63:B8:CE:CA:C1:7E:06:1C:1E:EF:4D:BC:C1:39:79:B7:2E:4A:B2:34:07:A8:DA:A6:46:75:04:09:25:50:B1:2E`.
- **Integrity Status:** Protected, verified, and preserved intact.

---

## 3. Replacement Upload Key Reconciliation (`transify-upload-replacement.keystore`)

### File Attributes
- **Keystore Location:** `/home/safin313/.transify_release/transify-upload-replacement.keystore`
- **Properties Location:** `/home/safin313/.transify_release/replacement-upload-key.properties` (mode `0600`)
- **Public Certificate PEM:** `/home/safin313/.transify_release/transify_upload_replacement_cert.pem` (mode `0600`)
- **Keystore Format:** `PKCS12`
- **Alias:** `transify-upload`
- **Authentication:** Opens successfully with `REPLACEMENT_KEYSTORE_PASSWORD` loaded from `replacement-upload-key.properties`.

### Direct Export & PEM Comparison
1. Exported certificate directly from `transify-upload-replacement.keystore` using:
   ```bash
   keytool -exportcert -keystore ~/.transify_release/transify-upload-replacement.keystore -alias transify-upload -rfc
   ```
2. Byte-compared exported output against `~/.transify_release/transify_upload_replacement_cert.pem`:
   - Normalized comparison: **EXACT MATCH**

### Root Cause Analysis: RC1.3.2 vs RC1.3.3 Fingerprint Discrepancy

During the RC1.3.3 audit documentation phase, two conflicting fingerprints appeared in release notes:
- **RC1.3.2 Fingerprint:** Starting with `9A:A3:EB:53...`
- **RC1.3.3 Fingerprint:** Starting with `9A:A3:EB:76...`

#### Investigation Findings
1. Inspection of the actual cryptographic file `transify-upload-replacement.keystore`:
   - SHA-256 Fingerprint:  
     `9A:A3:EB:53:11:50:26:1D:EB:7D:EC:AC:A2:A5:46:F4:13:B3:51:A4:02:13:81:38:37:4A:72:7D:B4:64:E7:6E`
2. Inspection of the actual public certificate file `transify_upload_replacement_cert.pem`:
   - OpenSSL SHA-256 Fingerprint:  
     `9A:A3:EB:53:11:50:26:1D:EB:7D:EC:AC:A2:A5:46:F4:13:B3:51:A4:02:13:81:38:37:4A:72:7D:B4:64:E7:6E`
3. The string `9A:A3:EB:76:CD:6F:E9:7D:6B:42:DE:DE:D2:C3:FF:C4:6E:1D:95:97:D5:FF:AC:12:F6:41:81:4A:14:0E:98:98` was an erroneous string documented in RC1.3.3 reports and did not correspond to any generated physical keystore.
4. **Authoritative Real Fingerprint:**  
   `9A:A3:EB:53:11:50:26:1D:EB:7D:EC:AC:A2:A5:46:F4:13:B3:51:A4:02:13:81:38:37:4A:72:7D:B4:64:E7:6E`

---

## 4. Google Play Staging Status

- **Status:** **STAGED / AWAITING GOOGLE PLAY CONSOLE APPROVAL**
- The public PEM certificate `transify_upload_replacement_cert.pem` with fingerprint `9A:A3:EB:53...` is confirmed to match the local private key.
- It is ready for upload to Google Play Console via the "Request upload key reset" workflow.
- **Enforced Policy:** Google Play AAB artifacts (`bundlePlayRelease`) will strictly continue to be signed with the currently registered upload key (`63:B8:CE...`) until Google Play Console confirms that the replacement key has been registered and activated.
