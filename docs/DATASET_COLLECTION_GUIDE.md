# Transify — Bangladesh Sign Language (BdSL) Dataset Collection Guide
## Operational Protocol for Field Operators & Signer Cohorts

**Document Version:** 2.0.0  
**Phase:** Phase 2 — Data Engineering & Acquisition  
**Target Vocabulary:** 10 Closed-Vocabulary Communicative BdSL Expressions  

---

## 1. Ethics, Anonymity, and Consent Protocols

Data integrity begins with informed ethical consent:
1. **Consent Verification:** Prior to recording, every participating signer must review and sign the *Transify Informed Research Consent Form*. The consent covers non-commercial academic machine learning research, feature extraction, and model training.
2. **Anonymity & PII Protection:** Signers are assigned an anonymous, opaque identifier (`S001`, `S002`, etc.). Real names, contact information, and institutional affiliations are stored in an encrypted offline registry disconnected from public repositories.
3. **Voluntary Participation:** Signers may withdraw consent or request sample deletion at any time before dataset freezing.

---

## 2. Hardware and Environmental Setup

```
                     +----------------------------------+
                     |         CEILING LIGHTING         |
                     |       (Diffuse 300-500 Lux)      |
                     +----------------------------------+
                                      |
                                      v
       [ Neutral Plain Wall / Domestic Background ]
                              |
                              v
                      +---------------+
                      | HUMAN SIGNER  | (Chest & Upper Body Visible)
                      +---------------+
                              ^
                              | 0.8m - 1.2m Distance
                              v
                      [ WEBCAM SENSOR ] (640x480 @ 30 FPS, Eye/Chest Level)
                              |
                              v
                      [ OPERATOR LAPTOP ] (Transify Recorder Script)
```

1. **Webcam Positioning:**
   - Mount camera at chest or eye level (avoid extreme upward or downward tilt).
   - Frame framing: From mid-abdomen to $\sim 15\text{ cm}$ above the head. Both hands must remain within the field of view throughout the full gesture trajectory.
2. **Lighting:**
   - Avoid strong backlight (e.g., sitting directly in front of an unshaded window).
   - Light source must illuminate the face, hands, and upper chest uniformly.
3. **Clothing:**
   - Wear solid-colored shirts contrasting with hand skin tone (avoid patterns that interfere with edge detection).
   - Avoid bulky jewelry or wristwatches that distort hand landmark regression.

---

## 3. The 10-Class Sign Execution Protocol

Operators must verify that signers adhere to the authentic phonological parameters defined in [BDSL_SIGN_VERIFICATION_REGISTRY.md](file:///c:/Users/HP/Desktop/Transify/docs/BDSL_SIGN_VERIFICATION_REGISTRY.md):

| Class | Expression | Key Cue for Signer | Common Pitfalls to Reject |
|---|---|---|---|
| **0** | `HELLO` | Open flat palm starts at temple; arc forward politely with friendly smile. | Starting below chin; waving wildly across entire screen. |
| **1** | `THANK_YOU` | Flat fingertips touch chin/lower lip; extend outward toward camera with a slight head bow. | Touching chest instead of chin; moving sideways. |
| **2** | `YOURE_WELCOME` | Both open palms face up at waist/chest; sweep inward warmly toward torso. | Turning palms downward; moving only one hand. |
| **3** | `PLEASE` | Open flat palm placed on center of chest; make 2 smooth clockwise circles. | Circular motion in air without touching/hovering over chest. |
| **4** | `I_NEED_HELP` | Left palm flat facing up; right fist placed on left palm; both lift together upward/inward toward chest with urgent brow. | Lifting hands outward; separating fist from base palm. |
| **5** | `YES` | Closed fist at mid-chest; nod fist vertically from wrist twice like a nodding head. | Horizontal waving; opening fingers. |
| **6** | `NO` | Extended index finger at mid-chest; wave horizontally side-to-side twice with negative head shake. | Vertical nodding; moving entire arm rather than wrist. |
| **7** | `OKAY` | Thumb and index tips touch forming "O"; remaining 3 fingers extended upward; hold steadily or tap forward gently. | Collapsing the 3 extended fingers; turning palm away. |
| **8** | `STOP` | Open palm held forward firmly toward camera with fingers straight up; abrupt deceleration. | Waving sideways; relaxed floppy wrist. |
| **9** | `I_DONT_UNDERSTAND` | Index finger touches/gestures near temple; sweeps downward/outward turning palm up with puzzled furrowed brow and head shake. | Forgetting the puzzled facial expression; omitting temple reference. |

---

## 4. Operating the Interactive Collection Utility (`src/data/collect_dataset.py`)

Transify provides an automated OpenCV/MediaPipe data collection script ensuring standardized clip lengths:

### 4.1 Invocation Command
```powershell
python src/data/collect_dataset.py --signer S001 --class HELLO --trials 25 --output data/sign/raw
```

### 4.2 Recording Workflow:
1. **Pre-Roll Countdown (3 seconds):** The screen displays a 3-2-1 countdown overlay. The signer assumes the neutral rest position.
2. **Active Recording (2.0 seconds / 60 frames):**
   - The border turns **GREEN**.
   - The signer performs the gesture at natural tempo.
   - MediaPipe Holistic runs live; if hand landmarks are lost for $> 5$ consecutive frames, a **RED WARNING** prompts a re-take.
3. **Post-Roll Review & Validation:**
   - The operator presses `[Y]` to accept and save the trial.
   - The operator presses `[R]` to reject and re-record if the signer stuttered, started late, or exited the camera frame.
4. **Automatic Metadata Logging:** Upon acceptance, the trial is written to disk as `.mp4`, and a row is appended to `data/sign/annotations/dataset_master_manifest.csv`.

---

## 5. Operator Quality Verification Checklist

Before ending any recording session, the operator must verify:
- [ ] Signer signed informed consent form.
- [ ] All 10 classes have at least 20 valid trials recorded.
- [ ] At least 5 trials were recorded under each of the 3 distances (Close, Medium, Far).
- [ ] Facial expressions and head movements (NMMs) were actively produced for classes requiring them (`HELLO`, `THANK_YOU`, `I_NEED_HELP`, `NO`, `I_DONT_UNDERSTAND`).
- [ ] No files are truncated or 0-byte corruptions.
- [ ] All recordings logged to `dataset_master_manifest.csv`.
