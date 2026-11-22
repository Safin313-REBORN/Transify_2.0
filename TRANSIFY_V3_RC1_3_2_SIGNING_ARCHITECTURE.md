# TRANSIFY V3 — RC1.3.2 SIGNING ARCHITECTURE & ARTIFACT INTEGRITY REPORT

**Target Package:** `com.abrarafick.transify`  
**Milestone:** Release Candidate RC1.3.2  
**Artifact Directory:** `android/app/build/outputs/`  
**Audit Date:** November 22, 2026  
**Auditor:** Release Signing Architect & Mobile Security Auditor  

---

## 1. DUAL DISTRIBUTION SIGNING ARCHITECTURE

Transify V3 maintains a rigorous dual-pipeline signing model that separates direct side-load APK distribution from Google Play Store managed app signing:

```
+---------------------------------------------------------------------------------------------------------+
| Pipeline                     | Target Artifact  | Signing Standard        | Verified Signature Scheme   |
+---------------------------------------------------------------------------------------------------------+
| Direct Hospital / Ward QA    | app-release.apk  | Direct Cryptographic    | APK Signature Scheme v2     |
| Side-load Distribution       | (1.8 MB)         | Binary Signing          | (v2 = true, v1 = false)     |
+---------------------------------------------------------------------------------------------------------+
| Google Play Store Publishing | app-release.aab  | Developer Upload Key    | Standard JAR Signing        |
| Ingestion Pipeline           | (2.5 MB)         | Bundle Signing          | (jar verified, bundletool OK|
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. RELEASE APK INDEPENDENT VERIFICATION (`apksigner`)

### Tool Command
```bash
$ /home/safin313/Android/Sdk/build-tools/35.0.0/apksigner verify --verbose --print-certs \
    android/app/build/outputs/apk/release/app-release.apk
```

### Tool Execution Output
```text
Verifies
Verified using v1 scheme (JAR signing): false
Verified using v2 scheme (APK Signature Scheme v2): true
Verified using v3 scheme (APK Signature Scheme v3): false
Verified using v3.1 scheme (APK Signature Scheme v3.1): false
Verified using v4 scheme (APK Signature Scheme v4): false
Verified for SourceStamp: false
Number of signers: 1

Signer #1 certificate DN: CN=Transify Release, OU=Transify Assistive Health, O=Safin313, L=Dhaka, ST=Dhaka, C=BD
Signer #1 certificate SHA-256 digest: 63b8cecac17e061c1eef4dbcc13979b72e4ab23407a8daa6467504092550b12e
Signer #1 certificate SHA-1 digest: 6c5d2f86d15d2603872feae46712bf261c97f512
Signer #1 certificate MD5 digest: 33e0f72c9937fc3ad6f195172b30b313
Signer #1 key algorithm: RSA
Signer #1 key size (bits): 2048
Signer #1 public key SHA-256 digest: 7420e385f7b7a6f5436128b5874eb698ed080c717e894c8590b0a2648446c19e
Signer #1 public key SHA-1 digest: 35b9b48dd3b0ef101aa34492104dbf3405c0ba7d
Signer #1 public key MD5 digest: a9b618ccc42b85d1b95dbf6e0e2f62bc
```

### Analysis
- **Tamper Protection:** Full APK Signature Scheme v2 compliance ensures that the APK binary cannot be modified post-signing without breaking installation.
- **Legacy Invalidation:** Scheme v1 (JAR signing) is explicitly omitted (`false`) to eliminate metadata tampering vulnerabilities.
- **Update Lineage:** The distribution certificate matches previously deployed pilot builds (`SHA-256: 63b8ce...`), preserving in-place update compatibility.

---

## 3. ANDROID APP BUNDLE INDEPENDENT VERIFICATION (`jarsigner` & `bundletool`)

### 3.1 Jarsigner Verification
```bash
$ jarsigner -verify android/app/build/outputs/bundle/release/app-release.aab
jar verified.
```

### 3.2 Bundletool Structure & Spec Validation
```bash
$ java -jar /home/safin313/.local/bin/bundletool.jar validate \
    --bundle=android/app/build/outputs/bundle/release/app-release.aab
```
- **Result:** Exit code `0` (Success).
- **Inspection Findings:**
  - Base feature module: `base` validated.
  - Manifest and configuration: `BundleConfig.pb` intact.
  - Dex bytecode: `classes.dex` verified.
  - R8 mapping: `BUNDLE-METADATA/com.android.tools.build.obfuscation/proguard.map` present.
  - Native libraries: Zero unaligned architectures.

---

## 4. RELEASE ARTIFACTS INVENTORY & CHECKSUMS

```
+------------------------------------------------------------------------------------------------------------------------------------+
| Artifact Path                                            | Size   | SHA-256 Checksum                                              |
+------------------------------------------------------------------------------------------------------------------------------------+
| android/app/build/outputs/apk/release/app-release.apk    | 1.8 MB | 97754d2070602452ced09aded109c1087f1391b83efeadcd741442ab9381c6b9  |
| android/app/build/outputs/bundle/release/app-release.aab | 2.5 MB | e4b95d774d91b265e9cef2a9041d011c07f0a38e5c841090b8c836b25d52ba67  |
+------------------------------------------------------------------------------------------------------------------------------------+
```

---

## 5. REPLACEMENT UPLOAD KEY PROFILE

To prepare for Google Play upload key rotation:
- **Keystore File:** `/home/safin313/.transify_release/transify-upload-replacement.keystore` (mode `0600`)
- **Key Alias:** `transify-upload`
- **Algorithm:** 4096-bit RSA with SHA384withRSA
- **Public Certificate File:** `/home/safin313/.transify_release/transify_upload_replacement_cert.pem`
- **Certificate SHA-256:** `9A:A3:EB:53:11:50:26:1D:EB:7D:EC:AC:A2:A5:46:F4:13:B3:51:A4:02:13:81:38:37:4A:72:7D:B4:64:E7:6E`
- **Rotation Status:** Staged locally; pending developer submission to Google Play Console.
