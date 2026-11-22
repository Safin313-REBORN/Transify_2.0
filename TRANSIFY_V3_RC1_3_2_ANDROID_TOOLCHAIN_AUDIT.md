# TRANSIFY V3 — RC1.3.2 ANDROID TOOLCHAIN & API 36 ALIGNMENT AUDIT

**Project:** Transify V3 Android Application  
**Package:** `com.abrarafick.transify`  
**Milestone:** Release Candidate RC1.3.2  
**Target Environment:** Android 16 (API 36) Compliant Toolchain  
**JDK:** OpenJDK 17.0.12 (Eclipse Adoptium)  
**Audit Date:** November 22, 2026  

---

## 1. TOOLCHAIN VERSION MATRIX

The previous configuration (`compileSdk = 34`, `targetSdk = 36`, AGP `8.5.2`, Gradle `8.9`) has been fully aligned with modern Android 16 build requirements:

```
+--------------------------------------------------------------------------------------------------+
| Component                   | Previous (RC1.3.1) | Required (RC1.3.2) | Verified Actual Status   |
+--------------------------------------------------------------------------------------------------+
| compileSdk                  | 34 (Android 14)    | 36 (Android 16)    | 36 (ALIGNED & VERIFIED)  |
| targetSdk                   | 36 (Android 16)    | 36 (Android 16)    | 36 (ALIGNED & VERIFIED)  |
| minSdk                      | 24 (Android 7.0)   | 24 (Android 7.0)   | 24 (PRESERVED)           |
| Android Gradle Plugin (AGP) | 8.5.2              | >= 8.9.1           | 8.9.1 (UPGRADED)         |
| Gradle Distribution         | 8.9                | >= 8.11.1          | 8.11.1 (UPGRADED)        |
| Kotlin Gradle Plugin        | 2.0.21             | 2.0.21             | 2.0.21 (COMPATIBLE)      |
| Build-Tools                 | 34.0.0             | 35.0.0 / 36.0.0    | 35.0.0 / 36.0.0 INSTALLED|
| JDK Platform                | OpenJDK 17         | JDK 17             | OpenJDK 17 (Java 17)     |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. ANDROID SDK PLATFORM & BUILD-TOOLS INSTALLATION

To enable compilation against Android 16 APIs, the following official SDK packages were downloaded and verified in `/home/safin313/Android/Sdk/`:

1. **SDK Platform 36 (`platforms/android-36`):**
   - Package: `platforms;android-36` (Revision 2).
   - Source: `https://dl.google.com/android/repository/platform-36_r02.zip`.
   - Extracted to: `/home/safin313/Android/Sdk/platforms/android-36`.
   - Content: `android.jar` (API 36 core framework symbols).

2. **SDK Build-Tools 36.0.0 & 35.0.0:**
   - Packages installed:
     - `/home/safin313/Android/Sdk/build-tools/36.0.0`
     - `/home/safin313/Android/Sdk/build-tools/35.0.0`
   - Tools verified: `aapt`, `aapt2`, `apksigner`, `d8`, `zipalign`.

---

## 3. ANDROID 16 (API 36) ARCHITECTURAL COMPATIBILITY AUDIT

### 3.1 Edge-to-Edge Window Insets
- **Policy:** Android 15/16 enforces edge-to-edge layout by default for apps targeting API 35+.
- **Verification:** In `MainActivity.kt`, `ViewCompat.setOnApplyWindowInsetsListener` handles `WindowInsetsCompat.Type.systemBars()` and `WindowInsetsCompat.Type.ime()`.
- **Result:** Navigation bars, status bars, and on-screen keyboards reflow smoothly without occluding input fields or the WebView bottom navigation controls.

### 3.2 Predictive Back Navigation
- **Policy:** Supported via `OnBackPressedCallback` introduced in AndroidX Activity 1.9.0.
- **Verification:** `MainActivity.kt` registers `OnBackPressedCallback` with `webView.canGoBack()` checks.
- **Result:** Back navigation delegates to WebView browser history if available; otherwise exits or closes active modals cleanly.

### 3.3 16 KB Page-Size Memory Alignment
- **Policy:** Android 15/16 introduces support for devices with 16 KB memory page sizes (replacing standard 4 KB page sizes).
- **Verification:** The Transify Android application contains **zero unaligned native C/C++ libraries** (`.so` files). All ML inference operates in the WebView via WebAssembly/LiteRT or pure Java/Kotlin code (`mergeReleaseNativeLibs NO-SOURCE`, `stripReleaseDebugSymbols NO-SOURCE`).
- **Result:** Fully compatible with 16 KB page-size kernel configurations.

### 3.4 AndroidX Dependencies Compatibility
All core AndroidX libraries were verified for full compatibility with AGP 8.9.1 and compileSdk 36:
- `androidx.core:core-ktx:1.13.1`
- `androidx.appcompat:appcompat:1.7.0`
- `com.google.android.material:material:1.12.0`
- `androidx.activity:activity-ktx:1.9.0`
- `androidx.swiperefreshlayout:swiperefreshlayout:1.1.0`
- `androidx.webkit:webkit:1.11.0`

---

## 4. AAPT DUMP BADGING VERIFICATION

Execution of `/home/safin313/Android/Sdk/build-tools/35.0.0/aapt dump badging` on `app-release.apk` verifies exact platform alignment:

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

**Conclusion:** The application now compiles natively against API 36 (`compileSdkVersion='36'`), targets API 36 (`targetSdkVersion:'36'`), supports Android 7.0+ (`sdkVersion:'24'`), and builds using the latest stable AGP 8.9.1 and Gradle 8.11.1 toolchain.
