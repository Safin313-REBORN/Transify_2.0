# TRANSIFY V3 — RC1.3 APK & AAB RELEASE ARTIFACT VERIFICATION

**Date:** November 22, 2026  
**Repository:** `Safin313-REBORN/Transify_2.0`  
**Branch:** `main`  
**Checkpoint:** `3832a5f` (Published to `origin/main`)  
**Package:** `com.abrarafick.transify`  
**Auditor:** Principal Android Release Engineer & Mobile Security Specialist  
**Status:** **VERIFIED, MINIFIED, SIGNED & READY FOR STAGING**  

---

## 1. Executive Summary

This report certifies the integrity, security, cryptographic signing, and configuration compliance of the production release artifacts generated for Transify V3.

Both the **Android App Bundle (.aab)** for Google Play Console distribution and the **Standalone Release APK (.apk)** for direct sideloading and internal testing have been compiled with R8 whole-program optimization, asset shrinking, and cryptographically signed using a dedicated release certificate.

```
+------------------------------------------------------------------------------------------------------+
| Artifact Attribute           | Certified Specification                                               |
+------------------------------------------------------------------------------------------------------+
| Application ID               | com.abrarafick.transify                                               |
| Version Code                 | 1                                                                     |
| Version Name                 | 1.0.0                                                                 |
| Target SDK                   | API 36 (Android 16) — November 2026 Google Play Mandate Compliant     |
| Minimum SDK                  | API 24 (Android 7.0 Nougat)                                           |
| Compile SDK                  | API 34                                                                |
| Optimization Engine          | R8 Compiler + Proguard Resource Shrinker Enabled                      |
| Cryptographic Scheme         | APK Signature Scheme v2 (Verified)                                   |
| Keystore Location            | ~/.transify_release/transify-release.keystore (Outside Git)           |
+------------------------------------------------------------------------------------------------------+
```

---

## 2. Release Artifact Files & Cryptographic Checksums

```
+---------------------+---------------------------------------------------------+----------+------------------------------------------------------------------+
| Format              | Relative File Path                                      | Size     | SHA-256 Checksum                                                 |
+---------------------+---------------------------------------------------------+----------+------------------------------------------------------------------+
| Android App         | android/app/build/outputs/bundle/release/app-release.aab| 2.0 MB   | 6873aead8ec7867a7062334927053d2d70fb2086055d968e3de79bed41797f85|
| Bundle (.aab)       |                                                         |          |                                                                  |
+---------------------+---------------------------------------------------------+----------+------------------------------------------------------------------+
| Standalone Release  | android/app/build/outputs/apk/release/app-release.apk   | 1.8 MB   | c9c09ce3469d8615a8bffddc0f5cc042b6b8594c3956f91cdda0d5ece8071f67|
| APK (.apk)          |                                                         |          |                                                                  |
+---------------------+---------------------------------------------------------+----------+------------------------------------------------------------------+
```

---

## 3. Cryptographic Signature & Certificate Details

Command executed:
```bash
$ /home/safin313/Android/Sdk/build-tools/34.0.0/apksigner verify --verbose --print-certs \
  android/app/build/outputs/apk/release/app-release.apk
```

### Signature Verification Output:
- **Signature Status:** **Verifies**
- **Verified via v1 scheme (JAR signing):** `false`
- **Verified via v2 scheme (APK Signature Scheme v2):** **`true`**
- **Verified via v3 / v4 scheme:** `false`
- **Number of signers:** 1
- **Signer #1 Certificate DN:** `CN=Transify Release, OU=Transify Assistive Health, O=Safin313, L=Dhaka, ST=Dhaka, C=BD`
- **Signer #1 Key Algorithm:** `RSA 2048-bit`
- **Signer #1 Public Key SHA-256:** `7420e385f7b7a6f5436128b5874eb698ed080c717e894c8590b0a2648446c19e`
- **Signer #1 Certificate SHA-256:** `63b8cecac17e061c1eef4dbcc13979b72e4ab23407a8daa6467504092550b12e`
- **Signer #1 Certificate SHA-1:** `6c5d2f86d15d2603872feae46712bf261c97f512`

---

## 4. Manifest Configuration & Permission Analysis

Output from `aapt dump badging`:
```
package: name='com.abrarafick.transify' versionCode='1' versionName='1.0.0'
sdkVersion:'24'
targetSdkVersion:'36'
application-label:'Transify'
```

### Certified Release Permissions:
1. `android.permission.INTERNET`: Required for connecting to the Transify Care server backend.
2. `android.permission.ACCESS_NETWORK_STATE`: Required by `NetworkMonitor.kt` for connectivity loss detection and graceful recovery.
3. `android.permission.CAMERA`: Required for real-time sign language recognition and Braille document OCR snapshots. Declared with `required=false` so devices without hardware cameras can still install the app.
4. `android.permission.RECORD_AUDIO`: Required for native Speech-to-Text via `SpeechRecognizer`. Declared with `required=false`.
5. `android.permission.MODIFY_AUDIO_SETTINGS`: Required for routing speech audio to speakerphone or headset.
6. `android.permission.WRITE_EXTERNAL_STORAGE (maxSdkVersion=28)`: Legacy download permission restricted to Android 9 and lower. On Android 10+ (API 29+), `FileProvider` app-private storage is used exclusively.

---

## 5. R8 Minification & Code Optimization Verification

- **Code Minification:** Enabled (`isMinifyEnabled = true`).
- **Resource Shrinking:** Enabled (`isShrinkResources = true`).
- **ProGuard Retention Rules:** Preserved `@JavascriptInterface` reflection methods, `androidx.webkit.**`, and all native host bridges under `com.abrarafick.transify.**`.
- **Optimization Impact:** APK footprint was reduced by **69.5%** (from 5.9 MB unminified debug APK to 1.8 MB optimized release APK).

---

## 6. Bundletool Archive Integrity

- Executed `unzip -t android/app/build/outputs/bundle/release/app-release.aab`.
- Result: **Zero errors detected in compressed data**.
- Signed bundle structure confirmed (`META-INF/TRANSIFY.SF`, `META-INF/TRANSIFY.RSA`, `META-INF/MANIFEST.MF` verified).
