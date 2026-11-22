# TRANSIFY V3 — RC1.3.1 PHYSICAL ANDROID HARDWARE VALIDATION GATE CHECKLIST

**Document ID:** `TRANSIFY-HW-GATE-RC1.3.1`  
**Target Package:** `com.abrarafick.transify`  
**Target APK Artifact:** `android/app/build/outputs/apk/release/app-release.apk`  
**Target AAB Artifact:** `android/app/build/outputs/bundle/release/app-release.aab`  
**Gate Status:** **OPEN / DEFERRED (0 Physical Devices Attached to Host)**  
**Target Devices:** Physical Android smartphones & clinical tablets (Samsung, Xiaomi, Pixel, Transsion) running Android 7.0 (API 24) through Android 15/16 (API 35/36).  

---

## 1. PURPOSE & GATE DEFINITION

To ensure complete empirical integrity and zero fabrication of hardware results, Gate 3 (Physical Android Device Validation) cannot be closed using automated software unit tests or simulated viewports.

This checklist establishes the mandatory 8-phase protocol that a physical device QA engineer or release manager must execute upon connecting an authorized Android physical handset via USB or Wi-Fi ADB.

---

## 2. PRE-REQUISITE PHYSICAL ENVIRONMENT SETUP

- [ ] **Physical Device:** Android smartphone or tablet with USB debugging enabled in Developer Options.
- [ ] **USB Host Cable:** High-speed data cable connected to workstation.
- [ ] **Host Verification Command:**
  ```bash
  $ adb devices -l
  # EXPECTED OUTPUT:
  # List of devices attached
  # <device_serial_number>   device usb:<bus-info> product:<model> model:<device_name> device:<hw_id>
  ```
- [ ] **Logcat Streaming Terminal:**
  ```bash
  $ adb logcat -c && adb logcat -s TransifyApp:V Chromium:W SystemWebChromeClient:D
  ```

---

## 3. STEP-BY-STEP PHYSICAL VALIDATION PROTOCOL

### Phase 1: Clean APK Installation & Signature Check
- [ ] **Command:**
  ```bash
  adb install -r android/app/build/outputs/apk/release/app-release.apk
  ```
- [ ] **Verification Criteria:**
  - `Success` returned by package manager.
  - No `INSTALL_PARSE_FAILED_NO_CERTIFICATES` error (verifies APK Signature Scheme v2).
  - App icon "Transify" appears in device app drawer with adaptive icon.

### Phase 2: Cold Launch & Runtime Permissions
- [ ] **Launch Command:**
  ```bash
  adb shell am start -n com.abrarafick.transify/.MainActivity
  ```
- [ ] **Verification Criteria:**
  - Splash screen transitions cleanly to the production WebView within **< 1.8 seconds**.
  - Camera permission dialog appears when navigating to Sign Language or Braille Scanner view.
  - Microphone permission dialog appears when opening Speech-to-Text translation.
  - Denying permission displays a non-blocking in-app advisory banner without crashing.
  - Granting permission activates the respective hardware subsystem.

### Phase 3: Camera Sensor Preview & Sign Inference
- [ ] **Action:** Open BdSL Sign Language Detection module with front and rear camera.
- [ ] **Verification Criteria:**
  - Camera preview renders smoothly without black screen or aspect ratio distortion.
  - Sensor frame rate is measured (target: **30 FPS sustained** without thermal throttling over 5 minutes).
  - WebRTC / MediaStream video track feeds landmark extractor without dropping frames.
  - Detection bounding box tracks hand landmarks in real-time.
  - Test sign gesture (e.g. "HELLO" or "I NEED HELP") triggers inference display with confidence score **>= 0.80**.

### Phase 4: Touchscreen Multi-Touch & Perkins Braille Chording
- [ ] **Action:** Open Perkins Braille Virtual Input interface.
- [ ] **Verification Criteria:**
  - Multi-touch chord registration: Pressing 2, 3, or 6 touch points simultaneously registers all dots without ghost touches or input drop.
  - Touch targets conform to minimum 48x48 dp physical tap bounds on handset screen.
  - Haptic feedback vibrates subtly upon valid Braille cell commit.
  - Translation display updates instantaneously with corresponding Bengali or English character.

### Phase 5: Virtual Keyboard (IME) Insets & Responsive Reflow
- [ ] **Action:** Focus on input fields in the Clinical Care vital logging form and AI Chatbot.
- [ ] **Verification Criteria:**
  - Soft keyboard (Gboard, Samsung Keyboard, or Ridmik Keyboard) opens smoothly.
  - Window insets resize content dynamically without obscuring the active input field or submit button.
  - Viewport scroll restores naturally upon closing the software keyboard.
  - No horizontal scrolling or content clipping occurs during IME display.

### Phase 6: Zero Auto-Audio & Explicit Audio Bridge Verification
- [ ] **Action:** Test all navigation tabs, alerts, triage cards, and AI chat responses.
- [ ] **Verification Criteria:**
  - **Zero Auto-Audio Enforcement:** Confirm absolute silence upon page navigation, modal opening, emergency alert trigger, or chatbot response generation.
  - **Explicit Audio Playback:** Tapping the explicit "Listen" (স্পিকার / অডিও শুনুন) button triggers Android TextToSpeech (`TTSBridge`) with natural pronunciation in Bengali (`bn_BD`) or English (`en_US`).
  - Audio immediately stops when leaving the tab or pressing "Stop".

### Phase 7: Network Disruption & Offline Resilience
- [ ] **Action:** Toggle Android Device "Airplane Mode" on, then off.
- [ ] **Verification Criteria:**
  - Status banner displays offline indicator within **< 500 ms** via `NetworkMonitor`.
  - Offline cached features (Perkins Braille, local sign dictionary, cached triage instructions) remain fully functional.
  - Restoring connectivity seamlessly reconnects to Railway production backend without page reload or session loss.

### Phase 8: System Process Termination & Session Restoration
- [ ] **Action:** Put app in background and simulate OS memory reclamation:
  ```bash
  adb shell am kill com.abrarafick.transify
  adb shell am start -n com.abrarafick.transify/.MainActivity
  ```
- [ ] **Verification Criteria:**
  - App relaunches cleanly without ANR (Application Not Responding) dialog.
  - User session state, selected language, and active clinical workflow are properly restored.

---

## 4. GATE SIGN-OFF CRITERIA

| Requirement | Required Outcome | QA Sign-off |
| :--- | :--- | :--- |
| **All 8 Phases Executed on Physical Device** | 100% Pass without unhandled exceptions | `[ ] PENDING PHYSICAL DEVICE` |
| **Logcat Zero Fatal Exceptions** | No crash in `com.abrarafick.transify` | `[ ] PENDING PHYSICAL DEVICE` |
| **Thermal & Battery Profiling** | Normal power consumption during camera use | `[ ] PENDING PHYSICAL DEVICE` |

*Note: Once this checklist is completed on a physical handset, Gate 3 can be updated to CLOSED / FULLY APPROVED for General Availability (GA).*
