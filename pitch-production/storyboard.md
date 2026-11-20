# Transify Care — 180-Second Video Pitch Storyboard
**Competition**: AI Builders Congress  
**Challenge**: HealthSphere AI → CareAnywhere  
**Track**: Idea to Unicorn — Preliminary Submission  
**Total Running Time**: Exactly 180 Seconds (03:00)

---

## 🎬 Narrative Arc Overview

| Act | Timestamp | Title | Core Focus | Visual Style |
|---|---|---|---|---|
| **Act I** | 0:00 – 0:30 (30s) | The Silent Barrier | The Crisis of Healthcare Accessibility in Bangladesh | Editorial human photography, stark statistic |
| **Act II** | 0:30 – 1:00 (30s) | Transify Care | The Unified Modality Engine (Sign, Braille, Voice, Text) | Sleek UI, modality grid, live sensor feeds |
| **Act III** | 1:00 – 2:00 (60s) | Live Demonstration | 3 Representative Real-World Clinical Triage Scenarios | Screen capture of real working app, Zero Auto-Audio |
| **Act IV** | 2:00 – 2:30 (30s) | AI Safety Architecture | Deterministic Rules + Clinical RAG + Clinician Overrides | Technical architecture diagram, guideline citations |
| **Act V** | 2:30 – 3:00 (30s) | The CareAnywhere Horizon | Low-Bandwidth Edge Sync, Primary Clinic Impact, Unicorn Scale | Dhaka clinic visuals, roadmap, closing mission |

---

## Act I: The Silent Barrier (0:00 – 0:30)

### Scene 1.1: The Waiting Room (0:00 – 0:12)
- **Visual**: Raking morning light in an outpatient primary clinic in Dhaka. An anxious Deaf patient sits opposite a busy doctor, trying to communicate chest discomfort. The doctor struggles to comprehend.
- **On-Screen Text**: *"59.1% of surveyed individuals with disabilities in Bangladesh report dissatisfaction with healthcare information and communication."* (Source: BMC Health Services Research, 2022 — Nawshin Torsha et al.).
- **Audio/Narration**: "In healthcare, communication is not a luxury. It is a vital sign. Yet in Bangladesh, over fifty-nine percent of surveyed individuals with disabilities report dissatisfaction with access to healthcare information and communication."
- **Key Emotion**: Urgent, empathetic, real-world grounding.

### Scene 1.2: The Core Dilemma (0:12 – 0:30)
- **Visual**: Macro montage: Fingertips feeling medical labels in Braille; a phone with inaccessible medical portals; hands signing urgently with no interpreter present.
- **On-Screen Text**: *"When symptoms cannot be communicated, care cannot begin."*
- **Audio/Narration**: "When acute chest pain strikes, or a child suffers dengue complications, seconds decide survival. For millions of Deaf, blind, and speech-impaired citizens, navigating primary clinics without accessible communication tools remains a critical barrier to timely care."

---

## Act II: Transify Care — The Unified Modality Engine (0:30 – 1:00)

### Scene 2.1: Introducing Transify Care (0:30 – 0:45)
- **Visual**: Camera pans smoothly to the Transify Care UI on a tablet. The home bento grid appears with its four assistive pillars: Sign Language, Braille OCR, Live Captions, and Natural Speech Synthesis.
- **On-Screen Text**: **TRANSIFY CARE** — *Breaking Communication Barriers. Making Healthcare Accessible.*
- **Audio/Narration**: "This is Transify Care. We have extended our multi-modal assistive AI into CareAnywhere: an accessible health intake and safety triage research prototype."

### Scene 2.2: The Multi-Modal Gateway (0:45 – 1:00)
- **Visual**: Split four-quadrant UI preview:
  1. Top-Left: Camera tracking 162-D hand landmarks (ASL/BdSL).
  2. Top-Right: Camera scanning an embossed UEB Grade 1 Braille prescription.
  3. Bottom-Left: 32-bar audio waveform live speech captions.
  4. Bottom-Right: Patient intake summary generated in real-time.
- **Audio/Narration**: "By combining real-time sign language recognition, optical Braille reading, continuous speech captioning, and natural voice synthesis, Transify Care enables patients to articulate acute symptoms in the modality they know best—whether Bangladesh Sign Language, embossed Braille, or spoken voice."

---

## Act III: Live Product Demonstration (1:00 – 2:00)

### Scene 3.1: Case 1 — RED Emergency (Sign Language Acute Chest Pain) (1:00 – 1:25)
- **Visual**: Screen recording of Transify Care Wizard.
  - Modality: **Sign Language** chosen.
  - Camera captures gestures: *Chest Pain*, *Difficulty Breathing*.
  - Patient confirms: *"Severe crushing chest pain radiating to left arm for 45 minutes."* Severity slider set to 9. Trajectory: *Worsening*.
  - Patient checks explicit mandatory consent.
  - Triage Result instantly flags **URGENCY: RED** (`RULE-EMERG-001`).
  - Emergency contact box displays one-touch direct buttons to **National Emergency 999** and **Health Helpline 16263**.
