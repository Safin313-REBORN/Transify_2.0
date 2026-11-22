# TRANSIFY V3 — RC1.3.3 SIGNING ARCHITECTURE & ARTIFACT INTEGRITY REPORT

**Target Artifacts:**
- `android/app/build/outputs/apk/direct/release/app-direct-release.apk`
- `android/app/build/outputs/bundle/playRelease/app-play-release.aab`
**Package Identifier:** `com.abrarafick.transify`  
**Milestone:** Release Candidate RC1.3.3  
**Audit Date:** November 22, 2026  
**Auditor:** Release Signing Architect & Mobile Security Auditor  

---

## 1. DUAL-PIPELINE SIGNING OVERVIEW

In RC1.3.3, release signing is divided into two genuinely independent pipelines, each targeting a specific distribution channel:

```
+-----------------------------------------------------------------------------------------------------------+
| Pipeline                    | Build Command               | Output Artifact         | Signing Scheme      |
+-----------------------------------------------------------------------------------------------------------+
| Direct Hospital / Ward QA   | ./gradlew assembleDirectRelease | app-direct-release.apk  | APK Signature Scheme|
| Side-load Distribution      |                             | (1.8 MB)                | v2 (Whole-file)     |
+-----------------------------------------------------------------------------------------------------------+
| Google Play Store           | ./gradlew bundlePlayRelease | app-play-release.aab    | Standard JAR Signing|
| Ingestion Pipeline          |                             | (2.5 MB)                | Upload Key Contract |
+-----------------------------------------------------------------------------------------------------------+
```

---

## 2. DIRECT APK SIGNATURE VERIFICATION (`apksigner`)

### Tool Command
```bash
$ /home/safin313/Android/Sdk/build-tools/35.0.0/apksigner verify --verbose --print-certs \
    android/app/build/outputs/apk/direct/release/app-direct-release.apk
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

### Signature Analysis
- **APK Signature Scheme v2 = true:** Validates complete binary integrity against post-compilation modification.
- **Scheme v1 = false:** Eliminates vulnerable ZIP entry metadata hashing.
- **Certificate Identity:** Matches the original distribution certificate, ensuring seamless update installation over existing pilot installations on clinical tablets.

---

## 3. PLAY RELEASE AAB VERIFICATION (`jarsigner` & `bundletool`)

### 3.1 Jarsigner Verification
```bash
$ jarsigner -verify -verbose -certs \
    android/app/build/outputs/bundle/playRelease/app-play-release.aab
jar verified.
```
- **Signer Certificate:** `CN=Transify Release, OU=Transify Assistive Health, O=Safin313, L=Dhaka, ST=Dhaka, C=BD`
- **Certificate Fingerprint:** `SHA-256: 63b8cecac17e061c1eef4dbcc13979b72e4ab23407a8daa6467504092550b12e`
- **Upload Key Note:** The AAB is signed using the currently registered Google Play upload key. The replacement upload key (`9A:A3:EB...`) remains staged locally until Google Play Console confirms activation.

### 3.2 Bundletool Structure Validation
```bash
$ java -jar /home/safin313/.local/bin/bundletool.jar validate \
    --bundle=android/app/build/outputs/bundle/playRelease/app-play-release.aab
```
- **Result:** Exit code `0` (Success).
- **Inspected Modules:** Feature module `base` verified, containing `classes.dex`, compiled resources, AndroidManifest.xml, and ProGuard obfuscation map (`BUNDLE-METADATA/com.android.tools.build.obfuscation/proguard.map`).

---

## 4. RELEASE ARTIFACTS INVENTORY & CHECKSUMS

```
+------------------------------------------------------------------------------------------------------------------------------------------+
| Artifact Path                                                   | Size   | SHA-256 Checksum                                              |
+------------------------------------------------------------------------------------------------------------------------------------------+
| android/app/build/outputs/apk/direct/release/app-direct-release.apk| 1.8 MB | 8621c1bd79b4acf28545c536a66b7303694f693662da313ef6c522dd4479fbe7 |
| android/app/build/outputs/bundle/playRelease/app-play-release.aab | 2.5 MB | 9614af569af81681e280dfa23c3db39464f89f4d8c92c78f8db0a9e700b3e4bd |
+------------------------------------------------------------------------------------------------------------------------------------------+
```
