# Transify — Sign Language Dataset Acquisition & Engineering Plan
## 10-Class Bangladesh Sign Language (BdSL) Closed-Vocabulary MVP

**Document Version:** 2.0.0  
**Phase:** Phase 2 — Dataset Engineering & Feasibility  
**Target Architecture:** MediaPipe Holistic (162D Features) + Temporal Sequence Recognition  

---

## 1. Executive Feasibility Audit of Existing BdSL Datasets

A central scientific principle of Transify is: **Never assume a dataset with word-level labels covers our exact target communicative expressions, and never relabel unrelated signs.**

Our team audited all six publicly cataloged Bangladesh Sign Language (BdSL) datasets to determine whether existing corpora can supply the 10 target expressions:

| Candidate Dataset | Primary Modality & Scope | Total Classes | Actual Label Inventory Profile | Target 10-Class Coverage Assessment |
|---|---|---|---|---|
| **BdSL-D1500** | Static RGB Images (132,061 images) | 87 Classes | 38 single-hand characters, 36 two-hand characters, 10 Bengali digits, compound numerals | **0 of 10 expressions.** Covers alphabet orthography only; zero communicative phrases. |
| **Ishara-Lipi** | Static Images (2,800 images) | 46 Classes | 36 isolated Bengali alphabet letters + 10 digits | **0 of 10 expressions.** Pure alphabet benchmark. |
| **BdSL36** | Static Images (40,000 bbox images) | 36 Classes | 36 basic Bengali sign letter categories | **0 of 10 expressions.** Pure alphabet benchmark. |
| **BdSLW60** | Video Clips (9,307 trials, 18 signers)| 60 Classes | Kinship terms (Father, Mother, Brother...) and Food/Nouns (Potato, Mango, Tea, Cake...) | **0 of 10 expressions.** Highly specific semantic domain (Family & Foods); lacks courtesy & emergency phrases. |
| **SignBD-Word** | Video Clips (6,000 clips, 16 signers)| 200 Classes | General dictionary vocabulary across full-body and upper-body perspectives | **Partial Stem Overlap (2 of 10):** Contains generic verbs "সাহায্য" (Help) and "না" (No), but lacks communicative inflection and courtesy signs ("PLEASE", "YOURE_WELCOME", "I_DONT_UNDERSTAND"). |
| **BdSLW401** | Multi-View Video (102,176 videos) | 401 Classes | Broad dictionary vocabulary across multiple semantic categories | **Partial Overlap (3 of 10):** Covers basic lexical roots, but lacks conversational expressions and standardized first-person inflections. |

---

## 2. Dataset Coverage Matrix

The coverage matrix below provides an empirical assessment of existing dataset availability versus required custom collection:

| Class ID | Target English Expression | Verified BdSL Sign / Gloss | Existing Public Data Status | Additional Collection Required |
|---|---|---|---|---|
| **0** | `HELLO` | হ্যালো / শুভেচ্ছা (Temple forward arc) | ❌ Unavailable in public research datasets | **100% Custom Collection Required** |
| **1** | `THANK_YOU` | ধন্যবাদ (Chin downward arc) | ❌ Unavailable in public research datasets | **100% Custom Collection Required** |
| **2** | `YOURE_WELCOME` | স্বাগতম / কিছু না (Chest inward sweep) | ❌ Unavailable in public research datasets | **100% Custom Collection Required** |
| **3** | `PLEASE` | দয়া করে (Chest circular motion) | ❌ Unavailable in public research datasets | **100% Custom Collection Required** |
| **4** | `I_NEED_HELP` | আমার সাহায্য প্রয়োজন (Fist on palm lift) | ⚠️ Generic "সাহায্য" in SignBD; lacks first-person directional inflection | **Custom Directional Collection Required** |
| **5** | `YES` | হ্যাঁ (Vertical fist nod) | ❌ Unavailable as verified isolated video benchmark | **100% Custom Collection Required** |
| **6** | `NO` | না (Horizontal index wag) | ⚠️ Isolated static gestures exist; video sequence unavailable | **Custom Temporal Collection Required** |
| **7** | `OKAY` | ঠিক আছে (O-ring forward tap) | ❌ Unavailable in public research datasets | **100% Custom Collection Required** |
| **8** | `STOP` | থামো / বন্ধ (Abrupt open palm forward) | ⚠️ Generic "থামা" in large corpora; lacks standardized frontal camera trials | **Custom Frontal Collection Required** |
| **9** | `I_DONT_UNDERSTAND` | বুঝি না (Temple tap to outward sweep) | ❌ Unavailable in public research datasets | **100% Custom Collection Required** |

**Scientific Conclusion:**  
No single existing public BdSL dataset provides the complete 10-class communicative vocabulary. Attempting to force-fit family kinship signs (from `BdSLW60`) or alphabet characters (from `BdSL-D1500`) into communicative labels would constitute scientific fraud. Consequently, **Transify must establish a dedicated, controlled custom dataset collection protocol.**

---

## 3. Custom Dataset Collection Architecture

