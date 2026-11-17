# Transify — Experimental Validation Plan & Evaluation Protocol (Revised)

## 1. Experimental Integrity and Anti-Leakage Protocol

Assistive AI models that evaluate on flawed or leaking data splits report misleading benchmark numbers that collapse in real-world use. 

Transify enforces strict, non-negotiable validation boundaries:
1. **Zero Random Frame Splitting:** Under no circumstances are video frames randomly split into train and test sets. Temporal sequences must be preserved in their entirety.
2. **Strict Signer-Independent Splitting for BdSL:** Test signers must never appear in training or validation sets. The model must be evaluated on human subjects, skin tones, and anatomical dimensions it has never seen.
3. **Strict Document-Independent Splitting for Braille:** Slices or crops originating from the same physical sheet of Braille paper must remain in the same split. Splitting patches from one photograph across train and test sets leaks paper texture, embossing depth, and lighting angles.
4. **Prohibition of Training Accuracy Reporting:** Training loss and accuracy are logged solely for convergence monitoring; blind held-out test splits alone determine reported performance.

---

## 2. Module 01: Bangladesh Sign Language (BdSL) Evaluation Protocol

### 2.1 Signer-Independent Split Schema
For BdSL dataset partitions (`BdSL-D1500`, `BdSLW60`, `SignBD-Word`), we implement a **Leave-Signers-Out (LSO)** protocol:

```
+----------------------------------------------------------------------------------------------------+
|                         BDSL SIGNER-INDEPENDENT SPLITTING SCHEMA (LSO)                             |
|                                                                                                    |
| Total Available Signers (e.g., S = 18 signers from BdSLW60 / 50 subjects from BdSL-D1500)          |
|                                                                                                    |
|   [ Training Split: ~70% of Signers ]    [ Validation Split: ~15% ]     [ Test Split: ~15% ]       |
|   Signers: S_1 through S_12              Signers: S_13 through S_15     Signers: S_16 through S_18 |
|   (Model Optimization)                   (Hyperparameter Tuning &       (Final Blind Benchmark     |
|                                           Early Stopping)                Reporting Only)           |
+----------------------------------------------------------------------------------------------------+
```

### 2.2 Mathematical Metrics for BdSL Evaluation

#### 1. Macro-Averaged F1-Score
To prevent majority-class dominance across alphabet signs and word glosses:
$$\text{Precision}_c = \frac{\text{TP}_c}{\text{TP}_c + \text{FP}_c}, \quad \text{Recall}_c = \frac{\text{TP}_c}{\text{TP}_c + \text{FN}_c}$$
$$\text{F1}_c = 2 \cdot \frac{\text{Precision}_c \cdot \text{Recall}_c}{\text{Precision}_c + \text{Recall}_c}, \quad \text{Macro F1} = \frac{1}{C} \sum_{c=1}^C \text{F1}_c$$

#### 2. Sequence-Level Word Error Rate (WER) & Character Error Rate (CER)
For synthesized sentences translated into English:
$$\text{CER} = \frac{S_c + D_c + I_c}{N_c} \times 100\%, \quad \text{WER} = \frac{S_w + D_w + I_w}{N_w} \times 100\%$$
Where $S$ is substitutions, $D$ is deletions, $I$ is insertions, and $N$ is total reference tokens.

---

## 3. Module 02: Braille Evaluation Protocol (UEB Grade 1)

### 3.1 Document-Independent Split Schema
Image partitioning is executed at the source book/sheet level:

```
+----------------------------------------------------------------------------------------------------+
|                         BRAILLE DOCUMENT-INDEPENDENT SPLITTING SCHEMA                              |
|                                                                                                    |
| Total Source Pages (e.g., P = 120 physical sheets from DSBI, Angelina, and Roboflow)               |
|                                                                                                    |
|   [ Training Split: 70% ]         [ Validation Split: 15% ]         [ Test Split: 15% ]           |
|   Pages 1 through 84              Pages 85 through 102              Pages 103 through 120         |
|   (All crops / slices of pages    (All crops / slices of pages      (Unseen paper textures,       |
|    1..84 stay in Training)         85..102 stay in Validation)       lighting, and book bindings) |
+----------------------------------------------------------------------------------------------------+
```

