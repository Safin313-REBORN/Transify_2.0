# Transify Care — Step-by-Step Live Demo Presentation Script
**Demo URL**: `http://localhost:8000` (or local development server)  
**Target Duration**: 180 Seconds  
**Objective**: Demonstrate multi-modal healthcare intake, deterministic triage safety engine, emergency contact actions, clinical evidence lookup prototype, and clinician review governance.

---

## 🛠️ Pre-Flight Preparation (30 seconds before recording)

1. Ensure the server daemon is running:
   ```bash
   ./.venv/bin/uvicorn src.api.server:app --port 8000
   ```
2. Open Chrome or Chromium to `http://localhost:8000`.
3. Click the yellow pill in the header: **⚡ 180s Demo Cases** (or run `curl -X POST http://localhost:8000/api/care/demo/reset`).
   > [!NOTE]
   > This endpoint pre-populates three synthetic cases for rapid workflow demonstration. Do not describe pre-populated demo records as live camera, microphone, or Braille capture. Live sign and Braille modules can be demonstrated separately; when genuine recognition output is transferred into the intake wizard, highlight the patient confirmation step.

---

## 🖱️ Step-by-Step Execution Guide

### Part 1: Home Overview & Impact (0:00 – 0:45)
1. **Starting Point**: User is on `http://localhost:8000` (Home Hub).
2. **Action 1**: Point to the **Transify Care** header and live **Online** badge.
3. **Action 2**: Highlight the **59.1%** disability healthcare barrier statistic banner (citing BMC Health Services Research, 2022).
4. **Action 3**: Hover over the Bento Grid showing the four working modalities:
   - Hand Sign (ASL & BdSL camera recognition)
   - Braille (Optical UEB Grade 1 OCR)
   - Speech to Text (Live audio captioning)
   - Text to Speech (Natural voice synthesis)

---

### Part 2: Starting Accessible Health Intake (0:45 – 1:15)
1. **Action 4**: Click the large top bento card: **"Accessible Health Intake"** (or press the **Care** pill in the bottom nav).
2. **Transition**: Slide 05 `#slide-care-intake` smoothly opens from the right.
3. **Action 5**: In **Step 1 (Modality)**, click the **Sign Language (🤟)** card.
   - Point out that live sensor recognition can be used, with the user reviewing and confirming the recognized symptom text.
   - Type or verify confirmed symptom text: *"I have severe crushing chest pain radiating to my left arm for 45 minutes."*
4. **Action 6**: Click **"Continue to Symptom Details →"**.

---

### Part 3: Structured Symptom Clarification & Triage (1:15 – 1:45)
1. **Action 7**: In **Step 2 (Symptoms)**:
   - Chief Complaint: `Severe crushing chest pain`
   - Duration: `45 minutes`
   - Trajectory: Click **"Worse"** (worsening).
   - Severity: Drag the slider to **9 / 10**.
   - Medical Context: `Deaf signer, hypertension`.
2. **Action 8**: Click **"Review & Consent →"**.
3. **Action 9**: In **Step 3 (Consent)**:
   - Point out the mandatory patient consent checkbox (`#care-consent-check`). Note that server enforcement rejects any intake without explicit consent.
   - Click **"Submit Healthcare Intake"**.
4. **Action 10**: The **Triage Assessment** evaluates instantly:
   - Highlight the prominent **URGENCY: RED** banner (`RULE-EMERG-001`).
   - Highlight the **Emergency Escalation Box**: Displays emergency contact actions with one-touch direct buttons to **National Emergency 999** and **Health Helpline 16263**.
   - Point out the **Clinical Evidence Lookup Prototype** citing the *WHO Integrated Primary Care Protocol*.
   - **Zero Auto-Audio Demo**: Emphasize that no audio plays uninvited. Click **"🔊 Listen to Assessment"** to show explicit, on-demand speech synthesis.

---

### Part 4: Clinician Review Portal & Governance (1:45 – 2:25)
1. **Action 11**: Click **"Clinician Queue →"** (or click the **Clinic** pill on the bottom navigation).
2. **Transition**: Slide 06 `#slide-clinician-portal` opens smoothly.
3. **Action 12**: Point out the live telemetry metrics:
   - Total Intakes Queued
   - Clinical Evidence Sources (WHO, DGHS Bangladesh 5th Ed, NINS)
   - Append-Only Tamper-Evident Audit Logging
4. **Action 13**: Click row **#1** (Demo Patient 001 - Severe Crushing Chest Pain).
   - The **Clinical Case Inspector** expands.
   - Point out the side-by-side view: Patient reported input vs. AI safety evaluation vs. Clinical evidence protocol excerpt.
5. **Action 14**: Show the **Clinician Governance Control**:
   - Change Clinician Action to **"COMPLETED"**.
   - Test override: If Urgency is set to **"GREEN"**, point out that the system strictly enforces a mandatory text justification in `#clinician-override-reason`.
   - Type justification: *"Confirmed acute red flag presentation; recommended immediate physical emergency evaluation."*
   - Click **"Complete Clinical Review & Sign Off"**.
   - Notice the queue updates immediately and audit log is permanently committed.

---

### Part 5: Evidence Query & Offline Resilience (2:25 – 3:00)
1. **Action 15**: In the Clinician Evidence Search box at the bottom:
   - Type `dengue` and click **"Search"**.
   - Show the retrieved protocol excerpt: *DGHS National Guidelines for Clinical Management of Dengue Syndrome in Bangladesh (5th Edition, 2023)* with official source reference.
2. **Action 16**: Concluding remark:
   - Transify Care provides an offline draft capture prototype and deterministic safety rules, designed to make healthcare communication truly accessible across Bangladesh and developing regions.
