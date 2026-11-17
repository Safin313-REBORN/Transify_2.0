# Transify — Comprehensive End-User Manual & Operational Guide

> **Document:** End-User Operational Manual  
> **Accessibility Standard:** WCAG 2.1 AAA Compliant  
> **App Version:** Transify 1.0  

---

## 1. Introduction & Target Audiences

Transify is designed to be fully usable by individuals with varying communicative and sensory needs:
1. **Deaf & Hard of Hearing Users:** Translate spoken words into live, readable captions via Speech-to-Text.
2. **Speech-Impaired / Non-Verbal / Mute Communicators:** Express intentions using hand signs, A–Z fingerspelling, or 1-tap quick phrases, which Transify speaks aloud via Text-to-Speech.
3. **Blind & Visually Impaired Users:** Digitize and listen to embossed paper Braille documents through camera photo capture and audio playback.
4. **General Communicators & Caregivers:** Seamless bidirectional communication with anyone regardless of sensory barriers.

---

## 2. Navigating the Interface

### 2.1 Home Screen Overview
- Upon opening `http://localhost:8000/`, you are greeted with the **Transify Services Planner**.
- **Four Core Feature Panels:**
  1. 🖐️ **Hand Signal Card:** Live Sign Language & Gesture AI.
  2. ⠃ **Braille Language Card:** Optical Braille document scanner.
  3. 🎙️ **Speech to Text:** Real-time microphone captions.
  4. 🔊 **Text to Speech:** Natural voice synthesizer.
- **Top Bar:** Quick profile avatar and navigation back to home.
- **Slide Navigation:** Clicking any card opens a fluid, hardware-accelerated slide panel. Click **`← Home`** or press **`Esc`** at any time to return.

---

## 3. Module 01: Hand Signal Translator

### Step-by-Step Instructions:
1. **Open the Panel:** Click the **Hand Signal** card on the home screen.
2. **Start Camera:** Click the **`📹 Start Camera`** button and allow camera access when prompted by the browser.
3. **Target Box Positioning:** 
   - A colored target guide box appears on the video feed.
   - Use the **`👉 Right`**, **`🎯 Center`**, or **`👈 Left`** buttons to place the box where you prefer to hold your hand.
   - *Note:* Recognition activates when your hand is positioned inside the target box.
4. **Mode Selection (3 Switchable Modes):**
   - **🖐️ Live Expressions:** Real-time continuous sign recognition with debounce consensus.
   - **✋ A–Z Alphabet Speller:** Displays an interactive 26-letter virtual alphabet grid. Tap any letter to spell out words letter-by-letter.
   - **📚 Common Vocabulary:** Expands quick-tap buttons for essential life needs:
     - *Emergency:* `I Need Help`, `Stop`, `Pain`, `Doctor`, `Restroom`.
     - *Daily Needs:* `Water`, `Food`, `Sleep`, `Home`.
     - *Social:* `Hello`, `Thank You`, `Please`, `Yes`, `No`, `Okay`.
5. **Continuous Sentence Stream:**
   - As you sign or spell words, they automatically accumulate into the **Live Sentence Stream** below.
   - Click **`🔊 Speak Sentence`** to vocalize your complete thought.
   - Click **`✨ Synthesize Thought`** to convert raw keywords into natural, polite English.

---

## 4. Module 02: Braille Document Scanner

### Step-by-Step Instructions:
1. **Open the Panel:** Click the **Braille** card on the home screen.
2. **Upload Document Image:**
   - Drag and drop any photo or scan of physical embossed Braille into the dropzone, or click **Browse Files**.
   - Supported formats: PNG, JPG, JPEG, BMP, WebP.
3. **Automatic Quality Assessment & Translation:**
   - Once selected, Transify automatically evaluates the image sharpness and contrast (IQA).
   - If acceptable, dots are classified using the 99.4% ExtraTrees model.
4. **Reviewing the Output:**
   - The translated English text appears in the text area.
   - If confidence is $\ge 98\%$, the green **`🎯 CUSTOM AI MODEL (>= 98%)`** badge is displayed.
   - If confidence is $< 98\%$, the system automatically switches to the **`🤖 MCP Resolver`** and displays a yellow notification.
5. **Speech & Export:**
   - Click **`🔊 Speak Text`** to hear the translated document read aloud.
   - Click **`📋 Copy`** to copy text to clipboard.
   - Click **`⬇️ Download`** to save a `.txt` file.

---

## 5. Module 03: Speech-to-Text (STT)

### Step-by-Step Instructions:
1. **Open the Panel:** Click the **Speech to Text** card.
2. **Select Language:** Choose **English (US)**, **English (UK)**, or **Bengali (BD)** from the dropdown.
3. **Start Listening:** Click the large microphone button (🎙️).
4. **Speak Clearly:** As you speak, real-time interim text appears in orange italics, followed by finalized high-confidence text.
5. **Font Scaling:** Click **`🔍 Font: Large / Extra Large`** to increase caption size for easier distance viewing.
6. **One-Click Send to TTS:** Click **`🔊 Speak Back (TTS)`** to immediately forward the recognized text into the Text-to-Speech synthesizer.

---

## 6. Module 04: Text-to-Speech (TTS)

### Step-by-Step Instructions:
1. **Open the Panel:** Click the **Text to Speech** card.
2. **Enter Text:** Type any message into the text area.
3. **Configure Voice:**
   - Select your preferred voice locale.
   - Set the playback speed (**0.8x**, **1.0x**, or **1.2x**).
4. **Quick Phrases (1-Tap Speak):**
   - Click any preset card (e.g., *"Need assistance"*, *"Where is the restroom?"*, *"Thank you"*) to speak it immediately.
5. **Playback Controls:** Click **`🔊 Speak Voice`** to play or **`⏹️ Stop`** to cancel.

---

## 7. Accessibility & Keyboard Shortcuts

- **`Escape` Key:** Closes any active slide modal and returns to the home screen.
- **`Tab` / `Shift + Tab`:** Cycles sequentially through all interactive controls in a logical WCAG-compliant order.
- **Screen Reader Announcements:** Dynamic live region updates (`aria-live="assertive"`) ensure screen reader users hear state changes, transcription results, and errors.
