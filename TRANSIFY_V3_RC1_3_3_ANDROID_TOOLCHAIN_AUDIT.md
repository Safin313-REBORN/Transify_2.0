# TRANSIFY V3 — RC1.3.3 ANDROID TOOLCHAIN & BUILD MATRIX AUDIT

**Project:** Transify V3 Android Application  
**Package Name:** `com.abrarafick.transify`  
**Milestone:** Release Candidate RC1.3.3  
**Branch:** `fix/rc1.3.3-signing-pipeline`  
**Audit Date:** November 22, 2026  

---

## 1. BUILD TOOLCHAIN ALIGNMENT

```
+----------------------------------------------------------------------------------------------------+
| Component                     | Configured Specification | Build Toolchain Provider & Status       |
+----------------------------------------------------------------------------------------------------+
| `compileSdk`                  | 36 (Android 16)          | Android SDK Platform 36 (platforms/android-36) |
| `targetSdk`                   | 36 (Android 16)          | Android 16 Behavior Target Contract     |
| `minSdk`                      | 24 (Android 7.0)         | Backwards Compatibility to Nougat       |
| Android Gradle Plugin (AGP)   | 8.9.1                    | Official Stable AGP 8.9.1               |
| Gradle Distribution           | 8.11.1                   | gradle-8.11.1-bin.zip                   |
| Kotlin Gradle Plugin          | 2.0.21                   | JetBrains Kotlin 2.0.21                 |
| Android SDK Build-Tools       | 35.0.0 / 36.0.0          | Official SDK Build-Tools                |
| Java Development Kit (JDK)    | OpenJDK 17.0.12          | Eclipse Adoptium OpenJDK 17             |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. BUILD VARIANTS & FLAVOR REGISTRATION

In RC1.3.3, Gradle product flavors were introduced to cleanly separate the release pipelines:

```kotlin
flavorDimensions += "distribution"
productFlavors {
    create("direct") {
        dimension = "distribution"
        signingConfig = signingConfigs.getByName("directRelease")
    }
    create("play") {
        dimension = "distribution"
        signingConfig = signingConfigs.getByName("playRelease")
    }
}
```

### Registered Build Variants
1. **`directDebug` / `playDebug`:** Development builds with debug instrumentation.
2. **`directRelease`:**
   - Dedicated Command: `./gradlew assembleDirectRelease`
   - Generated Artifact: `android/app/build/outputs/apk/direct/release/app-direct-release.apk`
   - Purpose: Direct side-load APK distribution for clinical hospital tablets and QA devices.
3. **`playRelease`:**
   - Dedicated Command: `./gradlew bundlePlayRelease`
   - Generated Artifact: `android/app/build/outputs/bundle/playRelease/app-play-release.aab`
   - Purpose: Android App Bundle for Google Play Console ingestion.

---

## 3. AAPT DUMP BADGING AUDIT

Running `/home/safin313/Android/Sdk/build-tools/35.0.0/aapt dump badging` against `app-direct-release.apk`:

```text
package: name='com.abrarafick.transify' versionCode='1' versionName='1.0.0' platformBuildVersionName='16' platformBuildVersionCode='36' compileSdkVersion='36' compileSdkVersionCodename='16'
sdkVersion:'24'
targetSdkVersion:'36'
uses-permission: name='android.permission.INTERNET'
uses-permission: name='android.permission.ACCESS_NETWORK_STATE'
uses-permission: name='android.permission.CAMERA'
uses-permission: name='android.permission.RECORD_AUDIO'
uses-permission: name='android.permission.MODIFY_AUDIO_SETTINGS'
application-label:'Transify'
application-icon-160:'res/mipmap-mdpi-v4/ic_launcher.png'
application-icon-240:'res/mipmap-hdpi-v4/ic_launcher.png'
application-icon-320:'res/mipmap-xhdpi-v4/ic_launcher.png'
application-icon-480:'res/mipmap-xxhdpi-v4/ic_launcher.png'
application-icon-640:'res/mipmap-xxxhdpi-v4/ic_launcher.png'
```

### Architectural Findings
- **`compileSdkVersion='36'`:** Bytecode is compiled directly against Android 16 framework classes.
- **`targetSdkVersion='36'`:** Runtime behavior contract explicitly targets Android 16.
- **Window Inset Management:** Implemented in `MainActivity.kt` for Edge-to-Edge compliance.
- **16 KB Memory Page Alignment:** Zero native C/C++ libraries (`.so`); 100% compliant with 16 KB page-size kernels.
