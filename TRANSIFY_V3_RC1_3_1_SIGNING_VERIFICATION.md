# TRANSIFY V3 — RC1.3.1 CODE SIGNING & CRYPTOGRAPHIC VERIFICATION REPORT

**Target Artifacts:** 
- `android/app/build/outputs/apk/release/app-release.apk`
- `android/app/build/outputs/bundle/release/app-release.aab`
**Package Identifier:** `com.abrarafick.transify`  
**Signing Key Alias:** `transify`  
**Keystore Path:** `~/.transify_release/transify-release.keystore` (Isolated outside Git)  
**Verification Date:** November 22, 2026  
**Auditor:** Mobile Security & Cryptographic Release Auditor  

---

## 1. CRYPTOGRAPHIC SIGNING SUMMARY

Transify V3 uses dual-pipeline code signing designed for both direct side-load distribution (APK) and Google Play Store publishing (AAB):

```
+-----------------------------------------------------------------------------------------------------------+
| Distribution Channel | Target Artifact | Verification Tool | Verification Standard | Result               |
+-----------------------------------------------------------------------------------------------------------+
| Direct Hospital / QA | app-release.apk | apksigner v34     | APK Signature Scheme  | PASSED               |
| Side-load Distribution|                 |                   | v2 (Whole-file SHA256)| (v2 = true, v1 = false)|
+-----------------------------------------------------------------------------------------------------------+
| Google Play Store    | app-release.aab | jarsigner v17     | Standard JAR Digest   | PASSED               |
| App Signing Pipeline |                 |                   | Manifest Verification | (jar verified)       |
+-----------------------------------------------------------------------------------------------------------+
```

---

## 2. APK SIGNATURE SCHEME V2 VERIFICATION

### Tool Command
```bash
$ /home/safin313/Android/Sdk/build-tools/34.0.0/apksigner verify --verbose --print-certs \
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

### Cryptographic Security Analysis
1. **APK Signature Scheme v2 Protection:** Scheme v2 treats the entire APK file as a contiguous sequence of binary bytes protected by a cryptographic signature block. Any post-signing modification to classes.dex, resources.arsc, or AndroidManifest.xml immediately invalidates the signature and causes package installation to abort (`INSTALL_PARSE_FAILED_NO_CERTIFICATES`).
2. **Disabling Scheme v1:** Scheme v1 (JAR signing) leaves metadata files in `META-INF/` unverified and is susceptible to ZIP entry manipulation. By signing strictly with Scheme v2, Transify eliminates legacy JAR tampering vectors.

---

## 3. ANDROID APP BUNDLE (AAB) SIGNING VERIFICATION

### Tool Command
```bash
$ jarsigner -verify android/app/build/outputs/bundle/release/app-release.aab
```

### Tool Execution Output
```text
jar verified.

Signer:
X.509, CN=Transify Release, OU=Transify Assistive Health, O=Safin313, L=Dhaka, ST=Dhaka, C=BD
Signature algorithm: SHA384withRSA, 2048-bit RSA key
Certificate valid from: 11/22/26, 5:26 PM to 4/9/54, 5:26 PM
```

### Google Play App Signing Architecture
1. **Developer Upload Key:** The AAB is signed using the `transify` upload key (`~/.transify_release/transify-release.keystore`).
2. **Google Play Ingestion:** When uploaded to Google Play, the Play Console authenticates the bundle against the registered upload certificate SHA-256 (`63b8cecac17e061c1eef4dbcc13979b72e4ab23407a8daa6467504092550b12e`).
3. **App Signing Key Generation:** Google Play strips the bundle, extracts architecture-specific split APKs, and signs them with Google's HSM-managed App Signing Key for distribution to end-user devices.

---

## 4. KEStore MANAGEMENT & REPOSITORY SANITATION

- **Keystore Absolute Path:** `/home/safin313/.transify_release/transify-release.keystore`
- **Git Ignore & Repository Status:** Located in the user's home hidden directory completely outside `/home/safin313/Downloads/transify-main`.
- **Git Commit Inspection:** Confirmed zero instances of private keys, `.keystore`, `.jks`, or keystore credentials in the repository commit tree.
- **Passphrase Security:** Managed via environment variables `KEYSTORE_PASSWORD` and `KEY_PASSWORD` during automated production CI/CD builds.
