# Optical Braille Recognition Model Architecture Specification
## Two-Stage Hybrid Computer Vision Architecture: Cell Localization & Six-Dot Pattern Recognition

---

## 1. Architectural Philosophy and System Topology

Optical Braille Recognition (OBR) differs fundamentally from optical character recognition of printed fonts. Printed fonts possess high-contrast ink boundaries, whereas Braille dots are 3D tactile deformations whose visibility is governed by lighting-induced highlights and shadows.

Transify deploys a **Two-Stage Decoupled Computer Vision Architecture**:

```
+----------------------------------------------------------------------------------------------------+
|                               TWO-STAGE OBR PIPELINE ARCHITECTURE                                  |
|                                                                                                    |
|    [ Raw Input Image (RGB/Grayscale) ]                                                             |
|                    │                                                                               |
|                    ▼                                                                               |
|    [ Image Quality Assessment ] ───(Rejection if Blurry / Dark / Glare)                            |
|                    │                                                                               |
|                    ▼                                                                               |
|    [ Adaptive Preprocessor ]                                                                       |
|      ├── Illumination Background Division                                                          |
|      ├── CLAHE Micro-Relief Enhancement                                                            |
|      ├── Bilateral Edge-Preserving Denoising                                                       |
|      └── Skew Angle Detection & Deskewing                                                          |
|                    │                                                                               |
|                    ▼                                                                               |
|    ┌───────────────────────────────────────────────┐                                               |
|    │ STAGE 1: BRAILLE CELL LOCALIZER & LAYOUT      │                                               |
|    │ ├── Adaptive Gaussian-Otsu Relief Mask        │                                               |
|    │ ├── Morphological Component Clustering        │                                               |
|    │ ├── Reading-Line Ordering (Top-to-Bottom)     │                                               |
|    │ ├── Intra-Line Cell Sorting (Left-to-Right)   │                                               |
|    │ └── Inter-Cell vs Inter-Word Space Detector   │                                               |
|    └───────────────────────────────────────────────┘                                               |
|                    │  List of Normalized Cell Patches (28x28)                                      |
|                    ▼                                                                               |
|    ┌───────────────────────────────────────────────┐                                               |
|    │ STAGE 2: 6-DOT PATTERN CLASSIFIER             │                                               |
|    │ ├── 6-Subcell Relief Feature Extractor (244D) │                                               |
|    │ ├── Multi-Output Decision Ensemble / MLP      │                                               |
|    │ ├── Dot Probabilities: (p1, p2, p3, p4, p5, p6)│                                              |
|    │ └── Uncertainty Estimator (Min Confidence)    │                                               |
|    └───────────────────────────────────────────────┘                                               |
|                    │  Classified Dot Vectors (d1..d6) + Confidences                                |
|                    ▼                                                                               |
|    [ UEB Grade 1 Deterministic State Machine ]                                                     |
|      ├── Capital Indicators (⠠, ⠠⠠)                                                               |
|      ├── Numeric Indicators (⠼) & Digits 0-9                                                       |
|      ├── Punctuation & Word Reconstruction                                                         |
|      └── Grade 2 Contraction Auditor                                                               |
|                    │                                                                               |
|                    ▼                                                                               |
|    [ Output: Formatted English Text + Optional TTS Audio ]                                         |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Stage 1: Braille Cell Detection & Layout Analysis

### 2.1 Optical Relief Accentuation
Embossed Braille dots produce characteristic paired light-dark dipolar contours under directional raking light. 
Stage 1 detects these features using adaptive local variance filtering:
$$I_{\text{binary}}(x, y) = \begin{cases} 255 & \text{if } I_{\text{enhanced}}(x, y) < T_{\text{adaptive}}(x, y) - C \\ 0 & \text{otherwise} \end{cases}$$
where $T_{\text{adaptive}}$ is a Gaussian-weighted local mean computed over a $15 \times 15$ neighborhood.

### 2.2 Hierarchical Grid and Reading-Line Clustering
1. **Vertical Projection Profiling:**
   - The document is sliced into horizontal projections $H(y) = \sum_{x} I_{\text{binary}}(x, y)$. Peaks in $H(y)$ separated by the physical inter-line spacing $c_{\text{line}} \approx 36–45\text{ px}$ identify distinct reading lines.
2. **Horizontal Cell Segmentation:**
   - Along each identified line stripe, connected dot components are clustered into 6-dot cell bounding boxes of dimension $[W_{\text{cell}} \times H_{\text{cell}}]$.
3. **Space Classification:**
   - The horizontal distance $\Delta x$ between consecutive cell bounding boxes $[x_{\min}^{(k+1)} - x_{\max}^{(k)}]$ is evaluated:
     $$\text{Is\_Space} = \begin{cases} \text{True} & \text{if } \Delta x > 0.8 \times W_{\text{cell}} \\ \text{False} & \text{otherwise} \end{cases}$$

---

## 3. Stage 2: Six-Dot Pattern Classification

### 3.1 6-Subcell Relief Feature Engineering (244 Dimensions)
Each localized cell patch is normalized to a standard resolution of $28 \times 28$ pixels.
Because the spatial topology of a 6-dot Braille cell is rigidly fixed by the Marburg standard, the $28 \times 28$ patch is partitioned into six distinct sub-regions corresponding to dot positions $1$ through $6$:

```
   Sub-region 1 (D1)      Sub-region 4 (D4)
   [x: 0..14, y: 0..9]    [x: 14..28, y: 0..9]
   
   Sub-region 2 (D2)      Sub-region 5 (D5)
   [x: 0..14, y: 9..19]   [x: 14..28, y: 9..19]
   
   Sub-region 3 (D3)      Sub-region 6 (D6)
   [x: 0..14, y: 19..28]  [x: 14..28, y: 19..28]
