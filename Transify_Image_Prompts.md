# Transify Photography Style Bible & Generation Pack (Production)

This document governs all documentary photography and assistive imagery in Transify 2.0. Transify is an assistive communication application serving Deaf, hard-of-hearing, blind, low-vision, and non-verbal communities across English and Bengali contexts.

---

## 1. Photographic Tenets & Style Bible

All imagery adheres strictly to a shared documentary photographic look:
```
Documentary photograph, natural window light, 35mm lens, shallow depth of field,
muted realistic colour grading with slightly desaturated tones, fine film grain,
candid unposed moment, South Asian setting (Dhaka, Bangladesh), authentic everyday
clothing, no text, no logos, no watermarks, no illustration, no 3D render,
no cartoon, no glossy stock-photo look.
```

### Global Negative Prompt
```
cartoon, illustration, vector art, 3d render, CGI, plastic skin, oversaturated,
HDR glow, deformed hands, extra fingers, fused fingers, extra limbs, text, letters,
watermark, logo, stock photo smile, staged pose, looking at camera with a forced grin
```

### Core Design Rules
1. **Dignity & Everyday Life**: Active, empowered people communicating naturally. No pity, struggle, or "inspiration" tropes.
2. **Hand Anatomy Integrity**: Clear, anatomically accurate hands with motion-blurred gestures to guarantee realistic handshapes for BdSL and ASL.
3. **Scrim & Grain Integration**: Scrim overlays (`photo-scrim`) guarantee a minimum 4.5:1 text contrast for all overlaid interface typography, backed by subtle CSS SVG noise (`feTurbulence`) film grain.

---

## 2. Production Asset Registry

| Slot # | Role / Name | Primary File | Responsive Sizes | Alt Text (Communication-Centric) |
|---|---|---|---|---|
| **Slot 1** | Welcome Hero / Cover | `welcome-sign` (`hero-sign-welcome`) | AVIF, WebP, JPG, LQIP (800w, 1600w, master) | *"Two people communicating in sign language across a desk"* |
| **Slot 2** | Sign Translator / Camera Viewport | `sign-camera` (`tile-sign-camera`) | AVIF, WebP, JPG, LQIP (800w, 1600w, master) | *"Person signing directly toward laptop camera"* |
| **Slot 3** | Braille Scanner / Reader | `braille-page` (`braille-bg-wide`) | AVIF, WebP, JPG, LQIP (800w, 1600w, master) | *"Braille document with embossed dots in raking light"* |
| **Slot 4** | Voice Hub / Captions | `voice-cafe` (`voice-bg-wide`) | AVIF, WebP, JPG, LQIP (800w, 1600w, master) | *"Person reading live speech captions on phone"* |
| **Slot 5** | Home Sign Wide Room | `sign-bg-wide` | AVIF, WebP, JPG, LQIP (800w, master) | *"Person signing toward laptop in a sunlit room"* |
| **Slot 6** | Home Braille Tile (1:1) | `braille-tile` (`tile-braille-embossed`) | AVIF, WebP, JPG, LQIP (800w, 1600w, master) | *"Fingertips resting lightly on embossed Braille paper dots"* |
| **Slot 7** | Home Voice Tile (1:1) | `voice-tile` (`tile-voice-caption`) | AVIF, WebP, JPG, LQIP (800w, 1600w, master) | *"Person reading live speech captions on smartphone"* |
| **Extra 1** | Auth Screen Background | `auth-bg` (`login-hero-bg`) | AVIF, WebP, JPG, LQIP (800w, master) | *"Soft out-of-focus warm interior background"* |
| **Extra 2** | Empty State: Sign (1:1) | `empty-sign` | AVIF, WebP, JPG, LQIP (800w, master) | *"Single open hand resting in gentle window light"* |
| **Extra 3** | Empty State: Braille (1:1) | `empty-braille` | AVIF, WebP, JPG, LQIP (800w, master) | *"Clean textured document sheet in raking window light"* |
| **Extra 4** | Empty State: Voice (1:1) | `empty-voice` | AVIF, WebP, JPG, LQIP (800w, master) | *"Phone resting on wooden table next to glass of water"* |

---

## 3. Processing & Encoding Pipeline

The automated processing script (`process_images.py`):
1. **Shared Color Grade**:
   - Saturation reduced by 12% (`enhance(0.88)`).
   - Shadows lifted slightly with non-linear tone curve (`8 + (x/255)^0.97 * 247`).
2. **Next-Gen Compression**:
   - **AVIF**: SVT-AV1 (`libsvtav1`, CRF 35, YUV420p). Hero files average **30–42 KB** (well under the 120 KB threshold).
   - **WebP**: Native Pillow (Quality 75, Method 6). Files average **24–50 KB**.
   - **Progressive JPEG**: Fallback (Quality 82, optimized).
   - **LQIP (Low Quality Image Placeholder)**: 24px wide blurred JPEG (~700 bytes) for zero Cumulative Layout Shift (CLS).
3. **HTML Modern Picture Implementation**:
   ```html
   <picture>
     <source srcset="/static/photos/welcome-sign.avif" type="image/avif">
     <source srcset="/static/photos/welcome-sign.webp" type="image/webp">
     <img src="/static/photos/welcome-sign.jpg" alt="Two people communicating in sign language across a desk" width="1600" height="2000">
   </picture>
   ```