- **On-Screen Text**: **URGENCY LEVEL: RED** • Potential Acute Coronary Syndrome Flag • Direct 999 & 16263 Actions.
- **Audio/Narration**: "Watch this live. A Deaf patient signs severe chest pain radiating down their arm. Transify Care parses the sensor landmarks, confirms symptom details, and executes our deterministic safety engine. It immediately flags Urgency RED—potential acute coronary syndrome. There is no ambiguous chatbot hallucination: it instantly displays emergency contact actions with direct one-touch calls to Bangladesh National Emergency 999 and the 16263 health helpline."

### Scene 3.2: Case 2 — YELLOW Urgent (Voice STT Dengue Warning Signs) (1:25 – 1:45)
- **Visual**:
  - Modality: **Voice Hub**.
  - Patient speaks in Bengali/English: *"3 days high fever, severe persistent stomach pain, vomiting."*
  - Structured clarification: Severity 7, Trajectory: *Worsening*.
  - Triage Result: **URGENCY: YELLOW** (`RULE-URGENT-001`).
  - Evidence lookup accordion highlights: *DGHS National Dengue Clinical Management Guidelines (5th Ed, 2023)*.
- **Audio/Narration**: "Next, a febrile patient speaks through our Voice Hub. Symptoms of high fever and persistent vomiting match DGHS national guideline warning signs, categorizing the case as Urgency YELLOW for prompt clinical examination."

### Scene 3.3: Case 3 — GREEN Routine (Braille OCR Mild Cough) (1:45 – 2:00)
- **Visual**:
  - Modality: **Braille Document Scanner**.
  - Upload of embossed Braille card. OCR decodes: *"Mild dry cough for 2 days, no fever."*
  - Severity: 2, Trajectory: *Stable*.
  - Triage Result: **URGENCY: GREEN** (`RULE-ROUTINE-001`).
  - Patient taps **"🔊 Listen to Assessment"** (Strict Zero Auto-Audio policy: voice synthesizes only on demand).
- **Audio/Narration**: "Finally, an embossed Braille card describing a mild dry cough is decoded and assigned Urgency GREEN. And respecting patient comfort, our strict Zero Auto-Audio policy speaks only when the user explicitly taps 'Listen.'"

---

## Act IV: AI Safety, Clinical Evidence Lookup & Human-in-the-Loop (2:00 – 2:30)

### Scene 4.1: Deterministic Rules & Grounded Evidence (2:00 – 2:12)
- **Visual**: Split animation showing an ungrounded LLM hallucinating medical advice vs. Transify Care's deterministic triage tree and protocol lookup.
- **On-Screen Text**: *Zero Ungrounded Generation • Deterministic Safety Rules • Protocol Citations*.
- **Audio/Narration**: "Safety in health AI is non-negotiable. Transify Care never offers autonomous medical diagnoses. Instead, our prototype keyword-based clinical evidence lookup retrieves protocol passages directly from World Health Organization and DGHS guidelines."

### Scene 4.2: Clinician Portal & Justified Overrides (2:12 – 2:30)
- **Visual**: Supervisor dashboard on desktop. A reviewer inspects the incoming queue.
  - Reviewer clicks Case #001.
  - Side-by-side view: Original Sign transcript + AI triage + Evidence lookup guideline citations.
  - Reviewer selects "Override Urgency". A mandatory clinical justification dialog appears: *Overrides are strictly audit-logged*.
- **Audio/Narration**: "In our clinician-review workflow prototype, healthcare staff can review incoming queues. If a reviewer modifies an urgency level, our system mandates a documented clinical justification—recording a tamper-evident audit trail of human oversight."

---

## Act V: Impact, Low-Bandwidth & The Path Forward (2:30 – 3:00)

### Scene 5.1: CareAnywhere: Offline Draft Capture Prototype (2:30 – 2:45)
- **Visual**: Tablet shows "Offline Mode". A rural clinic worker inputs a symptom draft. The badge updates to "Draft saved locally — no clinical assessment while offline". The tablet reconnects, and the badge switches to "Online — 1 Draft Synchronized".
- **On-Screen Text**: *CareAnywhere: Zero-Bandwidth Draft Capture • Authenticated Edge Sync*.
- **Audio/Narration**: "In rural community clinics across Bangladesh, internet connectivity is fragile. Transify Care includes an offline draft capture prototype—saving unassessed drafts locally and synchronizing once an authenticated connection is restored."

### Scene 5.2: The Vision & Closing Pitch (2:45 – 3:00)
- **Visual**: Hero shot of patient, family, and clinician in Dhaka smiling together. Logo lockup appears: **TRANSIFY CARE**.
- **On-Screen Text**: *HealthSphere AI • AI Builders Congress 2026 • Transify Care*.
- **Audio/Narration**: "Over one billion people live with disabilities worldwide. In Bangladesh alone, millions are locked out of timely care. Transify Care bridges the silence. Because healthcare begins when every patient can be understood."
- **Closing Title Card**: **Transify Care** | *Idea to Unicorn Submission* | GitHub: Safin313-REBORN/Transify_2.0
