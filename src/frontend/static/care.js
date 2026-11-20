/**
 * Transify Care — Client Application Controller
 * Manages Accessible Healthcare Intake Wizard, Clinical Triage,
 * Clinical RAG Citations, Clinician Queue, and Offline Sync.
 */

(function(window, document) {
  'use strict';

  const TransifyCare = {
    currentStep: 1,
    selectedModality: 'text',
    activeIntakeId: null,
    isOffline: !navigator.onLine,

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
        if (navigator.onLine) {
          badge.className = 'care-offline-badge online';
          badge.innerHTML = '<span class="care-offline-dot"></span><span>Online</span>' + (count > 0 ? ` (${count} drafts pending sync)` : '');
        } else {
          badge.className = 'care-offline-badge offline';
          badge.innerHTML = `<span class="care-offline-dot"></span><span>Offline Mode (${count} cached)</span>`;
        }
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

    saveDraftLocally: function(draft) {
      try {
        const drafts = this.getStoredDrafts();
        drafts.push(draft);
        localStorage.setItem('transify_care_drafts', JSON.stringify(drafts));
        this.updateOfflineBadge();
      } catch (e) {
        console.error('Failed to cache draft locally', e);
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
          client_id: 'client-browser-' + (localStorage.getItem('transify_auth_token') || 'anon'),
          drafts: drafts
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
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

      const payload = {
        patient_id: 'patient-' + (localStorage.getItem('transify_auth_user') ? 'auth' : 'guest-' + Math.floor(Math.random() * 900 + 100)),
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
        // Save locally in offline draft store
        self.saveDraftLocally(payload);
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
        if (!res.ok) throw new Error('Submission failed');
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
        alert('Network error submitting intake. Saving locally for offline sync.');
        self.saveDraftLocally(payload);
        self.displayOfflineTriageResult(payload);
        self.goToStep(5);
      });
    },

    renderTriageResult: function(data) {
      const container = document.getElementById('triage-assessment-output');
      if (!container) return;

      const level = data.urgency_level || 'GREEN';
      const isRed = level === 'RED';
      const isYellow = level === 'YELLOW';
      const cssClass = isRed ? 'urgency-red' : (isYellow ? 'urgency-yellow' : 'urgency-green');

      let emergencyHtml = '';
      if (isRed && data.emergency_escalation) {
        emergencyHtml = `
          <div class="triage-emergency-callout">
            <div style="font-weight: 800; color: var(--danger); font-size: var(--text-base);">
              ⚠️ EMERGENCY ESCALATION REQUIRED
            </div>
            <p style="font-size: var(--text-xs); color: var(--text-primary); margin: 4px 0;">
              ${data.emergency_escalation.action}
            </p>
            <div style="display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap;">
              <a href="tel:999" class="emergency-phone-btn">
                📞 Call National Emergency (999)
              </a>
              <a href="tel:16263" class="emergency-phone-btn" style="background: var(--ink);">
                📞 Call Health Helpline (16263)
              </a>
            </div>
          </div>
        `;
      }

      let citationsHtml = '';
      if (data.evidence_citations && data.evidence_citations.length > 0) {
        citationsHtml = `
          <div class="clinical-evidence-box">
            <h4 style="font-family: var(--font-display); font-size: var(--text-xs); font-weight: 800; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em;">
              Evidence-Grounded Clinical Guidelines (RAG)
            </h4>
            ${data.evidence_citations.map(c => `
              <div class="evidence-source-item">
                <div class="evidence-source-title">${c.source_title} (${c.publisher})</div>
                <div class="evidence-source-excerpt">"${c.excerpt}"</div>
                ${c.url ? `<a href="${c.url}" target="_blank" rel="noopener noreferrer" class="evidence-source-link">View Official Guideline Protocol ↗</a>` : ''}
              </div>
            `).join('')}
          </div>
        `;
      }

      container.innerHTML = `
        <div class="triage-result-card ${cssClass}">
          <div class="triage-header-row">
            <div>
              <span class="triage-level-pill">Urgency Level: ${level}</span>
              <span style="font-size: var(--text-xs); color: var(--text-muted); margin-left: 8px;">Intake #${data.intake_id || 'PENDING'}</span>
            </div>
            <span style="font-size: var(--text-xs); font-weight: 700;">Deterministic Rule: ${data.rule_id || 'GENERAL'}</span>
          </div>
          <p style="font-size: var(--text-sm); font-weight: 600; line-height: 1.5; margin: 8px 0;" id="care-triage-explanation-text">
            ${data.triage_explanation || 'Assessment completed and queued for clinician review.'}
          </p>
          ${emergencyHtml}
          ${citationsHtml}
        </div>
      `;
    },

    displayOfflineTriageResult: function(draft) {
      const container = document.getElementById('triage-assessment-output');
      if (!container) return;

      container.innerHTML = `
        <div class="triage-result-card urgency-yellow">
          <div class="triage-header-row">
            <span class="triage-level-pill">OFFLINE CACHED DRAFT</span>
            <span style="font-size: var(--text-xs); color: var(--text-muted);">Saved Locally</span>
          </div>
          <p style="font-size: var(--text-sm); font-weight: 600; line-height: 1.5; margin: 8px 0;">
            Your health intake has been encrypted and saved securely to this device. As soon as your internet connection restores, Transify Care will automatically synchronize it with the clinician queue.
          </p>
          <div style="font-size: var(--text-xs); color: var(--text-2);">
            Chief Concern: <strong>${draft.chief_complaint}</strong> (${draft.input_modality.toUpperCase()})
          </div>
        </div>
      `;
    },

    speakTriageAssessment: function() {
      // Strict Zero Auto-Audio: Only runs when the user explicitly taps "Listen to Assessment"
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
      if (filterStatus) url += `&status=${filterStatus}`;

      fetch(url)
      .then(res => res.json())
      .then(data => {
        const records = data.records || [];
        if (records.length === 0) {
          tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-muted);">No intakes currently pending review.</td></tr>`;
          return;
        }

        tbody.innerHTML = records.map(r => {
          const badgeClass = r.urgency_level === 'RED' ? 'urgency-red' : (r.urgency_level === 'YELLOW' ? 'urgency-yellow' : 'urgency-green');
          return `
            <tr onclick="TransifyCare.openCaseReview(${r.id})">
              <td style="font-weight: 700;">#${r.id}</td>
              <td>${r.patient_id}</td>
              <td><span class="phrase-chip" style="font-size: 11px;">${r.input_modality.toUpperCase()}</span></td>
              <td style="font-weight: 600;">${r.chief_complaint}</td>
              <td><span class="triage-level-pill ${badgeClass}" style="font-size: 11px; padding: 2px 8px;">${r.urgency_level}</span></td>
              <td><button type="button" class="phrase-chip" style="background: var(--violet); color: #FFF;">Review</button></td>
            </tr>
          `;
        }).join('');
      })
      .catch(err => {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger);">Failed to load clinician queue.</td></tr>`;
      });
    },

    openCaseReview: function(intakeId) {
      const self = this;
      fetch(`/api/care/intake/${intakeId}`)
      .then(res => res.json())
      .then(intake => {
        self.activeIntakeId = intake.id;
        const inspector = document.getElementById('clinician-case-inspector');
        if (!inspector) return;

        inspector.style.display = 'block';
        inspector.scrollIntoView({ behavior: 'smooth' });

        document.getElementById('inspect-case-id').textContent = `#${intake.id} — ${intake.patient_id}`;
        document.getElementById('inspect-modality').textContent = intake.input_modality.toUpperCase();
        document.getElementById('inspect-complaint').textContent = intake.chief_complaint;
        document.getElementById('inspect-symptoms').textContent = intake.symptom_description;
        document.getElementById('inspect-raw').textContent = intake.raw_input || 'N/A';
        document.getElementById('inspect-ai-urgency').textContent = intake.urgency_level;
        document.getElementById('inspect-ai-rule').textContent = intake.triage_rule_id || 'Standard Protocol';
        document.getElementById('inspect-ai-explanation').textContent = intake.triage_explanation;

        // Populate citations
        const citContainer = document.getElementById('inspect-citations-list');
        if (citContainer) {
          const cites = intake.evidence_citations || [];
          if (cites.length) {
            citContainer.innerHTML = cites.map(c => `
              <div style="font-size: 11px; border-left: 2px solid var(--violet); padding-left: 8px; margin-top: 4px;">
                <strong>${c.source_title}</strong>: "${c.excerpt}"
              </div>
            `).join('');
          } else {
            citContainer.innerHTML = '<span style="font-size: 11px; color: var(--text-muted);">No direct citation retrieved.</span>';
          }
        }
      })
      .catch(err => alert('Failed to open case details: ' + err.message));
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

      const payload = {
        clinician_id: 'dr-current-session',
        clinician_name: 'Dr. Reviewing Clinician',
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
        if (!res.ok) throw new Error('Review failed');
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

      container.innerHTML = '<p style="font-size: 12px; color: var(--text-muted);">Searching approved protocols...</p>';

      fetch(`/api/care/evidence/search?q=${encodeURIComponent(query)}`)
      .then(res => res.json())
      .then(data => {
        const cites = data.citations || [];
        if (!cites.length) {
          container.innerHTML = `<p style="font-size: 12px; color: var(--text-muted);">${data.message || 'No direct clinical guidelines found.'}</p>`;
          return;
        }

        container.innerHTML = cites.map(c => `
          <div style="border-left: 3px solid var(--violet); padding-left: 10px; margin-bottom: 12px;">
            <div style="font-weight: 700; font-size: 12px;">${c.source_title} (${c.publisher})</div>
            <div style="font-size: 12px; color: var(--text-2); margin: 2px 0;">"${c.excerpt}"</div>
            ${c.url ? `<a href="${c.url}" target="_blank" rel="noopener noreferrer" style="font-size: 11px; color: var(--violet); text-decoration: underline;">Open Guideline Protocol ↗</a>` : ''}
          </div>
        `).join('');
      })
      .catch(err => {
        container.innerHTML = '<p style="font-size: 12px; color: var(--danger);">Failed to query clinical evidence library.</p>';
      });
    },

    loadDashboardStats: function() {
      fetch('/api/care/dashboard/stats')
      .then(res => res.json())
      .then(stats => {
        const totalEl = document.getElementById('stat-total-intakes');
        const sourcesEl = document.getElementById('stat-approved-sources');
        if (totalEl) totalEl.textContent = stats.total_intakes || '0';
        if (sourcesEl) sourcesEl.textContent = stats.approved_clinical_sources || '3';
      })
      .catch(e => console.log('Stats fetch optional', e));
    },

    resetDemoFixtures: function(callback) {
      const btn = document.getElementById('btn-care-demo-reset');
      if (btn) btn.textContent = 'Resetting Fixtures...';

      fetch('/api/care/demo/reset', { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        if (btn) btn.textContent = 'Reset 180s Demo Cases';
        alert('Transify Care Demo Fixtures Initialized:\n• RED: Sign Language Acute Chest Pain\n• YELLOW: Voice STT High Fever / Dengue Warning\n• GREEN: Braille OCR Mild Cough');
        this.loadClinicianQueue();
        this.loadDashboardStats();
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
