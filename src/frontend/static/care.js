/**
 * Transify Care — Client Application Controller
 * Manages Accessible Healthcare Intake Wizard, Deterministic Triage Display,
 * Clinical Evidence Retrieval Prototype, Clinician Queue, and Offline Draft Capture.
 *
 * Security & Safety Principles:
 * 1. Safe DOM Rendering: Zero unsafe innerHTML interpolation of user-supplied or external strings.
 * 2. Truthful Offline Capabilities: Plaintext localStorage is explicitly treated as unencrypted prototype storage.
 * 3. Never display successful clinical triage while offline: "Draft saved locally — no clinical assessment performed while offline."
 * 4. Distinct safe visual presentations: RED, YELLOW, GREEN, REVIEW_REQUIRED, INSUFFICIENT_INFORMATION.
 * 5. Server-derived patient and clinician identities; no client-controlled impersonation.
 */

(function(window, document) {
  'use strict';

  function escapeText(str) {
    if (str === null || str === undefined) return '';
    return String(str);
  }

  function clearElement(el) {
    while (el && el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  const TRUSTED_DEMO_FIXTURES = {
    'synthetic-demo-patient-001': {
      modality: 'sign',
      chief_complaint: '[SYNTHETIC DEMO] Severe crushing chest pain and shortness of breath'
    },
    'synthetic-demo-patient-002': {
      modality: 'voice',
      chief_complaint: '[SYNTHETIC DEMO] High fever and severe persistent stomach pain'
    },
    'synthetic-demo-patient-003': {
      modality: 'braille',
      chief_complaint: '[SYNTHETIC DEMO] Mild dry cough and scratchy throat'
    }
  };

  const TransifyCare = {
    currentStep: 1,
    selectedModality: 'text',
    activeIntakeId: null,
    isOffline: !navigator.onLine,
    _demoSessionActive: false,

    init: function() {
      this.bindEvents();
      this.setupOfflineWatcher();
      this.updateOfflineBadge();
      this.loadDashboardStats();
      this.loadClinicianQueue();
    },

    bindEvents: function() {
      const self = this;

      // Severity Slider Sync
      const slider = document.getElementById('care-severity-slider');
      const badge = document.getElementById('care-severity-badge');
      if (slider && badge) {
        slider.addEventListener('input', function() {
          badge.textContent = slider.value;
        });
      }

      // Trajectory Buttons
      document.querySelectorAll('.traj-chip-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
          document.querySelectorAll('.traj-chip-btn').forEach(b => b.classList.remove('selected'));
          btn.classList.add('selected');
        });
      });

      // Modality Selector Buttons
      document.querySelectorAll('.modality-card-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
          const mod = btn.getAttribute('data-modality');
          self.selectModality(mod);
        });
      });

      // Step Navigation Buttons
      const nextBtn1 = document.getElementById('care-next-to-symptoms');
      if (nextBtn1) nextBtn1.addEventListener('click', () => self.goToStep(3));

      const backBtn3 = document.getElementById('care-back-to-modality');
      if (backBtn3) backBtn3.addEventListener('click', () => self.goToStep(1));

      const nextBtn3 = document.getElementById('care-next-to-consent');
      if (nextBtn3) nextBtn3.addEventListener('click', () => {
        const complaint = document.getElementById('care-chief-complaint')?.value?.trim();
        if (!complaint) {
          alert('Please describe your main health concern before proceeding.');
          return;
        }
        self.goToStep(4);
      });

      const backBtn4 = document.getElementById('care-back-to-symptoms');
      if (backBtn4) backBtn4.addEventListener('click', () => self.goToStep(3));

      // Submit Intake Button
      const submitBtn = document.getElementById('care-submit-intake-btn');
      if (submitBtn) submitBtn.addEventListener('click', () => self.submitIntake());

      // Reset Demo Button
      const demoBtn = document.getElementById('btn-care-demo-reset');
      if (demoBtn) demoBtn.addEventListener('click', () => self.resetDemoFixtures());

      // Quick Demo Pill on Home
      const quickDemoPill = document.getElementById('quick-demo-pill-btn');
      if (quickDemoPill) quickDemoPill.addEventListener('click', () => {
        self.resetDemoFixtures(function() {
          if (typeof openSlide === 'function') openSlide('slide-clinician-portal');
        });
      });

      // Clinician Review Form Submit
      const reviewSubmitBtn = document.getElementById('btn-complete-clinician-review');
      if (reviewSubmitBtn) reviewSubmitBtn.addEventListener('click', () => self.submitClinicianReview());

      // Clinician Evidence Search Form
      const evidenceSearchBtn = document.getElementById('btn-clinician-evidence-search');
      if (evidenceSearchBtn) evidenceSearchBtn.addEventListener('click', () => {
        const query = document.getElementById('clinician-evidence-search-input')?.value;
        if (query) self.searchEvidence(query);
      });

      // TTS Speak Triage Result (Strict Zero Auto-Audio: Only triggered on explicit user click)
      const ttsBtn = document.getElementById('btn-care-speak-triage');
      if (ttsBtn) ttsBtn.addEventListener('click', () => self.speakTriageAssessment());
    },

    setupOfflineWatcher: function() {
      const self = this;
      window.addEventListener('online', function() {
        self.isOffline = false;
        self.updateOfflineBadge();
        self.syncOfflineDrafts();
      });

      window.addEventListener('offline', function() {
        self.isOffline = true;
        self.updateOfflineBadge();
      });
    },

    updateOfflineBadge: function() {
      const badges = document.querySelectorAll('.care-offline-badge');
      const drafts = this.getStoredDrafts();
      const count = drafts.length;

      badges.forEach(function(badge) {
        clearElement(badge);
        const dot = document.createElement('span');
        dot.className = 'care-offline-dot';
        badge.appendChild(dot);

        const textSpan = document.createElement('span');
        if (navigator.onLine) {
          badge.className = 'care-offline-badge online';
          textSpan.textContent = count > 0 ? `Online (${count} drafts pending sync)` : 'Online';
        } else {
          badge.className = 'care-offline-badge offline';
          textSpan.textContent = `Offline Mode (${count} local drafts)`;
        }
        badge.appendChild(textSpan);
      });
    },

    getStoredDrafts: function() {
      try {
        const data = localStorage.getItem('transify_care_drafts');
        return data ? JSON.parse(data) : [];
      } catch (e) {
        return [];
      }
    },

    startDemoSession: function() {
      this._demoSessionActive = true;
    },

    endDemoSession: function() {
      this._demoSessionActive = false;
    },

    getTrustedDemoFixture: function(fixtureId) {
      if (!TRUSTED_DEMO_FIXTURES[fixtureId]) return null;
      const f = TRUSTED_DEMO_FIXTURES[fixtureId];
      return {
        fixture_id: fixtureId,
        patient_id: fixtureId,
        input_modality: f.modality,
        chief_complaint: f.chief_complaint,
        confirmed_text: f.chief_complaint,
        symptom_description: f.chief_complaint,
        severity: fixtureId === 'synthetic-demo-patient-001' ? 9 : (fixtureId === 'synthetic-demo-patient-002' ? 7 : 2),
        trajectory: fixtureId === 'synthetic-demo-patient-003' ? 'stable' : 'worsening',
        onset_duration: fixtureId === 'synthetic-demo-patient-001' ? '45 minutes' : (fixtureId === 'synthetic-demo-patient-002' ? '3 days' : '2 days'),
        consent_granted: true,
        is_trusted_fixture: true
      };
    },

    isSyntheticDemoDraft: function(draft) {
      if (!draft || typeof draft !== 'object') return false;
      // Fail closed: Never rely on patient-entered text substrings ("demo", "synthetic")
      // Never rely on globally writable JavaScript flags (e.g. window.TRANSIFY_SYNTHETIC_DEMO_MODE)
      // Must match a dedicated application-controlled demo fixture identity
      const fixtureId = draft.fixture_id || draft.demo_fixture_id || draft.patient_id;
      if (!fixtureId || !TRUSTED_DEMO_FIXTURES[fixtureId]) {
        return false;
      }
      const trusted = TRUSTED_DEMO_FIXTURES[fixtureId];
      // Verify modality matches the documented fixture
      if (draft.input_modality && draft.input_modality !== trusted.modality) {
        return false;
      }
      // Verify chief complaint matches the documented synthetic fixture definition
      if (draft.chief_complaint && draft.chief_complaint !== trusted.chief_complaint) {
        return false;
      }
      // Must be an application-trusted fixture or explicit application demo session
      return draft.is_trusted_fixture === true || this._demoSessionActive === true;
    },

    saveDraftLocally: function(draft) {
      try {
        if (!this.isSyntheticDemoDraft(draft)) {
          console.warn('[Care Privacy] Local plaintext storage of real patient health data is disabled for privacy protection.');
          return false;
        }
        const drafts = this.getStoredDrafts();
        drafts.push(draft);
        localStorage.setItem('transify_care_drafts', JSON.stringify(drafts));
        this.updateOfflineBadge();
        return true;
      } catch (e) {
        console.error('Failed to save draft locally', e);
        return false;
      }
    },

    syncOfflineDrafts: function() {
      const drafts = this.getStoredDrafts();
      if (!drafts.length) return;

      const self = this;
      fetch('/api/care/offline/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: 'browser-client-' + window.location.host,
          drafts: drafts
        })
      })
      .then(res => {
        if (res.status === 401) {
          console.warn('[Care Sync] Offline draft synchronization deferred: user authentication required.');
          return null;
        }
        if (!res.ok) throw new Error('Offline sync rejected by server.');
        return res.json();
      })
      .then(data => {
        if (data && data.success) {
          localStorage.removeItem('transify_care_drafts');
          self.updateOfflineBadge();
          self.loadClinicianQueue();
          console.log(`[Care Sync] Successfully synchronized ${data.synced_count} offline drafts.`);
        }
      })
      .catch(err => console.error('[Care Sync Error]', err));
    },

    selectModality: function(modality) {
      this.selectedModality = modality;
      document.querySelectorAll('.modality-card-btn').forEach(function(btn) {
        if (btn.getAttribute('data-modality') === modality) {
          btn.classList.add('selected');
        } else {
          btn.classList.remove('selected');
        }
      });

      // Populate text from existing modality if available
      const confirmedInput = document.getElementById('care-confirmed-text');
      const rawInput = document.getElementById('care-raw-input');

      if (modality === 'sign') {
        const pred = document.getElementById('pred-label-text')?.textContent;
        if (pred && pred !== 'Ready') {
          if (confirmedInput) confirmedInput.value = `Patient signed: ${pred}`;
          if (rawInput) rawInput.value = `ASL/BdSL Sensor: ${pred}`;
        }
      } else if (modality === 'braille') {
        const brailleOut = document.getElementById('braille-text-output')?.value;
        if (brailleOut) {
          if (confirmedInput) confirmedInput.value = brailleOut;
          if (rawInput) rawInput.value = `Braille OCR: ${brailleOut}`;
        }
      } else if (modality === 'voice') {
        const voiceText = document.getElementById('stt-final-text')?.textContent;
        if (voiceText) {
          if (confirmedInput) confirmedInput.value = voiceText;
          if (rawInput) rawInput.value = `STT Live Captions: ${voiceText}`;
        }
      }
    },

    goToStep: function(step) {
      this.currentStep = step;

      // Update Node indicators
      document.querySelectorAll('.wizard-step-node').forEach(function(node) {
        const nStep = parseInt(node.getAttribute('data-step'), 10);
        node.classList.remove('active', 'completed');
        if (nStep === step) {
          node.classList.add('active');
        } else if (nStep < step) {
          node.classList.add('completed');
        }
      });

      // Show target step container
      for (let i = 1; i <= 5; i++) {
        const el = document.getElementById(`care-step-${i}`);
        if (el) el.style.display = (i === step) ? 'block' : 'none';
      }

      // Auto-populate Step 4 Summary
      if (step === 4) {
        this.populateConfirmationSummary();
      }
    },

    populateConfirmationSummary: function() {
      const modality = this.selectedModality;
      const complaint = document.getElementById('care-chief-complaint')?.value || '';
      const desc = document.getElementById('care-symptom-desc')?.value || '';
      const onset = document.getElementById('care-onset-duration')?.value || 'Not specified';
      const severity = document.getElementById('care-severity-slider')?.value || '1';
      const traj = document.querySelector('.traj-chip-btn.selected')?.getAttribute('data-traj') || 'stable';

      const sumMod = document.getElementById('summary-modality-text');
      const sumComplaint = document.getElementById('summary-complaint-text');
      const sumDesc = document.getElementById('summary-desc-text');
      const sumMetrics = document.getElementById('summary-metrics-text');

      if (sumMod) sumMod.textContent = modality.toUpperCase();
      if (sumComplaint) sumComplaint.textContent = complaint;
      if (sumDesc) sumDesc.textContent = desc;
      if (sumMetrics) sumMetrics.textContent = `Severity: ${severity}/10 • Duration: ${onset} • Trajectory: ${traj}`;
    },

    submitIntake: function() {
      const consentCheck = document.getElementById('care-consent-check');
      if (!consentCheck || !consentCheck.checked) {
        alert('Explicit patient consent is required to process and queue health symptom data.');
        return;
      }

      const modality = this.selectedModality;
      const confirmed = document.getElementById('care-confirmed-text')?.value || document.getElementById('care-chief-complaint')?.value;
      const complaint = document.getElementById('care-chief-complaint')?.value || '';
      const desc = document.getElementById('care-symptom-desc')?.value || complaint;
      const onset = document.getElementById('care-onset-duration')?.value || '';
      const traj = document.querySelector('.traj-chip-btn.selected')?.getAttribute('data-traj') || 'stable';
      const severity = parseInt(document.getElementById('care-severity-slider')?.value || '1', 10);
      const medContext = document.getElementById('care-medical-context')?.value || '';
      const allergies = document.getElementById('care-allergies-meds')?.value || '';
      const rawInput = document.getElementById('care-raw-input')?.value || '';

      // Patient identity is derived strictly by server session; no client-controlled ID is sent
      const payload = {
        input_modality: modality,
        raw_input: rawInput,
        confirmed_text: confirmed,
        chief_complaint: complaint,
        symptom_description: desc,
        onset_duration: onset,
        trajectory: traj,
        severity: severity,
        medical_context: medContext,
        allergies_medications: allergies,
        consent_granted: true
      };

      const self = this;

      if (!navigator.onLine) {
        if (self.isSyntheticDemoDraft(payload)) {
          self.saveDraftLocally(payload);
        } else {
          alert('Offline caching of real patient health data is disabled for privacy protection. To protect personal health records, no plaintext data is cached in browser storage. Please reconnect to submit.');
        }
        self.displayOfflineTriageResult(payload);
        self.goToStep(5);
        return;
      }

      const submitBtn = document.getElementById('care-submit-intake-btn');
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Evaluating Triage...';
      }

      fetch('/api/care/intake', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => {
        if (res.status === 401) {
          throw new Error('Authentication required. Please sign in to submit a healthcare intake.');
        }
        if (!res.ok) throw new Error('Submission failed: ' + res.statusText);
        return res.json();
      })
      .then(data => {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Submit Healthcare Intake';
        }
        self.activeIntakeId = data.intake_id;
        self.renderTriageResult(data);
        self.goToStep(5);
        self.loadClinicianQueue();
        self.loadDashboardStats();
      })
      .catch(err => {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Submit Healthcare Intake';
        }
        if (err.message && err.message.includes('Authentication required')) {
          alert(err.message);
          window.location.href = '/login';
          return;
        }
        if (self.isSyntheticDemoDraft(payload)) {
          alert('Network or server error submitting intake. Saving synthetic demo fixture locally for offline sync.');
          self.saveDraftLocally(payload);
        } else {
          alert('Network or server error submitting intake. To protect patient privacy, real health records are not stored in unencrypted browser storage. Please reconnect to retry.');
        }
        self.displayOfflineTriageResult(payload);
        self.goToStep(5);
      });
    },

    renderTriageResult: function(data) {
      const container = document.getElementById('triage-assessment-output');
      if (!container) return;

      clearElement(container);

      const level = data.urgency_level || 'REVIEW_REQUIRED';
      let cssClass = 'urgency-review-required';
      let pillText = `URGENCY: ${level}`;

      if (level === 'RED') {
        cssClass = 'urgency-red';
        pillText = 'URGENCY: RED (EMERGENCY)';
      } else if (level === 'YELLOW') {
        cssClass = 'urgency-yellow';
        pillText = 'URGENCY: YELLOW (URGENT)';
      } else if (level === 'GREEN') {
        cssClass = 'urgency-green';
        pillText = 'URGENCY: GREEN (ROUTINE)';
      } else if (level === 'INSUFFICIENT_INFORMATION') {
        cssClass = 'urgency-insufficient';
        pillText = 'INSUFFICIENT INFORMATION';
      } else {
        cssClass = 'urgency-review-required';
        pillText = 'CLINICAL REVIEW REQUIRED';
      }

      const card = document.createElement('div');
      card.className = `triage-result-card ${cssClass}`;

      // Header row
      const headerRow = document.createElement('div');
      headerRow.className = 'triage-header-row';

      const leftDiv = document.createElement('div');
      const pill = document.createElement('span');
      pill.className = 'triage-level-pill';
      pill.textContent = pillText;
      leftDiv.appendChild(pill);

      const intakeNum = document.createElement('span');
      intakeNum.style.fontSize = 'var(--text-xs)';
      intakeNum.style.color = 'var(--text-muted)';
      intakeNum.style.marginLeft = '8px';
      intakeNum.textContent = `Intake #${data.intake_id || 'PENDING'}`;
      leftDiv.appendChild(intakeNum);
      headerRow.appendChild(leftDiv);

      const ruleSpan = document.createElement('span');
      ruleSpan.style.fontSize = 'var(--text-xs)';
      ruleSpan.style.fontWeight = '700';
      ruleSpan.textContent = `Rule: ${data.rule_id || 'GENERAL'}`;
      headerRow.appendChild(ruleSpan);

      card.appendChild(headerRow);

      // Explanation
      const explP = document.createElement('p');
      explP.id = 'care-triage-explanation-text';
      explP.style.fontSize = 'var(--text-sm)';
      explP.style.fontWeight = '600';
      explP.style.lineHeight = '1.5';
      explP.style.margin = '8px 0';
      explP.textContent = data.triage_explanation || 'Assessment completed and queued for clinician review.';
      card.appendChild(explP);

      // Emergency escalation callout
      if (level === 'RED' && data.emergency_escalation) {
        const emergDiv = document.createElement('div');
        emergDiv.className = 'triage-emergency-callout';

        const emergTitle = document.createElement('div');
        emergTitle.style.fontWeight = '800';
        emergTitle.style.color = 'var(--danger)';
        emergTitle.style.fontSize = 'var(--text-base)';
        emergTitle.textContent = '⚠️ EMERGENCY ESCALATION REQUIRED';
        emergDiv.appendChild(emergTitle);

        const emergAction = document.createElement('p');
        emergAction.style.fontSize = 'var(--text-xs)';
        emergAction.style.color = 'var(--text-primary)';
        emergAction.style.margin = '4px 0';
        emergAction.textContent = data.emergency_escalation.action;
        emergDiv.appendChild(emergAction);

        const btnRow = document.createElement('div');
        btnRow.style.display = 'flex';
        btnRow.style.gap = '8px';
        btnRow.style.marginTop = '8px';
        btnRow.style.flexWrap = 'wrap';

        const tel999 = document.createElement('a');
        tel999.href = 'tel:999';
        tel999.className = 'emergency-phone-btn';
        tel999.textContent = '📞 Call National Emergency (999)';
        btnRow.appendChild(tel999);

        const tel16263 = document.createElement('a');
        tel16263.href = 'tel:16263';
        tel16263.className = 'emergency-phone-btn';
        tel16263.style.background = 'var(--ink)';
        tel16263.textContent = '📞 Call Health Helpline (16263)';
        btnRow.appendChild(tel16263);

        emergDiv.appendChild(btnRow);
        card.appendChild(emergDiv);
      }

      // Evidence citations
      if (data.evidence_citations && data.evidence_citations.length > 0) {
        const citeBox = document.createElement('div');
        citeBox.className = 'clinical-evidence-box';

        const citeH4 = document.createElement('h4');
        citeH4.style.fontFamily = 'var(--font-display)';
        citeH4.style.fontSize = 'var(--text-xs)';
        citeH4.style.fontWeight = '800';
        citeH4.style.textTransform = 'uppercase';
        citeH4.style.color = 'var(--text-muted)';
        citeH4.style.letterSpacing = '0.05em';
        citeH4.textContent = 'Reference Clinical Evidence Guidelines (Prototype Lookup)';
        citeBox.appendChild(citeH4);

        data.evidence_citations.forEach(c => {
          const item = document.createElement('div');
          item.className = 'evidence-source-item';

          const title = document.createElement('div');
          title.className = 'evidence-source-title';
          title.textContent = `${c.source_title} (${c.publisher})`;
          item.appendChild(title);

          const excerpt = document.createElement('div');
          excerpt.className = 'evidence-source-excerpt';
          excerpt.textContent = `"${c.excerpt}"`;
          item.appendChild(excerpt);

          if (c.url && (c.url.startsWith('http://') || c.url.startsWith('https://'))) {
            const link = document.createElement('a');
            link.href = c.url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.className = 'evidence-source-link';
            link.textContent = 'View Official Guideline Protocol ↗';
            item.appendChild(link);
          }

          citeBox.appendChild(item);
        });

        card.appendChild(citeBox);
      }

      container.appendChild(card);
    },

    displayOfflineTriageResult: function(draft) {
      const container = document.getElementById('triage-assessment-output');
      if (!container) return;

      clearElement(container);

      const isDemo = this.isSyntheticDemoDraft(draft);

      const card = document.createElement('div');
      card.className = 'triage-result-card urgency-insufficient';

      const header = document.createElement('div');
      header.className = 'triage-header-row';

      const pill = document.createElement('span');
      pill.className = 'triage-level-pill';
      pill.textContent = isDemo ? 'OFFLINE DEMO DRAFT — UNASSESSED' : 'OFFLINE — PRIVACY PROTECTED';
      header.appendChild(pill);

      const label = document.createElement('span');
      label.style.fontSize = 'var(--text-xs)';
      label.style.color = 'var(--text-muted)';
      label.textContent = isDemo ? 'Demo Fixture Cached' : 'No Plaintext Storage';
      header.appendChild(label);
      card.appendChild(header);

      const msg = document.createElement('p');
      msg.style.fontSize = 'var(--text-sm)';
      msg.style.fontWeight = '600';
      msg.style.lineHeight = '1.5';
      msg.style.margin = '8px 0';
      msg.textContent = isDemo
        ? 'Draft saved locally — no clinical assessment performed while offline.'
        : 'Real patient health data is NOT stored in unencrypted browser storage.';
      card.appendChild(msg);

      const subMsg = document.createElement('p');
      subMsg.style.fontSize = 'var(--text-xs)';
      subMsg.style.color = 'var(--text-muted)';
      subMsg.style.margin = '4px 0';
      subMsg.textContent = isDemo
        ? 'Notice: Offline draft capture is active for synthetic demonstration fixtures only. No clinical assessment is performed offline.'
        : 'Notice: To protect patient privacy, unencrypted local draft caching is disabled for real patient health records. Please connect to an authenticated network to submit your intake directly.';
      card.appendChild(subMsg);

      const concern = document.createElement('div');
      concern.style.fontSize = 'var(--text-xs)';
      concern.style.color = 'var(--text-2)';
      concern.textContent = `Chief Concern: ${draft.chief_complaint} (${draft.input_modality.toUpperCase()})`;
      card.appendChild(concern);

      const advice = document.createElement('p');
      advice.style.fontSize = 'var(--text-xs)';
      advice.style.color = 'var(--text-muted)';
      advice.style.marginTop = '6px';
      advice.textContent = isDemo
        ? 'Status: Ready for authenticated sync when connectivity is restored.'
        : 'Status: Submission deferred until authenticated connection is restored.';
      card.appendChild(advice);

      container.appendChild(card);
    },

    speakTriageAssessment: function() {
      // Strict Zero Auto-Audio: Only runs when user explicitly taps "Listen to Assessment"
      const text = document.getElementById('care-triage-explanation-text')?.textContent;
      if (!text) {
        alert('No assessment text available to synthesize.');
        return;
      }

      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95;
        window.speechSynthesis.speak(utterance);
      } else {
        fetch('/api/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: text, language: 'en-US' })
        })
        .then(res => res.blob())
        .then(blob => {
          const audio = new Audio(URL.createObjectURL(blob));
          audio.play();
        })
        .catch(e => console.error('Audio playback failed', e));
      }
    },

    loadClinicianQueue: function(filterStatus) {
      const tbody = document.getElementById('clinician-queue-tbody');
      if (!tbody) return;

      let url = '/api/care/intakes?limit=50';
      if (filterStatus) url += `&status=${encodeURIComponent(filterStatus)}`;

      fetch(url)
      .then(res => {
        if (res.status === 401) {
          clearElement(tbody);
          const tr = document.createElement('tr');
          const td = document.createElement('td');
          td.colSpan = 6;
          td.style.textAlign = 'center';
          td.style.padding = '16px';
          td.style.color = 'var(--text-muted)';
          td.textContent = 'Please sign in to view the clinical review queue.';
          tr.appendChild(td);
          tbody.appendChild(tr);
          return null;
        }
        if (!res.ok) throw new Error('Failed to load queue.');
        return res.json();
      })
      .then(data => {
        if (!data) return;
        clearElement(tbody);
        const records = data.records || [];
        if (records.length === 0) {
          const tr = document.createElement('tr');
          const td = document.createElement('td');
          td.colSpan = 6;
          td.style.textAlign = 'center';
          td.style.padding = '24px';
          td.style.color = 'var(--text-muted)';
          td.textContent = 'No intakes currently in queue.';
          tr.appendChild(td);
          tbody.appendChild(tr);
          return;
        }

        records.forEach(r => {
          const tr = document.createElement('tr');
          tr.style.cursor = 'pointer';
          tr.addEventListener('click', () => TransifyCare.openCaseReview(r.id));

          const tdId = document.createElement('td');
          tdId.style.fontWeight = '700';
          tdId.textContent = `#${r.id}`;
          tr.appendChild(tdId);

          const tdPatient = document.createElement('td');
          tdPatient.textContent = r.patient_id;
          tr.appendChild(tdPatient);

          const tdMod = document.createElement('td');
          const modSpan = document.createElement('span');
          modSpan.className = 'phrase-chip';
          modSpan.style.fontSize = '11px';
          modSpan.textContent = (r.input_modality || '').toUpperCase();
          tdMod.appendChild(modSpan);
          tr.appendChild(tdMod);

          const tdComp = document.createElement('td');
          tdComp.style.fontWeight = '600';
          tdComp.textContent = r.chief_complaint;
          tr.appendChild(tdComp);

          const tdUrgency = document.createElement('td');
          const pill = document.createElement('span');
          const badgeClass = r.urgency_level === 'RED' ? 'urgency-red' : (r.urgency_level === 'YELLOW' ? 'urgency-yellow' : (r.urgency_level === 'GREEN' ? 'urgency-green' : 'urgency-review-required'));
          pill.className = `triage-level-pill ${badgeClass}`;
          pill.style.fontSize = '11px';
          pill.style.padding = '2px 8px';
          pill.textContent = r.urgency_level;
          tdUrgency.appendChild(pill);
          tr.appendChild(tdUrgency);

          const tdAct = document.createElement('td');
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'phrase-chip';
          btn.style.background = 'var(--violet)';
          btn.style.color = '#FFF';
          btn.textContent = 'Review';
          tdAct.appendChild(btn);
          tr.appendChild(tdAct);

          tbody.appendChild(tr);
        });
      })
      .catch(err => {
        clearElement(tbody);
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = 6;
        td.style.textAlign = 'center';
        td.style.color = 'var(--danger)';
        td.textContent = 'Failed to load clinician queue.';
        tr.appendChild(td);
        tbody.appendChild(tr);
      });
    },

    openCaseReview: function(intakeId) {
      const self = this;
      fetch(`/api/care/intake/${intakeId}`)
      .then(res => {
        if (res.status === 401) {
          throw new Error('Authentication required to view case details.');
        }
        if (res.status === 403) {
          throw new Error('Access denied: You are not authorized to inspect this intake record.');
        }
        if (!res.ok) throw new Error('Failed to load case record.');
        return res.json();
      })
      .then(intake => {
        self.activeIntakeId = intake.id;
        const inspector = document.getElementById('clinician-case-inspector');
        if (!inspector) return;

        inspector.style.display = 'block';
        inspector.scrollIntoView({ behavior: 'smooth' });

        document.getElementById('inspect-case-id').textContent = `#${intake.id} — ${intake.patient_id}`;
        document.getElementById('inspect-modality').textContent = (intake.input_modality || '').toUpperCase();
        document.getElementById('inspect-complaint').textContent = intake.chief_complaint;
        document.getElementById('inspect-symptoms').textContent = intake.symptom_description;
        document.getElementById('inspect-raw').textContent = intake.raw_input || 'N/A';
        document.getElementById('inspect-ai-urgency').textContent = intake.urgency_level;
        document.getElementById('inspect-ai-rule').textContent = intake.triage_rule_id || 'Standard Protocol';
        document.getElementById('inspect-ai-explanation').textContent = intake.triage_explanation;

        // Populate citations safely
        const citContainer = document.getElementById('inspect-citations-list');
        if (citContainer) {
          clearElement(citContainer);
          const cites = intake.evidence_citations || [];
          if (cites.length) {
            cites.forEach(c => {
              const div = document.createElement('div');
              div.style.fontSize = '11px';
              div.style.borderLeft = '2px solid var(--violet)';
              div.style.paddingLeft = '8px';
              div.style.marginTop = '4px';

              const strong = document.createElement('strong');
              strong.textContent = `${c.source_title || 'Guideline'}: `;
              div.appendChild(strong);

              const quote = document.createElement('span');
              quote.textContent = `"${c.excerpt || ''}"`;
              div.appendChild(quote);

              citContainer.appendChild(div);
            });
          } else {
            const noCite = document.createElement('span');
            noCite.style.fontSize = '11px';
            noCite.style.color = 'var(--text-muted)';
            noCite.textContent = 'No direct citation retrieved.';
            citContainer.appendChild(noCite);
          }
        }
      })
      .catch(err => alert(err.message));
    },

    submitClinicianReview: function() {
      if (!this.activeIntakeId) {
        alert('No active case selected for review.');
        return;
      }

      const action = document.getElementById('clinician-action-select')?.value || 'COMPLETED';
      const urgencyOverride = document.getElementById('clinician-override-select')?.value || 'NONE';
      const reason = document.getElementById('clinician-override-reason')?.value?.trim();
      const notes = document.getElementById('clinician-notes-textarea')?.value?.trim();

      if (urgencyOverride !== 'NONE' && !reason) {
        alert('A documented clinical justification is required when overriding AI urgency.');
        document.getElementById('clinician-override-reason')?.focus();
        return;
      }

      // Clinician ID and name are derived strictly by the server session
      const payload = {
        action: action,
        urgency_override: urgencyOverride,
        override_reason: reason || '',
        clinical_notes: notes || ''
      };

      const self = this;
      fetch(`/api/care/intake/${this.activeIntakeId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => {
        if (res.status === 401) {
          throw new Error('Authentication required. Please sign in as a clinician.');
        }
        if (res.status === 403) {
          throw new Error('Clinician role required. Only verified clinicians can record clinical reviews.');
        }
        if (!res.ok) throw new Error('Review submission failed.');
        return res.json();
      })
      .then(data => {
        alert('Clinician review successfully recorded. Queue updated.');
        document.getElementById('clinician-case-inspector').style.display = 'none';
        self.loadClinicianQueue();
        self.loadDashboardStats();
      })
      .catch(err => alert('Error recording review: ' + err.message));
    },

    searchEvidence: function(query) {
      const container = document.getElementById('clinician-evidence-results');
      if (!container) return;

      clearElement(container);
      const loading = document.createElement('p');
      loading.style.fontSize = '12px';
      loading.style.color = 'var(--text-muted)';
      loading.textContent = 'Searching cataloged guideline passages...';
      container.appendChild(loading);

      fetch('/api/care/evidence/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query })
      })
      .then(res => {
        if (res.status === 401) {
          throw new Error('Authentication required to query clinical evidence protocols.');
        }
        if (!res.ok) throw new Error('Evidence lookup failed.');
        return res.json();
      })
      .then(data => {
        clearElement(container);
        const cites = data.citations || [];
        if (!cites.length) {
          const noResults = document.createElement('p');
          noResults.style.fontSize = '12px';
          noResults.style.color = 'var(--text-muted)';
          noResults.textContent = data.message || 'No direct clinical guidelines found.';
          container.appendChild(noResults);
          return;
        }

        cites.forEach(c => {
          const card = document.createElement('div');
          card.style.borderLeft = '3px solid var(--violet)';
          card.style.paddingLeft = '10px';
          card.style.marginBottom = '12px';

          const title = document.createElement('div');
          title.style.fontWeight = '700';
          title.style.fontSize = '12px';
          title.textContent = `${c.source_title} (${c.publisher})`;
          card.appendChild(title);

          const excerpt = document.createElement('div');
          excerpt.style.fontSize = '12px';
          excerpt.style.color = 'var(--text-2)';
          excerpt.style.margin = '2px 0';
          excerpt.textContent = `"${c.excerpt}"`;
          card.appendChild(excerpt);

          if (c.url && (c.url.startsWith('http://') || c.url.startsWith('https://'))) {
            const link = document.createElement('a');
            link.href = c.url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.style.fontSize = '11px';
            link.style.color = 'var(--violet)';
            link.style.textDecoration = 'underline';
            link.textContent = 'Open Guideline Protocol ↗';
            card.appendChild(link);
          }

          container.appendChild(card);
        });
      })
      .catch(err => {
        clearElement(container);
        const errP = document.createElement('p');
        errP.style.fontSize = '12px';
        errP.style.color = 'var(--danger)';
        errP.textContent = 'Failed to query clinical evidence prototype.';
        container.appendChild(errP);
      });
    },

    loadDashboardStats: function() {
      fetch('/api/care/dashboard/stats')
      .then(res => {
        if (!res.ok) return null;
        return res.json();
      })
      .then(stats => {
        if (!stats) return;
        const totalEl = document.getElementById('stat-total-intakes');
        const sourcesEl = document.getElementById('stat-approved-sources');
        if (totalEl) totalEl.textContent = stats.total_intakes || '0';
        if (sourcesEl) sourcesEl.textContent = stats.clinical_sources_cataloged || '3';
      })
      .catch(e => console.log('Stats fetch optional', e));
    },

    resetDemoFixtures: function(callback) {
      const btn = document.getElementById('btn-care-demo-reset');
      if (btn) btn.textContent = 'Resetting Fixtures...';
      const self = this;

      fetch('/api/care/demo/reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Transify-Demo-Auth': 'transify-demo-authorized-2026'
        }
      })
      .then(res => {
        if (!res.ok) {
          throw new Error(`Demo reset rejected (HTTP ${res.status})`);
        }
        return res.json();
      })
      .then(data => {
        if (btn) btn.textContent = 'Reset 180s Demo Cases';
        self._demoSessionActive = true;
        alert('Transify Care Demonstration Fixtures Initialized:\n• RED: Sign Language Acute Chest Pain (Synthetic Case)\n• YELLOW: Voice STT High Fever / Dengue Warning (Synthetic Case)\n• GREEN: Braille OCR Mild Cough (Synthetic Case)\n\nAll demo cases are synthetic and isolated from real patient data.');
        self.loadClinicianQueue();
        self.loadDashboardStats();
        if (typeof callback === 'function') callback();
      })
      .catch(err => {
        if (btn) btn.textContent = 'Reset 180s Demo Cases';
        alert('Failed to reset demo fixtures: ' + err.message);
      });
    }
  };

  window.TransifyCare = TransifyCare;

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => TransifyCare.init());
  } else {
    TransifyCare.init();
  }

})(window, document);