```

For each sub-region $r \in \{1, \dots, 6\}$, eight statistical and morphological relief metrics are computed:
1. $\mu_r$: Mean intensity.
2. $\sigma_r$: Standard deviation of intensity (measures relief contrast).
3. $\text{Range}_r$: Peak-to-trough amplitude ($\max I - \min I$).
4. $\text{GradX}_r$: Mean horizontal Sobel gradient $|\nabla_x I|$.
5. $\text{GradY}_r$: Mean vertical Sobel gradient $|\nabla_y I|$.
6. $\text{LapVar}_r$: Laplacian edge variance (curvature of the embossed dome).
7. $\text{MaxRelief}_r$: Maximum intensity difference between local center and periphery.
8. $\text{ActiveRatio}_r$: Fraction of pixels exceeding local threshold.

This yields $6 \times 8 = 48$ domain-engineered tactile features. 
In addition, a spatially downsampled $14 \times 14 = 196$-dimensional raster feature is concatenated, producing a **comprehensive 244-dimensional feature vector** $\mathbf{x} \in \mathbb{R}^{244}$ per cell.

### 3.2 Candidate Classifier Formulations

#### Candidate A: Multi-Output Random Forest (Champion)
- **Structure:** 150 randomized decision trees with maximum depth 14.
- **Output:** Independent posterior probabilities for each of the six dot positions:
  $$\hat{P}(d_i = 1 | \mathbf{x}) = \frac{1}{T} \sum_{t=1}^{T} P_t(d_i = 1 | \mathbf{x}), \quad i \in \{1, \dots, 6\}$$
- **Discrete Decision:** $\hat{d}_i = \mathbb{I}(\hat{P}(d_i = 1 | \mathbf{x}) \ge 0.5)$.

#### Candidate B: Multi-Label Deep Multi-Layer Perceptron (MLP)
- **Architecture:** `Input(244) -> Dense(256, ReLU) -> Dropout(0.2) -> Dense(128, ReLU) -> Dense(64, ReLU) -> Output(6, Sigmoid)`.
- **Loss Function:** Multi-Label Binary Cross-Entropy Loss:
  $$\mathcal{L}_{\text{BCE}} = -\frac{1}{6} \sum_{i=1}^{6} \left[ d_i \ln \hat{p}_i + (1 - d_i) \ln (1 - \hat{p}_i) \right]$$

#### Candidate C: Multi-Output HistGradientBoosting / ExtraTrees
- **Structure:** Histogram-based gradient boosting trees optimizing individual dot logistic losses.

---

## 4. Confidence Assessment & Uncertainty Handling

To fulfill the strict scientific directive never to silently guess characters:
1. **Per-Dot Confidence:** $c_i = \max(\hat{p}_i, 1 - \hat{p}_i) \in [0.5, 1.0]$.
2. **Cell Confidence Score:**
   $$\text{Confidence}(\text{cell}) = \min_{i=1..6} c_i$$
3. **Thresholding Action:**
   - If $\text{Confidence} \ge 0.70$: High certainty; decoded directly.
   - If $0.50 \le \text{Confidence} < 0.70$: Moderate certainty; decoded, but tagged in `uncertain_cells` manifest for UI human review.
   - If $\text{Confidence} < 0.50$: Ambiguous cell; emitted with uncertainty flag `[?glyph]`.
