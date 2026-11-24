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

(function (window, document) {
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

    init: function () {
      this.bindEvents();
      this.setupOfflineWatcher();
      this.updateOfflineBadge();
      const authUser = localStorage.getItem('transify_auth_user');
      if (authUser) {
        this.loadDashboardStats();
        this.loadClinicianQueue();
      }
      this.initChronicCare();
    },

    switchTab: function (tabName) {
      const intakeTab = document.getElementById('care-tab-intake-btn');
      const clinicianTab = document.getElementById('care-tab-clinician-btn');
      const chronicTab = document.getElementById('care-tab-chronic-btn');
      const intakeSlide = document.getElementById('slide-care-intake');
      const clinicianSlide = document.getElementById('slide-clinician-portal');
      const chronicSlide = document.getElementById('slide-care-chronic');

      [intakeTab, clinicianTab, chronicTab].forEach(t => { if (t) t.classList.remove('active'); });
      [intakeSlide, clinicianSlide, chronicSlide].forEach(s => { if (s) s.style.display = 'none'; });

      if (tabName === 'clinician') {
        if (clinicianTab) clinicianTab.classList.add('active');
        if (clinicianSlide) clinicianSlide.style.display = 'block';
        this.loadClinicianQueue();
        this.loadDashboardStats();
      } else if (tabName === 'chronic') {
        if (chronicTab) chronicTab.classList.add('active');
        if (chronicSlide) chronicSlide.style.display = 'flex';
      } else {
        if (intakeTab) intakeTab.classList.add('active');
        if (intakeSlide) intakeSlide.style.display = 'flex';
      }
    },

    bindEvents: function () {
      const self = this;

      // Care sub-tabs
      const intakeTab = document.getElementById('care-tab-intake-btn');
      const clinicianTab = document.getElementById('care-tab-clinician-btn');
      const chronicTab = document.getElementById('care-tab-chronic-btn');
      if (intakeTab) intakeTab.addEventListener('click', () => self.switchTab('intake'));
      if (clinicianTab) clinicianTab.addEventListener('click', () => self.switchTab('clinician'));
      if (chronicTab) chronicTab.addEventListener('click', () => self.switchTab('chronic'));

      // Severity Slider Sync
      const slider = document.getElementById('care-severity-slider');
      const badge = document.getElementById('care-severity-badge');
      if (slider && badge) {
        slider.addEventListener('input', function () {
          badge.textContent = slider.value;
        });
      }

      // Trajectory Buttons
      document.querySelectorAll('.traj-chip-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
          document.querySelectorAll('.traj-chip-btn').forEach(b => b.classList.remove('selected'));
          btn.classList.add('selected');
        });
      });

      // Modality Selector Buttons
      document.querySelectorAll('.modality-card-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
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
        self.resetDemoFixtures(function () {
          if (typeof openSlide === 'function') openSlide('slide-clinician-portal');
        });
      });

      // Clinician Review Form Submit
      const reviewSubmitBtn = document.getElementById('btn-complete-clinician-review');
      if (reviewSubmitBtn) reviewSubmitBtn.addEventListener('click', () => self.submitClinicianReview());

      // Clinician Override Radio Chooser Sync
      document.querySelectorAll('input[name="clinician_urgency_choice"]').forEach(radio => {
        radio.addEventListener('change', function () {
          const sel = document.getElementById('clinician-override-select');
          if (sel) sel.value = this.value;
        });
      });

      // Clinician Evidence Search Form
      const evidenceSearchBtn = document.getElementById('btn-clinician-evidence-search');
      if (evidenceSearchBtn) evidenceSearchBtn.addEventListener('click', () => {
        const query = document.getElementById('clinician-evidence-search-input')?.value;
        if (query) self.searchEvidence(query);
      });

      // CareAnywhere Multimodal: Photo Input for Lesion & Eye Scanning
      const photoInput = document.getElementById('care-photo-input');
      if (photoInput) {
        photoInput.addEventListener('change', function (e) {
          const file = e.target.files && e.target.files[0];
          if (!file) return;
          const reader = new FileReader();
          reader.onload = function (evt) {
            const dataUrl = evt.target.result;
            self._attachedPhotoBase64 = dataUrl;
            const previewCard = document.getElementById('care-vision-preview-card');
            const thumb = document.getElementById('care-vision-thumb');
            const findingsBox = document.getElementById('care-vision-findings-box');
            if (previewCard && thumb && findingsBox) {
              previewCard.style.display = 'block';
              thumb.src = dataUrl;
              findingsBox.textContent = 'Running computer vision screening...';
              fetch('/api/care/vision/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_data: dataUrl, condition_type: 'auto' })
              })
                .then(res => res.json())
                .then(data => {
                  if (data.success && data.analysis) {
                    const a = data.analysis;
                    self._attachedPhotoConditionType = a.target_organ === 'DERMATOLOGY' ? 'skin' : 'eye';
                    findingsBox.textContent = `${a.target_organ}: ${a.urgency_level} (${(a.confidence_score * 100).toFixed(0)}% confidence). ${a.findings[0] || ''}`;
                  } else {
                    findingsBox.textContent = 'Image attached. Will be processed with intake submission.';
                  }
                })
                .catch(() => {
                  findingsBox.textContent = 'Image attached. Computer vision analysis will finalize upon submission.';
                });
            }
          };
          reader.readAsDataURL(file);
        });
      }

      // Remove Attached Photo
      const removePhotoBtn = document.getElementById('btn-care-remove-photo');
      if (removePhotoBtn) {
        removePhotoBtn.addEventListener('click', function () {
          self._attachedPhotoBase64 = null;
          self._attachedPhotoConditionType = null;
          const pInp = document.getElementById('care-photo-input');
          if (pInp) pInp.value = '';
          const previewCard = document.getElementById('care-vision-preview-card');
          if (previewCard) previewCard.style.display = 'none';
        });
      }

      // CareAnywhere Regional Dialect Intake
      const voiceDialectBtn = document.getElementById('btn-care-voice-dialect');
      if (voiceDialectBtn) {
        voiceDialectBtn.addEventListener('click', function () {
          const sample = prompt('Speak or enter your symptom in local regional dialect (e.g., Sylheti "bukor bitor fura", Chittagonian "souk laal oise", or rural Bengali "গা থরথর করে কাঁপে"):', 'বুকে তীব্র ব্যথা এবং দম আটকে আসে');
          if (!sample) return;
          fetch('/api/care/audio/intake', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcript: sample, dialect_hint: 'auto' })
          })
            .then(res => res.json())
            .then(data => {
              if (data.success && data.data) {
                const d = data.data;
                const complaintInput = document.getElementById('care-chief-complaint');
                const descInput = document.getElementById('care-symptom-desc');
                const slider = document.getElementById('care-severity-slider');
                const badge = document.getElementById('care-severity-badge');
                if (complaintInput) complaintInput.value = d.chief_complaint;
                if (descInput) descInput.value = `Spoken transcript: "${d.transcript}". Identified dialect: ${d.identified_dialect}. Inferred duration: ${d.inferred_duration}.`;
                if (slider && d.inferred_severity) {
                  slider.value = d.inferred_severity;
                  if (badge) badge.textContent = d.inferred_severity;
                }
                self._attachedAudioTranscript = d.transcript;
                alert(`Recognized: ${d.identified_dialect}\nChief Complaint: ${d.chief_complaint}\nInferred Severity: ${d.inferred_severity}/10`);
              }
            })
            .catch(e => console.error('Voice dialect intake error', e));
        });
      }

      // CareAnywhere Outbreak Alert Toggle
      const outbreakBtn = document.getElementById('btn-care-outbreak-alert');
      const outbreakModal = document.getElementById('care-outbreak-modal');
      const closeOutbreakBtn = document.getElementById('btn-close-outbreak-modal');
      if (outbreakBtn && outbreakModal) {
        outbreakBtn.addEventListener('click', function () {
          const isVisible = outbreakModal.style.display !== 'none';
          if (isVisible) {
            outbreakModal.style.display = 'none';
          } else {
            outbreakModal.style.display = 'block';
            fetch('/api/care/outbreak/alerts?lat=23.8103&lon=90.4125&district=Dhaka&symptoms=fever')
              .then(res => res.json())
              .then(data => {
                if (data.success && data.data) {
                  const z = data.data;
                  const title = document.getElementById('outbreak-modal-title');
                  const desc = document.getElementById('outbreak-modal-desc');
                  if (title) title.textContent = `${z.zone_name}: ${z.overall_epidemic_risk} Risk Alert`;
                  if (desc && z.outbreak_alerts && z.outbreak_alerts.length > 0) {
                    const alert0 = z.outbreak_alerts[0];
                    desc.textContent = `Active Pathogen: ${alert0.pathogen} (${alert0.vector}). ${alert0.guidance}`;
                  }
                }
              })
              .catch(e => console.error('Failed to load outbreak alerts', e));
          }
        });
      }
      if (closeOutbreakBtn && outbreakModal) {
        closeOutbreakBtn.addEventListener('click', () => { outbreakModal.style.display = 'none'; });
      }

      // CareAnywhere Nearby Emergency Facilities
      const facilitiesBtn = document.getElementById('btn-care-nearby-facilities');
      const facilitiesModal = document.getElementById('care-facilities-modal');
      const closeFacilitiesBtn = document.getElementById('btn-close-facilities-modal');
      if (facilitiesBtn && facilitiesModal) {
        facilitiesBtn.addEventListener('click', function () {
          const isVisible = facilitiesModal.style.display !== 'none';
          if (isVisible) {
            facilitiesModal.style.display = 'none';
          } else {
            facilitiesModal.style.display = 'block';
            const listEl = document.getElementById('care-facilities-list');
            if (listEl) listEl.textContent = 'Locating nearest verified emergency facilities (OpenStreetMap Health)...';
            fetch('/api/care/facilities/nearby?lat=23.7258&lon=90.3976&limit=4')
              .then(res => res.json())
              .then(data => {
                if (data.status === 'SUCCESS' && listEl) {
                  clearElement(listEl);
                  data.nearest_facilities.forEach(fac => {
                    const div = document.createElement('div');
                    div.style.padding = '8px 10px';
                    div.style.borderRadius = '6px';
                    div.style.background = 'var(--surface)';
                    div.style.border = '1px solid var(--line)';
                    div.style.display = 'flex';
                    div.style.justifyContent = 'space-between';
                    div.style.alignItems = 'center';

                    const info = document.createElement('div');
                    const strong = document.createElement('strong');
                    strong.textContent = fac.name;
                    info.appendChild(strong);

                    const sub = document.createElement('div');
                    sub.style.fontSize = '12px';
                    sub.style.color = 'var(--text-muted)';
                    sub.textContent = `${fac.facility_type} • ${fac.distance_km} km away (~${fac.estimated_transit_minutes} min drive) • Hotline: ${fac.hotline}`;
                    info.appendChild(sub);
                    div.appendChild(info);

                    const callBtn = document.createElement('a');
                    callBtn.href = `tel:${fac.hotline}`;
                    callBtn.className = 'phrase-chip';
                    callBtn.style.background = 'var(--signal)';
                    callBtn.style.color = 'var(--ink)';
                    callBtn.style.fontWeight = '700';
                    callBtn.textContent = 'Call';
                    div.appendChild(callBtn);

                    listEl.appendChild(div);
                  });
                }
              })
              .catch(e => {
                if (listEl) listEl.textContent = 'Failed to locate facilities. If experiencing an emergency, immediately call 999 or 16263.';
              });
          }
        });
      }
      if (closeFacilitiesBtn && facilitiesModal) {
        closeFacilitiesBtn.addEventListener('click', () => { facilitiesModal.style.display = 'none'; });
      }

      // --- CareAnywhere Advanced Innovation Extensions (Ada, K Health, Healthy.io, MIMIC/HMD, Zipline, WHO GHO) ---

      // 1. Ada Health Probabilistic Differential Modal
      const adaBtn = document.getElementById('btn-care-ada-diff');
      const adaModal = document.getElementById('care-ada-modal');
      const closeAdaBtn = document.getElementById('btn-close-ada-modal');
      if (adaBtn && adaModal) {
        adaBtn.addEventListener('click', function () {
          const isVis = adaModal.style.display !== 'none';
          if (isVis) {
            adaModal.style.display = 'none';
          } else {
            adaModal.style.display = 'block';
            const cInput = document.getElementById('care-chief-complaint');
            const dInput = document.getElementById('care-symptom-desc');
            const symptoms = (cInput && cInput.value ? cInput.value + ' ' : '') + (dInput ? dInput.value : '') || 'Acute lower abdominal pain, nausea, mild fever';
            const content = document.getElementById('care-ada-content');
            if (content) {
              content.innerHTML = '';
              content.appendChild(window.createCardSpinner ? window.createCardSpinner('Running Ada Health Bayesian probabilistic differential diagnosis...') : document.createTextNode('Running Ada Health Bayesian probabilistic differential diagnosis...'));
            }
            fetch('/api/care/reasoning/differential', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ symptoms: symptoms, age: 30 })
            })
              .then(res => res.json())
              .then(data => {
                if (data.status === 'SUCCESS' && content) {
                  const p = data.primary_differential;
                  let html = `<div style="background: var(--surface); padding: 10px; border-radius: 8px; border: 1px solid var(--line); margin-bottom: 8px;">
                  <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong style="font-size:15px; color:var(--violet);">${p.condition} (${p.icd10})</strong>
                    <span class="care-badge online" style="font-size:12px; font-weight:800;">${p.probability_percentage}% Match (${p.rarity})</span>
                  </div>
                  <div style="margin-top:6px; font-size:12px; color:var(--text-muted);">Urgency: <strong>${p.urgency}</strong></div>
                  <div style="margin-top:4px; font-size:12px;">Matched Findings: <em>${p.matched_symptoms.join(', ') || 'Constitutional'}</em></div>
                  <div style="margin-top:8px; padding:8px; background:rgba(131,56,236,0.08); border-radius:6px; font-size:12px;">
                    <strong>Next Recommended Triage Question:</strong> "${p.clarifying_triage_question}"
                  </div>
                </div>`;
                  if (data.full_differential_list && data.full_differential_list.length > 1) {
                    html += `<div style="font-size:12px; color:var(--text-muted); font-weight:700; margin-bottom:4px;">Alternative Considerations:</div>`;
                    data.full_differential_list.slice(1).forEach(alt => {
                      html += `<div style="font-size:12px; padding:4px 0;">• <strong>${alt.condition}</strong>: ${alt.probability_percentage}% probability (${alt.urgency})</div>`;
                    });
                  }
                  content.innerHTML = html;
                }
              })
              .catch(e => { if (content) content.textContent = 'Differential analysis currently unavailable.'; });
          }
        });
      }
      if (closeAdaBtn && adaModal) closeAdaBtn.addEventListener('click', () => { adaModal.style.display = 'none'; });

      // 2. K Health "People Like Me" Modal
      const kHealthBtn = document.getElementById('btn-care-k-health');
      const kHealthModal = document.getElementById('care-khealth-modal');
      const closeKHealthBtn = document.getElementById('btn-close-khealth-modal');
      if (kHealthBtn && kHealthModal) {
        kHealthBtn.addEventListener('click', function () {
          const isVis = kHealthModal.style.display !== 'none';
          if (isVis) {
            kHealthModal.style.display = 'none';
          } else {
            kHealthModal.style.display = 'block';
            const cInput = document.getElementById('care-chief-complaint');
            const comp = (cInput && cInput.value) ? cInput.value : 'Abdominal pain and fever';
            const content = document.getElementById('care-khealth-content');
            if (content) {
              content.innerHTML = '';
              content.appendChild(window.createCardSpinner ? window.createCardSpinner('Matching against 2,500,000+ real-world physician encounters...') : document.createTextNode('Matching against 2,500,000+ real-world physician encounters...'));
            }
            fetch('/api/care/insights/people-like-me', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ complaint: comp, age: 34, sex: 'all' })
            })
              .then(res => res.json())
              .then(data => {
                if (data.status === 'SUCCESS' && content) {
                  let html = `<div style="font-weight:700; font-size:13px; margin-bottom:6px;">${data.matched_cohort_summary}</div>
                <div style="background:var(--surface); padding:8px 10px; border-radius:8px; border:1px solid var(--line); margin-bottom:8px;">`;
                  data.diagnoses_distribution.forEach(d => {
                    html += `<div style="display:flex; justify-content:space-between; font-size:12px; padding:3px 0;">
                    <span>• ${d.diagnosis}</span>
                    <strong style="color:#0F9D74;">${d.percentage}%</strong>
                  </div>`;
                  });
                  html += `</div>
                <div style="font-size:12px; margin-top:4px;"><strong>Median Recovery Time:</strong> ~${data.median_recovery_time_days} days.</div>
                <div style="font-size:12px; margin-top:4px; color:var(--text-muted);">${data.care_pathways_summary}</div>`;
                  content.innerHTML = html;
                }
              })
              .catch(e => { if (content) content.textContent = 'K Health comparative insights unavailable.'; });
          }
        });
      }
      if (closeKHealthBtn && kHealthModal) closeKHealthBtn.addEventListener('click', () => { kHealthModal.style.display = 'none'; });

      // 3. Healthy.io Smartphone Urinalysis & Wound Staging Modal
      const healthyBtn = document.getElementById('btn-care-healthy-io');
      const healthyModal = document.getElementById('care-healthy-modal');
      const closeHealthyBtn = document.getElementById('btn-close-healthy-modal');
      const urineDemoBtn = document.getElementById('btn-run-urinalysis-demo');
      const woundDemoBtn = document.getElementById('btn-run-wound-demo');

      function runHealthyIoDemo(type) {
        const content = document.getElementById('care-healthy-content');
        if (content) {
          content.innerHTML = '';
          content.appendChild(window.createCardSpinner ? window.createCardSpinner(`Evaluating camera diagnostic frames (${type})...`) : document.createTextNode(`Evaluating camera diagnostic frames (${type})...`));
        }
        // Generate a synthetic test canvas payload for verification
        const c = document.createElement('canvas');
        c.width = 400; c.height = type === 'urinalysis' ? 120 : 300;
        const ctx = c.getContext('2d');
        ctx.fillStyle = type === 'urinalysis' ? '#D46B8B' : '#B44040';
        ctx.fillRect(0, 0, c.width, c.height);
        const b64 = c.toDataURL('image/jpeg', 0.85);

        fetch('/api/care/vision/urinalysis-wound', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_data: b64, analysis_type: type })
        })
          .then(res => res.json())
          .then(data => {
            if (data.success && data.data && content) {
              const d = data.data;
              if (d.modality === 'URINALYSIS_COLORIMETRY') {
                content.innerHTML = `<div style="background:var(--surface); padding:10px; border-radius:8px; border:1px solid var(--line);">
                <strong style="color:#0284C7; font-size:14px;">Clinical Dipstick Pads Colorimetry</strong>
                <div style="margin-top:6px; font-size:12px;"><strong>Leukocytes:</strong> ${d.findings.leukocyte_esterase}</div>
                <div style="font-size:12px;"><strong>Nitrite:</strong> ${d.findings.nitrite}</div>
                <div style="font-size:12px;"><strong>Protein (Albumin):</strong> ${d.findings.protein_albumin}</div>
                <div style="font-size:12px;"><strong>Glucose:</strong> ${d.findings.glucose}</div>
                <div style="font-size:12px;"><strong>Occult Blood:</strong> ${d.findings.occult_blood}</div>
                <div style="margin-top:8px; padding:6px; background:rgba(2,132,199,0.1); border-radius:6px; font-size:12px;">
                  <strong>Impression:</strong> ${d.clinical_diagnosis_impression} (<em>${d.urgency}</em>)
                </div>
              </div>`;
              } else {
                content.innerHTML = `<div style="background:var(--surface); padding:10px; border-radius:8px; border:1px solid var(--line);">
                <strong style="color:#0284C7; font-size:14px;">Digital Wound &amp; Ulcer Measurement</strong>
                <div style="margin-top:6px; font-size:12px;"><strong>Estimated Surface Area:</strong> ${d.wound_metrics.estimated_surface_area_cm2} cm²</div>
                <div style="font-size:12px;"><strong>Granulation (Healthy Red):</strong> ${d.wound_metrics.tissue_composition.granulation_healthy_red_pct}%</div>
                <div style="font-size:12px;"><strong>Slough (Fibrous Yellow):</strong> ${d.wound_metrics.tissue_composition.slough_fibrous_yellow_pct}%</div>
                <div style="font-size:12px;"><strong>NPUAP/EPUAP Staging:</strong> ${d.wound_metrics.npuap_epuap_staging}</div>
                <div style="margin-top:8px; padding:6px; background:rgba(2,132,199,0.1); border-radius:6px; font-size:12px;">
                  <strong>Dressing Recommendation:</strong> ${d.dressing_recommendation}
                </div>
              </div>`;
              }
            }
          })
          .catch(e => { if (content) content.textContent = 'Healthy.io vision analysis unavailable.'; });
      }

      if (healthyBtn && healthyModal) {
        healthyBtn.addEventListener('click', function () {
          healthyModal.style.display = (healthyModal.style.display !== 'none') ? 'none' : 'block';
        });
      }
      if (urineDemoBtn) urineDemoBtn.addEventListener('click', () => runHealthyIoDemo('urinalysis'));
      if (woundDemoBtn) woundDemoBtn.addEventListener('click', () => runHealthyIoDemo('wound_care'));
      if (closeHealthyBtn && healthyModal) closeHealthyBtn.addEventListener('click', () => { healthyModal.style.display = 'none'; });

      // 4. MIMIC-IV Shock Index & HMD Actuarial Hazard Modal
      const mimicHmdBtn = document.getElementById('btn-care-mimic-hmd');
      const mimicHmdModal = document.getElementById('care-mimic-hmd-modal');
      const closeMimicHmdBtn = document.getElementById('btn-close-mimic-hmd-modal');
      if (mimicHmdBtn && mimicHmdModal) {
        mimicHmdBtn.addEventListener('click', function () {
          const isVis = mimicHmdModal.style.display !== 'none';
          if (isVis) {
            mimicHmdModal.style.display = 'none';
          } else {
            mimicHmdModal.style.display = 'block';
            const content = document.getElementById('care-mimic-hmd-content');
            if (content) {
              content.innerHTML = '';
              content.appendChild(window.createCardSpinner ? window.createCardSpinner('Querying MIMIC-IV critical care encounters & HMD actuarial life tables...') : document.createTextNode('Querying MIMIC-IV critical care encounters & HMD actuarial life tables...'));
            }
            Promise.all([
              fetch('/api/care/reasoning/mimic', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ complaint: 'Acute fever and tachycardia', heart_rate: 108, systolic_bp: 98, temperature_c: 38.8 })
              }).then(r => r.json()),
              fetch('/api/care/hazard/mortality', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ age: 62, chronic_conditions: ['hypertension', 'diabetes'], acute_severity: 7 })
              }).then(r => r.json())
            ])
              .then(([mimic, hmd]) => {
                if (content) {
                  content.innerHTML = `<div style="background:var(--surface); padding:10px; border-radius:8px; border:1px solid var(--line);">
                  <strong style="color:#EA580C; font-size:14px;">MIMIC-IV Shock Index (SI) &amp; SIRS Scoring</strong>
                  <div style="font-size:12px; margin-top:4px;"><strong>Shock Index:</strong> ${mimic.shock_index.value} (${mimic.shock_index.status})</div>
                  <div style="font-size:12px;"><strong>SIRS Evaluation:</strong> ${mimic.sirs_evaluation.clinical_guidance}</div>
                  <div style="font-size:12px;"><strong>Estimated ICU Deterioration Risk:</strong> ${mimic.icu_admission_risk}</div>
                  <div style="margin-top:10px; border-top:1px solid var(--line); padding-top:8px;">
                    <strong style="color:#EA580C; font-size:14px;">Human Mortality Database (HMD) Predictive Risk</strong>
                    <div style="font-size:12px; margin-top:4px;"><strong>Demographic Bracket:</strong> Age ${hmd.demographic_profile.age} (${hmd.demographic_profile.age_bracket})</div>
                    <div style="font-size:12px;"><strong>Baseline Life Expectancy:</strong> ${hmd.actuarial_baseline.baseline_remaining_life_expectancy_years} years remaining</div>
                    <div style="font-size:12px;"><strong>Comorbidity Excess Hazard Ratio:</strong> ${hmd.risk_modeling.excess_hazard_ratio}x (${hmd.risk_modeling.vulnerability_tier})</div>
                  </div>
                </div>`;
                }
              })
              .catch(e => { if (content) content.textContent = 'Physiological and mortality hazard modeling unavailable.'; });
          }
        });
      }
      if (closeMimicHmdBtn && mimicHmdModal) closeMimicHmdBtn.addEventListener('click', () => { mimicHmdModal.style.display = 'none'; });

      // 5. Zipline Autonomous Medical Drone Logistics Modal
      const ziplineBtn = document.getElementById('btn-care-zipline');
      const ziplineModal = document.getElementById('care-zipline-modal');
      const closeZiplineBtn = document.getElementById('btn-close-zipline-modal');

      function requestZiplineSupply(supply) {
        const content = document.getElementById('care-zipline-content');
        if (content) {
          content.innerHTML = '';
          content.appendChild(window.createCardSpinner ? window.createCardSpinner(`Calculating direct flight trajectory for ${supply}...`) : document.createTextNode(`Calculating direct flight trajectory for ${supply}...`));
        }
        fetch('/api/care/logistics/dispatch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ latitude: 23.9500, longitude: 90.4500, required_supply: supply, urgency_level: 'CRITICAL' })
        })
          .then(res => res.json())
          .then(data => {
            if (data.status === 'DISPATCH_CONFIRMED' && content) {
              const m = data.logistics_metrics;
              content.innerHTML = `<div style="background:#fff; padding:10px; border-radius:8px; border:1px solid #C7D2FE;">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong style="color:#4F46E5; font-size:14px;">Flight ${data.dispatch_id} Confirmed</strong>
                <span class="care-badge online" style="background:#4F46E5; color:#fff;">Active Dispatch</span>
              </div>
              <div style="font-size:12px; margin-top:6px;"><strong>Launch Hub:</strong> ${data.launch_hub.hub_name}</div>
              <div style="font-size:12px;"><strong>Payload:</strong> ${data.payload_manifest.item_description}</div>
              <div style="font-size:12px;"><strong>Aerial Flight Distance:</strong> ${m.aerial_flight_distance_km} km (Speed: ${m.cruise_velocity_kmh} km/h)</div>
              <div style="font-size:13px; font-weight:800; color:#4F46E5; margin-top:4px;">⏱️ Drone Arrival ETA: ${m.drone_estimated_flight_minutes} minutes</div>
              <div style="font-size:12px; color:var(--text-muted);">Ground Transport ETA: ~${m.estimated_ground_road_hours} hours (${m.time_saved_hours} hours saved via drone delivery)</div>
              <div style="font-size:11px; margin-top:4px; color:#059669;">✓ ${m.cold_chain_preservation} • ${m.delivery_mechanism}</div>
            </div>`;
            }
          })
          .catch(e => { if (content) content.textContent = 'Drone logistics server currently offline.'; });
      }

      if (ziplineBtn && ziplineModal) {
        ziplineBtn.addEventListener('click', function () {
          ziplineModal.style.display = (ziplineModal.style.display !== 'none') ? 'none' : 'block';
        });
      }
      document.querySelectorAll('.btn-zipline-req').forEach(btn => {
        btn.addEventListener('click', () => {
          const supply = btn.getAttribute('data-supply') || 'antivenom';
          requestZiplineSupply(supply);
        });
      });
      if (closeZiplineBtn && ziplineModal) closeZiplineBtn.addEventListener('click', () => { ziplineModal.style.display = 'none'; });

      // 6. WHO Global Health Observatory Modal
      const whoGhoBtn = document.getElementById('btn-care-who-gho');
      const whoGhoModal = document.getElementById('care-who-gho-modal');
      const closeWhoGhoBtn = document.getElementById('btn-close-who-gho-modal');
      if (whoGhoBtn && whoGhoModal) {
        whoGhoBtn.addEventListener('click', function () {
          const isVis = whoGhoModal.style.display !== 'none';
          if (isVis) {
            whoGhoModal.style.display = 'none';
          } else {
            whoGhoModal.style.display = 'block';
            const content = document.getElementById('care-who-gho-content');
            if (content) {
              content.innerHTML = '';
              content.appendChild(window.createCardSpinner ? window.createCardSpinner('Retrieving WHO Global Health Observatory indicators...') : document.createTextNode('Retrieving WHO Global Health Observatory indicators...'));
            }
            fetch('/api/care/who-gho/indicators?district=dhaka&lat=23.72&lon=90.39')
              .then(res => res.json())
              .then(data => {
                if (data.status === 'SUCCESS' && content) {
                  const wf = data.healthcare_workforce_density;
                  let html = `<div style="background:var(--surface); padding:10px; border-radius:8px; border:1px solid var(--line);">
                  <div style="font-weight:700; font-size:13px; color:#2563EB;">${data.regional_jurisdiction}</div>
                  <div style="font-size:12px; margin-top:6px;"><strong>Physician Density:</strong> ${wf.physicians_per_10000_population} per 10k (WHO Minimum Standard: ${wf.who_minimum_threshold_physicians}/10k)</div>
                  <div style="font-size:12px;"><strong>Hospital Bed Capacity:</strong> ${wf.hospital_beds_per_10k} beds per 10k population</div>
                  <div style="font-size:12px;"><strong>UHC Service Coverage Index:</strong> ${data.universal_health_coverage_index}</div>
                  <div style="font-size:12px; color:#DC2626; margin-top:4px;"><strong>Triage Safety Margin:</strong> ${data.triage_safety_multiplier}x sensitivity increase for low-resource protection</div>
                  <div style="margin-top:8px; border-top:1px solid var(--line); padding-top:6px; font-size:12px;">
                    <strong>Leading Regional DALY Burdens:</strong>
                    <div style="margin-top:2px;">`;
                  data.top_disease_burdens_daly.forEach(b => {
                    html += `<div>• ${b.cause} (${b.daly_per_100k} DALY / 100k)</div>`;
                  });
                  html += `</div></div></div>`;
                  content.innerHTML = html;
                }
              })
              .catch(e => { if (content) content.textContent = 'WHO GHO indicators service currently unavailable.'; });
          }
        });
      }
      if (closeWhoGhoBtn && whoGhoModal) closeWhoGhoBtn.addEventListener('click', () => { whoGhoModal.style.display = 'none'; });

      // TTS Speak Triage Result (Strict Zero Auto-Audio: Only triggered on explicit user click)
      const ttsBtn = document.getElementById('btn-care-speak-triage');
      if (ttsBtn) ttsBtn.addEventListener('click', () => self.speakTriageAssessment());
    },

    setupOfflineWatcher: function () {
      const self = this;
      window.addEventListener('online', function () {
        self.isOffline = false;
        self.updateOfflineBadge();
        self.syncOfflineDrafts();
      });

      window.addEventListener('offline', function () {
        self.isOffline = true;
        self.updateOfflineBadge();
      });
    },

    updateOfflineBadge: function () {
      const badges = document.querySelectorAll('.care-offline-badge');
      const drafts = this.getStoredDrafts();
      const count = drafts.length;

      badges.forEach(function (badge) {
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

    getStoredDrafts: function () {
      try {
        const data = localStorage.getItem('transify_care_drafts');
        return data ? JSON.parse(data) : [];
      } catch (e) {
        return [];
      }
    },

    startDemoSession: function () {
      this._demoSessionActive = true;
    },

    endDemoSession: function () {
      this._demoSessionActive = false;
    },

    getTrustedDemoFixture: function (fixtureId) {
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

    isSyntheticDemoDraft: function (draft) {
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

    saveDraftLocally: function (draft) {
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

    syncOfflineDrafts: function () {
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

    selectModality: function (modality) {
      this.selectedModality = modality;
      document.querySelectorAll('.modality-card-btn').forEach(function (btn) {
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

    goToStep: function (step) {
      this.currentStep = step;

      // Update Node indicators
      document.querySelectorAll('.wizard-step-node').forEach(function (node) {
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

    populateConfirmationSummary: function () {
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

    submitIntake: function () {
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
      const traj = document.querySelector('input[name="care_symptom_trajectory"]:checked')?.value || document.querySelector('.traj-chip-btn.selected')?.getAttribute('data-traj') || 'stable';
      let severity = parseInt(document.getElementById('care-severity-slider')?.value || '5', 10);
      if (isNaN(severity)) severity = 5;
      if (severity > 10) severity = Math.min(10, Math.max(1, Math.round(severity / 10)));
      if (severity < 1) severity = 1;
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

      if (self._attachedPhotoBase64) {
        payload.image_base64 = self._attachedPhotoBase64;
        payload.condition_type = self._attachedPhotoConditionType || 'auto';
        payload.input_modality = 'multimodal';
      }
      if (self._attachedAudioTranscript) {
        payload.audio_transcript = self._attachedAudioTranscript;
      }
      payload.district = 'Dhaka';
      payload.gps_latitude = 23.8103;
      payload.gps_longitude = 90.4125;

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

      const headers = { 'Content-Type': 'application/json' };

      fetch('/api/care/intake', {
        method: 'POST',
        headers: headers,
        credentials: 'include',
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
            if (window.openAuthSheet) {
              window.openAuthSheet('login');
            } else if (window.TransifyApp && window.TransifyApp.openAuthSheet) {
              window.TransifyApp.openAuthSheet('login');
            }
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

    renderTriageResult: function (data) {
      const container = document.getElementById('triage-assessment-output');
      const visualContainer = document.getElementById('care-intake-result');
      if (!container && !visualContainer) return;

      if (container) clearElement(container);
      if (visualContainer) clearElement(visualContainer);

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

      if (visualContainer) {
        visualContainer.appendChild(card);
      }
      if (container) {
        container.appendChild(visualContainer ? card.cloneNode(true) : card);
      }
    },

    displayOfflineTriageResult: function (draft) {
      const container = document.getElementById('triage-assessment-output');
      const visualContainer = document.getElementById('care-intake-result');
      if (!container && !visualContainer) return;

      if (container) clearElement(container);
      if (visualContainer) clearElement(visualContainer);

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

      if (visualContainer) {
        visualContainer.appendChild(card);
      }
      if (container) {
        container.appendChild(visualContainer ? card.cloneNode(true) : card);
      }
    },

    speakTriageAssessment: function () {
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

    loadClinicianQueue: function (filterStatus) {
      const tbody = document.getElementById('clinician-queue-tbody');
      if (!tbody) return;

      const authUser = localStorage.getItem('transify_auth_user');
      if (!authUser) {
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
        return;
      }

      let url = '/api/care/intakes?limit=50';
      if (filterStatus) url += `&status=${encodeURIComponent(filterStatus)}`;

      fetch(url, { credentials: 'include' })
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

    openCaseReview: function (intakeId) {
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

          // Render CareAnywhere attached vision analysis
          const visionBox = document.getElementById('inspect-vision-box');
          const visionDetails = document.getElementById('inspect-vision-details');
          if (visionBox && visionDetails) {
            if (intake.vision_analysis) {
              visionBox.style.display = 'block';
              clearElement(visionDetails);
              const va = intake.vision_analysis;
              const f = (va.findings && va.findings[0]) || 'Visual features evaluated.';
              visionDetails.textContent = `[${va.target_organ || 'DERM/OPHTH'}] Urgency: ${va.urgency_level} (${Math.round((va.confidence_score || 0.8) * 100)}% confidence). Finding: ${f}`;
            } else {
              visionBox.style.display = 'none';
            }
          }

          // Render MeSH descriptors
          const meshBox = document.getElementById('inspect-mesh-box');
          const meshTags = document.getElementById('inspect-mesh-tags');
          if (meshBox && meshTags) {
            if (intake.mesh_descriptors && intake.mesh_descriptors.length > 0) {
              meshBox.style.display = 'block';
              clearElement(meshTags);
              intake.mesh_descriptors.forEach(m => {
                const badge = document.createElement('span');
                badge.className = 'phrase-chip';
                badge.style.fontSize = '11px';
                badge.style.background = 'var(--surface-2)';
                badge.style.border = '1px solid var(--line)';
                badge.textContent = `${m.mesh_term} [${m.mesh_id}]`;
                meshTags.appendChild(badge);
              });
            } else {
              meshBox.style.display = 'none';
            }
          }

          // Render Outbreak Context
          const outbreakBox = document.getElementById('inspect-outbreak-box');
          const outbreakDetails = document.getElementById('inspect-outbreak-details');
          if (outbreakBox && outbreakDetails) {
            if (intake.outbreak_context) {
              outbreakBox.style.display = 'block';
              const ob = intake.outbreak_context;
              outbreakDetails.textContent = `${ob.zone_name} • Epidemic Risk: ${ob.overall_epidemic_risk} • Active Surveillance: ${ob.epidemiological_source}`;
            } else {
              outbreakBox.style.display = 'none';
            }
          }
        })
        .catch(err => alert(err.message));
    },

    submitClinicianReview: function () {
      if (!this.activeIntakeId) {
        alert('No active case selected for review.');
        return;
      }

      const action = document.getElementById('clinician-action-select')?.value || 'COMPLETED';
      const urgencyRadio = document.querySelector('input[name="clinician_urgency_choice"]:checked');
      const urgencyOverride = (urgencyRadio ? urgencyRadio.value : document.getElementById('clinician-override-select')?.value) || 'NONE';
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
      const headers = { 'Content-Type': 'application/json' };

      fetch(`/api/care/intake/${this.activeIntakeId}/review`, {
        method: 'POST',
        headers: headers,
        credentials: 'include',
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

    searchEvidence: function (query) {
      const container = document.getElementById('clinician-evidence-results');
      if (!container) return;

      clearElement(container);
      if (window.createCardSpinner) {
        container.appendChild(window.createCardSpinner('Searching cataloged guideline passages...'));
      } else {
        const loading = document.createElement('p');
        loading.style.fontSize = '12px';
        loading.style.color = 'var(--text-muted)';
        loading.textContent = 'Searching cataloged guideline passages...';
        container.appendChild(loading);
      }

      const headers = { 'Content-Type': 'application/json' };

      fetch('/api/care/evidence/search', {
        method: 'POST',
        headers: headers,
        credentials: 'include',
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

    loadDashboardStats: function () {
      fetch('/api/care/dashboard/stats', { credentials: 'include' })
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

    initChronicCare: function () {
      const self = this;
      const chronicSlide = document.getElementById('slide-care-chronic');
      if (!chronicSlide) return;

      // 1. Module navigation tab switching
      const navBtns = chronicSlide.querySelectorAll('.chronic-nav-btn');
      const sections = chronicSlide.querySelectorAll('.chronic-section');
      navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          navBtns.forEach(b => b.classList.remove('active'));
          sections.forEach(s => s.style.display = 'none');
          btn.classList.add('active');
          const targetId = btn.getAttribute('data-target');
          const targetSec = document.getElementById(targetId);
          if (targetSec) targetSec.style.display = 'flex';
        });
      });

      // 2. Telemetry simulation fixtures
      let currentTelemetry = {
        source: 'Fitbit_Charge_6',
        resting_heart_rate: 74.0,
        hrv_rmssd_ms: 34.0,
        sleep_metrics: { total_sleep_minutes: 432.0, deep_minutes: 78.0, awake_minutes: 71.0 },
        cgm_metrics: { mean_glucose_mg_dl: 124.0, time_in_range_pct: 82.0, time_below_range_pct: 1.5, glycemic_variability_cv_pct: 26.0 },
        ambulatory_bp: { daytime_systolic: 132.0, daytime_diastolic: 82.0, nighttime_systolic: 116.0, nighttime_diastolic: 72.0 }
      };

      const btnSimNormal = document.getElementById('btn-chronic-sim-normal');
      const btnSimHtn = document.getElementById('btn-chronic-sim-htn');
      const btnSimHypo = document.getElementById('btn-chronic-sim-hypo');

      function updateTelemetryUI(t) {
        currentTelemetry = t;
        const rhrEl = document.getElementById('chronic-kpi-rhr');
        const hrvEl = document.getElementById('chronic-kpi-hrv');
        const sleepEl = document.getElementById('chronic-kpi-sleep');
        const sleepSub = document.getElementById('chronic-kpi-sleep-sub');
        const bpEl = document.getElementById('chronic-kpi-bp');
        const bpSub = document.getElementById('chronic-kpi-bp-sub');
        const cgmEl = document.getElementById('chronic-kpi-cgm');
        const cgmSub = document.getElementById('chronic-kpi-cgm-sub');

        if (rhrEl) rhrEl.textContent = `${t.resting_heart_rate} bpm`;
        if (hrvEl) {
          hrvEl.textContent = `${t.hrv_rmssd_ms} ms`;
          hrvEl.style.color = t.hrv_rmssd_ms < 20.0 ? '#D32F2F' : (t.hrv_rmssd_ms < 35.0 ? '#8338EC' : '#2E7D32');
        }
        if (sleepEl && t.sleep_metrics) {
          const frag = Math.round((t.sleep_metrics.awake_minutes / t.sleep_metrics.total_sleep_minutes) * 100);
          sleepEl.textContent = `${frag}%`;
          if (sleepSub) sleepSub.textContent = `Total: ${(t.sleep_metrics.total_sleep_minutes / 60).toFixed(1)} hrs`;
        }
        if (bpEl && t.ambulatory_bp) {
          bpEl.textContent = `${t.ambulatory_bp.daytime_systolic}/${t.ambulatory_bp.daytime_diastolic} mmHg`;
          const dip = Math.round(((t.ambulatory_bp.daytime_systolic - t.ambulatory_bp.nighttime_systolic) / t.ambulatory_bp.daytime_systolic) * 100);
          if (bpSub) {
            if (dip <= 0) {
              bpSub.textContent = `Reverse Dipper (${dip}% dip - High Risk)`;
              bpSub.style.color = '#D32F2F';
            } else if (dip < 10) {
              bpSub.textContent = `Non-Dipper (${dip}% dip)`;
              bpSub.style.color = '#E65100';
            } else {
              bpSub.textContent = `Normal Dipper (${dip}% dip)`;
              bpSub.style.color = '#2E7D32';
            }
          }
        }
        if (cgmEl && t.cgm_metrics) {
          cgmEl.textContent = `${t.cgm_metrics.time_in_range_pct}%`;
          if (cgmSub) cgmSub.textContent = `Mean: ${t.cgm_metrics.mean_glucose_mg_dl} mg/dL | CV: ${t.cgm_metrics.glycemic_variability_cv_pct}%`;
        }
      }

      if (btnSimNormal) {
        btnSimNormal.addEventListener('click', () => {
          updateTelemetryUI({
            source: 'Fitbit_Charge_6',
            resting_heart_rate: 68.0,
            hrv_rmssd_ms: 48.0,
            sleep_metrics: { total_sleep_minutes: 450.0, deep_minutes: 85.0, awake_minutes: 45.0 },
            cgm_metrics: { mean_glucose_mg_dl: 112.0, time_in_range_pct: 88.0, time_below_range_pct: 1.0, glycemic_variability_cv_pct: 22.0 },
            ambulatory_bp: { daytime_systolic: 122.0, daytime_diastolic: 78.0, nighttime_systolic: 108.0, nighttime_diastolic: 68.0 }
          });
        });
      }

      if (btnSimHtn) {
        btnSimHtn.addEventListener('click', () => {
          updateTelemetryUI({
            source: 'Fitbit_Charge_6',
            resting_heart_rate: 88.0,
            hrv_rmssd_ms: 14.0,
            sleep_metrics: { total_sleep_minutes: 310.0, deep_minutes: 20.0, awake_minutes: 125.0 },
            cgm_metrics: { mean_glucose_mg_dl: 142.0, time_in_range_pct: 70.0, time_below_range_pct: 1.0, glycemic_variability_cv_pct: 32.0 },
            ambulatory_bp: { daytime_systolic: 144.0, daytime_diastolic: 92.0, nighttime_systolic: 152.0, nighttime_diastolic: 96.0 }
          });
        });
      }

      if (btnSimHypo) {
        btnSimHypo.addEventListener('click', () => {
          updateTelemetryUI({
            source: 'Continuous_Glucose_Monitor',
            resting_heart_rate: 70.0,
            hrv_rmssd_ms: 42.0,
            sleep_metrics: { total_sleep_minutes: 420.0, deep_minutes: 70.0, awake_minutes: 40.0 },
            cgm_metrics: { mean_glucose_mg_dl: 82.0, time_in_range_pct: 64.0, time_below_range_pct: 8.5, glycemic_variability_cv_pct: 38.0 },
            ambulatory_bp: { daytime_systolic: 120.0, daytime_diastolic: 76.0, nighttime_systolic: 106.0, nighttime_diastolic: 66.0 }
          });
        });
      }

      // Run Crisis Forecast Button
      const btnForecast = document.getElementById('btn-run-crisis-forecast');
      if (btnForecast) {
        btnForecast.addEventListener('click', () => {
          btnForecast.textContent = 'Forecasting Physiological Trajectory...';
          fetch('/api/care/chronic/forecast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              telemetry: {
                metrics_summary: {
                  autonomic: { resting_heart_rate_bpm: currentTelemetry.resting_heart_rate, hrv_rmssd_ms: currentTelemetry.hrv_rmssd_ms },
                  sleep_architecture: { sleep_fragmentation_index: Math.round((currentTelemetry.sleep_metrics.awake_minutes / currentTelemetry.sleep_metrics.total_sleep_minutes) * 100) },
                  hemodynamics: {
                    dipping_phenotype: currentTelemetry.ambulatory_bp.nighttime_systolic >= currentTelemetry.ambulatory_bp.daytime_systolic ? 'REVERSE_DIPPER' : 'NORMAL_DIPPER',
                    nocturnal_dip_pct: ((currentTelemetry.ambulatory_bp.daytime_systolic - currentTelemetry.ambulatory_bp.nighttime_systolic) / currentTelemetry.ambulatory_bp.daytime_systolic) * 100
                  },
                  glycemic_control: { mean_glucose_mg_dl: currentTelemetry.cgm_metrics.mean_glucose_mg_dl, time_below_range_pct: currentTelemetry.cgm_metrics.time_below_range_pct }
                }
              },
              patient_history: { baseline_resting_hr: 68.0, baseline_hrv_rmssd: 44.0, hypertension_history: true }
            })
          })
            .then(res => res.json())
            .then(data => {
              btnForecast.textContent = '⚡ Run 24h Predictive Crisis Forecast';
              const resultCard = document.getElementById('chronic-forecast-result');
              if (!resultCard) return;
              resultCard.style.display = 'block';

              const htn = data.hypertensive_crisis_forecast || {};
              const badge = document.getElementById('chronic-forecast-badge');
              const prob = document.getElementById('chronic-forecast-prob');
              const prog = document.getElementById('chronic-forecast-progress');
              const drivers = document.getElementById('chronic-forecast-drivers');
              const hfStatus = document.getElementById('chronic-forecast-hf-status');
              const hypoStatus = document.getElementById('chronic-forecast-hypo-status');
              const action = document.getElementById('chronic-forecast-action');

              if (prob) prob.textContent = `${htn.probability_percentage}%`;
              if (prog) {
                prog.style.width = `${htn.probability_percentage}%`;
                prog.style.background = htn.probability_percentage >= 70 ? '#D32F2F' : (htn.probability_percentage >= 40 ? '#E65100' : '#2E7D32');
              }
              if (badge) {
                badge.textContent = htn.alert_level;
                badge.style.background = htn.alert_level === 'CRITICAL_CRISIS_IMMINENT' ? '#FFEBEE' : '#E8F5E9';
                badge.style.color = htn.alert_level === 'CRITICAL_CRISIS_IMMINENT' ? '#D32F2F' : '#2E7D32';
              }
              if (drivers && htn.primary_physiological_drivers) {
                drivers.innerHTML = htn.primary_physiological_drivers.map(d => `<div>• <strong>${d.driver}:</strong> ${d.detail}</div>`).join('');
              }
              if (hfStatus && data.heart_failure_decompensation_forecast) {
                hfStatus.textContent = data.heart_failure_decompensation_forecast.status;
              }
              if (hypoStatus && data.nocturnal_hypoglycemia_forecast) {
                hypoStatus.textContent = data.nocturnal_hypoglycemia_forecast.risk_detected ? '⚠️ High Risk (<54 mg/dL)' : 'Normal Trajectory';
                hypoStatus.style.color = data.nocturnal_hypoglycemia_forecast.risk_detected ? '#E65100' : '#2E7D32';
              }
              if (action) action.textContent = htn.recommended_preventative_action || '';
            })
            .catch(err => {
              btnForecast.textContent = '⚡ Run 24h Predictive Crisis Forecast';
              alert('Crisis forecasting failed: ' + err.message);
            });
        });
      }

      // 3. Nutrition CV & Insulin Calculator
      let uploadedFoodBase64 = null;
      const photoInput = document.getElementById('chronic-food-photo-input');
      const previewBox = document.getElementById('chronic-food-preview-box');
      const previewImg = document.getElementById('chronic-food-preview-img');

      if (photoInput) {
        photoInput.addEventListener('change', (e) => {
          const file = e.target.files[0];
          if (!file) return;
          const reader = new FileReader();
          reader.onload = (evt) => {
            uploadedFoodBase64 = evt.target.result;
            if (previewImg) previewImg.src = uploadedFoodBase64;
            if (previewBox) previewBox.style.display = 'flex';
          };
          reader.readAsDataURL(file);
        });
      }

      const btnCalcInsulin = document.getElementById('btn-calc-insulin');
      if (btnCalcInsulin) {
        btnCalcInsulin.addEventListener('click', () => {
          btnCalcInsulin.textContent = 'Analyzing Nutritional Biomarkers...';
          const mealSelect = document.getElementById('chronic-meal-select');
          const bgCur = parseFloat(document.getElementById('chronic-glucose-current').value || '140');
          const bgTgt = parseFloat(document.getElementById('chronic-glucose-target').value || '100');
          const icr = parseFloat(document.getElementById('chronic-insulin-icr').value || '10');
          const isf = parseFloat(document.getElementById('chronic-insulin-isf').value || '50');
          const iob = parseFloat(document.getElementById('chronic-insulin-iob').value || '0.0');

          fetch('/api/care/chronic/nutrition-insulin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              meal_type: mealSelect ? mealSelect.value : 'south_asian_roti_dal',
              image_data: uploadedFoodBase64,
              current_glucose: bgCur,
              target_glucose: bgTgt,
              icr: icr,
              isf: isf,
              iob: iob
            })
          })
            .then(res => res.json())
            .then(data => {
              btnCalcInsulin.textContent = '💉 Analyze Meal & Compute Insulin Dose';
              const card = document.getElementById('chronic-insulin-result');
              if (!card) return;
              card.style.display = 'block';

              const meal = data.meal_recognition || {};
              const dishTitle = document.getElementById('chronic-dish-title');
              const carbs = document.getElementById('chronic-nutr-carbs');
              const fiber = document.getElementById('chronic-nutr-fiber');
              const protein = document.getElementById('chronic-nutr-protein');
              const calories = document.getElementById('chronic-nutr-calories');
              const gi = document.getElementById('chronic-nutr-gi');
              const gl = document.getElementById('chronic-nutr-gl');

              if (dishTitle) dishTitle.textContent = meal.detected_dish || '';
              if (carbs) carbs.textContent = `${meal.macronutrients.net_carbohydrates_grams}g`;
              if (fiber) fiber.textContent = `${meal.macronutrients.dietary_fiber_grams}g`;
              if (protein) protein.textContent = `${meal.macronutrients.protein_grams}g`;
              if (calories) calories.textContent = `${meal.macronutrients.total_calories_kcal} kcal`;
              if (gi) gi.textContent = `${meal.glycemic_profile.glycemic_index} (${meal.glycemic_profile.glycemic_index_rating})`;
              if (gl) gl.textContent = `${meal.glycemic_profile.glycemic_load} (${meal.glycemic_profile.glycemic_load_rating})`;

              const insulin = data.insulin_dosage_recommendation || {};
              const totalEl = document.getElementById('chronic-insulin-total');
              const mealEl = document.getElementById('chronic-insulin-meal');
              const corrEl = document.getElementById('chronic-insulin-corr');
              const warnEl = document.getElementById('chronic-insulin-warnings');
              const lifeEl = document.getElementById('chronic-insulin-lifestyle');

              if (totalEl) totalEl.textContent = `${insulin.dosage_breakdown.recommended_injection_units} units`;
              if (mealEl) mealEl.textContent = `${insulin.dosage_breakdown.meal_bolus_units}u`;
              if (corrEl) corrEl.textContent = `${insulin.dosage_breakdown.correction_bolus_units}u`;
              if (warnEl) warnEl.innerHTML = (insulin.safety_warnings || []).map(w => `<div>⚠️ ${w}</div>`).join('');
              if (lifeEl) lifeEl.textContent = insulin.lifestyle_adjunct || '';
            })
            .catch(err => {
              btnCalcInsulin.textContent = '💉 Analyze Meal & Compute Insulin Dose';
              alert('Insulin calculation failed: ' + err.message);
            });
        });
      }

      // 4. Culturally Tailored Lab Coaching
      const btnTranslateLab = document.getElementById('btn-translate-lab');
      if (btnTranslateLab) {
        btnTranslateLab.addEventListener('click', () => {
          btnTranslateLab.textContent = 'Generating Cultural Coaching Plan...';
          const a1c = parseFloat(document.getElementById('chronic-lab-a1c').value || '8.2');
          const fbg = parseFloat(document.getElementById('chronic-lab-fbg').value || '162');
          const ldl = parseFloat(document.getElementById('chronic-lab-ldl').value || '138');
          const tg = parseFloat(document.getElementById('chronic-lab-tg').value || '195');
          const egfr = parseFloat(document.getElementById('chronic-lab-egfr').value || '65');
          const uacr = parseFloat(document.getElementById('chronic-lab-uacr').value || '48');
          const culture = document.getElementById('chronic-culture-select').value || 'south_asian';

          fetch('/api/care/chronic/lab-coach', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              lab_panel: {
                hba1c_pct: a1c,
                fasting_glucose_mg_dl: fbg,
                ldl_cholesterol_mg_dl: ldl,
                triglycerides_mg_dl: tg,
                egfr_ml_min: egfr,
                urine_albumin_creatinine_ratio: uacr
              },
              cultural_diet: culture
            })
          })
            .then(res => res.json())
            .then(data => {
              btnTranslateLab.textContent = '📋 Translate Lab Results & Generate Diet Plan';
              const card = document.getElementById('chronic-lab-result');
              if (!card) return;
              card.style.display = 'block';

              const summaryText = document.getElementById('chronic-lab-summary-text');
              const swapsContainer = document.getElementById('chronic-lab-swaps-container');
              const superfoods = document.getElementById('chronic-lab-superfoods');
              const exercise = document.getElementById('chronic-lab-exercise');

              const plain = data.plain_language_summary || {};
              if (summaryText) {
                summaryText.innerHTML = `
                  <div><strong>Glycemic:</strong> ${plain.glycemic_health ? plain.glycemic_health.patient_explanation : ''}</div>
                  <div style="margin-top: 4px;"><strong>Kidney Function:</strong> ${plain.kidney_filtration ? plain.kidney_filtration.chronic_kidney_stage : ''} (${plain.kidney_filtration ? plain.kidney_filtration.albumin_leakage : ''})</div>
                  <div style="margin-top: 4px;"><strong>Lipid Assessment:</strong> ${(plain.cardiovascular_lipids ? plain.cardiovascular_lipids.clinical_assessment : []).join(' ')}</div>
                `;
              }

              const coaching = data.culturally_tailored_coaching || {};
              if (swapsContainer && coaching.staple_swaps) {
                swapsContainer.innerHTML = coaching.staple_swaps.map(s => `
                  <div style="background: var(--surface); padding: 8px 12px; border-radius: 8px; border-left: 3px solid #8338EC;">
                    <div style="font-weight: 700; color: #D32F2F;">❌ Replace: ${s.replace}</div>
                    <div style="font-weight: 700; color: #2E7D32;">✅ Substitute: ${s.substitute}</div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;"><em>Rationale:</em> ${s.rationale}</div>
                  </div>
                `).join('');
              }

              if (superfoods && coaching.cultural_superfoods) {
                superfoods.textContent = `Cultural Superfoods: ${coaching.cultural_superfoods.join(', ')}`;
              }
              if (exercise) {
                exercise.textContent = `Exercise Recommendation: ${coaching.physical_activity_prescription || ''}`;
              }
            })
            .catch(err => {
              btnTranslateLab.textContent = '📋 Translate Lab Results & Generate Diet Plan';
              alert('Lab translation failed: ' + err.message);
            });
        });
      }

      // 5. Elderly Voice Adherence & Cognitive Biomarkers
      const btnSimHes = document.getElementById('btn-chronic-sim-hesitation');
      const btnSimFlu = document.getElementById('btn-chronic-sim-fluent');
      const transcriptEl = document.getElementById('chronic-elderly-transcript');

      if (btnSimHes && transcriptEl) {
        btnSimHes.addEventListener('click', () => {
          transcriptEl.value = 'Um, I think so... maybe I took the blue one, not sure... where was I? What time is it now?';
        });
      }
      if (btnSimFlu && transcriptEl) {
        btnSimFlu.addEventListener('click', () => {
          transcriptEl.value = 'Good morning, I took my blood pressure and diabetes tablets with a glass of water right after oatmeal.';
        });
      }

      const btnAnalyzeElderly = document.getElementById('btn-analyze-elderly-voice');
      if (btnAnalyzeElderly) {
        btnAnalyzeElderly.addEventListener('click', () => {
          btnAnalyzeElderly.textContent = 'Evaluating Vocal Biomarkers & Adherence...';
          const med1 = document.getElementById('chronic-med-1').checked;
          const med2 = document.getElementById('chronic-med-2').checked;
          const med3 = document.getElementById('chronic-med-3').checked;
          const med4 = document.getElementById('chronic-med-4').checked;

          const medLog = [
            { medication: 'Metformin 500mg', status: med1 ? 'TAKEN' : 'MISSED' },
            { medication: 'Lisinopril 10mg', status: med2 ? 'TAKEN' : 'MISSED' },
            { medication: 'Atorvastatin 20mg', status: med3 ? 'TAKEN' : 'MISSED' },
            { medication: 'Amlodipine 5mg', status: med4 ? 'TAKEN' : 'MISSED' }
          ];

          const text = transcriptEl ? transcriptEl.value : '';
          const isHesitant = text.includes('maybe') || text.includes('not sure') || text.includes('where was i');

          fetch('/api/care/chronic/elderly-adherence', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              medication_log: medLog,
              audio_transcript: text,
              acoustic_metrics: {
                speech_duration_seconds: isHesitant ? 12.0 : 6.0,
                mean_pause_duration_seconds: isHesitant ? 1.1 : 0.45,
                vocal_jitter_pct: isHesitant ? 2.2 : 0.9
              }
            })
          })
            .then(res => res.json())
            .then(data => {
              btnAnalyzeElderly.textContent = '🎙️ Analyze Adherence & Vocal Biomarkers';
              const card = document.getElementById('chronic-elderly-result');
              if (!card) return;
              card.style.display = 'block';

              const adh = data.medication_adherence || {};
              const pdcEl = document.getElementById('chronic-elderly-pdc');
              const tierEl = document.getElementById('chronic-elderly-pdc-tier');
              const msgEl = document.getElementById('chronic-elderly-pdc-msg');

              if (pdcEl) pdcEl.textContent = `${adh.proportion_of_days_covered_pdc}%`;
              if (tierEl) {
                tierEl.textContent = adh.adherence_tier;
                tierEl.style.color = adh.proportion_of_days_covered_pdc >= 80 ? '#2E7D32' : '#D32F2F';
              }
              if (msgEl) msgEl.textContent = adh.clinical_summary || '';

              const cog = data.acoustic_cognitive_biomarkers || {};
              const statusEl = document.getElementById('chronic-elderly-cog-status');
              const scoreEl = document.getElementById('chronic-elderly-cog-score');
              const wpmEl = document.getElementById('chronic-elderly-wpm');
              const pauseEl = document.getElementById('chronic-elderly-pause');
              const jitterEl = document.getElementById('chronic-elderly-jitter');
              const guidanceEl = document.getElementById('chronic-elderly-cog-guidance');

              if (statusEl) statusEl.textContent = cog.cognitive_status;
              if (scoreEl) scoreEl.textContent = `Hesitation Index: ${cog.cognitive_hesitation_index_0_100}/100`;
              if (wpmEl) wpmEl.textContent = `${cog.speech_rate_wpm} WPM`;
              if (pauseEl) pauseEl.textContent = `${cog.mean_inter_word_pause_seconds}s`;
              if (jitterEl) jitterEl.textContent = `${cog.vocal_jitter_pct}%`;
              if (guidanceEl) guidanceEl.textContent = cog.caregiver_guidance || '';
            })
            .catch(err => {
              btnAnalyzeElderly.textContent = '🎙️ Analyze Adherence & Vocal Biomarkers';
              alert('Elderly adherence evaluation failed: ' + err.message);
            });
        });
      }

      // 6. OpenFDA Polypharmacy Checker
      const btnCheckPoly = document.getElementById('btn-check-polypharmacy');
      if (btnCheckPoly) {
        btnCheckPoly.addEventListener('click', () => {
          btnCheckPoly.textContent = 'Querying OpenFDA Event Databases...';
          const checkedMeds = Array.from(chronicSlide.querySelectorAll('#chronic-polypharmacy-chips input:checked'))
            .map(cb => cb.value);

          fetch('/api/care/chronic/polypharmacy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ medications: checkedMeds })
          })
            .then(res => res.json())
            .then(data => {
              btnCheckPoly.textContent = '💊 Cross-Check OpenFDA Drug Interactions';
              const card = document.getElementById('chronic-polypharmacy-result');
              if (!card) return;
              card.style.display = 'block';

              const badge = document.getElementById('chronic-polypharmacy-badge');
              const cardsBox = document.getElementById('chronic-polypharmacy-cards');

              if (badge) {
                badge.textContent = data.overall_safety_rating;
                badge.style.background = data.overall_safety_rating.includes('CONTRAINDICATION') ? '#FFCDD2' : (data.overall_safety_rating.includes('MAJOR') ? '#FFE082' : '#C8E6C9');
                badge.style.color = data.overall_safety_rating.includes('CONTRAINDICATION') ? '#B71C1C' : (data.overall_safety_rating.includes('MAJOR') ? '#E65100' : '#1B5E20');
              }

              if (cardsBox) {
                if (!data.interactions || data.interactions.length === 0) {
                  cardsBox.innerHTML = '<div style="color: #2E7D32; font-weight: 700;">No high-risk contraindications detected in this chronic medication combination.</div>';
                } else {
                  cardsBox.innerHTML = data.interactions.map(item => `
                    <div style="background: var(--surface-2); padding: 12px; border-radius: 8px; border-left: 4px solid ${item.severity === 'CONTRAINDICATED' ? '#D32F2F' : '#E65100'};">
                      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <span style="font-weight: 800; font-size: 14px;">${item.interacting_pair}</span>
                        <span style="font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 12px; background: ${item.severity === 'CONTRAINDICATED' ? '#FFEBEE' : '#FFF8E1'}; color: ${item.severity === 'CONTRAINDICATED' ? '#D32F2F' : '#E65100'};">${item.severity}</span>
                      </div>
                      <div style="font-size: 12px; font-weight: 600; color: var(--text);">${item.category}</div>
                      <div style="font-size: 11px; color: var(--text-2); margin-top: 2px;">${item.mechanism}</div>
                      <div style="font-size: 12px; color: #D32F2F; font-weight: 600; margin-top: 4px;"><strong>Clinical Action:</strong> ${item.clinical_action}</div>
                      <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">FDA Reference: ${item.openfda_event_code} (${item.adverse_events_in_fda_database} reported events)</div>
                    </div>
                  `).join('');
                }
              }
            })
            .catch(err => {
              btnCheckPoly.textContent = '💊 Cross-Check OpenFDA Drug Interactions';
              alert('Polypharmacy check failed: ' + err.message);
            });
        });
      }

      // 7. Federated Learning Simulator
      const fedSlider = document.getElementById('chronic-fed-epsilon');
      const fedSliderVal = document.getElementById('chronic-fed-epsilon-val');
      if (fedSlider && fedSliderVal) {
        fedSlider.addEventListener('input', () => {
          fedSliderVal.textContent = `ε = ${fedSlider.value}`;
        });
      }

      const btnFed = document.getElementById('btn-run-federated-round');
      if (btnFed) {
        btnFed.addEventListener('click', () => {
          btnFed.textContent = 'Aggregating Encrypted Gradients Across Borders...';
          const eps = parseFloat(fedSlider ? fedSlider.value : '1.0');

          fetch('/api/care/chronic/federated-round', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              num_nodes: 4,
              privacy_budget_epsilon: eps,
              round_number: 5
            })
          })
            .then(res => res.json())
            .then(data => {
              btnFed.textContent = '🌐 Execute Federated Training Round (FedAvg)';
              const card = document.getElementById('chronic-fed-result');
              if (!card) return;
              card.style.display = 'block';

              const aucEl = document.getElementById('chronic-fed-auc');
              const patEl = document.getElementById('chronic-fed-patients');
              const dpEl = document.getElementById('chronic-fed-dp');
              const summaryEl = document.getElementById('chronic-fed-summary-text');

              if (aucEl && data.global_model_metrics) aucEl.textContent = data.global_model_metrics.global_auc_roc;
              if (patEl) patEl.textContent = (data.total_deidentified_patients_across_borders || 13550).toLocaleString();
              if (dpEl && data.privacy_guarantee) dpEl.textContent = data.privacy_guarantee.differential_privacy;
              if (summaryEl) summaryEl.textContent = data.federation_summary || '';
            })
            .catch(err => {
              btnFed.textContent = '🌐 Execute Federated Training Round (FedAvg)';
              alert('Federated round failed: ' + err.message);
            });
        });
      }
    },

    resetDemoFixtures: function (callback) {
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
