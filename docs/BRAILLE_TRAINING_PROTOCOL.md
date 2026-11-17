# Optical Braille Recognition Training Protocol & Experimental Design
## Document-Independent Training, Hyperparameter Optimization, and Model Selection

---

## 1. Experimental Integrity & Anti-Leakage Protocol

In accordance with strict scientific guidelines:
1. **Document-Independent Splitting:** All 5 optical variations (`L1`, `L2`, `P1`, `R1`, `D1`) of a given document belong strictly to the same partition.
   - **Training Set (71.46%):** 7 Documents (`DOC001`–`DOC004`, `DOC006`–`DOC008`), 35 Images, 1,765 Cell Patches.
   - **Validation Set (11.74%):** 1 Document (`DOC005`), 5 Images, 290 Cell Patches.
   - **Held-Out Test Set (16.80%):** 2 Documents (`DOC009`, `DOC010`), 10 Images, 415 Cell Patches.
2. **Fixed Random Seeds:** Global seed `SEED = 42` is enforced across NumPy, random, and Scikit-Learn to guarantee 100% deterministic reproducibility.
3. **Isolated Preprocessing:** Feature scalers (`StandardScaler`) are fitted strictly on the training partition and applied without modification to validation and test partitions.

---

## 2. Feature Representation & Input Normalization

Every $28 \times 28$ grayscale cell patch is processed through the 6-Subcell Relief Feature Extractor:
- Input: $28 \times 28$ Grayscale matrix $\mathbf{I} \in [0, 255]^{28 \times 28}$.
- Output: 244-dimensional feature vector $\mathbf{x} \in \mathbb{R}^{244}$.
- Target Labels: 6-dimensional binary vector $\mathbf{y} = (d_1, d_2, d_3, d_4, d_5, d_6) \in \{0, 1\}^6$.
- Feature Standardization:
  $$\tilde{\mathbf{x}} = \frac{\mathbf{x} - \boldsymbol{\mu}_{\text{train}}}{\boldsymbol{\sigma}_{\text{train}} + 10^{-7}}$$

---

## 3. Candidate Model Hyperparameter Specifications

| Architecture | Model Family | Hyperparameters & Configuration | Target Loss / Metric |
|---|---|---|---|
| **Candidate 1: Random Forest (Champion)** | Ensemble Trees | `n_estimators=150`, `max_depth=14`, `min_samples_split=2`, `min_samples_leaf=1`, `max_features='sqrt'`, `n_jobs=-1` | Multi-output Gini impurity |
| **Candidate 2: Deep MLP** | Neural Network | `hidden_layer_sizes=(256, 128, 64)`, `activation='relu'`, `solver='adam'`, `alpha=1e-4`, `batch_size=64`, `max_iter=300`, `early_stopping=True` | Binary Cross-Entropy Loss |
| **Candidate 3: Extra Trees** | Extremely Randomized Trees | `n_estimators=150`, `max_depth=16`, `min_samples_split=2`, `n_jobs=-1` | Multi-output Gini impurity |

---

## 4. Evaluation Metrics for Model Selection

Model selection is determined on the **Validation Set (`DOC005`)** using:
1. **Per-Dot Accuracy:** Mean accuracy across the 6 individual dots:
   $$\text{Dot Accuracy} = \frac{1}{6 N} \sum_{k=1}^{N} \sum_{i=1}^{6} \mathbb{I}(\hat{d}_i^{(k)} = d_i^{(k)})$$
2. **Exact Cell Accuracy (Strict 6-Dot Match):** Fraction of cells where all 6 dots are predicted correctly:
   $$\text{Exact Cell Acc} = \frac{1}{N} \sum_{k=1}^{N} \prod_{i=1}^{6} \mathbb{I}(\hat{d}_i^{(k)} = d_i^{(k)})$$
3. **Macro F1-Score:** Harmonic mean of precision and recall across all 6 binary dot targets.
4. **End-to-End Character Error Rate (CER):** Levenshtein distance between decoded text and ground truth text on full document pages.

The model achieving the highest Exact Cell Accuracy and lowest CER on validation data is selected as the Champion Model for final held-out testing and deployment export.
