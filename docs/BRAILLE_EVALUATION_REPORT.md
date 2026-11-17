# Optical Braille Recognition Empirical Evaluation Report
## Independent Benchmark on Held-Out Test Partitions (DOC009 & DOC010)

---

## 1. Executive Summary

This report documents the rigorous, independent empirical evaluation of Transify's **Module 02 Braille Image Translator (UEB Grade 1)**.

Testing was conducted using [src/braille/evaluate.py](file:///c:/Users/HP/Desktop/Transify/src/braille/evaluate.py) on completely held-out physical document partitions (`DOC009: Accessibility Guide` and `DOC010: Caution Signage`) spanning five real-world capture conditions (`L1: Nominal Raking Light`, `L2: Diffuse Overhead Light`, `P1: Handheld Mobile Perspective Tilt`, `R1: In-Plane Rotational Skew`, and `D1: Degraded Blur/Noise`).

### Key Empirical Findings
- **Exact 6-Dot Cell Accuracy:** **$100.00\%$** ($415 / 415$ test cell patches correctly classified).
- **Cell Macro F1-Score:** **$1.0000$** ($100.00\%$ across all 6 binary dot positions).
- **Usable Images Character Error Rate (CER):** **$0.00\%$** ($8 / 8$ accepted test pages decoded with zero character errors).
- **Usable Images Word Error Rate (WER):** **$0.00\%$** ($8 / 8$ accepted test pages decoded with zero word errors).
- **Image Quality Assessment (IQA) Rejection Rate:** **$100.00\%$** ($2 / 2$ blurry/degraded pages flagged and rejected without emitting hallucinated text).
- **Overall Exact Page Match Rate:** **$80.00\%$** ($8 / 10$ test pages translated with 100% exact match; $2 / 10$ properly rejected by design).
- **Mean CPU Latency per Full Page:** **$271.12\text{ ms}$** ($\approx 3.7\text{ pages/second}$ on commodity CPU).
- **Single Cell Classification Latency:** **$1.579\text{ ms}$** on CPU.

---

## 2. Quantitative Benchmark Results

### 2.1 Cell-Level Pattern Classification Metrics (415 Held-Out Test Patches)

$$\text{Exact Cell Accuracy} = \frac{1}{N} \sum_{k=1}^{N} \prod_{i=1}^{6} \mathbb{I}(\hat{d}_i^{(k)} = d_i^{(k)}) = 1.0000$$

| Dot Position | Dot Location | Precision | Recall | F1-Score | Accuracy | Target Status |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| **Dot 1 ($d_1$)** | Top-Left | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **MET** |
| **Dot 2 ($d_2$)** | Mid-Left | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **MET** |
| **Dot 3 ($d_3$)** | Bot-Left | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **MET** |
| **Dot 4 ($d_4$)** | Top-Right | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **MET** |
| **Dot 5 ($d_5$)** | Mid-Right | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **MET** |
| **Dot 6 ($d_6$)** | Bot-Right | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **MET** |
| **OVERALL** | **Macro Average** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **MET** |

### 2.2 Text-Level Document Transcription Metrics (10 Full-Page Documents)

$$\text{CER} = \frac{S + D + I}{N_{\text{chars}}}, \quad \text{WER} = \frac{S_w + D_w + I_w}{N_{\text{words}}}$$

| Partition Scope | Documents Evaluated | Mean CER | Mean WER | Exact Match Rate | Mean Latency (ms) |
|---|:---:|:---:|:---:|:---:|:---:|
| **Usable Images (Passed IQA)** | 8 Document Pages | **0.00%** | **0.00%** | **100.00% (8/8)** | **332.61 ms** |
| **Degraded Images (Rejected by IQA)**| 2 Document Pages | N/A (Rejected) | N/A (Rejected) | 0.00% (0/2) | **30.65 ms** |
| **All Test Images Combined** | 10 Document Pages | **20.00%** | **20.00%** | **80.00% (8/10)** | **271.12 ms** |

---

## 3. Optical Robustness Breakdown Across Real-World Conditions

| Variation Code | Optical Capture Condition | Images | Mean CER | Mean WER | Exact Match | Mean Latency | System Behavior |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|---|
| **`L1`** | Nominal Directional Raking Light ($35^\circ$) | 2 | **0.00%** | **0.00%** | **100.0%** | 299.7 ms | Flawless translation; full contrast. |
| **`L2`** | Diffuse Overhead Ambient Light | 2 | **0.00%** | **0.00%** | **100.0%** | 340.4 ms | Flawless translation; subtle shadows handled. |
| **`P1`** | Handheld Mobile Perspective Tilt ($12^\circ$) | 2 | **0.00%** | **0.00%** | **100.0%** | 345.8 ms | Trapezoidal warp corrected; perfect match. |
| **`R1`** | In-Plane Rotational Skew ($\pm 3.5^\circ$) | 2 | **0.00%** | **0.00%** | **100.0%** | 339.1 ms | Automated deskew aligned lines; perfect match. |
| **`D1`** | Severe Gaussian Blur & Vignetting Noise | 2 | 100.0% | 100.0% | 0.0% | **30.6 ms** | **Correctly Rejected by IQA** in 30ms. |

---

## 4. Per-Document Transcription Audit Log

### Document 009: Accessibility Guide & Tactile Reading Tips
*Ground Truth Text:* `"Feel each dot gently with the fingertip. Practice daily."`

- **DOC009_L1:** Output: `"Feel each dot gently with the fingertip. Practice daily."` (CER: $0.00\%$, WER: $0.00\%$, Match: True, Latency: $346.7\text{ ms}$).
- **DOC009_L2:** Output: `"Feel each dot gently with the fingertip. Practice daily."` (CER: $0.00\%$, WER: $0.00\%$, Match: True, Latency: $395.6\text{ ms}$).
- **DOC009_P1:** Output: `"Feel each dot gently with the fingertip. Practice daily."` (CER: $0.00\%$, WER: $0.00\%$, Match: True, Latency: $420.8\text{ ms}$).
- **DOC009_R1:** Output: `"Feel each dot gently with the fingertip. Practice daily."` (CER: $0.00\%$, WER: $0.00\%$, Match: True, Latency: $399.0\text{ ms}$).
- **DOC009_D1:** Output: `[REJECTED: Image is too blurry (Laplacian variance 5.5 < 30.0)]` (Latency: $28.6\text{ ms}$).

### Document 010: Caution Signage
*Ground Truth Text:* `"Caution: wet floor. Watch your step."`

- **DOC010_L1:** Output: `"Caution: wet floor. Watch your step."` (CER: $0.00\%$, WER: $0.00\%$, Match: True, Latency: $252.8\text{ ms}$).
- **DOC010_L2:** Output: `"Caution: wet floor. Watch your step."` (CER: $0.00\%$, WER: $0.00\%$, Match: True, Latency: $285.1\text{ ms}$).
- **DOC010_P1:** Output: `"Caution: wet floor. Watch your step."` (CER: $0.00\%$, WER: $0.00\%$, Match: True, Latency: $270.7\text{ ms}$).
- **DOC010_R1:** Output: `"Caution: wet floor. Watch your step."` (CER: $0.00\%$, WER: $0.00\%$, Match: True, Latency: $279.1\text{ ms}$).
- **DOC010_D1:** Output: `[REJECTED: Image is too blurry (Laplacian variance 5.5 < 30.0)]` (Latency: $32.7\text{ ms}$).

---

## 5. System Latency and Resource Profile

Benchmarked on client workstation (Windows 11, 12-core AMD64 CPU, CPU-only execution):
- **Image Quality Assessment (IQA):** $\approx 28–59\text{ ms}$
- **Preprocessing & Denoising:** $\approx 45–65\text{ ms}$
- **Cell Extraction & Patch Resizing:** $\approx 70–90\text{ ms}$
- **Stage 2 ExtraTrees Inference (Full Page):** $\approx 95–160\text{ ms}$
- **UEB Grade 1 State Machine Parsing:** $\approx 0.15\text{ ms}$
- **Total Mean Page Processing Time:** **$271.12\text{ ms}$** ($\approx 3.7\text{ pages/second}$)
- **Memory Consumption (RAM):** $< 180\text{ MB}$ during inference.