### 3.2 Mathematical Metrics for OBR Evaluation

1. **Cell Localization Precision (mAP@0.50):** Evaluates bounding box overlap for Stage 1 cell localization:
   $$\text{IoU}(B_{\text{pred}}, B_{\text{gt}}) \ge 0.50$$
2. **Cell Recognition Accuracy ($A_{\text{cell}}$):** The percentage of localized cells whose decoded 6-bit binary pattern matches ground truth exactly:
   $$A_{\text{cell}} = \frac{N_{\text{correct cells}}}{N_{\text{total cells}}} \times 100\%$$
3. **Perturbation Stress-Testing:** Held-out test images will be subjected to synthetic lighting shifts, blur kernels ($\sigma \in \{1.0, 2.0\}$), and perspective warps ($\pm 15^\circ$) to measure degradation under adverse conditions.

---

## 4. Planned Baseline & Experimental Progression

### 4.1 Module 01 Experiment Matrix (BdSL Priority)

| Experiment ID | Task Scope | Input Feature Space | Architecture Backbone | Evaluation Split | Research Hypothesis |
|---|---|---|---|---|---|
| **EXP-SLR-01** | BdSL Alphabet | Hands Only (42 landmarks) | 3-Layer MLP | Signer-Independent | High self-occlusion errors on two-handed BdSL characters. |
| **EXP-SLR-02 (Champion A)** | BdSL Alphabet | MediaPipe Holistic (162D) | 3-Layer MLP + BatchNorm | Signer-Independent | Shoulder-centering resolves two-handed spatial ambiguities. Target: $\text{Macro F1} \ge 90\%$. |
| **EXP-SLR-03** | BdSL Words (60 classes) | Holistic Landmarks (162D x 30 frames) | Random Forest on Keyframes | Signer-Independent | Baseline tree ensemble on temporal summary statistics. |
| **EXP-SLR-04 (Champion B)** | BdSL Words (60 classes) | Holistic Landmarks Sequence | 1D-CNN + BiLSTM Sequencer | Signer-Independent | Captures continuous gesture trajectories. Target: $\text{Top-1} \ge 80\%$. |

### 4.2 Module 02 Experiment Matrix (Two-Stage Braille)

| Experiment ID | Task Scope | Preprocessing | Architecture Backbone | Evaluation Split | Research Hypothesis |
|---|---|---|---|---|---|
| **EXP-OBR-01** | End-to-End Baseline | CLAHE | Single-Stage YOLOv8-nano (64 classes)| Document-Independent | Prone to class imbalance on rare Braille letters. |
| **EXP-OBR-02 (Stage 1)** | Cell Localization | CLAHE + Deskewing | 1-Class YOLOv8-nano (`braille_cell`) | Document-Independent | Highly balanced 1-class detector. Target: $\text{mAP@0.50} \ge 92\%$. |
| **EXP-OBR-03 (Stage 2)** | Pattern Classification | Normalization | Lightweight CNN / 6-Dot Classifier | Held-out cell crops | 6-bit binary classifier eliminates long-tail class imbalance. Target: $A_{\text{cell}} \ge 88\%$. |
| **EXP-OBR-04** | Linguistic Decoding | Reading-order Sort | UEB Grade 1 State Machine (2024 Rules)| Document-Independent | Deterministic decoding of prefixes (caps, numbers, symbols). |

---

## 5. Reproducibility and Experiment Tracking

1. **Seed Pinning:** Random seeds across Python, NumPy, PyTorch, and Scikit-Learn will be fixed to `SEED = 42`.
2. **Artifact Versioning:** Checkpoints will be archived with Git commit hashes, `config.yaml` hyperparameters, training/validation loss logs, and confusion matrix plots.
3. **Hardware & Package Tracking:** Every training run logs exact system configurations via `pip freeze` and platform diagnostics.
