# Transify 2.0 — Bangladesh Sign Language (BdSL) Community Validation & Vocabulary Expansion Protocol

**Document Version:** 2.1.0  
**Status:** National Hackathon Research & Engineering Protocol  
**Domain:** Assistive Multimodal Machine Learning & Deaf Community Co-Design  
**Target Source Language:** Bangladesh Sign Language (BdSL / বাংলা ইশারা ভাষা)

---

## 1. Ethical Stance & Linguistic Integrity

### 1.1 Non-Fabrication & Reality Principle
In human-facing assistive technology, claiming that a prototype model understands all sign language or recognizing words outside its training corpus is dangerous and unethical. 
1. **Separation of Language Modalities:**
   - **Bangladesh Sign Language (BdSL):** A natural, grammatically distinct visual-spatial language with its own morphology, syntax, and cultural context. Transify's production temporal sequence classifier operates on a closed vocabulary of **10 verified communicative expressions**.
   - **American Sign Language (ASL) Fingerspeller:** An independent 24-class static alphabet model (`A`–`Y` excluding `J` and `Z`) trained on Sign Language MNIST. ASL letter shapes must **never** be conflated with or labeled as BdSL characters.
   - **HaGRID Gesture Classifier:** A 24-pose geometric gesture classifier developed as a synthetic-template baseline for communicative and media controls. It is a gesture recognizer, not a sign language parser.
2. **Community Validation Prerequisite:**
   - No new sign class may be added to Transify solely by modifying code strings, writing heuristic bounding-box rules, duplicating existing weights, or synthesizing artificial hand landmarks.
   - Any expansion beyond the current 10 production classes requires direct consultation, review, and verification by native or fluent BdSL signers and qualified Deaf community educators.

---

## 2. Bounded Candidate Vocabulary for First Expansion

Transify proposes a high-utility, reviewable candidate vocabulary designed specifically for daily needs, safety, and assistive conversation:

| Candidate ID | English Concept | Proposed BdSL Gloss | Domain / Use Case | Status | Community Validation Target |
|:---|:---|:---|:---|:---|:---|
| `BDSL_C10` | Water, please | পানি / জল | Daily Needs | `PENDING_REVIEW` | 15 trials $\times$ 8 signers ($N=120$) |
| `BDSL_C11` | Food / Hungry | খাবার / ক্ষুধা | Daily Needs | `PENDING_REVIEW` | 15 trials $\times$ 8 signers ($N=120$) |
| `BDSL_C12` | Restroom | টয়লেট / শৌচাগার | Daily Needs | `PENDING_REVIEW` | 15 trials $\times$ 8 signers ($N=120$) |
| `BDSL_C13` | I am in pain | ব্যথা / যন্ত্রণা | Healthcare | `PENDING_REVIEW` | 15 trials $\times$ 8 signers ($N=120$) |
| `BDSL_C14` | Doctor | ডাক্তার / চিকিৎসক | Healthcare | `PENDING_REVIEW` | 15 trials $\times$ 8 signers ($N=120$) |
| `BDSL_C15` | Please wait | অপেক্ষা করুন | Conversation | `PENDING_REVIEW` | 15 trials $\times$ 8 signers ($N=120$) |
| `BDSL_C16` | Repeat / Slow | ধীরে বলুন / আবার বলুন | Accessibility | `PENDING_REVIEW` | 15 trials $\times$ 8 signers ($N=120$) |

---

## 3. Four-Stage Validation Pipeline

```
┌────────────────────────────────────────────────────────────────────────┐
│               BDSL VOCABULARY EXPANSION WORKFLOW                      │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Linguistic & Community Review                                       │
│    • Native BdSL signer / Deaf advisor review                          │
│    • Validate handshape, location, movement, orientation, facial cues   │
│    • Record anonymous advisor review ID (e.g. BD-DEAF-ADV-01)          │
│    • Document regional variations (Dhaka, Chittagong, Sylhet)          │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Informed-Consent Field Recording                                    │
│    • Minimum 8 diverse signers (varying skin tones, handedness, ages)  │
│    • 15 continuous video trials per signer per class (T=30 frames)     │
│    • Signed informed consent stored separately from landmark data      │
│    • Opaque signer IDs (S009 - S016) with zero PII in repo             │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Feature Extraction & Integrity Audit                                │
│    • 21 pose + 42 hand landmarks (162 features / frame)                │
│    • Rigorous check: 0 NaNs, 0 missing values, coordinate bounds check │
│    • Partition by signer into Train / Val / Test (Leave-Signer-Out)    │
│    • Zero data leakage across splits                                   │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Model Training & Independent LSO Acceptance                         │
│    • Train sequence classifier on Train split only                     │
│    • Tune thresholds on Val split; Held-out Test split untouched       │
│    • Acceptance Gate: Macro F1 >= 0.90 on unseen signers, p95 <= 120ms │
│    • Verified rejection of Out-Of-Vocabulary / Idle / Ambiguous signs  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. UI & Transparency Contract

In the Transify web workspace and mobile app:
1. **Production Signs:** Displayed with green badge `Supported (10-Class BdSL Closed Vocabulary)`.
2. **Candidate Signs:** Displayed with blue/amber badge `In Validation Pipeline — Coming after Community Review & Data Collection`.
3. **Ambiguity Handling:** When the neural network or landmark tracking produces confidence below the calibrated threshold, Transify displays `Not sure — please repeat` and presents alternative candidate options. It **never** auto-confirms or auto-speaks unverified signs.
4. **Safety-Critical Confirmation:** Health, pain, and emergency expressions require explicit human confirmation before dispatching or speaking.
