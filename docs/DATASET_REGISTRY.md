# Transify — Dataset Registry & Feasibility Inventory (Revised)

## 1. Registry Policy and Standards

This registry documents all verified candidate datasets investigated for **Transify**. In compliance with Phase 1 review directives:
- **Priority Domain:** Bangladesh Sign Language (BdSL) is the primary source language for the Phase 2 MVP, with American Sign Language (ASL) designated as a future expansion candidate.
- **Braille Specification:** Unified English Braille (UEB) Grade 1 in compliance with the **ICEB Rules of Unified English Braille, Third Edition (2024)**.
- **Verification Integrity:** Sample counts distinguish between master metadata indices and physically accessible/downloaded video samples. Official licensing files and research permissions are audited.
- **Zero Fabrication:** No synthetic datasets or imaginary metrics are reported. No large raw datasets are downloaded during Phase 1.

---

## 2. Module 01: Sign Language Recognition Datasets

### 2.1 Bangladesh Sign Language (BdSL) Datasets (Primary MVP Focus)

#### Candidate BDSL-01: BdSL-D1500
| Field | Verified Specification |
|---|---|
| **Official Name** | BdSL-D1500 (Bangla Sign Language Alphabets and Numerals Dataset) |
| **Official Source / DOI** | Podder et al., *Sensors* 2022 (MDPI) / [DOI: 10.3390/s22030974](https://doi.org/10.3390/s22030974) / [Mendeley Data](https://data.mendeley.com/) |
| **Language / Standard** | Bangladesh Sign Language (BdSL) — Alphabets & Numerals |
| **Modality** | Static RGB Images (extracted from video frames) |
| **Sample Count** | **~132,061 color images** (~1,500 images per class across diverse volunteers) |
| **Classes** | **87 distinct classes**: 38 one-hand alphabet signs, 36 two-hand alphabet signs, 10 digits (0–9), 2 compound numerals (`00`, `000`), 1 counting sign |
| **Annotation Format** | Directory-based classification labels; subject and lighting metadata manifests |
| **Signer Diversity** | High. Multiple volunteers of varying ages, skin tones, and backgrounds |
| **License** | **Creative Commons Attribution 4.0 International (CC BY 4.0)** |
| **Availability** | Open access; downloadable via MDPI supplementary materials and Mendeley Data |
| **Research Suitability** | Exceptional for static and two-handed BdSL alphabet recognition. Handles diverse skin tones and complex background clutter |
| **Known Limitations** | Isolated image frames; does not include continuous signing trajectory videos |

#### Candidate BDSL-02: SignBD-Word
| Field | Verified Specification |
|---|---|
| **Official Name** | SignBD-Word: Video-Based Bangla Word-Level Sign Language Dataset |
| **Official Source / DOI** | Sams, Akash, & Rahman, ICCCNT 2023 / [Zenodo DOI: 10.5281/zenodo.6779843](https://doi.org/10.5281/zenodo.6779843) |
| **Language / Standard** | Bangladesh Sign Language (BdSL) — Lexical Words |
| **Modality** | RGB Video (.mp4) + 2D Body Pose Metadata |
| **Sample Count** | **6,000 video clips** (~24.2 GB archive) |
| **Classes** | **200 unique lexical word signs** |
| **Annotation Format** | Video files mapped by gloss name; accompanying 2D pose coordinate files |
| **Signer Diversity** | Recorded from multiple signers with dual camera perspectives (full-body and upper-body) |
| **License** | **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)** |
| **Availability** | Fully downloadable via public Zenodo repository |
| **Research Suitability** | High for word-level dynamic BdSL recognition. Dual viewpoints (full-body and upper-body) facilitate torso and arm pose modeling |
| **Known Limitations** | Substantial archive size (24.2 GB); laboratory capture setting |

#### Candidate BDSL-03: BdSLW60
| Field | Verified Specification |
|---|---|
| **Official Name** | BdSLW60: A Word-Level Bangla Sign Language Dataset |
| **Official Source / DOI** | Rubaiyeat, Mahmud, Habib, & Hasan (arXiv:2402.10098, Feb 2024) / [GitHub: hasanssl/RQE](https://github.com/hasanssl/RQE) |
| **Language / Standard** | Bangladesh Sign Language (BdSL) — Lexical Words |
| **Modality** | RGB Video (.mp4) |
| **Sample Count** | **9,307 video trials** |
| **Classes** | **60 distinct sign words** |
| **Signer Diversity** | 18 native/fluent signers; annotations checked and verified by 60 annotators |
| **Annotation Format** | Bounding boxes, temporal boundary timestamps, gloss manifests |
| **License** | **GNU General Public License v2.0 (GPL 2.0)** (via official GitHub repository) |
| **Availability** | Available via GitHub project repository and author request links |
| **Research Suitability** | Excellent for evaluating temporal architectures and Relative Quantization Encoding (RQE) on dynamic signs |
| **Known Limitations** | Focuses on 60 core vocabulary words; requires license compliance with GPL 2.0 |

#### Candidate BDSL-04: BdSLW401
| Field | Verified Specification |
|---|---|
| **Official Name** | BdSLW401: Large-Scale Word-Level Bangla Sign Language Dataset |
| **Official Source / DOI** | Rubaiyeat et al. (arXiv:2503.02360, 2025) / [GitHub: hasanssl/RQE](https://github.com/hasanssl/RQE) |
| **Language / Standard** | Bangladesh Sign Language (BdSL) — Lexical Words |
| **Modality** | Multi-view RGB Video (.mp4) |
| **Sample Count** | **102,176 video samples** |
| **Classes** | **401 unique sign words** |
| **Signer Diversity** | 18 signers captured simultaneously across frontal and lateral viewpoints |
| **Annotation Format** | Skeletal landmark manifests, video temporal boundaries, gloss mappings |
| **License** | **GNU General Public License v2.0 (GPL 2.0)** |
| **Availability** | Research access hosted via academic project distribution |
| **Research Suitability** | The largest word-level BdSL video corpus available. Crucial for transformer-based sequence modeling |
| **Known Limitations** | Massive storage footprint; requires substantial GPU resources for raw video ingestion |

#### Candidate BDSL-05: BdSL36
| Field | Verified Specification |
|---|---|
| **Official Name** | BdSL36: A Dataset for Bangladeshi Sign Letters Recognition |
| **Official Source / DOI** | Hoque et al., ACCV Workshops 2021 / [arXiv:2110.00869](https://arxiv.org/abs/2110.00869) |
| **Language / Standard** | Bangladesh Sign Language (BdSL) — Letters |
| **Modality** | Static RGB Images |
| **Sample Count** | **~40,000 manually annotated images**; ~4,000,000 background-augmented images |
| **Classes** | **36 Bangladeshi sign letter categories** |
| **Annotation Format** | Pascal VOC XML and YOLO normalized bounding boxes |
| **Signer Diversity** | Multiple subjects; specifically evaluated across varying skin complexions |
| **License** | Academic Research Open Access |
| **Availability** | Available via authors' academic project repositories |
| **Research Suitability** | High for object-detection based hand localization and unconstrained background testing |
| **Known Limitations** | Synthetic background augmentation can create visual artifacts along finger boundaries |

#### Candidate BDSL-06: Ishara-Lipi
| Field | Verified Specification |
|---|---|
| **Official Name** | Ishara-Lipi: The First Complete Multipurpose Open Access Dataset of Isolated Characters for Bangla Sign Language |
| **Official Source / DOI** | Islam et al., DIU NLP Lab / [Mendeley Data](https://data.mendeley.com/) / [arXiv:1807.03901](https://arxiv.org/abs/1807.03901) |
| **Language / Standard** | Bangladesh Sign Language (BdSL) — Characters & Digits |
| **Modality** | Static RGB Images |
| **Sample Count** | **~2,800 images** (1,800 characters across 50 sets + 1,000 numeric digits) |
| **Classes** | **46 classes total**: 36 basic characters (6 vowels + 30 consonants) + 10 digits (0–9) |
| **Annotation Format** | Directory-based classification labels |
| **Signer Diversity** | 50 distinct human subjects |
| **License** | **Creative Commons Attribution 4.0 International (CC BY 4.0)** |
| **Availability** | Fully downloadable via Mendeley Data and Kaggle mirror |
| **Research Suitability** | Standard historical benchmark for isolated BdSL character classification |
| **Known Limitations** | Modest sample volume per class (~50 images); uniform indoor laboratory lighting |

---

### 2.2 American Sign Language (ASL) Datasets (Future Expansion Scope)

#### Candidate ASL-01: WLASL (Word-Level American Sign Language)
| Field | Verified Specification |
|---|---|
| **Official Name** | Word-Level American Sign Language (WLASL) |
| **Official Source / DOI** | Li et al., WACV 2020 / [arXiv:1910.11006](https://arxiv.org/abs/1910.11006) / [dxli94.github.io/WLASL](https://dxli94.github.io/WLASL/) |
| **Language / Standard** | American Sign Language (ASL) — Lexical Words |
| **Modality** | RGB Video (.mp4) |
| **Sample Count Breakdown** | **Master Index (`WLASL_v0.3.json`): 21,083 video instances.**<br>**Accessible / Filtered Videos: ~11,899 to ~14,200 videos** physically downloadable (due to YouTube link rot).<br>**Standard Subsets:**<br>- *WLASL100:* 100 classes, 2,038 video instances.<br>- *WLASL300:* 300 classes, 5,420 video instances.<br>- *WLASL1000:* 1,000 classes, 14,196 video instances.<br>- *WLASL2000:* 2,000 classes, 21,083 indexed instances. |
| **Annotation Format** | JSON metadata: `{gloss, instances: [{video_id, url, frame_start, frame_end, fps, box, signer_id}]}` |
| **Signer Diversity** | > 100 signers from educational dictionaries and online videos |
| **License** | **Computational Use of Data Agreement v1.0 (C-UDA-1.0)** — Academic, non-commercial research |
| **Availability** | Downloadable via official GitHub crawler / HuggingFace mirror |
| **Research Suitability** | High benchmark standard for isolated ASL word recognition |
| **Known Limitations** | Non-commercial restriction; broken third-party links require local cache mirrors |

#### Candidate ASL-02: MS-ASL (Microsoft American Sign Language)
| Field | Verified Specification |
|---|---|
| **Official Name** | Microsoft American Sign Language (MS-ASL) |
| **Official Source / DOI** | Vaezi Joze & Koller, BMVC 2019 / [arXiv:1812.01053](https://arxiv.org/abs/1812.01053) |
| **Language / Standard** | American Sign Language (ASL) — Lexical Words |
| **Modality** | RGB Video (.mp4) |
| **Sample Count** | **25,513 annotated video clips** (Subsets: MS-ASL100, MS-ASL200, MS-ASL500, MS-ASL1000) |
| **Classes** | **1,000 gloss classes** |
| **Signer Diversity** | 222 unique signers |
| **License** | **Computational Use of Data Agreement (C-UDA)** — Non-commercial academic research |
| **Availability** | Metadata downloadable; requires crawler execution |
| **Research Suitability** | High signer diversity and unconstrained real-world YouTube conditions |
| **Known Limitations** | Variable frame rates (15–60 FPS); non-commercial license |

#### Candidate ASL-03: ChicagoFSWild & ChicagoFSWild+
| Field | Verified Specification |
|---|---|
| **Official Name** | Chicago Fingerspelling in the Wild / Wild+ |
| **Official Source / DOI** | Shi et al., SLT 2018 & ICCV 2019 / [TTIC Research](https://ttic.edu/research/chicagofswild/) |
| **Language / Standard** | American Sign Language (ASL) — Dynamic Fingerspelling |
| **Modality** | RGB Video (.mp4) |
| **Sample Count** | 7,304 sequences (ChicagoFSWild) / **55,232 sequences** across 260 signers (ChicagoFSWild+) |
| **Classes** | 26 English letters (A–Z) in continuous fingerspelled sequences |
| **Signer Diversity** | 260 diverse online signers |
| **License** | Non-commercial Academic Research Use (TTIC / University of Chicago) |
| **Availability** | Research request via institutional contact |
| **Research Suitability** | The definitive benchmark for dynamic unconstrained fingerspelling sequences |
| **Known Limitations** | Severe motion blur and rapid co-articulation require CTC temporal decoders |

#### Candidate ASL-04: Kaggle ASL Alphabet (Akash / grassknoted)
| Field | Verified Specification |
|---|---|
| **Official Name** | ASL Alphabet Dataset |
| **Official Source / DOI** | [Kaggle: grassknoted/asl-alphabet](https://www.kaggle.com/datasets/grassknoted/asl-alphabet) (DOI: 10.34740/KAGGLE/DSV/29550) |
| **Language / Standard** | ASL Static Fingerspelling |
| **Modality** | Static RGB Images ($200 \times 200\text{ px}$) |
| **Sample Count** | 87,000 images (3,000 images per class in training set) |
| **Classes** | 29 classes: 26 letters (A–Z) + `SPACE`, `DELETE`, `NOTHING` |
| **Signer Diversity** | **Single human signer** (Zero demographic diversity) |
| **License** | **GNU General Public License v2.0 (GPL 2.0)** *(Corrected from CC BY-SA)* |
| **Availability** | Downloadable via Kaggle API |
| **Research Suitability** | **RESTRICTED:** Permitted ONLY for code pipeline smoke testing; completely unsuitable for generalizable validation due to severe single-signer bias |
| **Known Limitations** | Complete failure to generalize to unseen signers; copyleft GPL 2.0 license terms |

---

## 3. Module 02: Braille Recognition Datasets

#### Candidate OBR-01: DSBI (Double-Sided Braille Image Dataset)
| Field | Verified Specification |
|---|---|
| **Official Name** | Double-Sided Braille Image Dataset (DSBI) |
| **Official Source / DOI** | Li et al., Chinese Academy of Sciences / [arXiv:1811.10893](https://arxiv.org/abs/1811.10893) / [GitHub: yeluo1994/DSBI](https://github.com/yeluo1994/DSBI) |
| **Language / Standard** | Braille 6-dot matrix (scanned physical books) |
| **Modality** | Flatbed Color Scans (200 DPI, TIFF / PNG) |
| **Sample Count** | **114 double-sided page images** |
| **Classes / Annotations** | Recto dots, verso dots, cell coordinate boundaries in custom XML |
| **License Status** | **NO explicit OSI license file in repository.** Carries an academic research disclaimer: strictly for academic evaluation; commercial use and redistribution are unauthorized. |
| **Availability** | Publicly accessible on GitHub / OpenDataLab |
| **Research Suitability** | Gold-standard benchmark for recto/verso dot detection under controlled scanner lighting |
| **Known Limitations** | Flatbed scans lack smartphone camera lens distortion, perspective tilt, and shadows |

#### Candidate OBR-02: Angelina Braille Images Dataset
| Field | Verified Specification |
|---|---|
| **Official Name** | Angelina Braille Reader Dataset |
| **Official Source / DOI** | Ilya G. Ovodov, CVPRW 2021 / [arXiv:2104.14856](https://arxiv.org/abs/2104.14856) / [GitHub: IlyaOvodov/AngelinaDataset](https://github.com/IlyaOvodov/AngelinaDataset) |
| **Language / Standard** | Russian and English Braille (6-dot standard) |
| **Modality** | Real-world smartphone camera photographs (RGB, variable angles) |
| **Sample Count** | **~300+ full-page smartphone captures** (> 15,000 annotated characters) |
| **Classes / Annotations** | Bounding boxes around each Braille character cell labeled with class index (1–63) |
| **License Status** | **NO explicit open-source license file in repository.** Developed under an open non-profit educational assistive framework. Commercial use or redistribution rights are NOT formally granted. |
| **Availability** | Downloadable via GitHub |
| **Research Suitability** | High for real-world smartphone capture robustness (captures page folds, shadows, and perspective tilt) |
| **Known Limitations** | Absence of formal open-source license text; mixed language characters |

#### Candidate OBR-03: Braille Character Dataset (Kaggle / Shanks0465)
| Field | Verified Specification |
|---|---|
| **Official Name** | Braille Character Dataset |
| **Official Source** | [Kaggle: Shanks0465/braille-character-dataset](https://www.kaggle.com/datasets/shanks0465/braille-character-dataset) |
| **Language / Standard** | English Braille Grade 1 Alphabet (A–Z) |
| **Modality** | Segmented Grayscale Image Patches ($28 \times 28\text{ px}$) |
| **Sample Count** | **3,060 cropped image patches** (~117–120 images per class) |
| **Classes** | 26 English alphabet classes (`a` through `z`) |
| **License Status** | **Creative Commons Attribution 4.0 International (CC BY 4.0)** |
| **Availability** | Fully downloadable via Kaggle API |
| **Research Suitability** | Useful for pre-training isolated cell-pattern classifiers; not usable for document layout analysis |
| **Known Limitations** | Pre-cropped images bypass document-level segmentation, line detection, and skew correction |

#### Candidate OBR-04: Roboflow Braille Object Detection Datasets
| Field | Verified Specification |
|---|---|
| **Official Name** | Roboflow Braille YOLO Detection Datasets (e.g., `braille-wvmcp-2toax`) |
| **Official Source** | [Roboflow Universe](https://universe.roboflow.com/) |
| **Language / Standard** | 6-dot Braille cells (UEB compatible) |
| **Modality** | Photographed Braille document crops with annotated bounding boxes |
| **Sample Count** | Subsets ranging from 500 to 2,500 annotated photographs |
| **Classes / Annotations** | YOLOv8 normalized format: `class_id, x_center, y_center, width, height` |
| **License Status** | **Public Domain (CC0 1.0) or CC BY 4.0** (depending on individual project release) |
| **Availability** | Directly exportable in YOLOv8, Pascal VOC, or COCO formats |
| **Research Suitability** | High for fine-tuning cell localization models on natural photographs |
| **Known Limitations** | Community annotations require programmatic inspection to filter misaligned boxes |

---

## 4. Structured Dataset Feasibility Analysis (Revised for BdSL Priority)

### Q1: Which datasets are actually usable?
- **For Sign Language (BdSL MVP):**
  - **Static Alphabet Baseline:** `BdSL-D1500` (132,061 images across 87 classes, CC BY 4.0) provides an extensive, multi-subject image corpus covering both one-handed and two-handed alphabets. `Ishara-Lipi` (50 subjects, CC BY 4.0) and `BdSL36` serve as complementary benchmarks.
  - **Isolated Word Recognition:** `BdSLW60` (9,307 videos, 60 words, GPL 2.0) and `SignBD-Word` (6,000 videos, 200 words, CC BY-SA 4.0) are fully usable for training temporal sequence models on lexical BdSL words.
- **For Braille Recognition (UEB Grade 1 MVP):**
  - `Roboflow Braille Datasets` (CC0 / CC BY 4.0) and `Angelina Braille Images` provide the necessary bounding-box annotations for cell localization. `Braille Character Dataset` (CC BY 4.0) provides pre-segmented patches for cell-pattern classification.

### Q2: Which datasets require preprocessing?
- **BdSL Video Datasets (`SignBD-Word`, `BdSLW60`):** Require offline landmark extraction using MediaPipe Holistic (extracting both hands and upper-body pose), coordinate centering, scale normalization, and storage as compressed `.npy` arrays.
- **Braille Document Images:** Require resolution normalization, Laplacian blur rejection, CLAHE shadow compensation, and conversion to YOLO bounding box format.

### Q3: Whether multiple datasets can be combined?
- **BdSL Alphabet:** `Ishara-Lipi` and `BdSL-D1500` can be merged for shared character classes after label harmonization, increasing subject and background diversity.
- **Braille:** Roboflow photographs and DSBI scans can be combined to train a robust 1-class cell localization model.

### Q4: Whether additional data collection is necessary?
- **Yes, for local validation:** A gold-standard test set of 3–5 diverse signers performing core BdSL signs in front of standard consumer webcams must be collected locally to verify real-time performance on held-out subjects.

### Q5: Whether synthetic data can supplement real data?
- **Sign Language:** Coordinate augmentation (rotation $\pm 10^\circ$, scale perturbation $\pm 15\%$, Gaussian noise $\sigma = 0.005$) applied directly to numerical landmarks. No synthetic 3D avatars.
- **Braille:** Synthetic rendering of 6-dot Braille cells onto paper textures with randomized shadows and blur provides effective data augmentation for the cell-pattern classifier.

### Q6: Whether available datasets are sufficient for the intended MVP?
- **Verdict: YES.** The combination of `BdSL-D1500`, `BdSL36`, and `BdSLW60` provides sufficient sample volume, class coverage, and signer diversity to train a dedicated BdSL recognition engine without requiring custom dataset collection from scratch.
