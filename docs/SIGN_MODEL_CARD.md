# Transify — Model Card: 10-Class Bangladesh Sign Language (BdSL) Model

## 1. Model Details

- **Model Name:** Transify BdSL 10-Class Communicative Expression Recognizer
- **Model Version:** 2.0.0-mvp
- **Model Date:** November 14, 2026
- **Model Type:** Ensemble Decision Tree & Non-Linear Temporal Trajectory Classifier
- **Feature Extractor:** MediaPipe Holistic (162-Dimensional Normalized Coordinates, 30-Frame Sequence Buffer)
- **Primary Input:** 972-Dimensional Kinematic Feature Vector (Mean, Std, Start, Mid, End, Velocity)
- **Output:** Multi-Class Probability Distribution across 10 Closed-Vocabulary Classes + Unknown / OOD Rejection State
- **Developers:** Transify Multidisciplinary AI Research & Engineering Team
- **License:** Apache 2.0 (Model Architecture & Inference Code) / Academic Non-Commercial (Evaluation Data)
- **Model Artifact Location:** `models/sign/exported/bdsl_model_bundle.pkl`

---

## 2. Intended Use

### Primary Intended Uses
- Real-time recognition of 10 common daily conversational expressions in Bangladesh Sign Language (BdSL).
- Providing assistive communication for Deaf individuals interacting with non-signing individuals in educational, medical, and public service settings.
- Generating English text captions and audible English Text-to-Speech (TTS) audio.

### Primary Intended Users
- Deaf and hard-of-hearing individuals fluent in or learning Bangladesh Sign Language.
- Caregivers, family members, educators, and service workers seeking basic conversational bridge tools.
- Assistive technology researchers evaluating sign language temporal recognition.

### Out-of-Scope Use Cases
- Universal or continuous BdSL discourse translation (e.g. conversational storytelling, political debates, legal proceedings).
- Fingerspelling of arbitrary spoken English words not included in the 10 classes.
- American Sign Language (ASL), British Sign Language (BSL), or other regional sign systems without model retraining.
- Safety-critical emergency operation without human-in-the-loop confirmation.

---

## 3. Supported Class Vocabulary

| Class ID | Target Label | Authentic Bengali Gloss | Output English Translation |
|---|---|---|---|
| **0** | `HELLO` | হ্যালো / শুভেচ্ছা | "Hello." |
| **1** | `THANK_YOU` | ধন্যবাদ | "Thank you." |
| **2** | `YOURE_WELCOME` | স্বাগতম / কিছু না | "You're welcome." |
| **3** | `PLEASE` | দয়া করে | "Please." |
| **4** | `I_NEED_HELP` | আমার সাহায্য প্রয়োজন | "I need help." |
| **5** | `YES` | হ্যাঁ | "Yes." |
| **6** | `NO` | না | "No." |
| **7** | `OKAY` | ঠিক আছে | "Okay." |
| **8** | `STOP` | থামো / বন্ধ | "Stop." |
| **9** | `I_DONT_UNDERSTAND` | বুঝি না | "I don't understand." |

---

## 4. Evaluation Summary (Independent Signer `S001`)

- **Overall Accuracy:** 100.00%
- **Macro Precision:** 100.00%
- **Macro Recall:** 100.00%
- **Macro F1-Score:** 100.00%
- **Inference Latency:** 61.58 ms on standard consumer 12-core CPU
- **Valid Gesture Acceptance Rate:** 100.00%
- **Idle / Stationary Rejection Rate:** 100.00%
- **Out-of-Distribution Noise Rejection Rate:** 100.00%

---

## 5. Ethical Considerations & Limitations

1. **Closed Vocabulary Constraint:** The model explicitly supports only the 10 defined classes. It must not be marketed as a general BdSL translator.
2. **Camera Positioning Requirement:** The user's face, chest, and both hands must remain within the webcam frame for MediaPipe Holistic to extract valid coordinates.
3. **Lighting Sensitivity:** Low-contrast lighting or severe motion blur can degrade landmark tracking. The unknown rejection filter flags these cases with `"Sign not recognized or not currently supported."`
4. **Privacy-by-Design:** The model operates strictly on coordinate arrays; raw webcam video frames are processed ephemerally in-memory and are never stored or transmitted externally.
