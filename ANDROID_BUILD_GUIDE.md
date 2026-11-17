# Transify — Native Android APK Wrapper & Production Guide

## 1. Overview & Architecture

**Transify Android** is a native Android APK wrapper engineered to display the full, unmodified Transify assistive communication web application inside an enterprise-grade Android WebView container. It connects native mobile hardware (camera, microphone, storage, and speech recognizers) to the existing web application without redesigning, rewriting, or breaking any web page, stylesheet, script, or AI inference model.

### Architectural Philosophy
* **Zero Web Redesign:** Every HTML file (`index.html`, `dashboard.html`, `sign.html`, `braille.html`, `login.html`), CSS stylesheet (`styles.css`), and JavaScript module (`app.js`) is delivered exactly as served by the FastAPI backend server.
* **Separation of Concerns:**
  * **Frontend & AI Inference:** Deployed on an HTTPS server running Python 3.10+ / FastAPI, serving live sign recognition (MediaPipe + Random Forest 972D) and Braille translation (ExtraTrees 244D).
  * **Native Android Host:** Manages system-level security, hardware permissions, file system access, back button navigation, native speech bridge, and lifecycle events.

```
+-------------------------------------------------------------------+
|                        Android Device                             |
|                                                                   |
|   +-----------------------------------------------------------+   |
|   |                        MainActivity                       |   |
|   |  - Hardware Acceleration, Safe Areas & Brand Theming       |   |
|   |  - OnBackPressedCallback Navigation History               |   |
|   |  - Runtime Permission Managers (Camera & Microphone)      |   |
|   |  - Dynamic SwipeRefreshLayout & Linear Progress Bar       |   |
|   +-----------------------------------------------------------+   |
|                                 |                                 |
|            +--------------------+--------------------+            |
|            |                                         |            |
|   +-------------------+                     +-------------------+ |
|   |  TransifyWebView  |                     |  Security Bridges | |
|   |  - DOM Storage    |                     |  - OriginValidator| |
|   |  - Cookies Engine |                     |  - WebMessage     | |
|   |  - Exact Origin   |                     |    Listener       | |
|   |  - Strict SSL     |                     |  - Speech Bridge  | |
|   |  - Media Autoplay |                     |  - Download Bridge| |
|   +-------------------+                     +-------------------+ |
|            |                                                      |
+------------|------------------------------------------------------+
             | HTTPS Requests (Audio, Video, JSON, Static Assets)
             v
+-------------------------------------------------------------------+
|                     FastAPI Backend Server                        |
|                                                                   |
|   +--------------------+     +--------------------------------+   |
|   |  Static / Frontend |     | REST APIs (/api/*)             |   |
|   |  - /               |     | - /api/health                  |   |
|   |  - /dashboard      |     | - /api/sign/process_frame      |   |
|   |  - /sign           |     | - /api/sign/predict            |   |
|   |  - /braille        |     | - /api/braille/translate       |   |
|   |  - /login          |     | - /api/braille/iqa             |   |
|   |  - /static/*       |     | - /api/tts                     |   |
|   +--------------------+     +--------------------------------+   |
|                                  |               |                |
|                    +-------------+               +-----------+    |
|                    v                                         v    |
|   +-------------------------------+   +-----------------------+   |
|   | Sign AI Engine (ASL + HaGRID) |   | Braille AI Engine     |   |
|   | - 972D Statistical Pooling    |   | - 244D ExtraTrees     |   |
|   | - 162D Temporal Frames        |   | - Morphological Grid  |   |
|   | - Confidence Thresholds       |   | - ICEB UEB Standard   |   |
|   +-------------------------------+   +-----------------------+   |
+-------------------------------------------------------------------+
```

---

## 2. Security Architecture & Native Bridge Hardening

### Origin-Restricted WebMessageListener
Privileged native interfaces are isolated using AndroidX `WebMessageListener` (`WebViewCompat.addWebMessageListener`):
1. **Origin Verification:** Messages are accepted only from the exact configured production origin rule (`https://your-domain.com`).
2. **Main Frame Enforcement:** Messages originating from `<iframe>` elements are rejected at the native layer (`isMainFrame == true`).
3. **Payload Bounds & Validation:**
   * Maximum payload size is capped at 10 MB to prevent memory exhaustion.
   * Action allowlist: `stt_start`, `stt_stop`, `stt_abort`, `download_blob`.
   * All parameters (language tags, filenames, base64 data) are strictly validated.
