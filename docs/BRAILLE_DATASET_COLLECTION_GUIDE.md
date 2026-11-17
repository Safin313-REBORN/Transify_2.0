# Optical Braille Recognition Dataset Collection Protocol
## Standard Operating Procedures for Acquiring Real-World Braille Document Imagery

---

## 1. Physical Principles of Braille Optical Visibility

Braille characters are tactile reliefs embossed on paper or cardstock. They contain no chemical pigments or ink. Consequently, the visual perceptibility of a Braille dot is an optical function of **raking illumination** (oblique light casting directional shadows and specular highlights):

```
Directional Light Source (Raking Light @ 30° - 45° Angle)
       \
        \
         v
    . . . . . . 
    . . • . . .  <-- Raised Dot (Highlights on upper edge, shadow in trough)
   ══════════════════════════════════════════════════════════════ (Paper Surface)
```

Direct perpendicular flash photography flattens tactile relief and completely erases Braille dots. Therefore, dataset collection must capture real-world lighting variations while adhering to optical contrast protocols.

---

## 2. Hardware and Environmental Setup

### 2.1 Capture Devices
1. **Smartphone Cameras (Primary Target):**
   - Resolution: $\ge 12\text{ Megapixels}$ ($4032 \times 3024\text{ px}$ or $1920 \times 1080\text{ px}$ minimum).
   - Sensor: 1/2.55" to 1/1.3" CMOS sensors (iPhone 12–16, Samsung Galaxy S21–S25, Google Pixel 6–9).
   - Autofocus: Dual-pixel Phase Detection Autofocus (PDAF) enabled; tap-to-focus locked onto center page embossed cells.
2. **Flatbed Scanners (Controlled Calibration Benchmark):**
   - Optical Resolution: $200\text{ DPI}$ to $300\text{ DPI}$, 24-bit RGB TIFF/PNG.
   - CIS (Contact Image Sensor) vs CCD: Note that CCD scanners provide superior depth-of-field for embossed relief than shallow CIS scanners.

### 2.2 Physical Media and Materials
Collect samples across diverse real-world substrates:
- **Heavy Braille Paper ($120–160\text{ gsm}$):** Standard library and educational Braille book stock.
- **Office Copy Paper ($70–80\text{ gsm}$):** Consumer slate-and-stylus or portable embosser documents.
- **Kraft / Manila Cardstock:** Heavy embossed flashcards and directional signage.
- **Plastic Embossing Tape / Translucent Film:** High-contrast labels found on elevators and medicine packaging.

### 2.3 Lighting Variations
Each document should be captured under at least 3 distinct lighting conditions:
1. **Condition L1 (Directional Side Light):** Light source placed $30^\circ–45^\circ$ to the left or top of the page at $30\text{ cm}$ distance, producing distinct contrast shadows.
2. **Condition L2 (Diffused Overhead Lighting):** Standard fluorescent or LED indoor office lighting ($300–500\text{ lux}$), producing subtle micro-shadows.
3. **Condition L3 (Challenging Ambient / Window Light):** Natural angled daylight with soft room shadows or partial occlusion.

*Prohibited Lighting:* Direct on-axis camera flash (destroys shadow contours).

---

## 3. Geometric and Distance Protocols

### 3.1 Distance and Field of View
- **Full Page ($20–35\text{ cm}$ distance):** Captures complete letter/A4 sheet containing 15–25 lines of Braille.
- **Document Crop / Paragraph ($10–20\text{ cm}$ distance):** Macro view focusing on 3–8 lines of text with high dot detail.

### 3.2 Perspective and Orientation Variations
- **Nominal ($0^\circ$ Tilt):** Camera parallel to document plane.
- **Slight Tilt ($\pm 10^\circ$ to $\pm 15^\circ$ Pitch/Roll):** Simulates handheld mobile capture without a tripod.
- **Slight Skew ($\pm 5^\circ$ to $\pm 10^\circ$ In-plane Rotation):** Tests deskew and line-clustering algorithms.

---

## 4. Quality Control and Rejection Criteria

During data collection, images must be screened immediately through the following automated acceptance gates:

| Quality Criterion | Measurement Metric | Threshold for Rejection | Action on Failure |
|---|---|:---:|---|
| **Motion Blur** | Laplacian Variance $\sigma^2(\nabla^2 I)$ | $< 100.0$ | Reject; stabilize camera and re-capture. |
| **Underexposure** | Mean Pixel Luminance $\bar{Y}$ | $< 50$ (on 0-255 scale) | Reject; increase ambient lighting. |
| **Overexposure / Glare** | Percentage of Saturated Pixels ($Y > 250$) | $> 8.0\%$ | Reject; reposition light source to avoid specular reflection. |
| **Low Resolution** | Minimum Inter-Dot Distance in Pixels | $< 6\text{ px}$ | Reject; move camera closer or increase resolution. |
| **Extreme Perspective** | Trapezoidal Skew Angle | $> 25^\circ$ | Reject; realign camera parallel to paper plane. |
