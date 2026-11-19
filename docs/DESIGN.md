# Transify 2.0 — Design System & UI/UX Specification

**Design System Name:** Transify Kinetic Glass  
**Compliance Standard:** WCAG 2.1 Level AAA · Section 508 · Web Content Accessibility Guidelines  
**Target Viewports:** 320px (Mobile SE), 375px–414px (Mobile Standard), 768px (Tablet), 1280px+ (Desktop)  
**Date:** November 19, 2026

---

## 1. Design Philosophy

Transify 2.0 is built on the philosophy of **Empathetic Utility**: assistive technology should not look clinical or generic. It should feel modern, tactile, luminous, and fluid while maintaining absolute clarity and predictability for users with sensory, cognitive, or motor impairments.

### Core Principles
1. **Sensory Transparency:** Never hide status or trigger unexpected audio. Text is primary; audio is deliberate.
2. **Tactile Affordance:** Buttons, handles, and interactive cards provide clear physical feedback (hover lift, spring scale, luminous sheen sweep).
3. **Calibrated Physics:** Natural easing curves (`--ease-out-expo` and `--ease-spring`) replace linear or abrupt animations.
4. **Absolute Vestibular Safety:** When reduced motion is requested, all transitions snap instantly ($0.01\text{ ms}$) and all spatial translations are eliminated.

---

## 2. Color System & Design Tokens

Transify uses a high-contrast violet/purple semantic palette with WCAG AAA compliant contrast ratios ($\ge 7:1$ on text, $\ge 3:1$ on UI boundaries).

```css
:root {
  /* Brand Core */
  --primary-violet: #7c3aed;       /* Primary interactive actions */
  --primary-violet-hover: #6d28d9; /* Active/pressed state */
  --neon-violet: #b075fe;          /* Ambient glow and accent badge */
  --primary-glow: rgba(124, 58, 237, 0.28);

  /* Surface & Canvas */
  --bg-canvas-start: #f5f3ff;
  --bg-canvas-mid: #ede9fe;
  --bg-canvas-end: #f3e8ff;
  --card-bg: rgba(255, 255, 255, 0.94);
  --card-border: rgba(131, 56, 236, 0.16);

  /* Text & Contrast */
  --text-dark: #1e1b4b;            /* AAA contrast on light backgrounds (12.4:1) */
  --text-muted: #475569;           /* Secondary labels (5.2:1 contrast) */
  --text-white: #ffffff;           /* AAA contrast on primary violet (7.6:1) */

  /* Semantic Feedback */
  --status-success: #10b981;       /* Emerald confirmation */
  --status-warning: #f59e0b;       /* Amber target box / unsaved indicator */
  --status-error: #ef4444;         /* Crimson validation alert */
  --status-error-bg: #fef2f2;
}
```

---

## 3. Typography Hierarchy

The typographic system utilizes `Inter` with native system font fallbacks for instantaneous rendering:

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
```

| Element | Size | Weight | Line Height | Tracking | Purpose |
| :--- | :-: | :-: | :-: | :-: | :--- |
| **Hero Title** | `32px` (`2rem`) | `800` | `1.2` | `-0.025em` | Main application identity & welcome banner |
| **Section Title** | `22px` (`1.375rem`) | `700` | `1.3` | `-0.015em` | Card titles, slide modal headings |
| **Card Header** | `17px` (`1.06rem`) | `700` | `1.4` | `0` | Action cards, Hub contact names |
| **Body Primary** | `15px` (`0.94rem`) | `500` | `1.5` | `0` | Conversation messages, translation output |
| **Caption / Badge** | `13px` (`0.81rem`) | `600` | `1.4` | `0.02em` | Status chips (`Saved`, `HaGRID`), timestamps |

---

## 4. Motion System & Physics Dials

Transitions follow calibrated physical timing models:

```css
:root {
  --transition-fast: 160ms;
  --transition-normal: 280ms;
  --transition-slow: 450ms;

  /* Cubic Beziers */
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);     /* Smooth deceleration */
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);    /* Micro-bounce on toggles */
  --ease-smooth: cubic-bezier(0.4, 0, 0.2, 1);         /* Continuous flow */
}
```

### Micro-Interactions
1. **Luminous Button Sheen:** Action buttons (`.btn-primary`, `.auth-submit-action`) sweep an angled 45° luminous linear gradient on hover.
2. **Arrow Glide:** Action arrows (`.btn-arrow`, `.auth-guest-arrow`) translate $+4\text{px}$ horizontally with smooth spring recovery.
3. **Tactile Sheet Drag Handle:** `.auth-sheet-drag-handle` expands from $40\text{px}$ to $48\text{px}$ with a violet glow on hover.
4. **Validation Shake:** Validation errors trigger an energetic 400ms shake (`@keyframes authShake`), while success toasts pop in with `@keyframes popIn`.
5. **Concentric STT Pulse:** Microphone recording state displays multi-ring radial wave pulses (`@keyframes micRipplePulse`).
6. **Organic Ambient Breathing:** Background shapes smoothly scale ($1.0$ to $1.08$) and drift across 16s loops without CPU thrashing.

---

## 5. Strict Accessibility Rules

### 1. Mandatory NO-AUTO-AUDIO Rule
- **Rule:** Translations and transcripts must NEVER play audio automatically.
- **Enforcement:** Audio plays exclusively upon an explicit user click on a speaker button (`🔊`).
- **Rationale:** Unexpected audio causes severe distress to Deaf and hard-of-hearing users in public or quiet environments.

### 2. Reduced Motion Enforcement
```css
@media (prefers-reduced-motion: reduce), (update: slow) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
    transform: none !important;
  }
}
```

### 3. Touch Targets & Focus Indicators
- All interactive controls maintain a minimum touch bounding box of $48 \times 48\text{ px}$.
- Visible 3px violet focus rings (`outline: 3px solid #7c3aed; outline-offset: 2px`) are displayed on keyboard navigation (`:focus-visible`).