### 3.1 Signer Cohort & Recording Targets
To guarantee robust generalization across demographic diversity and prevent signer leakage:
- **Participating Signers:** Minimum 10–20 independent human signers (recruited with informed academic consent).
- **Diversity Dimensions:**
  - Diverse hand shapes, skin tones, arm spans, and heights.
  - Left-hand dominant, right-hand dominant, and ambidextrous signers.
  - Native BdSL signers, trained interpreters, and assisted learners.
- **Trial Quota per Signer:** 20–30 valid repetitions per expression.
- **Target Volume:**
  $$\text{Total Dataset Target} = 15\text{ signers} \times 10\text{ classes} \times 25\text{ trials} = 3,750\text{ video sequences}$$

### 3.2 Recording Environmental Variations
To make the model resilient against everyday webcam degradation, data collection enforces randomized environmental conditions:
1. **Camera Distance:**
   - Close-up ($0.5\text{ m}$ to $0.8\text{ m}$): Hand fills $40\%$ of frame.
   - Standard ($0.8\text{ m}$ to $1.2\text{ m}$): Upper torso and head visible.
   - Distant ($1.2\text{ m}$ to $1.8\text{ m}$): Waist-up perspective.
2. **Illumination Profiles:**
   - Direct natural window lighting ($\sim 500\text{ lux}$).
   - Diffuse overhead indoor fluorescent/LED lighting ($\sim 300\text{ lux}$).
   - Low-light / side-shadow lighting ($\sim 100\text{ lux}$).
3. **Background Complexity:**
   - Plain monochrome wall (laboratory baseline).
   - Cluttered domestic/office interior (bookshelves, furniture, posters).
4. **Execution Dynamics:**
   - Normal conversational tempo ($\sim 1.0\text{ s}$ per sign).
   - Fast signing tempo ($\sim 0.6\text{ s}$ per sign).
   - Slow / instructional tempo ($\sim 1.5\text{ s}$ per sign).

---

## 4. Standardized Directory and File Structure

All raw, processed, and split files follow a strict, auditable folder hierarchy:

```
data/
└── sign/
    ├── raw/
    │   ├── HELLO/
    │   │   ├── BDSL_S001_HELLO_SES01_T01.mp4
    │   │   ├── BDSL_S001_HELLO_SES01_T02.mp4
    │   │   └── ...
    │   ├── THANK_YOU/
    │   ├── YOURE_WELCOME/
    │   ├── PLEASE/
    │   ├── I_NEED_HELP/
    │   ├── YES/
    │   ├── NO/
    │   ├── OKAY/
    │   ├── STOP/
    │   └── I_DONT_UNDERSTAND/
    ├── processed/
    │   ├── landmarks/
    │   │   ├── BDSL_S001_HELLO_SES01_T01.npy  (Shape: [30, 162])
    │   │   └── ...
    │   └── manifest.json
    ├── annotations/
    │   ├── dataset_master_manifest.csv
    │   └── signers_registry.json
    └── splits/
        ├── signer_independent_train.csv  (Signers S01..S10)
        ├── signer_independent_val.csv    (Signers S11..S12)
        └── signer_independent_test.csv   (Signers S13..S15)
```

### 4.1 Sample Metadata Naming Convention
Every video and feature array adheres to the standard format:
$$\text{BDSL\_<SignerID>\_<ClassLabel>\_<SessionID>\_<TrialID>.<ext>}$$
- `BDSL_S003_I_NEED_HELP_SES02_T14.mp4`
  - Signer ID: `S003`
  - Class Label: `I_NEED_HELP`
  - Session ID: `SES02`
  - Trial ID: `T14`

---

## 5. Metadata Schema (`dataset_master_manifest.csv`)

For complete reproducibility, every trial preserves the following metadata attributes:

| Column Name | Data Type | Description |
|---|---|---|
| `sample_id` | String | Unique UUID for the recording. |
| `signer_id` | String | Unique anonymous signer identifier (e.g., `S001`). |
| `class_id` | Integer | Class index ($0$ to $9$). |
| `class_label` | String | Standard English label (`HELLO` to `I_DONT_UNDERSTAND`). |
| `bdsl_gloss` | String | Bengali sign gloss (`হ্যালো`, `ধন্যবাদ`, etc.). |
| `session_id` | String | Recording session identifier (`SES01`, `SES02`). |
| `video_filename` | String | Relative path to `.mp4` file. |
| `landmark_filename`| String | Relative path to normalized `.npy` array. |
| `duration_sec` | Float | Video duration in seconds. |
| `frame_count` | Integer | Total raw frames captured. |
| `fps` | Float | Native webcam frame rate (typically $30.0$). |
| `resolution` | String | Video dimensions (e.g., `640x480`). |
| `distance_category`| Enum | `CLOSE`, `MEDIUM`, `FAR`. |
| `lighting_category`| Enum | `NORMAL`, `LOW`, `BRIGHT`. |
| `dominant_hand` | Enum | `RIGHT`, `LEFT`, `BOTH`. |
| `landmark_valid` | Boolean | True if $\ge 85\%$ of frames have valid hand detections. |
| `consent_verified`| Boolean | True if signed consent form is archived. |
| `split_assignment`| Enum | `TRAIN`, `VAL`, `TEST`. |
