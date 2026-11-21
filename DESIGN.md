# DESIGN.md — Transify 2.0 Design System

## Identity & Personality
- **Character**: Precision Assistive Editorial — High-clarity, dignified, surgical legibility with bold tactile affordances for deaf, blind, and speech-impaired individuals.
- **Voice**: Direct, clinical-grade, empathetic, un-hyped. Zero generic AI buzzwords.

## Visual Dials
- **ENERGY**: 2 (Confident, punchy, high legibility contrast without garish neon slop)
- **RHYTHM**: 2 (Structured asymmetrical cards, alternating interactive controls and data visualizations, avoiding monotonous identical grids)
- **MOTION**: 1 (Instant / functional 150–200ms ease, respecting vestibular disorders and strict `prefers-reduced-motion`)

## Color Palette
- **Canvas / Background**: `#FFFFFF` (Light) | `#14111F` (Dark) | `#000000` (High Contrast)
- **Surface 1**: `#FFFFFF` (Light) | `#1B172C` (Dark) | `#0B0B0B` (High Contrast)
- **Surface 2**: `#F6F5FA` (Light) | `#25203B` (Dark) | `#181818` (High Contrast)
- **Primary Ink**: `#14111F` (Light) | `#FFFFFF` (Dark) | `#FFFFFF` (High Contrast)
- **Muted Ink / Secondary**: `#6B6882` (Light) | `#A9A5C4` (Dark) | `#E2E0EE` (High Contrast)
- **Border Lines**: `rgba(20, 17, 31, 0.10)` (Light) | `rgba(255, 255, 255, 0.12)` (Dark) | `#FFCB05` (High Contrast)
- **Signature Accent**: `#8338EC` (Electric Violet — Primary interactive controls)
- **Tactile Signal Accent**: `#FFCB05` (Signal Gold — Braille landmarks, high-visibility focus rings)
- **Status Semantic**:
  - Success / On-Device: `#10B981` (Emerald)
  - Caution / Review: `#F59E0B` (Warm Amber)
  - Urgent / Crisis: `#EF4444` (Clinical Crimson)

## Typography
- **Display / Headers**: `'Schibsted Grotesk', system-ui, -apple-system, sans-serif` (weight 700–800, tracking -0.02em)
- **Bengali & Indic**: `'Hind Siliguri', sans-serif`
- **Body & Form Controls**: `'Plus Jakarta Sans', 'Inter', system-ui, -apple-system, sans-serif` (weight 500–700, 14–15px body, 13px helper)

## Component Rules & Anti-Slop Discipline
1. **Settings Navbar**:
   - Modern segmented floating pill bar with 44px min-height tap targets.
   - Explicit active tab elevation (`box-shadow: 0 4px 14px rgba(20, 17, 31, 0.08)` in light, `#25203B` with accent border in dark).
   - Icons always carry purposeful SVG vector paths with exact 18x18 bounding boxes.
2. **Form Inputs & Selects**:
   - Minimum height: 44px for WCAG AAA tap accessibility.
   - Full structural width without truncated text or cramped select dropdowns.
   - Dedicated label + helper description + floating focus outline (`3px solid rgba(131, 56, 236, 0.2)`).
3. **Card Composition**:
   - Varied density: Profile editor uses a generous 2-column grid; Capabilities utilizes a rich hardware telemetry spec matrix with active progress bars.
   - Zero dead whitespace; every pixel communicates verified hardware status, privacy isolation, or personalized settings.
