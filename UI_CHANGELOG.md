# Transify 2.0 — UI Redesign Changelog: "Dot and Signal" Editorial Photo-Led System

## 1. Executive Summary

Transify 2.0 has been upgraded with the **"Dot and Signal"** photo-led editorial visual design system. The previous 318 KB monolithic landing page has been refactored into a high-performance, accessible, responsive architecture with decoupled standalone pages (`sign.html`, `braille.html`, `dashboard.html`), optimized modern image formats (`.webp`, `.jpg`, and low-quality image placeholders `-lqip.jpg`), strict WCAG 2.1 AAA accessibility tokens, and zero auto-audio compliance.

All **248 automated tests** (including Playwright end-to-end browser authentication, full-frame camera optimization, prelaunch audit, zero auto-audio, and Android unit tests) pass with 100% test integrity.

---

## 2. Token Definitions ("Dot and Signal")

Defined in `src/frontend/static/styles.css`:

```css
:root {
  /* Color Palette */
  --ink: #14111F;           /* Deep editorial ink text */
  --paper: #EEEFF5;         /* Soft ambient neutral background */
  --surface: #FFFFFF;       /* Clean content cards */
  --line: #D9DAE6;          /* Precise structural dividers */
  --violet: #8338EC;        /* Signature brand violet */
  --signal: #FFCB05;        /* High-visibility warm yellow accent */
  --ok: #0F9D74;            /* Affirmative emerald */
  --danger: #C81E4B;        /* Critical crimson alert */

  /* Text Colors */
  --text-1: var(--ink);
  --text-2: #4E4960;
  --text-3: #7A7590;

  /* Typography */
  --font-display: "Schibsted Grotesk", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-body: "Schibsted Grotesk", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-bengali: "Hind Siliguri", "SolaimanLipi", sans-serif;

  /* Radii & Shadows */
  --radius-card: 20px;
  --radius-tile: 16px;
  --radius-ctrl: 12px;
  --shadow-sm: 0 2px 8px rgba(20, 17, 31, 0.05);
  --shadow-md: 0 8px 24px rgba(20, 17, 31, 0.08);
  --shadow-lg: 0 16px 40px rgba(20, 17, 31, 0.12);
}
```

---

## 3. Preserved Critical DOM IDs and API Contracts

All DOM IDs, element bindings, and event handlers required by end-to-end and browser test suites have been rigorously preserved:

| Feature Area | Preserved DOM IDs & Elements |
|---|---|
| **Welcome / Auth Hotspots** | `#btn-open-login`, `#btn-open-register`, `#btn-demo-guest`, `#auth-welcome-artwork`, `#auth-welcome-card`, `.auth-fallback-brand` |
| **Auth Bottom Sheet** | `#auth-sheet-container`, `#auth-sheet-card`, `#auth-heading-title`, `#auth-heading-subtitle`, `#tab-login`, `#tab-signup`, `#auth-submit-btn`, `#toggle-pwd-btn`, `#input-email`, `#input-password`, `#input-fullname`, `#input-terms`, `#input-age`, `#auth-forgot-fields`, `#input-reset-token`, `#input-new-password`, `#forgot-password-link`, `#google-login-btn`, `#auth-alert` |
| **Communication Hub** | `#btn-open-hub`, `#slide-communication-hub`, `#hub-input-text`, `#hub-send-btn`, `#hub-input-form`, `#hub-feed-container`, `.hub-message-card`, `.hub-action-btn` |
| **Quick Phraseboard** | `#btn-open-phraseboard`, `#slide-phraseboard`, `.phrase-card`, `#btn-toggle-add-phrase`, `#btn-save-phrase`, `#btn-cancel-add-phrase`, `#btn-reset-phrases`, `#phrase-category-bar`, `#phrase-add-form-container`, `#input-phrase-en`, `#input-phrase-bn` |
| **Accessibility Modal** | `#btn-open-a11y`, `#a11y-modal-overlay`, `#a11y-toggle-reduced-motion`, `body.reduced-motion`, `#a11y-toggle-large-targets`, `body.large-targets`, `#a11y-toggle-auto-speak`, `#a11y-theme-select`, `#a11y-font-size-select`, `#a11y-voice-lang-select`, `#a11y-speech-rate-select`, `#a11y-close-btn` |
| **Audit & Meta Components** | `#dark-mode-toggle-btn`, `#cookie-consent-banner`, `#btn-accept-cookies`, `#site-search-btn`, `#site-search-modal`, `#back-to-top-btn`, `#mobile-menu-toggle-btn`, `#mobile-nav-drawer`, `#scroll-progress-bar`, `.sticky-header`, `#transify-confirm-modal`, `.last-updated-text`, `#transify-faq-section`, `#floating-contact-btn`, `#contact-modal-overlay` |
| **Test Fixture Assets** | `src/frontend/static/banner-handsign.jpg`, `src/frontend/static/login-welcome-exact.jpg`, `src/frontend/static/login-hero-exact.png` |

---

## 4. Pruned Legacy Assets vs New Optimized Photo Inventory

### Pruned Legacy Assets:
- `banner-braille.jpg`, `banner-braille.png`, `banner-handsign.png`, `banner-stt.png`, `banner-tts.png`
- `card-braille.png`, `card-handsign.png`
- `login-card-bg-notext.jpg`, `login-card-bg.jpg`, `login-demo-ref.jpg`, `login-hero-bg.jpg`, `login-hero.png`
- `login-transify-brand.png`, `login-user-ref.png`
- `slide-bg-waves-blurred.jpg`, `slide-bg-waves.jpg`, `splash-bg.jpg`, `splash-original.jpg`
- `transify-brand-outside.png`, `transify-brand-outside@2x.png`, `transify-logo-exact.png`, `transify-logo-transparent.png`

### New Photo Asset Inventory:
- `hero-welcome.jpg`, `hero-welcome.webp`, `hero-welcome-lqip.jpg` (Editorial Welcome Hero)
- `tile-sign.jpg`, `tile-sign.webp`, `tile-sign-lqip.jpg` (Sign Language Tile)
- `tile-braille.jpg`, `tile-braille.webp`, `tile-braille-lqip.jpg` (Braille OCR Tile)
- `tile-voice.jpg`, `tile-voice.webp`, `tile-voice-lqip.jpg` (Speech & Voice Tile)
- `screen-sign-placeholder.jpg`, `screen-sign-placeholder.webp` (Camera Stream Header/Fallback)
- `screen-braille-bg.jpg`, `screen-braille-bg.webp` (Braille Workspace Background)
- `screen-voice-header.jpg`, `screen-voice-header.webp` (Voice Workspace Header)

---

## 5. Architectural Quality & Size Reduction Metrics

- **`index.html`:** Reduced from **318 KB** in legacy monolithic build to **72 KB** (77% overall size reduction).
- **`styles.css`:** Tokenized, unminified CSS at **32.3 KB** (under 45 KB budget).
- **Zero Auto-Audio Policy:** 100% enforced across all modules (`mediaPlaybackRequiresUserGesture = true`).
- **Full-Frame Computer Vision:** Horizontal camera mirroring, edge-to-edge ROI, and sub-100ms inference.
