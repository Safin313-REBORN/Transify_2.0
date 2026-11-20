# Changelog — Transify 2.0

## [2.1.0] - Desktop & Tablet UI Rebuild (Pixel-Exact Alignment)

### Overview
Rebuilt and aligned the desktop and tablet frontend interface (viewports 768px and wider) to be pixel-exact with the official design references (`DesktopHome.dc.html`, `DesktopSign.dc.html`, `DesktopPhrases.dc.html`, `DesktopCover.dc.html`), while seamlessly integrating new features including Transify Care using identical design tokens and typography.

### Changes Per Screen

#### 1. App Shell & Navigation (§5)
- Implemented a persistent, sticky 112px left rail navigation (`#0E0C17` on `#sign`, `#14111F` on other views).
- Centered 6-dot Transify logo at top (9px dots in 2x3 grid with 5px gap).
- High-contrast SVG icons and labels for Home, Sign, Braille, Voice, Phrases, with Settings pinned to the bottom.
- Active state styled with `#FFCB05` yellow background and dark ink text; hover state styled with subtle white translucent background.
- Responsive tablet adjustment (768–1023px): rail width adjusts to 80px while preserving 14px accessible typography.

#### 2. Welcome Cover Screen (`#welcome`) (§10)
- Split-screen layout (Stage flex: 1, Aside: 540px).
- Left stage features photo gradients with SVG grain overlay and live interactive demos:
  - Sign demo: 388x388 hand skeleton with corner marks, scanning beam, typed word and confidence readout.
  - Braille demo: Interactive 6-dot braille cell with touchable dots and live A–Z character mapping.
  - Voice demo: Live caption card, 32-bar animated waveform, and 84px microphone toggle with 3 expanding concentric rings.
- Right panel features Transify branding, pause/play toggle, English/Bangla language switcher, animated headline line reveals, 3-step story tablist with 5.6s auto-advancing yellow progress bars, and CTAs ("Create account", "Log in", "Continue without an account").

#### 3. Home Screen (`#home`) (§7)
- 3-column CSS grid layout (112px rail, 1fr main content, 320px aside).
- Dynamic local-hour greeting ("Good morning", "Good afternoon", "Good evening") and user display name.
- Say-aloud bar with 56px input, 4 quick phrase chips, and purple "Speak" button showing 4 animated yellow waveform bars during active speech synthesis.
- Bento grid of 3 main tiles:
  - Tile 1 (Sign): 2-row span with radial gradient, grain, decorative animated hand SVG, floating arrow `.go`, and subtitle.
  - Tile 2 (Braille): "Read Braille" scanner card.
  - Tile 3 (Voice): "Voice hub" live captions and TTS card.
  - Featured Transify Care banner linking to accessible symptom intake and clinician triage portal.
- Right aside with recent translations and device privacy card.

#### 4. Sign Translator (`#sign`) (§6)
- Stage with mirrored video and canvas feeds, radial gradient fallback, grain overlay, and top scrim.
- Header bar with back button, 30px title, status chip, stop camera button, and BdSL/ASL toggle.
- Centered target ROI box (aspect ratio 1 / 0.92) with 4 yellow corner brackets and violet scanning beam.
- Camera-off overlay with 48px camera icon, truthful processing notice, and 60px "Start camera" button (camera never starts automatically).
- 520px result panel with Words/Letters/Sentence mode tabs, 3 progress debounce segments, auto-fitting recognized word (96px down to 40px), 104x104 SVG circular confidence ring, "Speak word", and "Add to sentence" action buttons.
- Dark sentence container with token chips, synthesized smooth sentence, and blinking yellow caret.

#### 5. Phrases Hub (`#phrases`) (§8)
- 1180px centered container with 44px title and purple "Add phrase" button.
- Collapsible add phrase drawer with category selector (Everyday, Needs, Emergency).
- Search input with real-time filtering and category tablist with live counts.
- 4-column card grid at 1440px with category badges (Emergency highlighted in `#B3173F`) and 5-bar animated waveform during TTS audio playback.
- Seeded with 11 approved starter phrases.

#### 6. Braille Scanner (`#braille`) & Voice Hub (`#stt` / `#tts`)
- Aligned to identical design tokens, colors, and typography.
- Optical Braille dropzone, document translation view, and interactive 6-dot cell explorer.
- Speech-to-text live captions with 32-bar waveform, 84px pulsing microphone button, and read aloud TTS card.

#### 7. Transify Care (`#care` / `#care-intake` / `#clinician`)
- Integrated into the editorial visual system with matching cards, inputs, and urgency badges (EMERGENT, URGENT, ROUTINE).
- Offline-first symptom intake form and clinician review triage queue.

### Privacy-Copy Decision & Evidence (§12)
- **Decision:** Updated camera-off and privacy card copy to state:
  > *"Camera frames are processed to recognize your signs. Video is never stored."*
  > *"Signs, Braille and speech are processed to communicate seamlessly. Camera video is never stored."*
- **Evidence:** Analysis of `src/frontend/static/app.js` and `src/api/sign_routes.py` confirms that camera frames are captured as base64 JPEGs and transmitted via HTTP POST to `/api/sign/process_frame` for landmark detection and classification. The frames are processed in memory and never persisted to disk or cloud storage. Therefore, the mock copy claiming "Nothing is uploaded" was inaccurate, while "Camera frames are processed to recognize your signs. Video is never stored." is truthful and accurate.

### Verification & Testing
- Full pytest suite: 97 passed in 9.75s (`tests/test_full_system.py`, `tests/test_care_browser.py`, `tests/test_care_security.py`, `tests/test_care_system.py`).
- Standalone UI audit script (`scripts/ui_audit.py`) validated all 8 viewports and 6 routes:
  - Zero horizontal scroll (`scrollWidth <= innerWidth`).
  - Strict minimum font size >= 14px.
  - Zero forbidden string violations.
  - Exact §13 geometry at 1440x900 (Rail: 112px, Sign stage: 808px, Result panel: 520px, Phrases container: 1180px).
  - Reduced motion mode validated (`data-motion="reduced"` results in 0 running animations).
  - Word auto-fit validated with Latin, Bangla, and long compound labels without overflow.