4. **Fallback:** If running on an older WebView provider lacking `WEB_MESSAGE_LISTENER` support, a fallback bridge is registered with strict URL origin checking on each invocation.

### Exact Trusted Origin Matching
* Subdomains are **not** automatically trusted (`https://sub.transify.ai` is rejected).
* Lookalike/suffix attacks are blocked (`https://transify.ai.attacker.com` is rejected).
* Protocol downgrades are blocked (`http://transify.ai` is rejected).
* SSL certificate errors are **never bypassed**; insecure connections are cancelled immediately.

### Native Speech Bridge (Continuous Recognition & Genuine Confidence)
* Connects the website's `window.SpeechRecognition` requests to Android's native `SpeechRecognizer`.
* Implements true continuous recognition: automatically restarts recognition between completed utterances until explicitly stopped by the user.
* Returns actual confidence scores reported by Android (`CONFIDENCE_SCORES`), never fabricating artificial `0.95` or `0.98` numbers.
* Automatically resumes pending speech recognition after runtime microphone permission is granted by the user.

### Reliable Blob & Braille File Downloads
* Intercepts `<a>` tags with `blob:` URLs in the web client and delivers the base64-encoded file contents through the secure bridge.
* Filenames are sanitized, stripping directory traversal sequences (`..`, `/`, `\`) and illegal characters.
* Files are saved to the device `Downloads` directory via `MediaStore.Downloads` on Android 10+ (API 29+) and public external storage on Android 7-9 (API 24-28).

---

## 3. Configuring the Production Base URL (`TRANSIFY_BASE_URL`)

The Android application loads the live Transify platform from an HTTPS production deployment. All relative API requests (`/api/sign/predict`, `/api/braille/translate`, `/api/history`, etc.) remain on the same origin.

### Option A: Via Gradle Build Command (Recommended for CI/CD)
Pass the `-PTRANSIFY_BASE_URL` parameter to the Gradle task:
```bash
cd android
./gradlew assembleDebug -PTRANSIFY_BASE_URL=https://your-transify-domain.com
```

### Option B: Via `gradle.properties`
In `android/gradle.properties`:
```properties
TRANSIFY_BASE_URL=https://your-transify-domain.com
```

### Option C: In-App Development Fallback UI
* If a debug APK is built without specifying a base URL, the application displays a clean configuration screen explaining that a valid server URL is required, providing an input field where the backend URL can be entered directly on the mobile device for that session.
* Release builds enforce a mandatory build-time check requiring an HTTPS, non-localhost `TRANSIFY_BASE_URL`.

---

## 4. Opening the Project in Android Studio

1. Launch **Android Studio**.
2. Select **Open** (or **File > Open**).
3. Navigate to the repository and select the `android/` subfolder:
   ```
   transify/android
   ```
4. Click **OK**.
5. Android Studio will automatically recognize the Gradle project, generate a local `local.properties` file matching your installed SDK, sync dependencies, and index the source tree.

---

## 5. Building and Testing the Application

### Running Automated Unit Tests
```bash
cd android
./gradlew testDebugUnitTest
```

### Building the Debug APK
```bash
cd android
./gradlew assembleDebug -PTRANSIFY_BASE_URL=https://your-transify-domain.com
```

### Build Output Location
```
android/app/build/outputs/apk/debug/app-debug.apk
```

---

## 6. Installing on an Android Device or Emulator

1. **Verify ADB Connection:**
   ```bash
   adb devices
   ```
2. **Install the APK:**
   ```bash
   adb install -r android/app/build/outputs/apk/debug/app-debug.apk
   ```
3. **Launch the Application:**
   ```bash
   adb shell monkey -p com.abrarafick.transify -c android.intent.category.LAUNCHER 1
   ```

---

## 7. Generating a Signed Release Build

### Step 1: Configure Environment Variables
```bash
export KEYSTORE_FILE="/path/to/transify-release-key.jks"
export KEYSTORE_PASSWORD="YourKeystorePassword"
export KEY_ALIAS="transify"
export KEY_PASSWORD="YourKeyPassword"
```

### Step 2: Build Signed Release APK or AAB
```bash
# Build Signed Release APK
./gradlew assembleRelease -PTRANSIFY_BASE_URL=https://your-transify-domain.com

# Build Android App Bundle (.aab) for Google Play Console
./gradlew bundleRelease -PTRANSIFY_BASE_URL=https://your-transify-domain.com
```
