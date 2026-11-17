# Optical Braille Recognition (OBR) Dataset License & Legal Audit
## Compliance, Redistribution Terms, and Commercial Rights Analysis

---

## 1. Regulatory Framework & Governance

Transify operates under strict intellectual property, data ethics, and open-source licensing governance.

This audit evaluates the copyright, licensing terms, and permitted use cases for all candidate Braille datasets investigated for Module 02.

---

## 2. In-Depth License Audit Matrix

| Dataset Identifier | Primary Source / Author | Explicit License | Commercial Use Permitted? | Redistribution Permitted? | Attribution Required? | Transify Compliance Action |
|---|---|---|:---:|:---:|:---:|---|
| **DSBI** | Li et al., CASIA (2018) | **No OSI License** (Academic Disclaimer) | **NO** | **NO** | YES | **Research Benchmark Only.** Do NOT bundle in commercial distributions or redistribute raw images. Used solely for algorithmic reference and parameter verification. |
| **Angelina Braille** | Ilya Ovodov (2021) | **No OSI License** (Non-profit Assistive) | **NO** (Unspecified) | Restricted | YES | **Research & Validation Only.** Use for validating smartphone camera angle robustness; do not package proprietary weights derived exclusively from Angelina in commercial distributions without written permission. |
| **Shanks0465 Braille** | Kaggle / shanks0465 | **Creative Commons CC BY 4.0** | **YES** | **YES** | YES | **Fully Permitted.** Can be used for training, pre-training, and commercial deployment provided author attribution is preserved. |
| **Roboflow Braille-wvmcp** | Roboflow Universe | **Public Domain (CC0 1.0)** | **YES** | **YES** | NO | **Fully Permitted.** Free for commercial and non-commercial usage without restriction. |
| **Roboflow Braille-cells** | Roboflow Universe | **Creative Commons CC BY 4.0** | **YES** | **YES** | YES | **Fully Permitted.** Requires standard attribution note in documentation. |
| **Transify Calibration Corpus** | Transify Engineering Team (2026) | **Apache License 2.0** | **YES** | **YES** | YES | **Fully Permitted.** In-house generated calibration and benchmark documents with 100% full legal rights and transparent provenance. |

---

## 3. Legal Risk Mitigations

1. **Zero Raw Dataset Redistribution:**
   - Raw images from DSBI and Angelina are never redistributed or committed to public release bundles.
   - All open-source distribution packages include only permissive (CC0, CC BY 4.0, or Apache 2.0) test artifacts and trained parameter checkpoints.
2. **Attribution Preservation:**
   - Formal attribution notices for CC BY 4.0 contributors (`shanks0465`, Roboflow Universe authors) are embedded in Transify's `LICENSE` and `docs/` directories.
3. **Clean-Room Training Verification:**
   - The primary champion model architecture is validated on independently generated, document-independent test sets to prevent any third-party copyright claims on model weights.
