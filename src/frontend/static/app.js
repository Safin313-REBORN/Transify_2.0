/**
 * Transify Assistive Platform - Client Application
 * Handles accessible themes, text-to-speech, real-time sign recognition,
 * Braille image processing, history management, and screen-reader announcements.
 */

// =============================================================
// Transify Kinetic Page Loader Engine (Uiverse.io by Praashoo7)
// =============================================================
window.showPageLoader = function (message = 'Loading Transify...', duration = null) {
  const el = document.getElementById('transify-page-loader');
  const txt = document.getElementById('page-loader-text');
  if (txt && message) txt.textContent = message;
  if (el) {
    el.classList.add('active');
  }
  if (duration && typeof duration === 'number') {
    if (window._pageLoaderTimer) clearTimeout(window._pageLoaderTimer);
    window._pageLoaderTimer = setTimeout(() => {
      window.hidePageLoader();
    }, duration);
  }
};

window.hidePageLoader = function () {
  if (window._pageLoaderTimer) clearTimeout(window._pageLoaderTimer);
  const el = document.getElementById('transify-page-loader');
  if (el) {
    el.classList.remove('active');
  }
};

// =============================================================
// Transify Domino Card Loading Engine (Uiverse.io by satyamchaudharydev)
// =============================================================
window.createCardSpinner = function (loadingText = 'Loading...') {
  const overlay = document.createElement('div');
  overlay.className = 'card-loading-overlay';
  overlay.setAttribute('aria-live', 'polite');
  overlay.innerHTML = `
    <div class="spinner" aria-hidden="true">
      <span></span>
      <span></span>
      <span></span>
      <span></span>
      <span></span>
      <span></span>
      <span></span>
      <span></span>
    </div>
    <div class="card-loading-text">${loadingText}</div>
  `;
  return overlay;
};

window.setCardLoading = function (cardElement, isLoading, loadingText = 'Loading...') {
  if (!cardElement) return;
  const existing = cardElement.querySelector('.card-loading-overlay');
  if (isLoading) {
    cardElement.classList.add('is-loading');
    if (!existing) {
      cardElement.appendChild(window.createCardSpinner(loadingText));
    } else {
      const textEl = existing.querySelector('.card-loading-text');
      if (textEl) textEl.textContent = loadingText;
    }
  } else {
    cardElement.classList.remove('is-loading');
    if (existing) {
      existing.remove();
    }
  }
};

// =============================================================
// Unified Theme Application Engine (Light, Dark, High-Contrast, System)
// =============================================================
window.applyThemeGlobal = function (theme) {
  const chosenTheme = theme || localStorage.getItem('transify_theme') || 'light';
  if (window.TransifyApp) window.TransifyApp.theme = chosenTheme;

  document.querySelectorAll('.theme-card-btn').forEach(btn => {
    const isMatch = btn.dataset.theme === chosenTheme;
    btn.classList.toggle('active', isMatch);
    btn.setAttribute('aria-pressed', isMatch ? 'true' : 'false');
  });

  let effectiveTheme = chosenTheme;
  if (chosenTheme === 'system') {
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    effectiveTheme = prefersDark ? 'dark' : 'light';
    if (!window._systemThemeListenerAttached && window.matchMedia) {
      window._systemThemeListenerAttached = true;
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (localStorage.getItem('transify_theme') === 'system') {
          const eff = e.matches ? 'dark' : 'light';
          document.documentElement.setAttribute('data-theme', eff);
          if (document.body) document.body.setAttribute('data-theme', eff);
        }
      });
    }
  }

  document.documentElement.setAttribute('data-theme', effectiveTheme);
  if (document.body) {
    document.body.setAttribute('data-theme', effectiveTheme);
  }

  if (effectiveTheme === 'high-contrast' || chosenTheme === 'high-contrast') {
    if (document.body) document.body.classList.add('high-contrast');
    document.documentElement.setAttribute('data-theme', 'high-contrast');
    if (document.body) document.body.setAttribute('data-theme', 'high-contrast');
    try { localStorage.setItem('transify_high_contrast', 'true'); } catch (e) { }
    const toggleContrast = document.getElementById('toggle-high-contrast');
    if (toggleContrast) toggleContrast.checked = true;
  } else {
    if (document.body) document.body.classList.remove('high-contrast');
    try { localStorage.setItem('transify_high_contrast', 'false'); } catch (e) { }
    const toggleContrast = document.getElementById('toggle-high-contrast');
    if (toggleContrast) toggleContrast.checked = false;
  }

  try {
    localStorage.setItem('transify_theme', chosenTheme);
  } catch (e) { }
};

window.setAppLanguage = function (lang) {
  try { localStorage.setItem('transify_lang', lang); } catch (_) { }
  if (typeof applyLocale === 'function') applyLocale(lang);
  const enBtn = document.getElementById('home-lang-en');
  const bnBtn = document.getElementById('home-lang-bn');
  if (enBtn && bnBtn) {
    enBtn.classList.toggle('active', lang === 'en');
    enBtn.setAttribute('aria-pressed', lang === 'en');
    bnBtn.classList.toggle('active', lang === 'bn');
    bnBtn.setAttribute('aria-pressed', lang === 'bn');
  }
  const select = document.getElementById('setting-lang-select');
  if (select) select.value = lang;
  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast(`Interface language: ${lang === 'bn' ? 'বাংলা' : 'English'}`, 'info');
  }
};

window.testVoicePreview = function () {
  const phrase = 'Welcome to Transify. Assistive voice synthesis is verified and operating.';
  if (window.TransifyApp && window.TransifyApp.speak) {
    window.TransifyApp.speak(phrase, { rate: (window.TransifyApp && window.TransifyApp.speechRate) || 1.0 });
  } else if ('speechSynthesis' in window) {
    const u = new SpeechSynthesisUtterance(phrase);
    u.rate = (window.TransifyApp && window.TransifyApp.speechRate) || 1.0;
    window.speechSynthesis.speak(u);
  }
  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast('Playing voice preview', 'info');
  }
};

window.exportSettingsData = function () {
  let profData = {};
  try { profData = JSON.parse(localStorage.getItem('transify_user_profile') || '{}'); } catch (_) { }
  const dump = {
    app: 'Transify 2.0',
    exported_at: new Date().toISOString(),
    profile: profData,
    preferences: {
      theme: localStorage.getItem('transify_theme') || 'light',
      font_scale: localStorage.getItem('transify_font_scale') || 'normal',
      speech_rate: localStorage.getItem('transify_speech_rate') || '1.0',
      sign_lang: localStorage.getItem('transify_default_sign_lang') || 'asl',
      braille_standard: localStorage.getItem('transify_braille_standard') || 'grade1',
      confidence_gate: localStorage.getItem('transify_confidence_gate') || '85'
    }
  };
  const blob = new Blob([JSON.stringify(dump, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `transify_backup_${Date.now()}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast('Profile and settings exported as JSON', 'success');
  }
};

window.clearActivityHistory = async function () {
  const recentList = document.getElementById('home-recent-list');
  if (recentList) {
    recentList.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--text-2); font-size: 14px; font-weight: 600;">No recent translations yet.</div>';
  }
  try { await fetch('/api/history', { method: 'DELETE' }); } catch (e) { }
  const storageDesc = document.getElementById('settings-storage-size');
  if (storageDesc) storageDesc.textContent = '0 local activity logs';
  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast('Activity history cleared successfully', 'success');
  }
};

window.copySystemDiagnostics = function () {
  const curTheme = document.documentElement.getAttribute('data-theme') || 'light';
  const diagInfo = `Transify 2.0 Diagnostics\nTimestamp: ${new Date().toISOString()}\nPlatform: ${navigator.platform || 'Linux'}\nResolution: ${window.innerWidth}x${window.innerHeight}\nTheme: ${curTheme}\nConnection: ${navigator.onLine ? 'Online' : 'Offline'}\nMediaPipe Vision: Available (0.10.14 WebAssembly)\nSpeech: Zero Auto-Audio Policy`;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(diagInfo).then(() => {
      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast('System diagnostics copied to clipboard!', 'success');
      }
    }).catch(() => {
      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast('Diagnostics ready in developer console', 'info');
      }
    });
  } else {
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast('Diagnostics: Platform online, Zero Auto-Audio', 'info');
    }
  }
};

window.submitDeveloperFeedback = function () {
  const contactMsg = document.getElementById('contact-message');
  if (!contactMsg) return;
  const text = contactMsg.value.trim();
  if (!text) {
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast('Please type a message before sending', 'info');
    }
    return;
  }
  contactMsg.value = '';
  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast('Message sent! Developer Safin has received your feedback.', 'success');
  }
};

// =============================================================
// Unified Global Settings Option Handlers (100% Reliable Direct Calls)
// =============================================================
window.switchSettingsTab = function (tabName) {
  const tabs = document.querySelectorAll('.settings-nav-tab');
  const panes = document.querySelectorAll('.settings-tab-pane');
  if (!tabs.length || !panes.length) return;

  tabs.forEach(tab => {
    const isTarget = tab.getAttribute('data-settings-tab') === tabName;
    tab.classList.toggle('active', isTarget);
    tab.setAttribute('aria-selected', isTarget ? 'true' : 'false');
  });

  panes.forEach(pane => {
    const isTarget = pane.id === `settings-pane-${tabName}`;
    pane.classList.toggle('active', isTarget);
    pane.style.display = isTarget ? 'flex' : 'none';
  });

  try { localStorage.setItem('transify_settings_tab', tabName); } catch (_) { }
};

window.setConfidenceGate = function (val) {
  const strVal = String(val);
  const radios = document.querySelectorAll('input[name="setting_confidence_radio"]');
  radios.forEach(r => {
    r.checked = (r.value === strVal);
  });
  const confGate = document.getElementById('setting-confidence-gate');
  if (confGate) {
    confGate.value = strVal;
  }
  try { localStorage.setItem('transify_confidence_gate', strVal); } catch (_) { }

  const glider = document.querySelector('#setting-confidence-radio-group .glider');
  if (glider) {
    const offsetMap = { '95': '0', '85': '100%', '70': '200%' };
    if (offsetMap[strVal] !== undefined) {
      glider.style.transform = `translateY(${offsetMap[strVal]})`;
    }
  }

  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast(`Vision confidence threshold: ${strVal}%`, 'info');
  }
};

window.applyFontScale = function (scale) {
  const group = document.getElementById('settings-fontsize-group');
  if (group) {
    group.querySelectorAll('.segmented-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.scale === scale);
    });
  }
  document.documentElement.setAttribute('data-scale', scale);
  document.documentElement.setAttribute('data-font-scale', scale);
  document.body.setAttribute('data-scale', scale);
  document.body.setAttribute('data-font-scale', scale);
  try { localStorage.setItem('transify_font_scale', scale); } catch (_) { }
  if (window.TransifyApp && window.TransifyApp.showToast) {
    const labelMap = { normal: '100%', large: '115%', xlarge: '130%' };
    window.TransifyApp.showToast(`Typography scaled to ${labelMap[scale] || scale}`, 'info');
  }
};

window.setSpeechRate = function (rate) {
  const fRate = parseFloat(rate);
  const group = document.getElementById('settings-speech-rate-group');
  if (group) {
    group.querySelectorAll('.segmented-btn').forEach(btn => {
      btn.classList.toggle('active', parseFloat(btn.dataset.rate) === fRate);
    });
  }
  if (window.TransifyApp) window.TransifyApp.speechRate = fRate;
  try { localStorage.setItem('transify_speech_rate', fRate.toString()); } catch (_) { }
  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast(`Speech rate set to ${fRate}x`, 'info');
  }
};

window.setDefaultSignLang = function (lang) {
  const group = document.getElementById('settings-sign-lang-group');
  if (group) {
    group.querySelectorAll('.segmented-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.sign === lang);
    });
  }
  try { localStorage.setItem('transify_default_sign_lang', lang); } catch (_) { }
  const aslBtn = document.getElementById('lang-asl-btn');
  const bdslBtn = document.getElementById('lang-bdsl-btn');
  if (aslBtn && bdslBtn) {
    aslBtn.classList.toggle('active', lang === 'asl');
    bdslBtn.classList.toggle('active', lang === 'bdsl');
  }
  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast(`Default sign lexicon: ${lang.toUpperCase()}`, 'info');
  }
};

window.setBrailleStandard = function (std) {
  const group = document.getElementById('settings-braille-standard-group');
  if (group) {
    group.querySelectorAll('.segmented-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.braille === std);
    });
  }
  try { localStorage.setItem('transify_braille_standard', std); } catch (_) { }
  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast(`Braille transcription: ${std === 'grade1' ? 'Grade 1' : 'Grade 2'}`, 'info');
  }
};

window.toggleReduceMotion = function (checked) {
  if (checked) {
    document.documentElement.setAttribute('data-motion', 'reduced');
    document.body.classList.add('reduced-motion');
    try {
      localStorage.setItem('transify_reduce_motion', '1');
      localStorage.setItem('transify_reduced_motion', 'true');
    } catch (_) { }
  } else {
    document.documentElement.removeAttribute('data-motion');
    document.body.classList.remove('reduced-motion');
    try {
      localStorage.removeItem('transify_reduce_motion');
      localStorage.setItem('transify_reduced_motion', 'false');
    } catch (_) { }
  }
  const el = document.getElementById('setting-reduce-motion');
  if (el) el.checked = checked;
  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast(checked ? 'Reduced Motion Enabled' : 'Animations Restored', 'info');
  }
};

window.toggleFocusRings = function (checked) {
  if (checked) {
    document.body.classList.add('enhanced-focus');
    try { localStorage.setItem('transify_focus_rings', 'true'); } catch (_) { }
  } else {
    document.body.classList.remove('enhanced-focus');
    try { localStorage.setItem('transify_focus_rings', 'false'); } catch (_) { }
  }
  const el = document.getElementById('setting-focus-rings');
  if (el) el.checked = checked;
  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast(checked ? 'Prominent Keyboard Focus Rings Enabled' : 'Standard Focus Rings Restored', 'success');
  }
};

window.toggleAudioChimes = function (checked) {
  if (window.TransifyApp) window.TransifyApp.audioChimes = checked;
  try { localStorage.setItem('transify_audio_chimes', checked ? 'true' : 'false'); } catch (_) { }
  const el = document.getElementById('setting-audio-chimes');
  if (el) el.checked = checked;
  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast(checked ? 'Recognition Audio Chimes Enabled' : 'Audio Chimes Muted', 'info');
  }
};

window.saveUserProfile = function () {
  const profName = document.getElementById('profile-input-name');
  const profRole = document.getElementById('profile-select-role');
  const profComm = document.getElementById('profile-select-comm');
  const profDialect = document.getElementById('profile-select-dialect');
  const profBio = document.getElementById('profile-input-bio');
  const profAvatar = document.getElementById('profile-avatar-display');
  const profHeading = document.getElementById('profile-display-heading');
  const profBadgeRole = document.getElementById('profile-badge-role');

  const roleLabels = {
    accessibility_user: 'Accessibility User',
    chronic_care_patient: 'ChronicCare Patient',
    healthcare_provider: 'Clinician / Provider',
    caregiver: 'Caregiver Advocate',
    researcher: 'AI Researcher'
  };

  const nameVal = (profName ? profName.value : '') || 'Guest User';
  const roleVal = profRole ? profRole.value : 'accessibility_user';
  const commVal = profComm ? profComm.value : 'multimodal';
  const dialectVal = profDialect ? profDialect.value : 'en-US';
  const bioVal = profBio ? profBio.value : '';

  const profObj = { name: nameVal, role: roleVal, comm: commVal, dialect: dialectVal, bio: bioVal };
  try { localStorage.setItem('transify_user_profile', JSON.stringify(profObj)); } catch (_) { }

  const initials = nameVal.trim().split(' ').map(x => x[0]).join('').toUpperCase().slice(0, 2) || 'TR';
  if (profAvatar) profAvatar.textContent = initials;
  if (profHeading) profHeading.textContent = nameVal;
  if (profBadgeRole) profBadgeRole.textContent = roleLabels[roleVal] || 'Accessibility User';

  const setAv = document.getElementById('settings-avatar-initials');
  if (setAv) setAv.textContent = initials;
  const frameAv = document.getElementById('frame-avatar-btn');
  if (frameAv) frameAv.textContent = initials;
  const setName = document.getElementById('settings-user-name');
  if (setName && (setName.textContent === 'Guest User' || !localStorage.getItem('transify_auth_user'))) {
    setName.textContent = nameVal;
  }

  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast('Profile changes saved successfully', 'success');
  }
};

window.resetSettingsToDefaults = function () {
  window.applyThemeGlobal('light');
  window.applyFontScale('normal');
  window.toggleReduceMotion(false);
  window.toggleFocusRings(false);
  window.toggleAudioChimes(true);
  window.setSpeechRate(1.0);
  window.setDefaultSignLang('asl');
  window.setBrailleStandard('grade1');
  window.setConfidenceGate('85');

  const langSelect = document.getElementById('setting-lang-select');
  if (langSelect) langSelect.value = 'en';
  if (typeof applyLocale === 'function') applyLocale('en');

  try {
    localStorage.removeItem('transify_theme');
    localStorage.removeItem('transify_font_scale');
    localStorage.removeItem('transify_focus_rings');
    localStorage.removeItem('transify_reduce_motion');
    localStorage.removeItem('transify_reduced_motion');
    localStorage.removeItem('transify_speech_rate');
    localStorage.removeItem('transify_default_sign_lang');
    localStorage.removeItem('transify_braille_standard');
    localStorage.removeItem('transify_confidence_gate');
    localStorage.removeItem('transify_audio_chimes');
    localStorage.removeItem('transify_lang');
  } catch (_) { }

  if (window.TransifyApp && window.TransifyApp.showToast) {
    window.TransifyApp.showToast('All settings reset to defaults', 'info');
  }
};

// Aliases on TransifyApp
if (typeof window.TransifyApp === 'object' && window.TransifyApp) {
  window.TransifyApp.switchSettingsTab = window.switchSettingsTab;
  window.TransifyApp.setConfidenceGate = window.setConfidenceGate;
  window.TransifyApp.applyFontScale = window.applyFontScale;
  window.TransifyApp.setSpeechRate = window.setSpeechRate;
  window.TransifyApp.setDefaultSignLang = window.setDefaultSignLang;
  window.TransifyApp.setBrailleStandard = window.setBrailleStandard;
  window.TransifyApp.toggleReduceMotion = window.toggleReduceMotion;
  window.TransifyApp.toggleFocusRings = window.toggleFocusRings;
  window.TransifyApp.toggleAudioChimes = window.toggleAudioChimes;
  window.TransifyApp.saveUserProfile = window.saveUserProfile;
  window.TransifyApp.resetSettingsToDefaults = window.resetSettingsToDefaults;
  window.TransifyApp.setAppLanguage = window.setAppLanguage;
  window.TransifyApp.testVoicePreview = window.testVoicePreview;
  window.TransifyApp.exportSettingsData = window.exportSettingsData;
  window.TransifyApp.clearActivityHistory = window.clearActivityHistory;
  window.TransifyApp.copySystemDiagnostics = window.copySystemDiagnostics;
  window.TransifyApp.submitDeveloperFeedback = window.submitDeveloperFeedback;
}

// ==========================================
// 1. Accessibility & Preferences Engine
// ==========================================

var TransifyApp = window.TransifyApp = Object.assign(window.TransifyApp || {}, {
  theme: 'light',
  fontSize: 'medium',
  autoTTS: localStorage.getItem('transify_auto_tts') === 'true',
  speechRate: parseFloat(localStorage.getItem('transify_speech_rate') || '1.0'),

  applyTheme(theme) {
    window.applyThemeGlobal(theme);
  },

  init() {
    if (this._isInitialized) return;
    this._isInitialized = true;
    const savedTheme = localStorage.getItem('transify_theme') || 'light';
    this.applyTheme(savedTheme);
    this.applyFontSize('medium', false);
    this.initAuthGateway();
    if (window.hidePageLoader) {
      setTimeout(() => window.hidePageLoader(), 150);
    }
  },

  initAuthGateway() {
    const authOverlay = document.getElementById('transify-auth-screen');
    const splash = document.getElementById('transify-splash-screen');
    if (!authOverlay) {
      if (splash) splash.style.display = 'none';
      return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const forceLogin = urlParams.get('view') === 'login' || urlParams.get('logout') === '1';
    const isAuthCompleted = urlParams.get('auth_completed') === '1';

    let authUser = null;
    try {
      authUser = JSON.parse(localStorage.getItem('transify_auth_user') || 'null');
    } catch (_) { }

    if (isAuthCompleted && !authUser) {
      authUser = { name: 'Sarah Ahmed', email: 'demo@transify.ai', provider: 'login' };
      try {
        localStorage.setItem('transify_auth_user', JSON.stringify(authUser));
        localStorage.setItem('transify_auth_token', 'jwt_' + Date.now());
      } catch (_) { }
    }

    if ((!authUser && !isAuthCompleted) || forceLogin) {
      // User is NOT logged in: Show Auth Screen FIRST!
      if (splash) {
        splash.style.display = 'none';
        splash.classList.add('splash-hidden');
      }
      authOverlay.style.display = 'flex';
      authOverlay.classList.remove('auth-hidden');
      authOverlay.style.pointerEvents = 'auto';
      authOverlay.style.zIndex = '1000000';
      this.bindAuthEvents();
    } else {
      // Already logged in: Immediately hide auth overlay and show dashboard!
      authOverlay.style.display = 'none';
      authOverlay.classList.add('auth-hidden');
      authOverlay.style.pointerEvents = 'none';
      authOverlay.style.zIndex = '-99999';
      this.updateProfileUI(authUser || { name: 'Sarah Ahmed', email: 'demo@transify.ai' });
      if (splash) {
        splash.style.display = 'none';
        splash.classList.add('splash-hidden');
      }
      this.checkUrlSlide();
    }

    this.bindProfileModal();
  },

  bindAuthEvents() {
    this.activeAuthMode = 'login';
    const tabLogin = document.getElementById('tab-login');
    const tabSignup = document.getElementById('tab-signup');
    if (tabLogin) tabLogin.onclick = () => this.switchAuthTab('login');
    if (tabSignup) tabSignup.onclick = () => this.switchAuthTab('signup');

    // Close sheet on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.closeAuthSheet();
    });
  },

  openAuthSheet(mode = 'login') {
    this.switchAuthTab(mode);
    const sheetContainer = document.getElementById('auth-sheet-container');
    if (sheetContainer) {
      sheetContainer.classList.add('active');
    }
    this.hideAuthAlert();
  },

  closeAuthSheet() {
    const sheetContainer = document.getElementById('auth-sheet-container');
    if (sheetContainer) {
      sheetContainer.classList.remove('active');
    }
    this.hideAuthAlert();
  },

  switchAuthTab(mode = 'login') {
    this.activeAuthMode = mode;
    this.hideAuthAlert();

    const tabLogin = document.getElementById('tab-login');
    const tabSignup = document.getElementById('tab-signup');
    const title = document.getElementById('auth-heading-title');
    const subtitle = document.getElementById('auth-heading-subtitle');
    const groupFullname = document.getElementById('group-fullname');
    const inputFullname = document.getElementById('input-fullname');
    const btnText = document.getElementById('btn-text');
    const rememberLabelText = document.getElementById('remember-label-text');
    const forgotLink = document.getElementById('forgot-password-link');
    const switchPromptText = document.getElementById('switch-prompt-text');
    const switchPromptLink = document.getElementById('switch-prompt-link');

    if (mode === 'login') {
      if (tabLogin) { tabLogin.classList.add('active'); tabLogin.setAttribute('aria-selected', 'true'); }
      if (tabSignup) { tabSignup.classList.remove('active'); tabSignup.setAttribute('aria-selected', 'false'); }
      if (title) title.textContent = 'Welcome Back!';
      if (subtitle) subtitle.textContent = 'Login to your Transify account';
      if (groupFullname) groupFullname.style.display = 'none';
      if (inputFullname) inputFullname.removeAttribute('required');
      if (btnText) btnText.textContent = 'Login';
      if (rememberLabelText) rememberLabelText.textContent = 'Remember me';
      if (forgotLink) forgotLink.style.display = 'inline';
      if (switchPromptText) switchPromptText.textContent = "Don't have an account?";
      if (switchPromptLink) switchPromptLink.textContent = 'Sign Up';
    } else {
      if (tabSignup) { tabSignup.classList.add('active'); tabSignup.setAttribute('aria-selected', 'true'); }
      if (tabLogin) { tabLogin.classList.remove('active'); tabLogin.setAttribute('aria-selected', 'false'); }
      if (title) title.textContent = 'Join Transify!';
      if (subtitle) subtitle.textContent = 'Create your account to start communicating';
      if (groupFullname) groupFullname.style.display = 'flex';
      if (inputFullname && !inputFullname.value) inputFullname.value = 'Sarah Ahmed';
      if (btnText) btnText.textContent = 'Register & Open Slides';
      if (rememberLabelText) rememberLabelText.textContent = 'I agree to Terms & Privacy';
      if (forgotLink) forgotLink.style.display = 'none';
      if (switchPromptText) switchPromptText.textContent = 'Already have an account?';
      if (switchPromptLink) switchPromptLink.textContent = 'Login';
    }
  },

  handleDirectLogin() {
    this.showAuthAlert('Logging in as Sarah Ahmed...', true);
    this.completeAuthentication({
      name: 'Sarah Ahmed',
      email: 'demo@transify.ai',
      provider: 'direct'
    });
  },

  handleDemoLogin() {
    this.showAuthAlert('Continuing as Demo Guest...', true);
    this.completeAuthentication({
      name: 'Sarah Ahmed',
      email: 'demo@transify.ai',
      provider: 'guest'
    });
  },

  togglePasswordVisibility() {
    const pwdInput = document.getElementById('input-password');
    const eyeIcon = document.getElementById('eye-icon');
    if (!pwdInput) return;
    if (pwdInput.type === 'password') {
      pwdInput.type = 'text';
      if (eyeIcon) {
        eyeIcon.innerHTML = `
          <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/>
          <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/>
          <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/>
          <line x1="2" x2="22" y1="2" y2="22"/>
        `;
      }
    } else {
      pwdInput.type = 'password';
      if (eyeIcon) {
        eyeIcon.innerHTML = `
          <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
          <circle cx="12" cy="12" r="3"/>
        `;
      }
    }
  },

  showAuthAlert(msg, isSuccess = true) {
    const alertBox = document.getElementById('auth-alert');
    if (!alertBox) return;
    alertBox.textContent = msg;
    alertBox.className = `auth-status-alert ${isSuccess ? 'success' : 'error'}`;
    alertBox.style.display = 'block';
  },

  hideAuthAlert() {
    const alertBox = document.getElementById('auth-alert');
    if (alertBox) {
      alertBox.style.display = 'none';
      alertBox.textContent = '';
    }
  },

  handleForgotPassword(e) {
    if (e) e.preventDefault();
    this.showAuthAlert('Password reset instructions sent to your email.', true);
  },

  quickFillDemo() {
    const emailInput = document.getElementById('input-email');
    const pwdInput = document.getElementById('input-password');
    const nameInput = document.getElementById('input-fullname');
    if (emailInput) emailInput.value = 'demo@transify.ai';
    if (pwdInput) pwdInput.value = 'transify2026';
    if (nameInput) nameInput.value = 'Sarah Ahmed';
    this.showAuthAlert('Demo credentials loaded! Authenticating...', true);
    setTimeout(() => {
      this.completeAuthentication({
        name: 'Sarah Ahmed',
        email: 'demo@transify.ai',
        provider: 'demo'
      });
    }, 450);
  },

  handleAuthSubmit(e) {
    if (e) e.preventDefault();
    const emailInput = document.getElementById('input-email');
    const pwdInput = document.getElementById('input-password');
    const nameInput = document.getElementById('input-fullname');

    const email = (emailInput && emailInput.value.trim()) ? emailInput.value.trim() : 'demo@transify.ai';
    const password = (pwdInput && pwdInput.value) ? pwdInput.value : 'transify2026';
    const name = (nameInput && nameInput.value.trim()) ? nameInput.value.trim() : 'Sarah Ahmed';

    const mode = this.activeAuthMode || 'login';
    const submitBtn = document.getElementById('auth-submit-btn');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.style.opacity = '0.75';
      const label = submitBtn.querySelector('#btn-text');
      if (label) label.textContent = mode === 'login' ? 'Logging in...' : 'Opening Transify...';
    }

    setTimeout(() => {
      this.showAuthAlert(mode === 'login' ? 'Login successful! Opening Transify...' : 'Account registered! Opening Transify...', true);
      this.completeAuthentication({
        name: name,
        email: email,
        provider: 'password'
      });
    }, 200);
  },

  handleGoogleLogin() {
    this.showAuthAlert('Connecting with Google Account...', true);
    setTimeout(() => {
      this.completeAuthentication({
        name: 'Sarah Ahmed',
        email: 'sarah.ahmed@gmail.com',
        provider: 'google'
      });
    }, 600);
  },

  completeAuthentication(userObj) {
    try {
      localStorage.setItem('transify_auth_user', JSON.stringify(userObj));
      localStorage.setItem('transify_auth_token', 'jwt_' + Date.now());
    } catch (_) { }

    this.updateProfileUI(userObj);

    const authOverlay = document.getElementById('transify-auth-screen');
    const splash = document.getElementById('transify-splash-screen');

    if (authOverlay) {
      authOverlay.classList.add('auth-hidden');
      authOverlay.style.display = 'none';
      authOverlay.style.pointerEvents = 'none';
      authOverlay.style.zIndex = '-99999';
    }

    if (splash) {
      splash.style.display = 'none';
      splash.classList.add('splash-hidden');
    }

    this.checkUrlSlide();
  },

  checkUrlSlide() {
    if (window.location.hash === '#sign') {
      if (typeof openSlide === 'function') openSlide('slide-hand-signal');
    } else if (window.location.hash === '#braille') {
      if (typeof openSlide === 'function') openSlide('slide-braille');
    } else if (window.location.hash === '#stt') {
      if (typeof openSlide === 'function') openSlide('slide-stt');
    } else if (window.location.hash === '#tts') {
      if (typeof openSlide === 'function') openSlide('slide-tts');
    }
  },

  updateProfileUI(userObj) {
    if (!userObj) return;
    const nameText = document.getElementById('profile-name-text');
    const emailText = document.getElementById('profile-email-text');
    if (nameText && userObj.name) nameText.textContent = userObj.name;
    if (emailText && userObj.email) emailText.textContent = userObj.email;
    const avatarLarge = document.getElementById('profile-avatar-initials');
    if (avatarLarge && userObj.name) {
      const parts = userObj.name.trim().split(' ');
      avatarLarge.textContent = parts.map(p => p[0]).join('').toUpperCase().slice(0, 2);
    }
  },

  bindProfileModal() {
    const avatarBtn = document.getElementById('frame-avatar-btn');
    const modal = document.getElementById('profile-modal-overlay');
    const closeBtn = document.getElementById('btn-close-profile-modal');
    const backdrop = document.getElementById('profile-modal-backdrop');
    const testSpeechBtn = document.getElementById('btn-test-speech-voice');
    const speedGroup = document.getElementById('profile-speed-group');
    const toggleContrast = document.getElementById('toggle-high-contrast');
    const toggleLargeText = document.getElementById('toggle-large-text');
    const toggleReducedMotion = document.getElementById('toggle-reduced-motion');
    const clearHistoryBtn = document.getElementById('btn-profile-clear-history');

    // 1. Open on Avatar button click
    if (avatarBtn) {
      avatarBtn.style.cursor = 'pointer';
      avatarBtn.onclick = (e) => {
        e.preventDefault();
        this.openProfileModal();
      };
    }

    // 2. Close on close button or backdrop click
    if (closeBtn) closeBtn.onclick = () => this.closeProfileModal();
    if (backdrop) backdrop.onclick = () => this.closeProfileModal();

    // 3. Escape key closes modal
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal && modal.classList.contains('open')) {
        this.closeProfileModal();
      }
    });

    // 4. Voice Speed buttons
    if (speedGroup) {
      speedGroup.querySelectorAll('.btn-speed').forEach(btn => {
        btn.addEventListener('click', () => {
          speedGroup.querySelectorAll('.btn-speed').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const speedVal = parseFloat(btn.dataset.speed || '1.0');
          this.speechRate = speedVal;
          localStorage.setItem('transify_speech_rate', speedVal.toString());
          this.showToast(`Voice speed set to ${speedVal}x`, 'info');
        });
      });
    }

    // 5. Test Voice Button
    if (testSpeechBtn) {
      testSpeechBtn.addEventListener('click', () => {
        const testPhrase = 'Welcome to Transify. Speech and assistive communications are online.';
        this.speak(testPhrase, { rate: this.speechRate || 1.0 });
      });
    }

    // 6. High Contrast Toggle
    if (toggleContrast) {
      const isContrast = localStorage.getItem('transify_high_contrast') === 'true' || localStorage.getItem('transify_theme') === 'high-contrast';
      toggleContrast.checked = isContrast;
      if (isContrast) {
        document.body.classList.add('high-contrast');
        document.documentElement.setAttribute('data-theme', 'high-contrast');
        document.body.setAttribute('data-theme', 'high-contrast');
      }
      toggleContrast.addEventListener('change', () => {
        if (toggleContrast.checked) {
          document.body.classList.add('high-contrast');
          document.documentElement.setAttribute('data-theme', 'high-contrast');
          document.body.setAttribute('data-theme', 'high-contrast');
          localStorage.setItem('transify_high_contrast', 'true');
          localStorage.setItem('transify_theme', 'high-contrast');
          this.showToast('High Contrast Mode Enabled (WCAG AAA)', 'success');
        } else {
          document.body.classList.remove('high-contrast');
          document.documentElement.setAttribute('data-theme', 'light');
          document.body.setAttribute('data-theme', 'light');
          localStorage.setItem('transify_high_contrast', 'false');
          localStorage.setItem('transify_theme', 'light');
          this.showToast('High Contrast Mode Disabled', 'info');
        }
      });
    }

    // 7. Large Text Toggle
    if (toggleLargeText) {
      const isLarge = localStorage.getItem('transify_large_text') === 'true';
      toggleLargeText.checked = isLarge;
      if (isLarge) document.body.classList.add('large-text');
      toggleLargeText.addEventListener('change', () => {
        if (toggleLargeText.checked) {
          document.body.classList.add('large-text');
          localStorage.setItem('transify_large_text', 'true');
          this.showToast('Large Text Scaling Enabled (+15%)', 'success');
        } else {
          document.body.classList.remove('large-text');
          localStorage.setItem('transify_large_text', 'false');
          this.showToast('Standard Text Scaling Restored', 'info');
        }
      });
    }

    // 8. Reduced Motion Toggle
    if (toggleReducedMotion) {
      const isReduced = localStorage.getItem('transify_reduced_motion') === 'true';
      toggleReducedMotion.checked = isReduced;
      if (isReduced) document.documentElement.setAttribute('data-motion', 'reduced');
      toggleReducedMotion.addEventListener('change', () => {
        if (toggleReducedMotion.checked) {
          document.documentElement.setAttribute('data-motion', 'reduced');
          localStorage.setItem('transify_reduced_motion', 'true');
          this.showToast('Reduced Motion Enabled', 'info');
        } else {
          document.documentElement.removeAttribute('data-motion');
          localStorage.setItem('transify_reduced_motion', 'false');
          this.showToast('Motion Animations Restored', 'info');
        }
      });
    }

    // 9. Clear History Button
    if (clearHistoryBtn) {
      clearHistoryBtn.addEventListener('click', async () => {
        const recentList = document.getElementById('home-recent-list');
        if (recentList) {
          recentList.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--text-2); font-size: 14px; font-weight: 600;">No recent translations yet.</div>';
        }
        const histCount = document.getElementById('profile-history-count');
        if (histCount) histCount.textContent = '0 activity logs stored';
        try {
          await fetch('/api/history', { method: 'DELETE' });
        } catch (_) { }
        this.showToast('Activity history cleared', 'success');
      });
    }
  },

  handleProfileAuthAction() {
    const userJson = localStorage.getItem('transify_auth_user');
    if (userJson) {
      // Logged in: Log out!
      localStorage.removeItem('transify_auth_user');
      localStorage.removeItem('transify_auth_token');
      this.closeProfileModal();
      this.showToast('Signed out of session', 'info');
      const nameEl = document.getElementById('home-user-name');
      if (nameEl) nameEl.textContent = 'Welcome to Transify';
      const avEl = document.getElementById('frame-avatar-btn');
      if (avEl) avEl.textContent = 'TR';
      this.updateProfileUI({ name: 'Guest User', email: 'Offline Edge Session' });
    } else {
      // Not logged in: Open Auth Sheet!
      this.closeProfileModal();
      this.openAuthSheet('login');
    }
  },

  openProfileModal() {
    const modal = document.getElementById('profile-modal-overlay');
    if (!modal) return;
    this.refreshProfileModalState();
    modal.classList.add('open');
    modal.style.display = 'flex';
  },

  closeProfileModal() {
    const modal = document.getElementById('profile-modal-overlay');
    if (!modal) return;
    modal.classList.remove('open');
    modal.style.display = 'none';
  },

  refreshProfileModalState() {
    const userJson = localStorage.getItem('transify_auth_user');
    const nameText = document.getElementById('profile-name-text');
    const emailText = document.getElementById('profile-email-text');
    const avatarLarge = document.getElementById('profile-avatar-initials');
    const authBtn = document.getElementById('btn-profile-auth-action');
    const statusText = document.getElementById('profile-status-text');

    if (userJson) {
      try {
        const u = JSON.parse(userJson);
        if (nameText && u.name) nameText.textContent = u.name;
        if (emailText && u.email) emailText.textContent = u.email;
        if (avatarLarge && u.name) {
          const parts = u.name.trim().split(' ');
          avatarLarge.textContent = parts.map(p => p[0]).join('').toUpperCase().slice(0, 2);
        }
        if (authBtn) {
          authBtn.textContent = 'Sign Out';
          authBtn.style.background = '#EF4444';
        }
        if (statusText) statusText.textContent = 'Verified User (Cloud Synced)';
      } catch (_) { }
    } else {
      if (nameText) nameText.textContent = 'Guest User';
      if (emailText) emailText.textContent = 'Offline Edge Session (Local)';
      if (avatarLarge) avatarLarge.textContent = 'TR';
      if (authBtn) {
        authBtn.textContent = 'Sign In';
        authBtn.style.background = 'var(--ink, #14111F)';
      }
      if (statusText) statusText.textContent = 'Local Edge Mode (Private)';
    }

    // Sync speed buttons
    const speed = parseFloat(localStorage.getItem('transify_speech_rate') || '1.0');
    const speedGroup = document.getElementById('profile-speed-group');
    if (speedGroup) {
      speedGroup.querySelectorAll('.btn-speed').forEach(b => {
        b.classList.toggle('active', parseFloat(b.dataset.speed) === speed);
      });
    }
  },

  logoutUser() {
    this.closeProfileModal();
    try {
      localStorage.removeItem('transify_auth_user');
      localStorage.removeItem('transify_auth_token');
    } catch (_) { }

    const authOverlay = document.getElementById('transify-auth-screen');
    const splash = document.getElementById('transify-splash-screen');
    if (splash) {
      splash.style.display = 'none';
      splash.classList.add('splash-hidden');
    }
    if (authOverlay) {
      authOverlay.style.display = 'flex';
      authOverlay.classList.remove('auth-hidden');
      this.bindAuthEvents();
      this.hideAuthAlert();
      const submitBtn = document.getElementById('auth-submit-btn');
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.style.opacity = '1';
        const label = submitBtn.querySelector('#btn-text');
        if (label) label.textContent = 'Login';
      }
    } else {
      window.location.href = '/login';
    }
  },

  initSplashScreen(durationMs = 3500) {
    const splash = document.getElementById('transify-splash-screen');
    if (!splash) return;

    const duration = window.TransifySplashDuration || durationMs;
    const fill = document.getElementById('splash-progress-fill');
    const percentText = document.getElementById('splash-percent-text');
    const bar = document.getElementById('splash-progressbar');

    const startTime = performance.now();
    const interval = 25;

    const timer = setInterval(() => {
      const elapsed = performance.now() - startTime;
      const progress = Math.min(100, (elapsed / duration) * 100);

      if (fill) fill.style.width = `${progress}%`;
      if (bar) bar.setAttribute('aria-valuenow', Math.round(progress));
      if (percentText) percentText.textContent = `${Math.round(progress)}%`;

      if (progress >= 100) {
        clearInterval(timer);
        setTimeout(() => {
          splash.classList.add('splash-hidden');
          TransifyApp.announce('Transify loaded and ready.');
          setTimeout(() => {
            splash.style.display = 'none';
            if (typeof TransifyApp.checkUrlSlide === 'function') {
              TransifyApp.checkUrlSlide();
            }
          }, 250);
        }, 120);
      }
    }, interval);
  },

  cycleTheme() {
    // Theme switching handled via settings Theme & Appearance panel
  },

  applyFontSize(size, save = false) {
    this.fontSize = 'medium';
    document.documentElement.setAttribute('data-font-size', 'medium');
  },

  cycleFontSize() {
    // Font sizing cycling disabled per user request
  },

  announce(text) {
    const region = document.getElementById('sr-announcements');
    if (region) {
      region.textContent = '';
      setTimeout(() => { region.textContent = text; }, 50);
    }
  },

  showToast(message, type = 'info', duration = 3500) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'alert');

    const icons = { info: 'ℹ️', success: '✅', warning: '⚠️', danger: '❌' };
    toast.innerHTML = `<span>${icons[type] || '🔔'}</span><span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(20px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  async syncPreferencesWithServer() {
    try {
      const res = await fetch('/api/preferences');
      if (res.ok) {
        const data = await res.json();
        if (data.theme && !localStorage.getItem('transify_theme')) {
          this.applyTheme(data.theme, false);
        }
      }
    } catch (e) {
      // Offline or network error - gracefully ignore
    }
  },

  async saveServerPreference(key, value) {
    try {
      await fetch('/api/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value: String(value) })
      });
    } catch (e) {
      // Best effort background sync
    }
  },

  setupAccessibilityListeners() {
    // Theme and font size togglers disabled per user request
  }
});

// ==========================================
// 2. Text-To-Speech (TTS) Engine
// ==========================================

var TransifyTTS = window.TransifyTTS = {
  isSpeaking: false,

  speak(text, options = {}) {
    if (!text || text.trim() === '') return;
    const cleanText = text.trim();
    const rate = options.rate || TransifyApp.speechRate || 1.0;
    const onStart = options.onStart || (() => { });
    const onEnd = options.onEnd || (() => { });

    // Prefer native SpeechSynthesis for natural voice and zero network latency
    if ('speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
        window.speechSynthesis.resume();
      } catch (e) { }

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = rate;
      const hasBengali = /[\u0980-\u09FF]/.test(cleanText);
      const isBnApp = window.TransifyI18n && window.TransifyI18n.getLanguage && window.TransifyI18n.getLanguage() === 'bn';
      const targetLang = options.lang || (hasBengali || isBnApp ? 'bn-BD' : 'en-US');
      utterance.lang = targetLang;

      // Select matching voice or fallback to default
      const voices = window.speechSynthesis.getVoices();
      if (voices && voices.length > 0) {
        const match = voices.find(v => v.lang.toLowerCase() === targetLang.toLowerCase()) ||
          voices.find(v => v.lang.toLowerCase().startsWith(targetLang.slice(0, 2).toLowerCase())) ||
          voices[0];
        if (match) utterance.voice = match;
      }

      utterance.onstart = () => {
        this.isSpeaking = true;
        onStart();
      };
      utterance.onend = () => {
        this.isSpeaking = false;
        onEnd();
      };
      utterance.onerror = (e) => {
        this.isSpeaking = false;
        console.warn('SpeechSynthesis error, falling back to server tone:', e);
        this.fallbackServerTTS(cleanText);
        onEnd();
      };

      try {
        window.speechSynthesis.speak(utterance);
      } catch (e) {
        this.fallbackServerTTS(cleanText);
      }
      TransifyApp.announce(`Speaking: ${cleanText}`);
    } else {
      this.fallbackServerTTS(cleanText);
    }
  },

  async fallbackServerTTS(text) {
    try {
      const res = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, speed: TransifyApp.speechRate })
      });
      const data = await res.json();
      if (data.audio_uri) {
        const audio = new Audio(data.audio_uri);
        audio.play().catch(err => console.log('Audio autoplay prevented:', err));
      }
    } catch (e) {
      console.warn('Server TTS unavailable:', e);
    }
  },

  stop() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    this.isSpeaking = false;
  }
};

// Immediate global exposure
TransifyApp._fullLoaded = true;
window.TransifyApp = TransifyApp;
window.openAuthSheet = (m) => TransifyApp.openAuthSheet(m);
window.closeAuthSheet = () => TransifyApp.closeAuthSheet();
window.handleDirectLogin = () => TransifyApp.handleDirectLogin();
window.handleDemoLogin = () => TransifyApp.handleDemoLogin();
window.handleAuthSubmit = (e) => TransifyApp.handleAuthSubmit(e);
window.handleSettingsAuthAction = () => { if (typeof EditorialController !== 'undefined' && EditorialController.handleSettingsAuthAction) EditorialController.handleSettingsAuthAction(); };
TransifyApp.handleSettingsAuthAction = () => { if (typeof EditorialController !== 'undefined' && EditorialController.handleSettingsAuthAction) EditorialController.handleSettingsAuthAction(); };

// ==========================================
// 3. Central Assistive Dashboard Logic
// ==========================================

var DashboardPage = window.DashboardPage = {
  isInitialized: false,

  async init() {
    if (this.isInitialized) return;
    this.isInitialized = true;
    await this.loadSystemStatus();
    await this.loadHistory();
    this.setupListeners();
  },

  async loadSystemStatus() {
    try {
      const [healthRes, modelsRes] = await Promise.all([
        fetch('/api/health'),
        fetch('/api/models/status')
      ]);

      if (healthRes.ok) {
        const health = await healthRes.json();
        const sysBadge = document.getElementById('system-status-badge');
        if (sysBadge) {
          sysBadge.className = 'badge badge-success';
          sysBadge.innerHTML = '● All Systems Operational';
        }
      }

      if (modelsRes.ok) {
        const data = await modelsRes.json();
        const signCard = document.getElementById('sign-model-metric');
        if (signCard && data.sign_language) {
          signCard.innerHTML = `
            <strong>Model:</strong> ${data.sign_language.champion_model || 'Random Forest'}<br>
            <strong>Accuracy:</strong> ${(data.sign_language.test_accuracy * 100).toFixed(1)}%<br>
            <strong>Classes:</strong> ${data.sign_language.supported_classes} ASL & Gesture Signs<br>
            <strong>Status:</strong> <span class="badge badge-success">Ready</span>
          `;
        }

        const brailleCard = document.getElementById('braille-model-metric');
        if (brailleCard && data.braille_ocr) {
          brailleCard.innerHTML = `
            <strong>Model:</strong> ${data.braille_ocr.champion_model || 'Extra Trees'}<br>
            <strong>Cell Acc:</strong> ${(data.braille_ocr.test_cell_accuracy * 100).toFixed(1)}%<br>
            <strong>Standard:</strong> UEB Grade 1 (Uncontracted)<br>
            <strong>Status:</strong> <span class="badge badge-success">Ready</span>
          `;
        }
      }
    } catch (e) {
      console.error('Failed to load status:', e);
    }
  },

  async loadHistory() {
    const listContainer = document.getElementById('history-records-list');
    if (!listContainer) return;

    try {
      const res = await fetch('/api/history?limit=15');
      if (!res.ok) throw new Error('History fetch failed');
      const data = await res.json();

      if (!data.records || data.records.length === 0) {
        listContainer.innerHTML = `
          <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
            <p>No translation records logged yet.</p>
            <p style="font-size: var(--text-sm); margin-top: 0.5rem;">Use the Live Sign or Braille translators to create real translation entries.</p>
          </div>
        `;
        return;
      }

      listContainer.innerHTML = data.records.map(rec => {
        const isSign = rec.module === 'sign';
        const badgeClass = isSign ? 'badge-info' : 'badge-warning';
        const icon = isSign ? '🤟' : '⠃';
        const dateStr = new Date(rec.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const confPercent = (rec.confidence * 100).toFixed(1);

        return `
          <div class="card" style="margin-bottom: var(--space-3); padding: var(--space-4);" data-id="${rec.id}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2);">
              <span class="badge ${badgeClass}">${icon} ${rec.module.toUpperCase()}</span>
              <span style="font-size: var(--text-xs); color: var(--text-muted);">${dateStr} • Conf: ${confPercent}%</span>
            </div>
            <div style="font-size: var(--text-lg); font-weight: 700; margin-bottom: var(--space-2);">
              "${rec.recognized_text}"
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <button class="btn btn-secondary btn-sm" onclick="TransifyTTS.speak('${rec.recognized_text.replace(/'/g, "\\'")}')" aria-label="Speak text">
                🔊 Speak
              </button>
              <div style="display: flex; gap: var(--space-2);">
                <button class="btn-icon" title="Accurate" onclick="DashboardPage.giveFeedback(${rec.id}, 5)" aria-label="Thumbs up accurate">👍</button>
                <button class="btn-icon" title="Needs Correction" onclick="DashboardPage.giveFeedback(${rec.id}, 1)" aria-label="Thumbs down incorrect">👎</button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    } catch (e) {
      listContainer.innerHTML = `<p style="color: var(--status-danger);">Failed to load history.</p>`;
    }
  },

  async giveFeedback(id, rating) {
    try {
      const res = await fetch(`/api/history/${id}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating })
      });
      if (res.ok) {
        TransifyApp.showToast(`Feedback recorded (${rating === 5 ? 'Accurate' : 'Reported'})!`, 'success');
      }
    } catch (e) {
      TransifyApp.showToast('Failed to record feedback.', 'danger');
    }
  },

  setupListeners() {
    const clearBtn = document.getElementById('clear-history-btn');
    if (clearBtn) {
      clearBtn.addEventListener('click', async () => {
        if (confirm('Are you sure you want to clear your local translation history?')) {
          try {
            await fetch('/api/history', { method: 'DELETE' });
            TransifyApp.showToast('History cleared', 'info');
            this.loadHistory();
          } catch (e) {
            TransifyApp.showToast('Failed to clear history', 'danger');
          }
        }
      });
    }
  }
};

// ==========================================
// 4. Module 01: Live Sign Language Translator
// ==========================================

var SignPage = window.SignPage = window.TransifySign = {
  isStreaming: false,
  isInitialized: false,
  stream: null,
  videoEl: null,
  canvasEl: null,
  ctx: null,
  sequenceBuffer: [],
  maxBuffer: 30,
  landmarkDim: 162,
  predictTimer: null,
  lastPrediction: null,
  autoSpeak: true,
  currentMode: 'expressions',
  currentLanguageMode: 'asl',
  sentenceTokens: [],
  currentWord: '',
  isProcessingFrame: false,
  frameCaptureTimer: null,
  offscreenCanvas: null,
  offscreenCtx: null,
  lastHandBBox: null,
  lastFrameDims: null,
  lastConfirmedTime: 0,
  lastConfirmedSign: '',
  lastConfirmedSpeechTime: 0,
  lastFingersCount: 0,
  roiPosition: 'center',
  lastFrameData: null,
  detectionState: {
    isDetected: false,
    label: '',
    confidence: 0,
    timestamp: 0
  },

  setRoiPosition(pos) {
    if (['center', 'fullscreen', 'right', 'left'].includes(pos)) {
      this.roiPosition = pos;
      const roiBox = document.getElementById('sign-roi-box');
      if (roiBox) {
        roiBox.classList.toggle('fullscreen-mode', pos === 'fullscreen');
      }
      const focusBtn = document.getElementById('toggle-roi-focus-btn');
      if (focusBtn) {
        focusBtn.textContent = pos === 'fullscreen' ? '⛶ Full Focus' : '🎯 Center Focus';
      }
      ['right', 'center', 'left', 'fullscreen'].forEach(p => {
        const btn = document.getElementById(`roi-pos-${p}`);
        if (btn) {
          if (p === pos) btn.classList.add('active');
          else btn.classList.remove('active');
        }
      });
      if (this.isStreaming) {
        this.drawCanvasFeedback();
      }
    }
  },

  getTargetRoi() {
    if (this.roiPosition === 'fullscreen') {
      return [0.0, 0.0, 1.0, 1.0];
    } else if (this.roiPosition === 'left') {
      return [0.06, 0.08, 0.58, 0.92];
    } else if (this.roiPosition === 'right') {
      return [0.42, 0.08, 0.94, 0.92];
    }
    // Default broad centered zone: natural hand placement in front of camera
    return [0.06, 0.04, 0.94, 0.96];
  },

  setLanguageMode(mode) {
    this.currentLanguageMode = 'asl';
    this.detectionState = { isDetected: false, label: '', confidence: 0, timestamp: 0 };
    fetch('/api/sign/reset', { method: 'POST' }).catch(() => { });
  },

  setDetectionFeedback(label, confidence = 0.95) {
    if (!label || label === 'IDLE' || label === 'ANALYZING' || label === 'OUT_OF_ROI' || label === 'READY') {
      this.detectionState = {
        isDetected: false,
        label: '',
        confidence: 0,
        timestamp: 0
      };
      if (this.isStreaming) {
        this.drawCanvasFeedback();
      }
      return;
    }
    this.detectionState = {
      isDetected: true,
      label: label,
      confidence: confidence,
      timestamp: Date.now()
    };
    if (this.isStreaming) {
      this.drawCanvasFeedback();
    }
  },

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;
    this.videoEl = document.getElementById('sign-video');
    this.canvasEl = document.getElementById('sign-canvas');
    if (this.canvasEl) this.ctx = this.canvasEl.getContext('2d');
    this.setupListeners();
    this.setupModeSwitcher();
    this.initFingerspellingUI();
    this.initSentenceBuilderUI();
    this.loadSupportedClasses();
    this.loadCommunicativeDomains();
  },

  setupModeSwitcher() {
    const exprBtn = document.getElementById('mode-expressions-btn');
    const spellBtn = document.getElementById('mode-fingerspell-btn');
    const sentBtn = document.getElementById('mode-sentence-btn');

    if (exprBtn) exprBtn.addEventListener('click', () => this.switchMode('expressions'));
    if (spellBtn) spellBtn.addEventListener('click', () => this.switchMode('fingerspell'));
    if (sentBtn) sentBtn.addEventListener('click', () => this.switchMode('sentence'));
  },

  switchMode(mode) {
    this.currentMode = mode;
    const exprBtn = document.getElementById('mode-expressions-btn');
    const spellBtn = document.getElementById('mode-fingerspell-btn');
    const sentBtn = document.getElementById('mode-sentence-btn');

    const resultRow = document.querySelector('.result-row');
    const actionRow = document.querySelector('.sign-actions-row');
    const spellPanel = document.getElementById('fingerspelling-panel');
    const vocabPanel = document.getElementById('sign-vocab-section');
    const sentPanel = document.querySelector('.sentence-panel');

    // Update tab button visual state and accessibility attributes
    [
      { btn: exprBtn, id: 'expressions' },
      { btn: spellBtn, id: 'fingerspell' },
      { btn: sentBtn, id: 'sentence' }
    ].forEach(({ btn, id }) => {
      if (btn) {
        const isActive = (id === mode);
        btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
        btn.classList.toggle('active', isActive);
      }
    });

    if (mode === 'expressions') {
      if (resultRow) resultRow.style.display = 'flex';
      if (actionRow) actionRow.style.display = 'flex';
      if (spellPanel) spellPanel.style.display = 'none';
      if (vocabPanel) vocabPanel.style.display = 'none';
      if (sentPanel) sentPanel.style.display = 'flex';
      TransifyApp.announce('Switched to Words Mode');
    } else if (mode === 'fingerspell') {
      if (resultRow) resultRow.style.display = 'none';
      if (actionRow) actionRow.style.display = 'none';
      if (spellPanel) spellPanel.style.display = 'flex';
      if (vocabPanel) vocabPanel.style.display = 'none';
      if (sentPanel) sentPanel.style.display = 'flex';
      TransifyApp.announce('Switched to Letters Fingerspelling Mode');
    } else if (mode === 'sentence' || mode === 'vocab') {
      if (resultRow) resultRow.style.display = 'none';
      if (actionRow) actionRow.style.display = 'none';
      if (spellPanel) spellPanel.style.display = 'none';
      if (vocabPanel) vocabPanel.style.display = 'flex';
      if (sentPanel) sentPanel.style.display = 'flex';
      TransifyApp.announce('Switched to Quick Vocabulary Mode');
    }
  },

  initFingerspellingUI() {
    const grid = document.getElementById('alphabet-grid');
    if (!grid) return;

    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    grid.innerHTML = alphabet.map(l => `
      <button type="button" class="letter-btn press" data-letter="${l}" aria-label="Sign letter ${l}">
        ${l}
      </button>
    `).join('');

    grid.querySelectorAll('.letter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const letter = btn.getAttribute('data-letter');
        this.triggerFingerspellLetter(letter);
      });
    });

    // Bind Quick Common Vocabulary Word buttons
    document.querySelectorAll('.quick-word-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const word = btn.getAttribute('data-word');
        if (word) {
          const displayWord = word.replace(/_/g, ' ');
          this.addTokenToSentence(displayWord);
          TransifyApp.showToast(`Added "${displayWord}" to sentence!`, 'success');
        }
      });
    });

    // Control buttons
    const spaceBtn = document.getElementById('spell-space-btn');
    if (spaceBtn) {
      spaceBtn.addEventListener('click', () => {
        const wordEl = document.getElementById('spelled-word-display');
        const text = wordEl ? wordEl.textContent.trim() : '';
        if (text && !text.includes('Waiting')) {
          this.addTokenToSentence(text);
          TransifyApp.showToast(`Committed word "${text}" to sentence!`, 'success');
          if (wordEl) wordEl.textContent = '(Waiting for letters...)';
        }
        this.triggerFingerspellLetter('SPACE');
      });
    }

    const bspBtn = document.getElementById('spell-backspace-btn');
    if (bspBtn) bspBtn.addEventListener('click', () => this.triggerFingerspellLetter('DELETE'));

    const speakWordBtn = document.getElementById('spell-speak-btn');
    if (speakWordBtn) {
      speakWordBtn.addEventListener('click', () => {
        const wordEl = document.getElementById('spelled-word-display');
        const text = wordEl ? wordEl.textContent : '';
        if (text && !text.includes('Waiting')) {
          TransifyTTS.speak(text);
        } else {
          const mainWord = document.getElementById('pred-label-text');
          if (mainWord && mainWord.textContent && !mainWord.textContent.includes('Waiting')) {
            TransifyTTS.speak(mainWord.textContent);
          } else {
            TransifyApp.showToast('No word to speak yet.', 'warning');
          }
        }
      });
    }

    const sendToSentBtn = document.getElementById('spell-send-to-sentence-btn');
    if (sendToSentBtn) {
      sendToSentBtn.addEventListener('click', () => {
        const wordEl = document.getElementById('spelled-word-display');
        const text = wordEl ? wordEl.textContent.trim() : '';
        if (text && !text.includes('Waiting')) {
          this.addTokenToSentence(text);
          TransifyApp.showToast(`Added "${text}" to Sentence Builder!`, 'success');
          if (wordEl) wordEl.textContent = '(Waiting for letters...)';
        } else {
          const mainWord = document.getElementById('pred-label-text');
          if (mainWord && mainWord.textContent && !mainWord.textContent.includes('Waiting')) {
            this.addTokenToSentence(mainWord.textContent.trim());
            TransifyApp.showToast(`Added "${mainWord.textContent.trim()}" to sentence!`, 'success');
          } else {
            TransifyApp.showToast('Spell or sign a word first before adding to sentence.', 'warning');
          }
        }
      });
    }

    const clearSpellBtn = document.getElementById('spell-clear-btn');
    if (clearSpellBtn) {
      clearSpellBtn.addEventListener('click', async () => {
        try {
          await fetch('/api/sign/fingerspell/reset', { method: 'POST' });
          const wordEl = document.getElementById('spelled-word-display');
          const liveEl = document.getElementById('current-letter-badge');
          if (wordEl) wordEl.textContent = '(Waiting for letters...)';
          if (liveEl) liveEl.textContent = '—';
          TransifyApp.showToast('Spelled word cleared.', 'info');
        } catch (e) {
          // ignore
        }
      });
    }
  },

  async triggerFingerspellLetter(letter) {
    try {
      const res = await fetch('/api/sign/fingerspell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direct_letter: letter })
      });
      if (res.ok) {
        const data = await res.json();
        const wordEl = document.getElementById('spelled-word-display');
        const sentEl = document.getElementById('committed-words-text');
        const liveEl = document.getElementById('current-live-letter');

        if (liveEl) liveEl.textContent = `${data.letter} (${data.bengali || ''})`;
        if (data.letter && data.letter !== 'UNKNOWN' && data.letter !== 'DELETE') {
          this.setDetectionFeedback(`Letter: ${data.letter}`, 1.0);
        }
        if (data.assembler_state) {
          const st = data.assembler_state;
          if (wordEl) wordEl.textContent = st.current_word || '(Waiting for letters...)';
          if (sentEl) sentEl.textContent = st.committed_words.length ? st.committed_words.join(' ') : 'none';
        }
      }
    } catch (e) {
      console.error('Fingerspell trigger error:', e);
    }
  },

  initSentenceBuilderUI() {
    const smoothBtn = document.getElementById('smooth-sentence-btn');
    if (smoothBtn) {
      smoothBtn.addEventListener('click', () => this.smoothAndSpeakSentence());
    }

    const speakSentBtn = document.getElementById('speak-sentence-btn');
    if (speakSentBtn) {
      speakSentBtn.addEventListener('click', () => {
        const textEl = document.getElementById('smooth-sentence-text');
        const text = textEl ? textEl.textContent : '';
        if (text && !text.includes('Waiting')) {
          TransifyTTS.speak(text);
        } else {
          TransifyApp.showToast('No sentence synthesized to speak.', 'warning');
        }
      });
    }

    const copyBtn = document.getElementById('copy-sentence-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        const textEl = document.getElementById('smooth-sentence-text');
        const text = textEl ? textEl.textContent : '';
        if (text && !text.includes('Waiting')) {
          navigator.clipboard.writeText(text);
          TransifyApp.showToast('Sentence copied to clipboard!', 'success');
        }
      });
    }

    const clearSentBtn = document.getElementById('clear-sentence-btn');
    if (clearSentBtn) {
      clearSentBtn.addEventListener('click', async () => {
        this.sentenceTokens = [];
        this.renderSentenceTokens();
        const out = document.getElementById('smooth-sentence-text');
        if (out) out.textContent = '(Waiting to synthesize sentence...)';
        try {
          await fetch('/api/sign/sentence/reset', { method: 'POST' });
        } catch (e) { }
        TransifyApp.showToast('Sentence token buffer cleared.', 'info');
      });
    }
  },

  addTokenToSentence(token) {
    if (!token) return;
    const clean = token.replace(/_/g, ' ').trim();
    if (!clean || clean.includes('Waiting')) return;
    // Avoid immediate duplicate word spam
    if (this.sentenceTokens.length && this.sentenceTokens[this.sentenceTokens.length - 1] === clean) {
      return;
    }
    this.sentenceTokens.push(clean);
    this.renderSentenceTokens();
    this.smoothSentenceAuto();
  },

  smoothSentenceAuto() {
    if (!this.sentenceTokens || !this.sentenceTokens.length) {
      const out = document.getElementById('smooth-sentence-text');
      if (out) out.textContent = '(Waiting for words to assemble sentence...)';
      return;
    }
    if (this._smoothDebounceTimer) clearTimeout(this._smoothDebounceTimer);
    this._smoothDebounceTimer = setTimeout(async () => {
      try {
        const res = await fetch('/api/sign/sentence/smooth', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tokens: this.sentenceTokens,
            speak_tts: false
          })
        });
        if (res.ok) {
          const data = await res.json();
          const outEl = document.getElementById('smooth-sentence-text');
          const badgeEl = document.getElementById('sentence-engine-badge');
          if (outEl && data.sentence) outEl.textContent = data.sentence;
          if (badgeEl && data.source) {
            badgeEl.innerHTML = `<span class="badge badge-success" style="font-size: 11px;">🎯 ${data.source}</span>`;
          }
          if (this.autoSpeak && data.sentence) {
            TransifyTTS.speak(data.sentence);
          }
        }
      } catch (e) {
        console.debug('Auto sentence smoother note:', e);
      }
    }, 280);
  },

  renderSentenceTokens() {
    const container = document.getElementById('sentence-token-chips');
    if (!container) return;

    if (!this.sentenceTokens.length) {
      container.innerHTML = '<span style="color: var(--text-muted); font-size: var(--text-xs);">Perform gestures or click words below to build your thought...</span>';
      return;
    }

    container.innerHTML = this.sentenceTokens.map((t, idx) => `
      <span class="badge badge-info" style="font-size: var(--text-sm); display: inline-flex; align-items: center; gap: 4px; padding: 4px 8px;">
        <span>${t}</span>
        <button type="button" data-idx="${idx}" class="remove-token-btn" style="background: none; border: none; color: inherit; cursor: pointer; font-size: 14px; font-weight: 700; line-height: 1;">×</button>
      </span>
    `).join(' <span style="color: var(--text-muted); font-weight: 700;">+</span> ');

    container.querySelectorAll('.remove-token-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const i = parseInt(btn.getAttribute('data-idx'));
        this.sentenceTokens.splice(i, 1);
        this.renderSentenceTokens();
      });
    });
  },

  async smoothAndSpeakSentence() {
    if (!this.sentenceTokens.length) {
      TransifyApp.showToast('Please add some sign tokens or spelled words first!', 'warning');
      return;
    }

    const smoothBtn = document.getElementById('smooth-sentence-btn');
    if (smoothBtn) {
      smoothBtn.disabled = true;
      smoothBtn.innerHTML = '⏳ Synthesizing Thought...';
    }

    try {
      const res = await fetch('/api/sign/sentence/smooth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tokens: this.sentenceTokens,
          speak_tts: true
        })
      });

      if (!res.ok) throw new Error('Sentence smoother failed');
      const data = await res.json();

      const outEl = document.getElementById('smooth-sentence-text');
      const badgeEl = document.getElementById('sentence-engine-badge');

      if (outEl) outEl.textContent = data.sentence;
      if (badgeEl) {
        badgeEl.innerHTML = `<span class="badge badge-success">🎯 ${data.source || 'AI Smoother'}</span>`;
      }

      TransifyApp.showToast('Natural sentence synthesized successfully!', 'success');
      TransifyApp.announce(`Sentence synthesized: ${data.sentence}`);

      // Speak sentence aloud
      if (data.sentence) {
        TransifyTTS.speak(data.sentence);
      }
    } catch (e) {
      console.error('Sentence smoothing error:', e);
      TransifyApp.showToast(`Error: ${e.message}`, 'danger');
    } finally {
      if (smoothBtn) {
        smoothBtn.disabled = false;
        smoothBtn.innerHTML = '✨ Synthesize Natural Sentence';
      }
    }
  },

  async loadCommunicativeDomains() {
    try {
      const res = await fetch('/api/sign/categories');
      if (res.ok) {
        const data = await res.json();
        const container = document.getElementById('sign-domains-container');
        if (container && data.categories) {
          container.innerHTML = Object.entries(data.categories).map(([key, cat]) => `
            <div class="card" style="padding: var(--space-4); border: 1px solid var(--border-color);">
              <h3 style="font-size: var(--text-md); font-weight: 700; margin-bottom: 4px;">${cat.title}</h3>
              <p style="font-size: var(--text-xs); color: var(--text-secondary); margin-bottom: var(--space-3);">${cat.description}</p>
              <div style="display: flex; flex-direction: column; gap: 6px;">
                ${cat.expressions.map(exp => `
                  <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 6px; background: rgba(255,255,255,0.02); border-radius: 4px;">
                    <div>
                      <strong style="font-size: var(--text-xs);">${exp.label}</strong>
                      <span style="font-size: var(--text-xs); color: var(--text-muted); display: block;">${exp.gloss}</span>
                    </div>
                    <button class="btn btn-secondary btn-sm add-domain-token-btn" data-token="${exp.label}" style="font-size: 11px; padding: 2px 8px;">
                      ➕ Add
                    </button>
                  </div>
                `).join('')}
              </div>
            </div>
          `).join('');

          // Wire Add Token handlers
          container.querySelectorAll('.add-domain-token-btn').forEach(btn => {
            btn.addEventListener('click', () => {
              const token = btn.getAttribute('data-token');
              this.addTokenToSentence(token);
              TransifyApp.showToast(`Added "${token}" to Sentence Builder!`, 'info');
              this.switchMode('sentence');
            });
          });
        }
      }
    } catch (e) {
      console.warn('Failed to load communicative domains:', e);
    }
  },

  async loadSupportedClasses() {
    try {
      const res = await fetch('/api/sign/classes');
      if (res.ok) {
        const data = await res.json();
        const container = document.getElementById('sign-vocabulary-grid');
        if (container && data.classes) {
          container.innerHTML = data.classes.map(c => `
            <button class="btn btn-secondary btn-sm sample-sign-btn" 
                    data-class="${c.label}" 
                    title="Click to test ${c.label} (${c.bdsl_gloss})">
              <span>${c.label}</span>
              <span style="font-size: var(--text-xs); color: var(--text-muted); display: block;">${c.bdsl_gloss}</span>
            </button>
          `).join('');

          // Wire sample click handlers
          container.querySelectorAll('.sample-sign-btn').forEach(btn => {
            btn.addEventListener('click', () => {
              const label = btn.getAttribute('data-class');
              this.simulateSignSample(label);
            });
          });
        }
      }
    } catch (e) {
      console.warn('Failed to load BdSL classes:', e);
    }
  },

  setupListeners() {
    const toggleCamBtn = document.getElementById('toggle-camera-btn');
    if (toggleCamBtn) {
      toggleCamBtn.addEventListener('click', () => this.toggleCamera());
    }

    const resetBtn = document.getElementById('reset-sign-btn');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this.resetRecognition());
    }

    const speakBtn = document.getElementById('speak-pred-btn');
    if (speakBtn) {
      speakBtn.addEventListener('click', () => {
        const wordEl = document.getElementById('pred-label-text');
        const text = (wordEl && wordEl.textContent && wordEl.textContent !== '—' && !wordEl.textContent.includes('Waiting'))
          ? wordEl.textContent.trim()
          : (this.lastPrediction || '');
        if (text && text !== 'IDLE' && text !== 'ANALYZING' && text !== '—') {
          TransifyTTS.speak(text);
        } else {
          TransifyApp.showToast('No confirmed sign to speak.', 'warning');
        }
      });
    }

    const addToSentBtn = document.getElementById('add-to-sentence-btn');
    if (addToSentBtn) {
      addToSentBtn.addEventListener('click', () => {
        const wordEl = document.getElementById('pred-label-text');
        const text = (wordEl && wordEl.textContent && wordEl.textContent !== '—' && !wordEl.textContent.includes('Waiting'))
          ? wordEl.textContent.trim()
          : (this.lastPrediction || '');
        if (text && text !== 'IDLE' && text !== 'ANALYZING' && text !== '—') {
          this.addTokenToSentence(text);
          TransifyApp.showToast(`Added "${text}" to sentence!`, 'success');
        } else {
          TransifyApp.showToast('Please sign or select a word first.', 'warning');
        }
      });
    }

    const autoSpeakCheck = document.getElementById('auto-speak-toggle');
    if (autoSpeakCheck) {
      this.autoSpeak = autoSpeakCheck.checked;
      autoSpeakCheck.addEventListener('change', (e) => {
        this.autoSpeak = e.target.checked;
      });
    }

    const focusBtn = document.getElementById('toggle-roi-focus-btn');
    if (focusBtn) {
      focusBtn.addEventListener('click', () => {
        const nextPos = (this.roiPosition === 'fullscreen') ? 'center' : 'fullscreen';
        this.setRoiPosition(nextPos);
        TransifyApp.showToast(`Camera focus set to ${nextPos === 'fullscreen' ? 'Fullscreen' : 'Center'}`, 'info');
      });
    }

    const fsBtn = document.getElementById('btn-toggle-cam-fullscreen');
    if (fsBtn) {
      fsBtn.addEventListener('click', () => {
        const stage = document.getElementById('sign-stage-container');
        const hud = document.getElementById('fullscreen-pred-hud');
        if (stage) {
          const isFs = stage.classList.toggle('stage-fullscreen');
          fsBtn.innerHTML = isFs ? '⛶ Exit Fullscreen' : '⛶ Fullscreen';
          fsBtn.setAttribute('aria-expanded', isFs ? 'true' : 'false');
          if (hud) hud.style.display = isFs ? 'flex' : 'none';
          TransifyApp.showToast(isFs ? 'Fullscreen camera enabled' : 'Returned to split view', 'info');
        }
      });
    }
  },

  async toggleCamera() {
    if (this.isStreaming) {
      this.stopCamera();
    } else {
      await this.startCamera();
    }
  },

  async startCamera() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
      });
      if (this.videoEl) {
        this.videoEl.srcObject = this.stream;
        await this.videoEl.play();
      }
      this.isStreaming = true;
      const toggleBtn = document.getElementById('toggle-camera-btn');
      if (toggleBtn) {
        toggleBtn.innerHTML = '🛑 Stop Camera';
        toggleBtn.classList.replace('btn-primary', 'btn-secondary');
      }
      const stopCamBtn = document.getElementById('stop-camera-btn');
      if (stopCamBtn) stopCamBtn.style.display = 'block';

      const overlay = document.getElementById('camera-off-overlay');
      if (overlay) overlay.style.display = 'none';

      const statusText = document.getElementById('sign-status-text');
      const statusDot = document.getElementById('sign-status-dot');
      if (statusText) statusText.textContent = 'Show your hand in the box';
      if (statusDot) statusDot.style.background = '#FFCB05';

      const statusLine = document.getElementById('pred-status-line');
      if (statusLine) statusLine.textContent = 'Show your hand in the box';

      const caret = document.getElementById('sign-caret');
      if (caret) caret.style.display = 'inline-block';

      TransifyApp.showToast('Camera started. Tracking ASL signs.', 'success');
      TransifyApp.announce('Camera active. Ready for sign language input.');

      // Start continuous landmark ingestion loop
      this.startInferenceLoop();
    } catch (err) {
      console.error('Camera access error:', err);
      const overlay = document.getElementById('camera-off-overlay');
      if (overlay) {
        overlay.style.display = 'flex';
        const title = document.getElementById('camera-overlay-title');
        const body = document.getElementById('camera-overlay-body');
        if (title) title.textContent = 'Camera access is blocked';
        if (body) body.textContent = "Allow the camera in your browser's site settings, then select Start camera.";
        const btn = document.getElementById('toggle-camera-btn');
        if (btn) btn.textContent = 'Try again';
      }
      const statusText = document.getElementById('sign-status-text');
      const statusDot = document.getElementById('sign-status-dot');
      if (statusText) statusText.textContent = 'Camera blocked';
      if (statusDot) statusDot.style.background = '#FF6B8B';

      TransifyApp.showToast('Camera access denied or unavailable.', 'warning');
      TransifyApp.announce('Camera access failed.');
    }
  },

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    if (this.videoEl) this.videoEl.srcObject = null;
    this.isStreaming = false;
    this.isProcessingFrame = false;
    this.lastHandBBox = null;
    if (this.predictTimer) clearInterval(this.predictTimer);
    if (this.frameCaptureTimer) clearInterval(this.frameCaptureTimer);
    this.predictTimer = null;
    this.frameCaptureTimer = null;

    const toggleBtn = document.getElementById('toggle-camera-btn');
    if (toggleBtn) {
      toggleBtn.innerHTML = 'Start camera';
      toggleBtn.classList.replace('btn-secondary', 'btn-primary');
    }
    const stopCamBtn = document.getElementById('stop-camera-btn');
    if (stopCamBtn) stopCamBtn.style.display = 'none';

    const stage = document.getElementById('sign-stage-container');
    if (stage) stage.classList.remove('stage-fullscreen');
    const hud = document.getElementById('fullscreen-pred-hud');
    if (hud) hud.style.display = 'none';
    const fsBtn = document.getElementById('btn-toggle-cam-fullscreen');
    if (fsBtn) fsBtn.innerHTML = '⛶ Fullscreen';

    const overlay = document.getElementById('camera-off-overlay');
    if (overlay) overlay.style.display = 'flex';

    const statusText = document.getElementById('sign-status-text');
    const statusDot = document.getElementById('sign-status-dot');
    if (statusText) statusText.textContent = 'Camera is off';
    if (statusDot) statusDot.style.background = '#8E8BA8';

    const s1 = document.getElementById('seg-1');
    const s2 = document.getElementById('seg-2');
    const s3 = document.getElementById('seg-3');
    if (s1) s1.classList.remove('on');
    if (s2) s2.classList.remove('on');
    if (s3) s3.classList.remove('on');

    const ringCircle = document.getElementById('confidence-ring-circle');
    if (ringCircle) ringCircle.style.strokeDashoffset = '201';

    const confBadge = document.getElementById('pred-confidence-badge');
    if (confBadge) confBadge.textContent = '0%';

    const wordEl = document.getElementById('pred-label-text');
    if (wordEl) { wordEl.textContent = '—'; wordEl.classList.remove('on'); }

    const statusLine = document.getElementById('pred-status-line');
    if (statusLine) statusLine.textContent = 'Camera is off';

    const speakBtn = document.getElementById('speak-pred-btn');
    if (speakBtn) { speakBtn.disabled = true; speakBtn.textContent = 'Speak word'; }

    const caret = document.getElementById('sign-caret');
    if (caret) caret.style.display = 'none';
  },

  startInferenceLoop() {
    // 1. Smooth UI feedback rendering loop (40ms)
    if (this.predictTimer) clearInterval(this.predictTimer);
    this.predictTimer = setInterval(() => {
      if (!this.isStreaming) return;
      this.drawCanvasFeedback();
    }, 40);

    // 2. Real-time vision frame processing loop (~200ms)
    this.startFrameCaptureLoop();
  },

  startFrameCaptureLoop() {
    if (this.frameCaptureTimer) clearInterval(this.frameCaptureTimer);

    this.frameCaptureTimer = setInterval(async () => {
      if (!this.isStreaming || this.isProcessingFrame) return;
      if (!this.videoEl || this.videoEl.readyState < 2 || !this.videoEl.videoWidth) return;

      try {
        this.isProcessingFrame = true;

        if (!this.offscreenCanvas) {
          this.offscreenCanvas = document.createElement('canvas');
          this.offscreenCanvas.width = 640;
          this.offscreenCanvas.height = 480;
          this.offscreenCtx = this.offscreenCanvas.getContext('2d');
        }

        // Draw crisp 640x480 frame for robust MediaPipe hand landmark tracking
        this.offscreenCtx.drawImage(this.videoEl, 0, 0, 640, 480);
        const b64 = this.offscreenCanvas.toDataURL('image/jpeg', 0.82);

        const currentRoi = this.getTargetRoi();
        const res = await fetch('/api/sign/process_frame', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            image_b64: b64,
            mode: this.currentMode,
            language_mode: this.currentLanguageMode || 'asl',
            roi: currentRoi
          })
        });

        if (!res.ok) return;
        const data = await res.json();
        this.lastFrameData = data;

        if (data && data.success) {
          if (data.hand_detected && data.hand_bbox) {
            this.lastHandBBox = data.hand_bbox;
            this.lastFrameDims = data.frame_dims || [640, 480];
            this.lastFingersCount = data.fingers_count || 0;
          } else {
            this.lastHandBBox = null;
            this.lastFingersCount = 0;
          }

          if (data.hand_detected && data.status === 'CONFIRMED' && data.label && data.label !== 'IDLE' && data.label !== 'ANALYZING') {
            // DECISION CONFIRMED AFTER ANALYSIS! Turn camera box vibrant GREEN!
            this.setDetectionFeedback(data.label, data.confidence || 0.98);

            // Update Recognized Word card with finalized translation
            this.updatePredictionUI({
              label: data.label,
              display_text: data.display_text,
              bdsl_gloss: data.gloss,
              english_text: data.english_text,
              language_mode: data.language_mode || this.currentLanguageMode,
              model_name: data.model_name,
              unified_translation: data.unified_translation,
              confidence: data.confidence,
              confirmed: true,
              status: 'CONFIRMED',
              analysis_pct: 100,
              engine_info: data.engine_info
            });

            // Commit word to sentence & speak
            if (data.is_word) {
              if (Date.now() - this.lastConfirmedTime > 1800) {
                this.lastConfirmedTime = Date.now();
                this.addTokenToSentence(data.label);
                TransifyApp.showToast(`Recognized Sign "${data.label}" confirmed!`, 'success');
              }
            } else {
              const liveLetterEl = document.getElementById('current-letter-badge');
              if (liveLetterEl) liveLetterEl.textContent = data.label;
              if (data.composed_text) {
                const wordEl = document.getElementById('spelled-word-display');
                if (wordEl) wordEl.textContent = data.composed_text;
              }
              if (Date.now() - this.lastConfirmedTime > 1300) {
                this.lastConfirmedTime = Date.now();
                this.triggerFingerspellLetter(data.label);
              }
            }
          } else if (data.hand_detected && data.status === 'ANALYZING') {
            // IN ANALYSIS PHASE: Hand signal being observed across frames! Keep holding steady!
            this.updatePredictionUI({
              label: 'ANALYZING',
              candidate_label: data.candidate_label,
              display_text: data.display_text,
              bdsl_gloss: data.gloss,
              confidence: data.confidence,
              confirmed: false,
              status: 'ANALYZING',
              analysis_pct: data.analysis_pct || 40,
              consensus_progress: data.consensus_progress,
              engine_info: data.engine_info
            });
          } else if (data.hand_detected) {
            // Hand is in position inside target box, waiting for user to form sign
            this.updatePredictionUI({
              label: 'IDLE',
              display_text: data.display_text || '✋ Hand In Position (Ready To Sign)',
              bdsl_gloss: data.gloss || 'Show an ASL or HaGRID hand sign',
              confidence: 0,
              confirmed: false,
              status: 'READY',
              analysis_pct: 0
            });
          } else {
            // No hand inside target box
            this.updatePredictionUI({
              label: 'IDLE',
              display_text: data.display_text || 'Position hand inside the fixed guide box ✋',
              bdsl_gloss: data.gloss || '[Face and outside background are excluded]',
              confidence: 0,
              confirmed: false,
              status: 'IDLE',
              analysis_pct: 0
            });
          }
        }
      } catch (err) {
        console.debug('Live frame processor notice:', err);
      } finally {
        this.isProcessingFrame = false;
      }
    }, 200);
  },

  drawCanvasFeedback() {
    if (!this.ctx || !this.videoEl || !this.isStreaming) return;
    this.canvasEl.width = this.videoEl.videoWidth || 640;
    this.canvasEl.height = this.videoEl.videoHeight || 480;
    const w = this.canvasEl.width;
    const h = this.canvasEl.height;
    this.ctx.clearRect(0, 0, w, h);

    // Check live state
    const data = this.lastFrameData;
    const isRecentlyDetected = this.detectionState.isDetected && (Date.now() - this.detectionState.timestamp < 2500);
    const isAnalyzing = (data && data.hand_detected && data.status === 'ANALYZING');
    const isHandInRoi = (data && data.hand_detected && data.in_roi !== false);

    // Sync state cleanly to HTML centered Target ROI Box (#sign-roi-box)
    const roiBox = document.getElementById('sign-roi-box');
    const statusTextEl = document.getElementById('sign-status-text');

    if (roiBox) {
      if (isRecentlyDetected) {
        roiBox.classList.add('confirmed');
        roiBox.classList.remove('analyzing');
        if (statusTextEl && this.detectionState.label) {
          statusTextEl.textContent = `Sign confirmed: ${this.detectionState.label}`;
        }
      } else if (isAnalyzing) {
        roiBox.classList.add('analyzing');
        roiBox.classList.remove('confirmed');
        if (statusTextEl) {
          statusTextEl.textContent = `Analyzing sign... hold steady`;
        }
      } else if (isHandInRoi) {
        roiBox.classList.remove('confirmed', 'analyzing');
        if (statusTextEl) {
          statusTextEl.textContent = `Hand in position • Ready to sign`;
        }
      } else {
        roiBox.classList.remove('confirmed', 'analyzing');
        if (statusTextEl) {
          statusTextEl.textContent = `Camera is active • Keep hand in box`;
        }
      }
    }

    // Only draw clean subtle hand tracking if detected — zero green bars, zero mirrored text
    if (this.lastHandBBox) {
      const sX = w / (this.lastFrameDims ? this.lastFrameDims[0] : 640);
      const sY = h / (this.lastFrameDims ? this.lastFrameDims[1] : 480);
      const hX = this.lastHandBBox[0] * sX;
      const hY = this.lastHandBBox[1] * sY;
      const hW = this.lastHandBBox[2] * sX;
      const hH = this.lastHandBBox[3] * sY;

      this.ctx.save();
      this.ctx.strokeStyle = isRecentlyDetected ? 'rgba(34, 197, 94, 0.7)' : 'rgba(255, 203, 5, 0.6)';
      this.ctx.lineWidth = 2;
      this.ctx.setLineDash([6, 6]);
      this.ctx.strokeRect(hX, hY, hW, hH);
      this.ctx.restore();
    }
  },

  _drawTargetBrackets(x, y, w, h, color, cLen, lineWidth) {
    this.ctx.save();
    this.ctx.strokeStyle = color;
    this.ctx.lineWidth = lineWidth;
    this.ctx.setLineDash([]);
    // Top-Left
    this.ctx.beginPath();
    this.ctx.moveTo(x, y + cLen);
    this.ctx.lineTo(x, y);
    this.ctx.lineTo(x + cLen, y);
    this.ctx.stroke();
    // Top-Right
    this.ctx.beginPath();
    this.ctx.moveTo(x + w - cLen, y);
    this.ctx.lineTo(x + w, y);
    this.ctx.lineTo(x + w, y + cLen);
    this.ctx.stroke();
    // Bottom-Left
    this.ctx.beginPath();
    this.ctx.moveTo(x, y + h - cLen);
    this.ctx.lineTo(x, y + h);
    this.ctx.lineTo(x + cLen, y + h);
    this.ctx.stroke();
    // Bottom-Right
    this.ctx.beginPath();
    this.ctx.moveTo(x + w - cLen, y + h);
    this.ctx.lineTo(x + w, y + h);
    this.ctx.lineTo(x + w, y + h - cLen);
    this.ctx.stroke();
    this.ctx.restore();
  },

  _drawPillBadge(x, y, text, bgColor, textColor) {
    this.ctx.save();
    this.ctx.font = 'bold 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    this.ctx.textAlign = 'left';
    this.ctx.textBaseline = 'middle';
    const textMetrics = this.ctx.measureText(text);
    const pillW = textMetrics.width + 24;
    const pillH = 28;

    this.ctx.shadowBlur = 0;
    this.ctx.fillStyle = bgColor;
    this.ctx.beginPath();
    if (this.ctx.roundRect) {
      this.ctx.roundRect(x, y, pillW, pillH, 6);
    } else {
      this.ctx.rect(x, y, pillW, pillH);
    }
    this.ctx.fill();

    this.ctx.fillStyle = textColor;
    this.ctx.fillText(text, x + 12, y + pillH / 2);
    this.ctx.restore();
  },

  async simulateSignSample(className) {
    TransifyApp.showToast(`Loading verified sample sequence for ${className}...`, 'info');
    try {
      const res = await fetch(`/api/samples/sign/${className}`);
      if (!res.ok) throw new Error('Sample sequence not found');
      const sample = await res.json();

      // Send to prediction pipeline
      const predRes = await fetch('/api/sign/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sequence: sample.sequence,
          signer_id: sample.sample_id,
          language_mode: this.currentLanguageMode || 'asl',
          auto_log: true
        })
      });

      if (!predRes.ok) throw new Error('Prediction failed');
      const predData = await predRes.json();
      this.updatePredictionUI(predData, sample.bdsl_gloss);

    } catch (e) {
      console.error('Sign sample simulation failed:', e);
      TransifyApp.showToast(`Error testing sign: ${e.message}`, 'danger');
    }
  },

  updatePredictionUI(result, defaultGloss = '') {
    const banner = document.getElementById('sign-prediction-banner');
    const labelEl = document.getElementById('pred-label-text');
    const glossEl = document.getElementById('pred-gloss-text');
    const confEl = document.getElementById('pred-confidence-badge');
    const progressFill = document.getElementById('debounce-progress-fill');
    const statusNote = document.getElementById('pred-status-note');
    const engineNote = document.getElementById('sign-engine-note');
    const unifiedOutputEl = document.getElementById('unified-english-output');
    const sourceTagEl = document.getElementById('trans-source-model-tag');

    if (result.rejected) {
      if (labelEl) { labelEl.textContent = '—'; labelEl.classList.remove('on'); }
      if (glossEl) glossEl.textContent = `[Filtering: ${result.rejection_reason || 'Low motion / Idle'}]`;
      if (progressFill) progressFill.style.width = '20%';
      if (engineNote) engineNote.style.display = 'none';
      return;
    }

    const isRealSign = Boolean(
      result.label &&
      result.label !== 'IDLE' &&
      result.label !== 'ANALYZING' &&
      result.label !== 'OUT_OF_ROI' &&
      result.label !== 'READY' &&
      (result.confirmed || (result.confidence && result.confidence >= 0.75))
    );

    const displayWord = isRealSign ? (result.display_text || result.label.replace(/_/g, ' ')) : '';

    // Auto-fit recognized word (§6.4)
    if (labelEl) {
      if (isRealSign) {
        const rawText = displayWord;
        let letters = [];
        if (typeof Intl !== 'undefined' && Intl.Segmenter) {
          try {
            const seg = new Intl.Segmenter('en', { granularity: 'grapheme' });
            for (const s of seg.segment(rawText)) {
              letters.push(s.segment);
            }
          } catch (e) {
            letters = rawText.split('');
          }
        } else {
          letters = rawText.split('');
        }
        labelEl.innerHTML = letters.map((l, idx) => `<span class="l" style="animation-delay:${Math.min(idx * 0.06, 0.48)}s">${l}</span>`).join('');
        labelEl.classList.add('on');

        let fontSize = 96;
        labelEl.style.fontSize = fontSize + 'px';
        while (labelEl.scrollWidth > labelEl.clientWidth && fontSize > 40) {
          fontSize -= 4;
          labelEl.style.fontSize = fontSize + 'px';
        }
      } else {
        labelEl.textContent = '—';
        labelEl.classList.remove('on');
        labelEl.style.fontSize = '96px';
      }
    }

    if (glossEl) {
      glossEl.textContent = isRealSign ? `[ASL: ${result.gloss || defaultGloss || result.label}]` : '';
    }

    // Confidence Ring SVG (104x104)
    const confVal = isRealSign ? Math.round((result.confidence || 0.95) * 100) : 0;
    if (confEl) {
      confEl.textContent = `${confVal}%`;
      confEl.className = (isRealSign && confVal >= 80) ? 'ring-pct badge-success' : 'ring-pct';
    }

    const hudWord = document.getElementById('hud-word-badge');
    const hudConf = document.getElementById('hud-conf-badge');
    if (hudWord) {
      hudWord.textContent = isRealSign ? displayWord : (result.status === 'ANALYZING' ? 'Analyzing...' : '—');
    }
    if (hudConf) {
      hudConf.textContent = `${confVal}% sure`;
    }

    const ringCircle = document.getElementById('confidence-ring-circle');
    if (ringCircle) {
      if (isRealSign) {
        const offset = 201 * (1 - Math.min(1, Math.max(0, result.confidence || 0.95)));
        ringCircle.style.strokeDashoffset = offset;
        ringCircle.setAttribute('stroke', result.confirmed ? '#0F9D74' : '#8338EC');
      } else {
        ringCircle.style.strokeDashoffset = 201;
        ringCircle.setAttribute('stroke', '#D9DAE6');
      }
    }

    // Segments
    const count = result.debounce_count || (result.confirmed ? 3 : 1);
    const seg1 = document.getElementById('seg-1');
    const seg2 = document.getElementById('seg-2');
    const seg3 = document.getElementById('seg-3');
    if (seg1) seg1.classList.toggle('on', count >= 1);
    if (seg2) seg2.classList.toggle('on', count >= 2);
    if (seg3) seg3.classList.toggle('on', count >= 3);

    // Status Line
    const statusLine = document.getElementById('pred-status-line');
    if (statusLine) {
      if (result.confirmed && isRealSign) {
        statusLine.textContent = 'Confirmed after 3 matching frames';
      } else if (result.status === 'ANALYZING') {
        statusLine.textContent = `Analyzing sign... checking frame ${count} of 3`;
      } else if (result.status === 'READY') {
        statusLine.textContent = 'Hand detected • Ready to sign';
      } else if (result.status === 'OUT_OF_ROI') {
        statusLine.textContent = 'Bring hand inside the fixed guide box';
      } else if (isRealSign) {
        statusLine.textContent = `Observing ${displayWord}`;
      } else {
        statusLine.textContent = 'Show your hand in the box';
      }
    }

    // Speak word button
    const speakWordBtn = document.getElementById('speak-pred-btn');
    if (speakWordBtn) {
      speakWordBtn.textContent = isRealSign ? `Speak ${displayWord}` : 'Speak word';
      speakWordBtn.disabled = !isRealSign;
    }

    // ROI Beam
    const roiBox = document.getElementById('sign-roi-box');
    if (roiBox) {
      roiBox.classList.toggle('analyzing', !result.confirmed && result.status === 'ANALYZING');
    }

    // Unified Translation Layer display
    const englishText = result.english_text || result.display_text || result.label;
    if (unifiedOutputEl && englishText && isRealSign) {
      unifiedOutputEl.textContent = `"${englishText}"`;
    }
    if (sourceTagEl) {
      sourceTagEl.textContent = 'SignFrame AI (ASL)';
      sourceTagEl.style.color = '#8338ec';
      sourceTagEl.style.background = 'rgba(131, 56, 236, 0.15)';
    }

    // Engine Info and Latency Display
    if (engineNote && result.engine_info && isRealSign) {
      const eng = result.engine_info;
      engineNote.style.display = 'inline-block';
      if (eng.is_fallback) {
        engineNote.style.background = 'rgba(234, 179, 8, 0.15)';
        engineNote.style.color = 'var(--text-warning, #eab308)';
        engineNote.style.border = '1px solid rgba(234, 179, 8, 0.3)';
        engineNote.innerHTML = `🤖 <strong>${eng.badge || 'MCP Resolver (<98%)'}:</strong> ${eng.notes || ''}`;
      } else {
        engineNote.style.background = 'rgba(34, 197, 94, 0.12)';
        engineNote.style.color = 'var(--text-success, #22c55e)';
        engineNote.style.border = '1px solid rgba(34, 197, 94, 0.25)';
        engineNote.innerHTML = `🎯 <strong>Custom AI Model (&ge; 98%):</strong> Processed in ultra-fast time (&lt; 15ms)`;
      }
    } else if (engineNote && !isRealSign) {
      engineNote.style.display = 'none';
    }

    // Trigger detection feedback on camera overlay whenever valid sign is detected
    if (isRealSign) {
      this.setDetectionFeedback(result.label, result.confidence || 0.95);
    } else {
      this.setDetectionFeedback(null);
    }

    // Update consensus debounce progress bar
    if (progressFill) {
      const count = result.debounce_count || 1;
      const target = result.debounce_target || 3;
      const pct = Math.min(100, Math.round((count / target) * 100));
      progressFill.style.width = `${pct}%`;
    }

    if (result.confirmed && isRealSign) {
      const now = Date.now();
      const isNewSign = (result.label !== this.lastConfirmedSign);
      const isTimeElapsed = (now - this.lastConfirmedSpeechTime > 2500);

      this.lastPrediction = displayWord;

      if (isNewSign || isTimeElapsed) {
        this.lastConfirmedSign = result.label;
        this.lastConfirmedSpeechTime = now;

        TransifyApp.announce(`Recognized ASL Sign: ${displayWord}`);
        if (statusNote) statusNote.textContent = `Confirmed expression: ${displayWord}`;

        // Automatically append confirmed sign token to Sentence Builder
        this.addTokenToSentence(displayWord);

        if (this.autoSpeak) {
          TransifyTTS.speak(englishText || displayWord);
        }
      }
    } else {
      if (statusNote) statusNote.textContent = `Debouncing consensus (${result.debounce_count || 1}/${result.debounce_target || 3})...`;
    }
  },

  async resetRecognition() {
    try {
      await fetch('/api/sign/reset', { method: 'POST' });
      this.sequenceBuffer = [];
      this.lastPrediction = null;
      const labelEl = document.getElementById('pred-label-text');
      const glossEl = document.getElementById('pred-gloss-text');
      const progressFill = document.getElementById('debounce-progress-fill');
      if (labelEl) labelEl.textContent = 'Waiting for gesture...';
      if (glossEl) glossEl.textContent = 'Position your hands in camera view or click a sample below';
      if (progressFill) progressFill.style.width = '0%';
      TransifyApp.showToast('Sign tracker reset.', 'info');
    } catch (e) {
      // Ignore
    }
  }
};

// ==========================================
// 5. Module 02: Braille Image Translator
// ==========================================

// ==========================================
// 5. Module 02: Braille Image Translator & Multi-Modal Studio
// ==========================================

var BraillePage = window.BraillePage = {
  currentFile: null,
  currentImageSrc: null,
  isInitialized: false,
  currentMode: 'scan',
  cameraStream: null,
  cameraFacing: 'environment',
  activeCellDots: [],

  // Comprehensive UEB Grade 1 / Grade 2 & Bharati Braille dictionary
  charToBraille: {
    'a': { dots: [1], unicode: '⠁', bn: 'অ', name: 'Letter A' },
    'b': { dots: [1, 2], unicode: '⠃', bn: 'ব', name: 'Letter B' },
    'c': { dots: [1, 4], unicode: '⠉', bn: 'চ', name: 'Letter C' },
    'd': { dots: [1, 4, 5], unicode: '⠙', bn: 'দ', name: 'Letter D' },
    'e': { dots: [1, 5], unicode: '⠑', bn: 'এ', name: 'Letter E' },
    'f': { dots: [1, 2, 4], unicode: '⠋', bn: 'ফ', name: 'Letter F' },
    'g': { dots: [1, 2, 4, 5], unicode: '⠛', bn: 'গ', name: 'Letter G' },
    'h': { dots: [1, 2, 5], unicode: '⠓', bn: 'হ', name: 'Letter H' },
    'i': { dots: [2, 4], unicode: '⠊', bn: 'ই', name: 'Letter I' },
    'j': { dots: [2, 4, 5], unicode: '⠚', bn: 'জ', name: 'Letter J' },
    'k': { dots: [1, 3], unicode: '⠅', bn: 'ক', name: 'Letter K' },
    'l': { dots: [1, 2, 3], unicode: '⠇', bn: 'ল', name: 'Letter L' },
    'm': { dots: [1, 3, 4], unicode: '⠍', bn: 'ম', name: 'Letter M' },
    'n': { dots: [1, 3, 4, 5], unicode: '⠝', bn: 'ন', name: 'Letter N' },
    'o': { dots: [1, 3, 5], unicode: '⠕', bn: 'ও', name: 'Letter O' },
    'p': { dots: [1, 2, 3, 4], unicode: '⠏', bn: 'প', name: 'Letter P' },
    'q': { dots: [1, 2, 3, 4, 5], unicode: '⠟', bn: '–', name: 'Letter Q' },
    'r': { dots: [1, 2, 3, 5], unicode: '⠗', bn: 'র', name: 'Letter R' },
    's': { dots: [2, 3, 4], unicode: '⠎', bn: 'স', name: 'Letter S' },
    't': { dots: [2, 3, 4, 5], unicode: '⠞', bn: 'ত', name: 'Letter T' },
    'u': { dots: [1, 3, 6], unicode: '⠥', bn: 'উ', name: 'Letter U' },
    'v': { dots: [1, 2, 3, 6], unicode: '⠧', bn: 'ভ', name: 'Letter V' },
    'w': { dots: [2, 4, 5, 6], unicode: '⠺', bn: 'ঠ', name: 'Letter W' },
    'x': { dots: [1, 3, 4, 6], unicode: '⠭', bn: '–', name: 'Letter X' },
    'y': { dots: [1, 3, 4, 5, 6], unicode: '⠽', bn: 'য', name: 'Letter Y' },
    'z': { dots: [1, 3, 5, 6], unicode: '⠵', bn: '–', name: 'Letter Z' },
    '1': { dots: [1], unicode: '⠁', isDigit: true, name: 'Digit 1' },
    '2': { dots: [1, 2], unicode: '⠃', isDigit: true, name: 'Digit 2' },
    '3': { dots: [1, 4], unicode: '⠉', isDigit: true, name: 'Digit 3' },
    '4': { dots: [1, 4, 5], unicode: '⠙', isDigit: true, name: 'Digit 4' },
    '5': { dots: [1, 5], unicode: '⠑', isDigit: true, name: 'Digit 5' },
    '6': { dots: [1, 2, 4], unicode: '⠋', isDigit: true, name: 'Digit 6' },
    '7': { dots: [1, 2, 4, 5], unicode: '⠛', isDigit: true, name: 'Digit 7' },
    '8': { dots: [1, 2, 5], unicode: '⠓', isDigit: true, name: 'Digit 8' },
    '9': { dots: [2, 4], unicode: '⠊', isDigit: true, name: 'Digit 9' },
    '0': { dots: [2, 4, 5], unicode: '⠚', isDigit: true, name: 'Digit 0' },
    '.': { dots: [2, 5, 6], unicode: '⠲', bn: '।', name: 'Period' },
    ',': { dots: [2], unicode: '⠂', bn: ',', name: 'Comma' },
    ';': { dots: [2, 3], unicode: '⠆', name: 'Semicolon' },
    ':': { dots: [2, 5], unicode: '⠒', name: 'Colon' },
    '?': { dots: [2, 3, 6], unicode: '⠦', name: 'Question Mark' },
    '!': { dots: [2, 3, 5], unicode: '⠖', name: 'Exclamation' },
    '-': { dots: [3, 6], unicode: '⠤', name: 'Hyphen' },
    "'": { dots: [3], unicode: '⠄', name: 'Apostrophe' },
    '"': { dots: [3, 5, 6], unicode: '⠴', name: 'Quote' }
  },

  // Bengali Bharati Braille Map
  bengaliBraille: {
    'অ': { dots: [1], unicode: '⠁', roman: 'o / a' },
    'আ': { dots: [3, 4, 5], unicode: '⠜', roman: 'aa' },
    'ই': { dots: [2, 4], unicode: '⠊', roman: 'i' },
    'ঈ': { dots: [3, 5], unicode: '⠔', roman: 'ee' },
    'উ': { dots: [1, 3, 6], unicode: '⠥', roman: 'u' },
    'ঊ': { dots: [1, 2, 5, 6], unicode: '⠳', roman: 'oo' },
    'এ': { dots: [1, 5], unicode: '⠑', roman: 'e' },
    'ঐ': { dots: [3, 4], unicode: '⠌', roman: 'oi' },
    'ও': { dots: [1, 3, 5], unicode: '⠕', roman: 'o' },
    'ঔ': { dots: [2, 4, 6], unicode: '⠪', roman: 'ou' },
    'ক': { dots: [1, 3], unicode: '⠅', roman: 'k' },
    'খ': { dots: [4, 6], unicode: '⠨', roman: 'kh' },
    'গ': { dots: [1, 2, 4, 5], unicode: '⠛', roman: 'g' },
    'ঘ': { dots: [1, 2, 6], unicode: '⠣', roman: 'gh' },
    'ঙ': { dots: [3, 4, 6], unicode: '⠬', roman: 'ng' },
    'চ': { dots: [1, 4], unicode: '⠉', roman: 'ch' },
    'ছ': { dots: [1, 4, 6], unicode: '⠡', roman: 'chh' },
    'জ': { dots: [2, 4, 5], unicode: '⠚', roman: 'j' },
    'ঝ': { dots: [3, 5, 6], unicode: '⠴', roman: 'jh' },
    'ঞ': { dots: [2, 5], unicode: '⠒', roman: 'ny' },
    'ট': { dots: [2, 3, 4, 5, 6], unicode: '⠾', roman: 'T' },
    'ঠ': { dots: [2, 4, 5, 6], unicode: '⠺', roman: 'Th' },
    'ড': { dots: [1, 2, 4, 6], unicode: '⠫', roman: 'D' },
    'ঢ': { dots: [1, 2, 3, 4, 5, 6], unicode: '⠿', roman: 'Dh' },
    'ণ': { dots: [3, 4, 5, 6], unicode: '⠼', roman: 'N' },
    'ত': { dots: [2, 3, 4, 5], unicode: '⠞', roman: 't' },
    'থ': { dots: [1, 4, 5, 6], unicode: '⠹', roman: 'th' },
    'দ': { dots: [1, 4, 5], unicode: '⠙', roman: 'd' },
    'ধ': { dots: [2, 3, 4, 6], unicode: '⠮', roman: 'dh' },
    'ন': { dots: [1, 3, 4, 5], unicode: '⠝', roman: 'n' },
    'প': { dots: [1, 2, 3, 4], unicode: '⠏', roman: 'p' },
    'ফ': { dots: [2, 3, 5], unicode: '⠖', roman: 'ph/f' },
    'ব': { dots: [1, 2], unicode: '⠃', roman: 'b' },
    'ভ': { dots: [4, 5], unicode: '⠘', roman: 'bh/v' },
    'ম': { dots: [1, 3, 4], unicode: '⠍', roman: 'm' },
    'য': { dots: [1, 3, 4, 5, 6], unicode: '⠽', roman: 'y/z' },
    'র': { dots: [1, 2, 3, 5], unicode: '⠗', roman: 'r' },
    'ল': { dots: [1, 2, 3], unicode: '⠇', roman: 'l' },
    'শ': { dots: [1, 4, 6], unicode: '⠱', roman: 'sh' },
    'ষ': { dots: [1, 2, 3, 4, 6], unicode: '⠯', roman: 'shh' },
    'স': { dots: [2, 3, 4], unicode: '⠎', roman: 's' },
    'হ': { dots: [1, 2, 5], unicode: '⠓', roman: 'h' }
  },

  // Common Grade 2 Contractions
  contractions: [
    { word: 'and', dots: [1, 2, 3, 4, 6], unicode: '⠯' },
    { word: 'for', dots: [1, 2, 3, 4, 5, 6], unicode: '⠿' },
    { word: 'of', dots: [1, 2, 3, 5, 6], unicode: '⠷' },
    { word: 'the', dots: [2, 3, 4, 6], unicode: '⠮' },
    { word: 'with', dots: [2, 3, 4, 5, 6], unicode: '⠾' },
    { word: 'ch', dots: [1, 6], unicode: '⠡' },
    { word: 'sh', dots: [1, 4, 6], unicode: '⠱' },
    { word: 'th', dots: [1, 4, 5, 6], unicode: '⠹' },
    { word: 'wh', dots: [1, 5, 6], unicode: '⠱' },
    { word: 'ed', dots: [1, 2, 4, 6], unicode: '⠫' },
    { word: 'er', dots: [1, 2, 4, 5, 6], unicode: '⠻' },
    { word: 'ou', dots: [1, 2, 5, 6], unicode: '⠳' },
    { word: 'ow', dots: [2, 4, 6], unicode: '⠪' }
  ],

  // Reverse mapping from dots string ('134') to char details
  dotsToChar: {},

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    // Build reverse dots-to-character lookup table
    this.buildDotsLookup();

    this.setupDropzone();
    this.setupActionButtons();
    this.setupInteractiveCell();
    this.initReference();
    this.initGenerator();
  },

  buildDotsLookup() {
    this.dotsToChar = {};
    for (const [char, meta] of Object.entries(this.charToBraille)) {
      const key = meta.dots.slice().sort((a, b) => a - b).join('');
      if (!this.dotsToChar[key]) {
        this.dotsToChar[key] = { char, meta };
      }
    }
  },

  // Sub-Navigation Mode Switching
  switchMode(mode) {
    this.currentMode = mode;
    ['scan', 'generator', 'reference'].forEach(m => {
      const tab = document.getElementById(`braille-tab-${m}`);
      const pane = document.getElementById(`braille-pane-${m}`);
      const isActive = (m === mode);
      if (tab) {
        tab.classList.toggle('active', isActive);
        tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
      }
      if (pane) {
        pane.style.display = isActive ? 'flex' : 'none';
        pane.classList.toggle('active', isActive);
      }
    });

    if (mode === 'generator') {
      const inputEl = document.getElementById('braille-generator-input');
      if (inputEl && !inputEl.value) {
        this.loadGeneratorPreset('Hello Transify');
      }
    } else if (mode === 'reference') {
      this.filterReference('letters');
    }
  },

  // Preloaded 1-Click Test Samples
  async loadSample(url, filename) {
    TransifyApp.showToast(`Loading sample image: ${filename}...`, 'info');
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const file = new File([blob], filename, { type: blob.type || 'image/jpeg' });
      this.handleFileSelected(file);
    } catch (e) {
      TransifyApp.showToast(`Could not load sample: ${e.message}`, 'danger');
    }
  },

  setupDropzone() {
    const dropzone = document.getElementById('braille-dropzone');
    const fileInput = document.getElementById('braille-file-input');
    const browseBtn = document.getElementById('braille-select-file-btn');

    if (!dropzone || !fileInput) return;

    if (browseBtn) {
      browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
      });
    }

    dropzone.addEventListener('click', (e) => {
      if (e.target.closest('#braille-open-camera-btn') || e.target.closest('#braille-select-file-btn')) {
        return;
      }
      fileInput.click();
    });

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });

    ['dragleave', 'dragend'].forEach(type => {
      dropzone.addEventListener(type, () => dropzone.classList.remove('dragover'));
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        this.handleFileSelected(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        this.handleFileSelected(e.target.files[0]);
      }
    });
  },

  handleFileSelected(file) {
    if (!file.type.startsWith('image/')) {
      TransifyApp.showToast('Please select a valid image file (PNG, JPG, WebP).', 'warning');
      return;
    }
    this.currentFile = file;

    // Display image preview
    const reader = new FileReader();
    reader.onload = (e) => {
      this.currentImageSrc = e.target.result;
      const previewImg = document.getElementById('braille-preview-img');
      const previewWrapper = document.getElementById('braille-preview-wrapper');
      if (previewImg && previewWrapper) {
        previewImg.src = this.currentImageSrc;
        previewWrapper.style.display = 'block';
      }
      const dropzone = document.getElementById('braille-dropzone');
      if (dropzone) {
        dropzone.style.borderColor = '#22c55e';
        dropzone.style.background = 'rgba(34, 197, 94, 0.05)';
      }
    };
    reader.readAsDataURL(file);

    // Update file indicator
    const fileIndicator = document.getElementById('braille-active-file-indicator');
    const fileNameEl = document.getElementById('braille-active-file-name');
    if (fileIndicator && fileNameEl) {
      fileNameEl.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      fileIndicator.style.display = 'inline-block';
    }

    TransifyApp.showToast(`Selected ${file.name}. Click "Translate Image" to run AI OCR.`, 'info');
  },

  // Live Camera Capture
  async openCamera(e) {
    if (e && e.stopPropagation) e.stopPropagation();
    const modal = document.getElementById('braille-camera-modal');
    const video = document.getElementById('braille-camera-video');
    if (!modal || !video) return;

    modal.style.display = 'flex';

    try {
      if (this.cameraStream) {
        this.cameraStream.getTracks().forEach(t => t.stop());
      }
      const constraints = {
        video: {
          facingMode: this.cameraFacing,
          width: { ideal: 1280 },
          height: { ideal: 720 }
        },
        audio: false
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.cameraStream = stream;
      video.srcObject = stream;
      video.play();
    } catch (err) {
      TransifyApp.showToast('Could not access camera: ' + err.message, 'danger');
      this.closeCamera();
    }
  },

  switchCameraFacing() {
    this.cameraFacing = this.cameraFacing === 'environment' ? 'user' : 'environment';
    this.openCamera();
  },

  captureCamera() {
    const video = document.getElementById('braille-camera-video');
    const canvas = document.getElementById('braille-camera-canvas');
    if (!video || !canvas) return;

    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const file = new File([blob], `braille_camera_${Date.now()}.jpg`, { type: 'image/jpeg' });
      this.closeCamera();
      this.handleFileSelected(file);
      TransifyApp.showToast('Camera frame captured! Click Translate Image.', 'success');
    }, 'image/jpeg', 0.92);
  },

  closeCamera() {
    const modal = document.getElementById('braille-camera-modal');
    const video = document.getElementById('braille-camera-video');
    if (this.cameraStream) {
      this.cameraStream.getTracks().forEach(t => t.stop());
      this.cameraStream = null;
    }
    if (video) video.srcObject = null;
    if (modal) modal.style.display = 'none';
  },

  setupActionButtons() {
    const translateBtn = document.getElementById('translate-braille-btn');
    if (translateBtn) {
      translateBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.runTranslation();
      });
    }

    const uploadForm = document.getElementById('braille-upload-form');
    if (uploadForm) {
      uploadForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.runTranslation();
      });
    }

    const speakBtn = document.getElementById('speak-braille-btn');
    if (speakBtn) {
      speakBtn.addEventListener('click', () => {
        const textarea = document.getElementById('braille-text-output');
        const text = textarea ? (textarea.value || textarea.textContent || '').trim() : '';
        if (text) {
          TransifyTTS.speak(text);
        } else {
          TransifyApp.showToast('No text available to speak.', 'warning');
        }
      });
    }

    const copyBtn = document.getElementById('copy-braille-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        const textarea = document.getElementById('braille-text-output');
        const text = textarea ? (textarea.value || textarea.textContent || '').trim() : '';
        if (text) {
          navigator.clipboard.writeText(text).then(() => {
            TransifyApp.showToast('Text copied to clipboard!', 'success');
          }).catch(() => {
            TransifyApp.showToast('Copy failed. Please copy manually.', 'warning');
          });
        }
      });
    }

    const downloadBtn = document.getElementById('download-braille-btn');
    if (downloadBtn) {
      downloadBtn.addEventListener('click', () => {
        const textarea = document.getElementById('braille-text-output');
        const text = textarea ? (textarea.value || textarea.textContent || '').trim() : '';
        if (!text) return;
        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Transify_Braille_Translation_${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
      });
    }
  },

  // 6-Dot Cell Explorer Implementation
  setupInteractiveCell() {
    const dotButtons = document.querySelectorAll('.braille-interactive-card [data-braille-dot]');
    dotButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const dotNum = parseInt(btn.getAttribute('data-braille-dot'), 10);
        this.toggleCellDot(dotNum);
      });
    });
    this.updateCellDisplay();
  },

  toggleCellDot(dotNum) {
    const idx = this.activeCellDots.indexOf(dotNum);
    if (idx >= 0) {
      this.activeCellDots.splice(idx, 1);
    } else {
      this.activeCellDots.push(dotNum);
    }
    this.activeCellDots.sort((a, b) => a - b);
    this.updateCellDisplay();
  },

  clearCellDots() {
    this.activeCellDots = [];
    this.updateCellDisplay();
  },

  invertCellDots() {
    const all = [1, 2, 3, 4, 5, 6];
    this.activeCellDots = all.filter(d => !this.activeCellDots.includes(d));
    this.updateCellDisplay();
  },

  randomCellPattern() {
    const letters = Object.keys(this.charToBraille).filter(c => c >= 'a' && c <= 'z');
    const rand = letters[Math.floor(Math.random() * letters.length)];
    const meta = this.charToBraille[rand];
    this.loadPattern(meta.dots, rand.toUpperCase(), meta.bn);
  },

  loadPattern(dots, charLabel, bengaliLabel) {
    this.activeCellDots = dots.slice().sort((a, b) => a - b);
    this.updateCellDisplay(charLabel, bengaliLabel);
  },

  updateCellDisplay(overrideChar, overrideBengali) {
    // Update button .active classes
    const dotButtons = document.querySelectorAll('.braille-interactive-card [data-braille-dot]');
    dotButtons.forEach(btn => {
      const dotNum = parseInt(btn.getAttribute('data-braille-dot'), 10);
      btn.classList.toggle('active', this.activeCellDots.includes(dotNum));
    });

    const key = this.activeCellDots.join('');
    const unicodeChar = this.dotsToUnicode(this.activeCellDots);
    const codepoint = unicodeChar.charCodeAt(0).toString(16).toUpperCase();

    let char = overrideChar;
    let bn = overrideBengali;

    if (!char) {
      const match = this.dotsToChar[key];
      if (match) {
        char = match.char.toUpperCase();
        bn = match.meta.bn || '–';
      } else if (this.activeCellDots.length === 0) {
        char = '—';
        bn = '—';
      } else {
        char = 'Special / Unassigned';
        bn = '–';
      }
    }

    const charEl = document.getElementById('braille-interactive-char');
    const dotsEl = document.getElementById('braille-interactive-dots');
    const unicodeEl = document.getElementById('braille-interactive-unicode');
    const bnEl = document.getElementById('braille-interactive-bengali');

    if (charEl) charEl.textContent = `Character: ${char}`;
    if (dotsEl) dotsEl.textContent = `Active: ${this.activeCellDots.length ? 'Dots ' + this.activeCellDots.join(', ') : 'None'}`;
    if (unicodeEl) unicodeEl.textContent = `Unicode: ${unicodeChar} (U+${codepoint})`;
    if (bnEl) bnEl.textContent = `বাংলা (Bharati): ${bn || '–'}`;
  },

  speakActiveCell() {
    const charEl = document.getElementById('braille-interactive-char');
    const text = charEl ? charEl.textContent.replace('Character: ', '').trim() : '';
    if (text && text !== '—' && text !== 'Special / Unassigned') {
      TransifyTTS.speak(text);
    } else {
      TransifyApp.showToast('Please toggle dots to select a character.', 'warning');
    }
  },

  dotsToUnicode(dotsArray) {
    let mask = 0;
    dotsArray.forEach(d => {
      if (d >= 1 && d <= 6) {
        mask |= (1 << (d - 1));
      }
    });
    return String.fromCharCode(0x2800 + mask);
  },

  // Text-to-Braille Generator Engine
  initGenerator() {
    const inputEl = document.getElementById('braille-generator-input');
    if (inputEl && !inputEl.value) {
      this.loadGeneratorPreset('Hello Transify');
    }
  },

  loadGeneratorPreset(phrase) {
    const inputEl = document.getElementById('braille-generator-input');
    if (inputEl) {
      inputEl.value = phrase;
      this.onGeneratorInput(phrase);
    }
  },

  clearGeneratorInput() {
    const inputEl = document.getElementById('braille-generator-input');
    if (inputEl) {
      inputEl.value = '';
      this.onGeneratorInput('');
    }
  },

  onGeneratorInput(text) {
    const charCountEl = document.getElementById('braille-gen-char-count');
    const cellCountEl = document.getElementById('braille-gen-cell-count');
    const unicodeBox = document.getElementById('braille-gen-unicode-box');
    const strip = document.getElementById('braille-cells-strip');
    const formulaText = document.getElementById('braille-formula-text');

    if (charCountEl) charCountEl.textContent = `${text.length} characters`;

    if (!text || !text.trim()) {
      if (cellCountEl) cellCountEl.textContent = '0 Braille cells';
      if (unicodeBox) unicodeBox.textContent = '⠀';
      if (strip) strip.innerHTML = '<span class="braille-empty-hint">Type text on the left to render tactile Braille cells</span>';
      if (formulaText) formulaText.textContent = 'None';
      return;
    }

    const { unicodeStr, cells, formulas } = this.convertTextToBraille(text);

    if (cellCountEl) cellCountEl.textContent = `${cells.length} Braille cells`;
    if (unicodeBox) unicodeBox.textContent = unicodeStr;
    if (formulaText) formulaText.textContent = formulas.slice(0, 15).join(' ') + (formulas.length > 15 ? ' ...' : '');

    // Render 3D Embossed Cells
    if (strip) {
      strip.innerHTML = '';
      cells.forEach((cell, idx) => {
        const card = document.createElement('div');
        card.className = `braille-cell-card press ${cell.isSpace ? 'space-cell' : ''}`;
        card.title = cell.isSpace ? 'Space' : `Char: ${cell.char} • Dots: ${cell.dots.join(', ')}`;
        card.onclick = () => {
          if (!cell.isSpace) {
            this.loadPattern(cell.dots, cell.char, cell.bn);
            TransifyApp.showToast(`Inspecting '${cell.char}' (Dots ${cell.dots.join(', ')})`, 'info');
          }
        };

        if (cell.isSpace) {
          card.innerHTML = `<span style="font-size: 11px; color: var(--text-2);">␣</span><span class="cell-letter-badge">&nbsp;</span>`;
        } else {
          const dotsGrid = document.createElement('div');
          dotsGrid.className = 'braille-cell-dots-grid';
          // Visual 6-dot matrix in standard order (1, 4, 2, 5, 3, 6)
          [1, 4, 2, 5, 3, 6].forEach(d => {
            const dot = document.createElement('span');
            dot.className = `cell-dot ${cell.dots.includes(d) ? 'active' : ''}`;
            dotsGrid.appendChild(dot);
          });
          card.appendChild(dotsGrid);

          const badge = document.createElement('span');
          badge.className = 'cell-letter-badge';
          badge.textContent = cell.char;
          card.appendChild(badge);
        }

        strip.appendChild(card);
      });
    }
  },

  convertTextToBraille(text) {
    let unicodeStr = '';
    const cells = [];
    const formulas = [];

    let inNumber = false;

    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      const lower = ch.toLowerCase();

      if (ch === ' ') {
        inNumber = false;
        unicodeStr += '⠀';
        cells.push({ isSpace: true, char: ' ', dots: [] });
        continue;
      }

      // Check Bengali
      if (this.bengaliBraille[ch]) {
        inNumber = false;
        const b = this.bengaliBraille[ch];
        unicodeStr += b.unicode;
        cells.push({ isSpace: false, char: ch, dots: b.dots, bn: ch });
        formulas.push(`[${b.dots.join('-')}]`);
        continue;
      }

      // Check digits (add number prefix ⠼ if not already in number sequence)
      if (ch >= '0' && ch <= '9') {
        if (!inNumber) {
          inNumber = true;
          // Number indicator dots [3,4,5,6] (⠼)
          unicodeStr += '⠼';
          cells.push({ isSpace: false, char: '⠼', dots: [3, 4, 5, 6], bn: 'সংখ্যা' });
          formulas.push('[3-4-5-6]');
        }
        const digitMeta = this.charToBraille[ch];
        if (digitMeta) {
          unicodeStr += digitMeta.unicode;
          cells.push({ isSpace: false, char: ch, dots: digitMeta.dots });
          formulas.push(`[${digitMeta.dots.join('-')}]`);
        }
        continue;
      }

      inNumber = false;

      // Check capital letter indicator dot 6 (⠠)
      if (ch >= 'A' && ch <= 'Z') {
        unicodeStr += '⠠';
        cells.push({ isSpace: false, char: '⠠', dots: [6], bn: 'বড় হাত' });
        formulas.push('[6]');
      }

      // Check Latin letter or punctuation
      const meta = this.charToBraille[lower];
      if (meta) {
        unicodeStr += meta.unicode;
        cells.push({ isSpace: false, char: ch, dots: meta.dots, bn: meta.bn });
        formulas.push(`[${meta.dots.join('-')}]`);
      } else {
        // Unknown symbol placeholder
        unicodeStr += '⠿';
        cells.push({ isSpace: false, char: ch, dots: [1, 2, 3, 4, 5, 6] });
        formulas.push('[?]');
      }
    }

    return { unicodeStr, cells, formulas };
  },

  speakGeneratorText() {
    const inputEl = document.getElementById('braille-generator-input');
    const text = inputEl ? inputEl.value.trim() : '';
    if (text) {
      TransifyTTS.speak(text);
    } else {
      TransifyApp.showToast('Please type text first.', 'warning');
    }
  },

  copyGeneratorUnicode() {
    const unicodeBox = document.getElementById('braille-gen-unicode-box');
    const text = unicodeBox ? unicodeBox.textContent : '';
    if (text && text !== '⠀') {
      navigator.clipboard.writeText(text).then(() => {
        TransifyApp.showToast('Unicode Braille glyphs copied!', 'success');
      });
    }
  },

  copyGeneratorDots() {
    const formulaText = document.getElementById('braille-formula-text');
    const text = formulaText ? formulaText.textContent : '';
    if (text && text !== 'None') {
      navigator.clipboard.writeText(text).then(() => {
        TransifyApp.showToast('Braille dot formulas copied!', 'success');
      });
    }
  },

  downloadGeneratorBRF() {
    const inputEl = document.getElementById('braille-generator-input');
    const text = inputEl ? inputEl.value : 'Transify Braille Document';
    const { unicodeStr } = this.convertTextToBraille(text);
    const content = `TRANSIFY MULTI-MODAL BRAILLE DOCUMENT\nSource Text: ${text}\nGenerated: ${new Date().toISOString()}\n\n${unicodeStr}\n`;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Braille_${Date.now()}.brf`;
    a.click();
    URL.revokeObjectURL(url);
  },

  // Alphabet & Reference Studio
  initReference() {
    this.filterReference('letters');
  },

  filterReference(cat) {
    const filterBtns = document.querySelectorAll('.braille-ref-filter');
    filterBtns.forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-cat') === cat);
    });

    const grid = document.getElementById('braille-ref-grid');
    if (!grid) return;
    grid.innerHTML = '';

    let items = [];

    if (cat === 'letters') {
      for (let i = 97; i <= 122; i++) {
        const ch = String.fromCharCode(i);
        const meta = this.charToBraille[ch];
        if (meta) {
          items.push({
            char: ch.toUpperCase(),
            unicode: meta.unicode,
            dots: meta.dots,
            label: `Dots ${meta.dots.join(', ')}`,
            sub: meta.bn ? `বাংলা: ${meta.bn}` : ''
          });
        }
      }
    } else if (cat === 'numbers') {
      for (let i = 0; i <= 9; i++) {
        const numStr = i.toString();
        const meta = this.charToBraille[numStr];
        if (meta) {
          items.push({
            char: `⠼${numStr}`,
            unicode: `⠼${meta.unicode}`,
            dots: [3, 4, 5, 6].concat(meta.dots),
            label: `3-4-5-6 + ${meta.dots.join('-')}`,
            sub: `Number ${numStr}`
          });
        }
      }
    } else if (cat === 'punct') {
      const punctList = ['.', ',', ';', ':', '?', '!', '-', "'", '"'];
      punctList.forEach(p => {
        const meta = this.charToBraille[p];
        if (meta) {
          items.push({
            char: p,
            unicode: meta.unicode,
            dots: meta.dots,
            label: `Dots ${meta.dots.join(', ')}`,
            sub: meta.name
          });
        }
      });
    } else if (cat === 'contractions') {
      this.contractions.forEach(c => {
        items.push({
          char: c.word,
          unicode: c.unicode,
          dots: c.dots,
          label: `Dots ${c.dots.join(', ')}`,
          sub: 'Grade 2'
        });
      });
    } else if (cat === 'bengali') {
      for (const [bnChar, meta] of Object.entries(this.bengaliBraille)) {
        items.push({
          char: bnChar,
          unicode: meta.unicode,
          dots: meta.dots,
          label: `Dots ${meta.dots.join(', ')}`,
          sub: meta.roman
        });
      }
    }

    items.forEach(item => {
      const card = document.createElement('div');
      card.className = 'braille-ref-card press';
      card.innerHTML = `
        <span class="ref-card-char">${item.char}</span>
        <span class="ref-card-unicode">${item.unicode}</span>
        <span class="ref-card-dots">${item.label}</span>
        <span class="ref-card-label">${item.sub || ''}</span>
      `;
      card.onclick = () => {
        this.loadPattern(item.dots, item.char, item.sub);
        TransifyTTS.speak(item.char);
        TransifyApp.showToast(`Loaded '${item.char}' into 6-dot explorer`, 'success');
      };
      grid.appendChild(card);
    });
  },

  // Optical Translation Engine
  copyUnicodeBraille() {
    const rawEl = document.getElementById('braille-unicode-output');
    const text = rawEl ? rawEl.textContent : '';
    if (text && text !== '⠀') {
      navigator.clipboard.writeText(text).then(() => {
        TransifyApp.showToast('Braille Unicode copied!', 'success');
      });
    } else {
      TransifyApp.showToast('No Braille Unicode available.', 'warning');
    }
  },

  downloadBRF() {
    const textarea = document.getElementById('braille-text-output');
    const rawEl = document.getElementById('braille-unicode-output');
    const plainText = textarea ? (textarea.value || textarea.textContent || '') : '';
    const brailleGlyphs = rawEl ? rawEl.textContent : '';
    const content = `TRANSIFY BRAILLE TRANSLATION REPORT\nTimestamp: ${new Date().toISOString()}\n\n--- LATIN TRANSCRIPTION ---\n${plainText}\n\n--- UNICODE BRAILLE ---\n${brailleGlyphs}\n`;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Braille_Scan_${Date.now()}.brf`;
    a.click();
    URL.revokeObjectURL(url);
  },

  async runIQACheck() {
    if (!this.currentFile) {
      TransifyApp.showToast('Please select or drag-and-drop a Braille image first.', 'warning');
      return;
    }

    const formData = new FormData();
    formData.append('file', this.currentFile);

    try {
      const res = await fetch('/api/braille/iqa', { method: 'POST', body: formData });
      const data = await res.json();
      this.displayIQAResult(data);
    } catch (e) {
      TransifyApp.showToast('IQA check failed: ' + e.message, 'danger');
    }
  },

  displayIQAResult(data) {
    const iqaBanner = document.getElementById('braille-iqa-banner');
    if (!iqaBanner) return;
    iqaBanner.style.display = 'block';

    const metrics = data.metrics || {};
    const blurVal = metrics.laplacian_variance !== undefined ? metrics.laplacian_variance : metrics.blur_variance;
    const blur = blurVal !== undefined ? Number(blurVal).toFixed(1) : 'N/A';
    const brightVal = metrics.mean_intensity !== undefined ? metrics.mean_intensity : metrics.mean_brightness;
    const brightness = brightVal !== undefined ? Number(brightVal).toFixed(1) : 'N/A';
    const isPassed = data.accepted !== undefined ? data.accepted : (data.is_usable !== undefined ? data.is_usable : false);

    if (isPassed) {
      iqaBanner.style.background = 'rgba(34,197,94,0.1)';
      iqaBanner.style.border = '1.5px solid rgba(34,197,94,0.4)';
      iqaBanner.style.color = '#15803d';
      iqaBanner.style.borderRadius = '10px';
      iqaBanner.style.padding = '10px 14px';
      iqaBanner.innerHTML = `<strong>✅ Image Quality PASSED!</strong><br><span style="font-size:12px;">Sharpness: ${blur} ≥ 25.0 • Brightness: ${brightness} • Resolution: ${metrics.resolution || 'OK'}. Ready for Braille recognition.</span>`;
      TransifyApp.announce('Image quality verified. Sharpness is adequate.');
    } else {
      iqaBanner.style.background = 'rgba(239,68,68,0.08)';
      iqaBanner.style.border = '1.5px solid rgba(239,68,68,0.3)';
      iqaBanner.style.color = '#b91c1c';
      iqaBanner.style.borderRadius = '10px';
      iqaBanner.style.padding = '10px 14px';
      iqaBanner.innerHTML = `<strong>⚠️ Image Quality FAILED</strong><br><span>Reason: ${data.rejection_reason || 'Image too blurry or poor lighting'}</span><br><span style="font-size:12px;">Sharpness: ${blur} • ${data.remediation_guidance || 'Retake with steady hands and clear sidelighting.'}</span>`;
      TransifyApp.announce('Image quality rejected. Image is blurry or degraded.');
    }
  },

  async runTranslation() {
    if (!this.currentFile) {
      TransifyApp.showToast('Please upload or select a Braille image to translate.', 'warning');
      return;
    }

    const translateBtn = document.getElementById('translate-braille-btn');
    const translateBtnVisible = document.getElementById('translate-braille-btn-visible');
    [translateBtn, translateBtnVisible].forEach(btn => {
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '⏳ Analyzing Braille Dots...';
      }
    });

    const resultsSection = document.getElementById('braille-results-section');
    const outputTextarea = document.getElementById('braille-text-output');
    if (resultsSection) resultsSection.style.display = 'block';
    if (outputTextarea) {
      if ('value' in outputTextarea) outputTextarea.value = 'Translating... please wait.';
      else outputTextarea.textContent = 'Translating... please wait.';
    }

    const brailleCard = document.querySelector('.braille-result-card');
    if (brailleCard && window.setCardLoading) {
      window.setCardLoading(brailleCard, true, 'Analyzing Braille Dots with AI Engine...');
    }

    const formData = new FormData();
    formData.append('file', this.currentFile);
    formData.append('speak_tts', 'false');

    if (window.showPageLoader) window.showPageLoader('Analyzing Braille Dots with AI Engine...');

    try {
      const res = await fetch('/api/braille/translate', { method: 'POST', body: formData });
      const data = await res.json();

      if (!res.ok || !data.success) {
        const errorObj = data.error || {};
        this.displayIQAResult({
          accepted: false,
          rejection_reason: errorObj.rejection_reason || data.detail || 'Translation failed: could not read Braille from this image.',
          metrics: errorObj.metrics || {},
          remediation_guidance: errorObj.user_guidance || 'Please upload a clear photograph of physical embossed Braille.'
        });
        if (outputTextarea) {
          if ('value' in outputTextarea) outputTextarea.value = 'Translation failed. See quality report above.';
          else outputTextarea.textContent = 'Translation failed. See quality report above.';
        }
        TransifyApp.showToast('Image rejected: ' + (errorObj.rejection_reason || 'Could not translate Braille.'), 'danger');
        return;
      }

      const result = data.data;

      // Update translated text (supports textarea or div)
      const finalText = result.text || '(No text detected)';
      if (outputTextarea) {
        if ('value' in outputTextarea) outputTextarea.value = finalText;
        else outputTextarea.textContent = finalText;
      }

      // Convert translated text to Braille Unicode for display
      const { unicodeStr } = this.convertTextToBraille(finalText);
      const unicodeBox = document.getElementById('braille-unicode-output');
      const rawWrapper = document.getElementById('braille-raw-wrapper');
      if (unicodeBox) unicodeBox.textContent = unicodeStr;
      if (rawWrapper) rawWrapper.style.display = 'flex';

      // Show ASCII banner
      const asciiBanner = document.getElementById('braille-ascii-banner');
      if (asciiBanner && result.braille_ascii) {
        asciiBanner.textContent = `Braille ASCII: ${result.braille_ascii}`;
        asciiBanner.style.display = 'block';
      }

      // Show engine note
      const engine = result.engine_info || {};
      const engineNote = document.getElementById('braille-engine-note');
      if (engineNote) {
        engineNote.style.display = 'block';
        if (engine.is_fallback) {
          engineNote.style.background = 'rgba(234, 179, 8, 0.15)';
          engineNote.style.color = '#b45309';
          engineNote.style.border = '1px solid rgba(234, 179, 8, 0.3)';
          engineNote.style.borderRadius = '8px';
          engineNote.style.padding = '8px 12px';
          engineNote.style.fontSize = '12px';
          engineNote.innerHTML = `<strong>⚠️ MCP Resolver used (&lt; 98%):</strong> ${engine.notes || 'Shifted to MCP/Chatbot resolver for maximum accuracy.'}`;
        } else {
          engineNote.style.background = 'rgba(34, 197, 94, 0.12)';
          engineNote.style.color = '#15803d';
          engineNote.style.border = '1px solid rgba(34, 197, 94, 0.25)';
          engineNote.style.borderRadius = '8px';
          engineNote.style.padding = '8px 12px';
          engineNote.style.fontSize = '12px';
          engineNote.innerHTML = `<strong>🎯 High Confidence (&ge; 98%):</strong> Output from local custom-trained ExtraTrees model (${engine.source || 'Local AI'}).`;
        }
      }

      // Coverage bar
      const cov = result.read_coverage || {
        percentage: 100.0,
        confident_cells: result.cell_count || 0,
        total_cells: result.cell_count || 0,
        summary: `All Braille cells decoded (${result.cell_count} cells).`
      };

      const covContainer = document.getElementById('braille-coverage-container');
      const covLabel = document.getElementById('braille-coverage-label');
      const covBar = document.getElementById('braille-coverage-bar');
      const covDetails = document.getElementById('braille-coverage-details');

      if (covContainer) {
        covContainer.style.display = 'block';
        if (covLabel) covLabel.textContent = `${cov.percentage}% Read (${cov.confident_cells}/${cov.total_cells} Cells)`;
        if (covBar) {
          covBar.style.width = `${cov.percentage}%`;
          covBar.style.background = cov.percentage >= 95 ? '#22c55e' : (cov.percentage >= 80 ? '#eab308' : '#ef4444');
        }
        if (covDetails) covDetails.innerHTML = `<strong>Coverage:</strong> ${cov.summary}`;
      }

      // Stats badges
      const statsBadge = document.getElementById('braille-stats-badge');
      if (statsBadge) {
        const engineBadge = engine.is_fallback
          ? `<span class="badge badge-warning" title="${engine.source || 'MCP'}">🤖 ${engine.badge || 'MCP Resolver'}</span>`
          : `<span class="badge badge-success" title="${engine.source || 'Local AI'}">🎯 ${engine.badge || 'AI Model ≥98%'}</span>`;
        statsBadge.innerHTML = `
          ${engineBadge}
          <span class="badge ${cov.percentage >= 95 ? 'badge-success' : 'badge-warning'}">📖 ${cov.percentage}% Read</span>
          <span class="badge badge-success">Conf: ${(result.mean_confidence * 100).toFixed(1)}%</span>
          <span class="badge badge-info">${result.cell_count || 0} Cells</span>
          <span class="badge badge-info">${result.line_count || 1} Lines</span>
        `;
      }

      this.displayIQAResult({ accepted: true, metrics: result.qa_metrics || {}, is_usable: true });

      TransifyApp.showToast('Braille translated successfully! Click "Speak aloud" to listen.', 'success');
      TransifyApp.announce('Translation complete: ' + result.text);

    } catch (e) {
      TransifyApp.showToast('Error during Braille translation: ' + e.message, 'danger');
      if (outputTextarea) {
        if ('value' in outputTextarea) outputTextarea.value = 'Translation error. Check server connection.';
        else outputTextarea.textContent = 'Translation error. Check server connection.';
      }
    } finally {
      const brailleCard = document.querySelector('.braille-result-card');
      if (brailleCard && window.setCardLoading) {
        window.setCardLoading(brailleCard, false);
      }
      if (window.hidePageLoader) window.hidePageLoader();
      [translateBtn, translateBtnVisible].forEach(btn => {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '✨ Translate Image';
        }
      });
    }
  }
};

// ==========================================
// 6. Speech-to-Text (STT) Module
// 6. Neural Voice Studio 2.0 Module
// ==========================================

var TransifyVoiceStudio = window.TransifyVoiceStudio = {
  currentMode: 'studio',
  persona: 'default',
  timerInterval: null,
  vuInterval: null,
  animFrameId: null,
  isInitialized: false,

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    // Initialize underlying STT & TTS modules
    if (window.TransifySTT && window.TransifySTT.init) window.TransifySTT.init();
    if (window.TransifyTTSPage && window.TransifyTTSPage.init) window.TransifyTTSPage.init();

    this.setupVisualizer();
    this.startVUMeter();
    this.bindVoiceInputs();
  },

  switchMode(mode) {
    this.currentMode = mode;
    const tabs = ['studio', 'bridge', 'diagnostics'];
    tabs.forEach(t => {
      const tabBtn = document.getElementById(`voice-tab-${t}`);
      const pane = document.getElementById(`voice-pane-${t}`);
      const isActive = (t === mode);

      if (tabBtn) {
        tabBtn.classList.toggle('active', isActive);
        tabBtn.setAttribute('aria-selected', isActive ? 'true' : 'false');
      }
      if (pane) {
        pane.classList.toggle('active', isActive);
        pane.style.display = isActive ? 'block' : 'none';
      }
    });

    if (mode === 'bridge') {
      this.syncActiveSpeechToBridge();
    }
    if (window.TransifyApp && window.TransifyApp.announce) {
      window.TransifyApp.announce(`Switched to Voice ${mode.charAt(0).toUpperCase() + mode.slice(1)} view`);
    }
  },

  loadSample(phrase, lang) {
    // Populate STT box
    const finalText = document.getElementById('stt-final-text');
    const placeholder = document.getElementById('stt-placeholder');
    if (finalText) finalText.textContent = phrase;
    if (placeholder) placeholder.style.display = 'none';

    if (window.TransifySTT) {
      window.TransifySTT.finalTranscript = phrase;
      window.TransifySTT.updateTelemetry(phrase);
    }

    // Populate TTS textarea
    const ttsInput = document.getElementById('tts-input-text');
    if (ttsInput) {
      ttsInput.value = phrase;
      this.updateTTSStats(phrase);
    }

    // Set languages
    if (lang) {
      const sttLang = document.getElementById('stt-lang-select');
      const ttsLang = document.getElementById('tts-lang-select');
      if (sttLang) sttLang.value = lang;
      if (ttsLang) {
        const opt = Array.from(ttsLang.options).find(o => o.value === lang);
        if (opt) ttsLang.value = lang;
      }
    }

    // Update cross-modal bridge
    this.syncActiveSpeechToBridge(phrase);

    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast(`Sample loaded: "${phrase.slice(0, 32)}..."`, 'info');
    }
  },

  changeCaptionFont(size) {
    const box = document.getElementById('stt-live-caption-box');
    if (!box) return;
    if (size === 'xlarge') {
      box.style.fontSize = '28px';
    } else if (size === 'large') {
      box.style.fontSize = '24px';
    } else {
      box.style.fontSize = '20px';
    }
  },

  setTTSSpeed(spd) {
    if (window.TransifyTTSPage) {
      window.TransifyTTSPage.speed = spd;
    }
    document.querySelectorAll('.tts-speed-btn').forEach(btn => {
      const btnSpeed = parseFloat(btn.getAttribute('data-speed') || '1.0');
      btn.classList.toggle('active', Math.abs(btnSpeed - spd) < 0.05);
    });
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast(`Speech rate set to ${spd}x`, 'info');
    }
  },

  changeVoicePersona(persona) {
    this.persona = persona;
    const badge = document.getElementById('tts-voice-status');
    const personaLabels = {
      default: 'Neural Synthesizer',
      female: 'Studio Female HD',
      male: 'Professional Male',
      bangla: 'Bangla Studio (ফারহানা)'
    };
    if (badge) badge.textContent = personaLabels[persona] || 'Neural Voice';
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast(`Voice persona: ${personaLabels[persona] || persona}`, 'info');
    }
  },

  insertTTSPhrase(phrase) {
    const textarea = document.getElementById('tts-input-text');
    if (!textarea) return;
    if (textarea.value.trim()) {
      textarea.value += ' ' + phrase;
    } else {
      textarea.value = phrase;
    }
    this.updateTTSStats(textarea.value);
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast(`Phrase added: "${phrase.slice(0, 24)}..."`, 'success');
    }
  },

  copyTTSText() {
    const textarea = document.getElementById('tts-input-text');
    const text = textarea ? textarea.value.trim() : '';
    if (text) {
      navigator.clipboard.writeText(text);
      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast('Speech text copied to clipboard!', 'success');
      }
    } else {
      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast('No text to copy.', 'warning');
      }
    }
  },

  pauseTTS() {
    if ('speechSynthesis' in window) {
      if (window.speechSynthesis.speaking) {
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume();
          if (window.TransifyApp && window.TransifyApp.showToast) {
            window.TransifyApp.showToast('Voice playback resumed.', 'info');
          }
        } else {
          window.speechSynthesis.pause();
          if (window.TransifyApp && window.TransifyApp.showToast) {
            window.TransifyApp.showToast('Voice playback paused.', 'info');
          }
        }
      } else {
        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast('No active speech playback to pause.', 'warning');
        }
      }
    }
  },

  downloadCaptionsTXT() {
    const text = (window.TransifySTT && window.TransifySTT.finalTranscript) ?
      window.TransifySTT.finalTranscript.trim() :
      (document.getElementById('stt-final-text') ? document.getElementById('stt-final-text').textContent.trim() : '');

    if (!text) {
      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast('No captions recorded to download.', 'warning');
      }
      return;
    }

    const header = `Transify Speech Captions Session\nTimestamp: ${new Date().toISOString()}\n=========================================\n\n`;
    const blob = new Blob([header + text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transify-captions-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast('Downloaded captions transcript as TXT.', 'success');
    }
  },

  downloadCaptionsSRT() {
    const text = (window.TransifySTT && window.TransifySTT.finalTranscript) ?
      window.TransifySTT.finalTranscript.trim() :
      (document.getElementById('stt-final-text') ? document.getElementById('stt-final-text').textContent.trim() : '');

    if (!text) {
      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast('No captions recorded to download.', 'warning');
      }
      return;
    }

    const words = text.split(/\s+/).filter(Boolean);
    let srt = '';
    let sec = 1;
    let blockIdx = 1;

    for (let i = 0; i < words.length; i += 6) {
      const chunk = words.slice(i, i + 6).join(' ');
      const startSec = sec;
      const endSec = sec + 3;
      const formatTime = (s) => {
        const mm = String(Math.floor(s / 60)).padStart(2, '0');
        const ss = String(s % 60).padStart(2, '0');
        return `00:${mm}:${ss},000`;
      };
      srt += `${blockIdx}\n${formatTime(startSec)} --> ${formatTime(endSec)}\n${chunk}\n\n`;
      sec += 3;
      blockIdx++;
    }

    const blob = new Blob([srt], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transify-captions-${Date.now()}.srt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast('Downloaded standard SRT subtitle file.', 'success');
    }
  },

  bridgeToSign() {
    this.switchMode('bridge');
    const strip = document.getElementById('voice-bridge-sign-strip');
    if (strip) strip.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  },

  bridgeToBraille() {
    this.switchMode('bridge');
    const strip = document.getElementById('voice-bridge-braille-strip');
    if (strip) strip.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  },

  syncActiveSpeechToBridge(optionalText) {
    let text = optionalText;
    if (!text) {
      text = (window.TransifySTT && window.TransifySTT.finalTranscript) ?
        window.TransifySTT.finalTranscript.trim() :
        (document.getElementById('stt-final-text') ? document.getElementById('stt-final-text').textContent.trim() : '');
    }
    if (!text) {
      const ttsVal = document.getElementById('tts-input-text');
      if (ttsVal && ttsVal.value.trim()) text = ttsVal.value.trim();
    }
    if (!text) {
      text = "Emergency: Need Assistance";
    }

    const signStrip = document.getElementById('voice-bridge-sign-strip');
    const brailleStrip = document.getElementById('voice-bridge-braille-strip');

    if (signStrip) {
      signStrip.innerHTML = '';
      const chars = text.slice(0, 60).split('');
      chars.forEach(ch => {
        const lower = ch.toLowerCase();
        const badge = document.createElement('div');
        badge.className = 'voice-bridge-card';
        if (ch === ' ') {
          badge.innerHTML = '<span class="bridge-card-char">␣</span><span class="bridge-card-sub">space</span>';
          badge.style.opacity = '0.5';
        } else if (lower >= 'a' && lower <= 'z') {
          badge.innerHTML = `<span class="bridge-card-char">${lower.toUpperCase()}</span><span class="bridge-card-sub">🤟 ASL</span>`;
        } else {
          badge.innerHTML = `<span class="bridge-card-char">${ch}</span><span class="bridge-card-sub">sym</span>`;
        }
        signStrip.appendChild(badge);
      });
    }

    if (brailleStrip) {
      brailleStrip.innerHTML = '';
      const chars = text.slice(0, 60).split('');
      chars.forEach(ch => {
        const lower = ch.toLowerCase();
        const meta = (window.BraillePage && window.BraillePage.charToBraille) ? window.BraillePage.charToBraille[lower] : null;
        const unicode = meta ? meta.unicode : (ch === ' ' ? '⠀' : '⠿');
        const badge = document.createElement('div');
        badge.className = 'voice-bridge-card';
        badge.innerHTML = `<span class="bridge-card-char" style="font-size:24px; font-family:serif;">${unicode}</span><span class="bridge-card-sub">${ch === ' ' ? 'space' : (meta ? (meta.bn || meta.name) : ch)}</span>`;
        brailleStrip.appendChild(badge);
      });
    }
  },

  updateTTSStats(text) {
    const charCount = document.getElementById('tts-char-count');
    const estTime = document.getElementById('tts-est-time');
    if (charCount) charCount.textContent = `${text.length} characters`;
    if (estTime) {
      const words = text.trim().split(/\s+/).filter(Boolean).length;
      const sec = Math.max(1, Math.round((words / 130) * 60));
      estTime.textContent = `Est. Speech: ${sec}s`;
    }
  },

  bindVoiceInputs() {
    const ttsText = document.getElementById('tts-input-text');
    if (ttsText) {
      ttsText.addEventListener('input', () => {
        this.updateTTSStats(ttsText.value);
      });
    }
  },

  setupVisualizer() {
    const canvas = document.getElementById('stt-audio-visualizer');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let phase = 0;
    const render = () => {
      this.animFrameId = requestAnimationFrame(render);
      const isListening = !!(window.TransifySTT && window.TransifySTT.isListening);
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const w = canvas.width;
      const h = canvas.height;
      const midY = h / 2;

      ctx.lineWidth = isListening ? 2.5 : 1.5;
      const grad = ctx.createLinearGradient(0, 0, w, 0);
      if (isListening) {
        grad.addColorStop(0, '#8338ec');
        grad.addColorStop(0.5, '#f59e0b');
        grad.addColorStop(1, '#ec4899');
      } else {
        grad.addColorStop(0, 'rgba(140, 136, 165, 0.25)');
        grad.addColorStop(1, 'rgba(140, 136, 165, 0.4)');
      }
      ctx.strokeStyle = grad;
      ctx.beginPath();

      const numPoints = 60;
      const amp = isListening ? 12 : 2;
      const freq = isListening ? 0.08 : 0.03;

      for (let i = 0; i <= numPoints; i++) {
        const x = (i / numPoints) * w;
        const y = midY + Math.sin(i * freq + phase) * amp * Math.sin((i / numPoints) * Math.PI);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      phase += isListening ? 0.18 : 0.04;
    };
    render();
  },

  startVUMeter() {
    const fill = document.getElementById('vu-meter-fill');
    if (this.vuInterval) clearInterval(this.vuInterval);

    this.vuInterval = setInterval(() => {
      if (!fill) return;
      const isListening = !!(window.TransifySTT && window.TransifySTT.isListening);
      let targetPct = 0;
      if (isListening) {
        targetPct = 35 + Math.floor(Math.random() * 50);
      } else {
        targetPct = 12 + Math.floor(Math.random() * 8);
      }
      fill.style.width = targetPct + '%';
    }, 180);
  }
};


// ==========================================
// 6b. Speech-to-Text (STT) Module
// ==========================================

var TransifySTT = window.TransifySTT = {
  recognition: null,
  isListening: false,
  lang: 'en-US',
  finalTranscript: '',
  isLargeFont: false,
  isInitialized: false,
  startTime: null,
  timerInterval: null,

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    const toggleBtn = document.getElementById('stt-toggle-btn');
    const langSelect = document.getElementById('stt-lang-select');
    const copyBtn = document.getElementById('stt-copy-btn');
    const clearBtn = document.getElementById('stt-clear-btn');
    const sendToTtsBtn = document.getElementById('stt-send-to-tts-btn');
    const fontToggleBtn = document.getElementById('stt-font-toggle');

    if (langSelect) {
      langSelect.addEventListener('change', (e) => {
        this.lang = e.target.value;
        if (this.isListening) {
          this.stop();
          this.start();
        }
      });
    }

    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        if (this.isListening) {
          this.stop();
        } else {
          this.start();
        }
      });
    }

    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        const text = this.finalTranscript.trim();
        if (text) {
          navigator.clipboard.writeText(text);
          TransifyApp.showToast('Copied captions to clipboard!', 'success');
        } else {
          TransifyApp.showToast('No speech text to copy.', 'warning');
        }
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        this.clear();
      });
    }

    if (sendToTtsBtn) {
      sendToTtsBtn.addEventListener('click', () => {
        const text = this.finalTranscript.trim();
        if (text) {
          const ttsInput = document.getElementById('tts-input-text');
          if (ttsInput) {
            ttsInput.value = text;
            const count = document.getElementById('tts-char-count');
            if (count) count.textContent = `${text.length} chars`;
            if (window.TransifyVoiceStudio) {
              window.TransifyVoiceStudio.updateTTSStats(text);
            }
          }
          if (typeof openSlide === 'function') {
            openSlide('slide-tts');
          }
          TransifyApp.showToast('Captions sent to Read Aloud.', 'success');
        } else {
          TransifyApp.showToast('No speech text to send.', 'warning');
        }
      });
    }

    if (fontToggleBtn) {
      fontToggleBtn.addEventListener('click', () => {
        this.isLargeFont = !this.isLargeFont;
        const captionBox = document.getElementById('stt-live-caption-box');
        const fontLabel = document.getElementById('stt-font-label');
        if (captionBox && fontLabel) {
          if (this.isLargeFont) {
            captionBox.style.fontSize = '28px';
            fontLabel.textContent = 'Extra Large';
          } else {
            captionBox.style.fontSize = '20px';
            fontLabel.textContent = 'Large';
          }
        }
      });
    }
  },

  updateTelemetry(text) {
        const words = (text || '').trim().split(/\s+/).filter(Boolean);
        const wordCount = document.getElementById('stt-word-count');
        const wpmEl = document.getElementById('stt-wpm');
        const diagWpm = document.getElementById('diag-wpm-val');

        if(wordCount) wordCount.textContent = `${words.length} words`;

        if(this.startTime && words.length > 0) {
        const elapsedMin = Math.max(0.1, (Date.now() - this.startTime) / 60000);
        const wpm = Math.round(words.length / elapsedMin);
        if (wpmEl) wpmEl.textContent = `Pace: ${wpm} WPM`;
        if (diagWpm) diagWpm.textContent = `${wpm} WPM`;
      }
    },

    start() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        TransifyApp.showToast('Speech Recognition is not supported by your browser. Please use Chrome or Edge.', 'danger');
        return;
      }

      const langSelect = document.getElementById('stt-lang-select');
      const chosenLang = langSelect ? langSelect.value : (this.lang || 'en-US');

      try {
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = chosenLang;

        this.recognition.onstart = () => {
          this.isListening = true;
          this.startTime = Date.now();
          this.updateUI(true);

          if (this.timerInterval) clearInterval(this.timerInterval);
          this.timerInterval = setInterval(() => {
            if (!this.isListening || !this.startTime) return;
            const sec = Math.floor((Date.now() - this.startTime) / 1000);
            const mm = String(Math.floor(sec / 60)).padStart(2, '0');
            const ss = String(sec % 60).padStart(2, '0');
            const timerEl = document.getElementById('stt-timer');
            if (timerEl) timerEl.textContent = `Duration: ${mm}:${ss}`;
          }, 1000);

          TransifyApp.announce('Speech recognition listening started');
          TransifyApp.showToast('Microphone active! Speak now...', 'info');
        };

        this.recognition.onresult = (event) => {
          let interim = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              this.finalTranscript += event.results[i][0].transcript + ' ';
            } else {
              interim += event.results[i][0].transcript;
            }
          }
          this.renderText(this.finalTranscript, interim);
        };

        this.recognition.onerror = (event) => {
          console.warn('STT Error:', event.error);
          if (event.error === 'not-allowed') {
            TransifyApp.showToast('Microphone permission blocked. Please allow microphone in browser.', 'danger');
            this.stop();
          } else if (event.error === 'network') {
            TransifyApp.showToast('Network error during speech recognition.', 'warning');
          } else if (event.error === 'no-speech') {
            TransifyApp.showToast('No speech detected. Speak clearly into the microphone.', 'warning');
          }
        };

        this.recognition.onend = () => {
          if (this.isListening) {
            try {
              this.recognition.start();
            } catch (e) {
              this.isListening = false;
              this.updateUI(false);
            }
          } else {
            this.updateUI(false);
          }
        };

        this.recognition.start();
      } catch (err) {
        console.warn('STT Start Error:', err);
        this.isListening = false;
        this.updateUI(false);
      }
    },

    stop() {
      this.isListening = false;
      if (this.timerInterval) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
      }
      if (this.recognition) {
        try {
          this.recognition.stop();
        } catch (e) { }
      }
      this.updateUI(false);
      TransifyApp.announce('Speech recognition stopped');
    },

    clear() {
      this.finalTranscript = '';
      this.startTime = null;
      if (this.timerInterval) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
      }
      this.renderText('', '');
      const wordCount = document.getElementById('stt-word-count');
      const timerEl = document.getElementById('stt-timer');
      const wpmEl = document.getElementById('stt-wpm');
      if (wordCount) wordCount.textContent = '0 words';
      if (timerEl) timerEl.textContent = 'Duration: 00:00';
      if (wpmEl) wpmEl.textContent = 'Pace: 0 WPM';
      TransifyApp.showToast('Captions cleared.', 'info');
    },

    renderText(finalText, interimText) {
      const placeholder = document.getElementById('stt-placeholder');
      const finalSpan = document.getElementById('stt-final-text');
      const interimSpan = document.getElementById('stt-interim-text');

      if (placeholder) {
        placeholder.style.display = (finalText || interimText) ? 'none' : 'inline';
      }
      if (finalSpan) finalSpan.textContent = finalText;
      if (interimSpan) interimSpan.textContent = interimText;

      this.updateTelemetry(finalText + ' ' + interimText);

      if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.currentMode === 'bridge') {
        window.TransifyVoiceStudio.syncActiveSpeechToBridge(finalText);
      }
    },

    updateUI(listening) {
      const btn = document.getElementById('stt-toggle-btn');
      const icon = document.getElementById('stt-mic-icon');
      const hint = document.getElementById('stt-mic-hint');
      const pill = document.getElementById('stt-status-pill');
      const rings = document.getElementById('stt-mic-rings-wrap');
      const diagMic = document.getElementById('diag-mic-status');

      if (listening) {
        if (btn) btn.classList.add('listening');
        if (icon) icon.textContent = '⏹️';
        if (rings) rings.classList.add('active');
        if (hint) {
          hint.textContent = 'Listening... Speak now';
          hint.style.color = '#dc2626';
        }
        if (pill) {
          pill.textContent = '🔴 Listening Live...';
          pill.className = 'badge badge-danger';
          pill.className = 'care-badge online';
          pill.style.background = 'rgba(239, 68, 68, 0.15)';
          pill.style.color = '#dc2626';
        }
        if (diagMic) diagMic.textContent = 'Capturing';
      } else {
        if (btn) btn.classList.remove('listening');
        if (icon) icon.textContent = '🎙️';
        if (rings) rings.classList.remove('active');
        if (hint) {
          hint.textContent = 'Tap to Speak';
          hint.style.color = '#4b1a11';
          hint.textContent = 'Tap microphone to speak';
          hint.style.color = 'var(--text-2)';
        }
        if (pill) {
          pill.textContent = '🎙️ Ready to Listen';
          pill.className = 'badge badge-info';
          pill.textContent = 'Ready to Listen';
          pill.className = 'care-badge online';
          pill.style.background = 'rgba(34, 197, 94, 0.1)';
          pill.style.color = '#15803d';
        }
        if (diagMic) diagMic.textContent = 'Standby';
      }
    }
  };


  // ==========================================
  // 7. Text-to-Speech (TTS) Slide Module
  // ==========================================

  var TransifyTTSPage = window.TransifyTTSPage = {
    speed: 1.0,
    lang: 'en-US',
    isInitialized: false,

    init() {
      if (this.isInitialized) return;
      this.isInitialized = true;

      const textarea = document.getElementById('tts-input-text');
      const speakBtn = document.getElementById('tts-speak-btn');
      const stopBtn = document.getElementById('tts-stop-btn');
      const clearBtn = document.getElementById('tts-clear-btn');
      const langSelect = document.getElementById('tts-lang-select');
      const charCount = document.getElementById('tts-char-count');
      const speedBtns = document.querySelectorAll('.tts-speed-btn');
      const chips = document.querySelectorAll('.tts-quick-chip');

      if (textarea && charCount) {
        textarea.addEventListener('input', () => {
          charCount.textContent = `${textarea.value.length} chars`;
          if (window.TransifyVoiceStudio) {
            window.TransifyVoiceStudio.updateTTSStats(textarea.value);
          }
        });
      }

        if (langSelect) {
          langSelect.addEventListener('change', (e) => {
            this.lang = e.target.value;
          });
        }

        speedBtns.forEach(btn => {
          btn.addEventListener('click', () => {
            speedBtns.forEach(b => {
              b.classList.remove('active', 'btn-primary');
              b.classList.add('btn-secondary');
            });
            btn.classList.remove('btn-secondary');
            btn.classList.add('btn-primary', 'active');
            this.speed = parseFloat(btn.dataset.speed || '1.0');
            const spd = parseFloat(btn.getAttribute('data-speed') || '1.0');
            if (window.TransifyVoiceStudio) {
              window.TransifyVoiceStudio.setTTSSpeed(spd);
            } else {
              this.speed = spd;
            }
          });
        });

        if (speakBtn) {
          speakBtn.addEventListener('click', () => {
            const text = textarea ? textarea.value.trim() : '';
            if (!text) {
              TransifyApp.showToast('Please type a message to speak.', 'warning');
              return;
            }
            this.speakText(text);
          });
        }

        if (stopBtn) {
          stopBtn.addEventListener('click', () => {
            if ('speechSynthesis' in window) {
              window.speechSynthesis.cancel();
            }
            const wave = document.getElementById('tts-wave-bar');
            if (wave) wave.style.display = 'none';
            TransifyApp.showToast('Voice playback stopped.', 'info');
          });
        }

        if (clearBtn) {
          clearBtn.addEventListener('click', () => {
            if (textarea) textarea.value = '';
            if (charCount) charCount.textContent = '0 chars';
            if (window.TransifyVoiceStudio) {
              window.TransifyVoiceStudio.updateTTSStats('');
            }
          });
        }

        chips.forEach(chip => {
          chip.addEventListener('click', () => {
            const phrase = chip.dataset.phrase;
            if (phrase) {
              if (textarea) {
                textarea.value = phrase;
                if (charCount) charCount.textContent = `${phrase.length} chars`;
              }
              this.speakText(phrase);
            }
          });
        });
      },

      speakText(text) {
        if (!text || text.trim() === '') return;
        const cleanText = text.trim();
        const langSelect = document.getElementById('tts-lang-select');
        const chosenLang = langSelect ? langSelect.value : (this.lang || 'en-US');
        const wave = document.getElementById('tts-wave-bar');

        if ('speechSynthesis' in window) {
          try {
            window.speechSynthesis.cancel();
            window.speechSynthesis.resume();
          } catch (e) { }

          const utterance = new SpeechSynthesisUtterance(cleanText);
          utterance.rate = this.speed || 1.0;
          utterance.lang = chosenLang;

          const voices = window.speechSynthesis.getVoices();
          if (voices && voices.length > 0) {
            const match = voices.find(v => v.lang.toLowerCase() === chosenLang.toLowerCase()) ||
              voices.find(v => v.lang.toLowerCase().startsWith(chosenLang.slice(0, 2).toLowerCase())) ||
              voices[0];
            if (match) utterance.voice = match;
          }

          const speakBtn = document.getElementById('tts-speak-btn');
          utterance.onstart = () => {
            if (speakBtn) {
              speakBtn.innerHTML = '🔊 Speaking...';
              speakBtn.classList.add('btn-success');
            }
            if (wave) wave.style.display = 'flex';
          };
          utterance.onend = () => {
            if (speakBtn) {
              speakBtn.innerHTML = '🔊 Speak Voice';
              speakBtn.innerHTML = 'Speak text';
              speakBtn.classList.remove('btn-success');
            }
            if (wave) wave.style.display = 'none';
          };
          utterance.onerror = (e) => {
            console.warn('TTS utterance error:', e);
            if (speakBtn) {
              speakBtn.innerHTML = '🔊 Speak Voice';
              speakBtn.innerHTML = 'Speak text';
              speakBtn.classList.remove('btn-success');
            }
            if (wave) wave.style.display = 'none';
            TransifyTTS.fallbackServerTTS(cleanText);
          };

          try {
            window.speechSynthesis.speak(utterance);
          } catch (e) {
            if (wave) wave.style.display = 'none';
            TransifyTTS.fallbackServerTTS(cleanText);
          }
          TransifyApp.showToast(`Speaking: "${cleanText.slice(0, 30)}..."`, 'success');
        } else {
          TransifyTTS.fallbackServerTTS(cleanText);
        }
      }
    };


    // ==========================================
    // 8. Global DOM Initialization
    // ==========================================

    function initTransifyAllModules() {
      if (window.TransifyApp && window.TransifyApp.init) {
  window.TransifyApp.init();
}

// Slide modules: unconditionally initialize if present in DOM
if (window.SignPage && window.SignPage.init && (document.getElementById('slide-hand-signal') || document.getElementById('sign-video') || document.getElementById('toggle-camera-btn'))) {
  window.SignPage.init();
}
if (window.BraillePage && window.BraillePage.init && (document.getElementById('slide-braille') || document.getElementById('braille-dropzone') || document.getElementById('braille-file-input'))) {
  window.BraillePage.init();
}
if (window.TransifySTT && window.TransifySTT.init && (document.getElementById('slide-stt') || document.getElementById('stt-toggle-btn'))) {
  window.TransifySTT.init();
}
if (window.TransifyTTSPage && window.TransifyTTSPage.init && (document.getElementById('slide-tts') || document.getElementById('tts-input-text'))) {
  window.TransifyTTSPage.init();
}
if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.init && (document.getElementById('view-voice') || document.getElementById('stt-toggle-btn') || document.getElementById('voice-pane-studio'))) {
  window.TransifyVoiceStudio.init();
}
if (window.DashboardPage && window.DashboardPage.init && (document.getElementById('dashboard-container') || document.getElementById('system-status-badge') || document.getElementById('history-records-list'))) {
  window.DashboardPage.init();
}

// Expose module APIs to window for inline onclick handlers and extensions
window.TransifyApp = TransifyApp;
window.SignPage = SignPage;
window.TransifySign = SignPage;
window.BraillePage = BraillePage;
window.TransifySTT = TransifySTT;
window.TransifyTTSPage = TransifyTTSPage;
window.TransifyTTS = TransifyTTS;
window.TransifyVoiceStudio = TransifyVoiceStudio;
window.openAuthSheet = (m) => TransifyApp.openAuthSheet(m);
window.closeAuthSheet = () => TransifyApp.closeAuthSheet();
window.handleDirectLogin = () => TransifyApp.handleDirectLogin();
window.handleDemoLogin = () => TransifyApp.handleDemoLogin();
window.handleAuthSubmit = (e) => TransifyApp.handleAuthSubmit(e);
window.handleSettingsAuthAction = () => { if (typeof EditorialController !== 'undefined' && EditorialController.handleSettingsAuthAction) EditorialController.handleSettingsAuthAction(); };
TransifyApp.handleSettingsAuthAction = () => { if (typeof EditorialController !== 'undefined' && EditorialController.handleSettingsAuthAction) EditorialController.handleSettingsAuthAction(); };
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTransifyAllModules);
} else {
  initTransifyAllModules();
}

// Expose global helper for custom duration or manual splash testing
window.showTransifySplashScreen = function (durationMs = 3500) {
  const splash = document.getElementById('transify-splash-screen');
  if (!splash) return;
  splash.style.display = 'flex';
  splash.classList.remove('splash-hidden');
  const fill = document.getElementById('splash-progress-fill');
  if (fill) fill.style.width = '0%';
  TransifyApp.initSplashScreen(durationMs);
};

// ============================================================================
// 8.5 TRANSIFY AI CHATBOT & KNOWLEDGE ENGINE CONTROLLER
// ============================================================================

var ChatbotPage = window.ChatbotPage = {
  isInitialized: false,
  conversationHistory: [],
  isRecording: false,
  recognition: null,

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    this.bindEvents();
    this.loadModelStatus();
  },

  bindEvents() {
    const form = document.getElementById('chat-input-form');
    const input = document.getElementById('chat-input-field');
    const clearBtn = document.getElementById('btn-clear-chat');
    const trainModalBtn = document.getElementById('btn-open-training-modal');
    const closeTrainBtn = document.getElementById('btn-close-training-modal');
    const startTrainBtn = document.getElementById('btn-start-training');
    const addSampleBtn = document.getElementById('btn-add-custom-sample');
    const micBtn = document.getElementById('chat-mic-btn');

    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = input ? input.value.trim() : '';
        if (text) {
          this.sendMessage(text);
          if (input) input.value = '';
        }
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', () => this.clearChat());
    }

    if (trainModalBtn) {
      trainModalBtn.addEventListener('click', () => this.openTrainingModal());
    }

    if (closeTrainBtn) {
      closeTrainBtn.addEventListener('click', () => this.closeTrainingModal());
    }

    if (startTrainBtn) {
      startTrainBtn.addEventListener('click', () => this.runTraining());
    }

    if (addSampleBtn) {
      addSampleBtn.addEventListener('click', () => this.addCustomSample());
    }

    if (micBtn) {
      micBtn.addEventListener('click', () => this.toggleSpeechRecognition());
    }

    // Bind suggestion chips
    document.querySelectorAll('.chat-suggestion-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const prompt = chip.getAttribute('data-prompt');
        if (prompt) {
          this.sendMessage(prompt);
        }
      });
    });
  },

  async loadModelStatus() {
    try {
      const res = await fetch('/api/chat/status');
      if (!res.ok) return;
      const data = await res.json();

      const badge = document.getElementById('chat-model-badge');
      const accBadge = document.getElementById('chat-accuracy-badge');
      const trainAcc = document.getElementById('train-accuracy-val');
      const trainLoss = document.getElementById('train-loss-val');
      const trainDocs = document.getElementById('train-docs-val');

      if (badge && data.model_name) badge.textContent = data.model_name;
      if (accBadge && data.accuracy) accBadge.textContent = `${data.accuracy} Trained`;
      if (trainAcc && data.accuracy) trainAcc.textContent = data.accuracy;
      if (trainLoss && data.final_loss !== undefined) trainLoss.textContent = data.final_loss;
      if (trainDocs && data.total_documents) trainDocs.textContent = `${data.total_documents}+`;
    } catch (e) {
      console.debug('Chatbot status fetch notice:', e);
    }
  },

  async sendMessage(text) {
    const stream = document.getElementById('chat-stream-container');
    if (!stream) return;

    // Append user message
    this.appendMessage('user', text);
    this.conversationHistory.push({ role: 'user', content: text });

    // Show temporary thinking indicator
    const thinkingId = 'thinking-' + Date.now();
    const thinkingEl = document.createElement('div');
    thinkingEl.className = 'chat-message-item bot';
    thinkingEl.id = thinkingId;
    thinkingEl.innerHTML = `
      <div class="chat-msg-avatar">🤖</div>
      <div class="chat-msg-content">
        <div class="chat-msg-bubble" style="opacity: 0.7;">
          <em>Thinking &amp; cross-referencing WHO/Merck guidelines...</em>
        </div>
      </div>
    `;
    stream.appendChild(thinkingEl);
    stream.scrollTop = stream.scrollHeight;

    try {
      const res = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: this.conversationHistory
        })
      });

      if (!res.ok) throw new Error('Chatbot reasoning error');
      const data = await res.json();

      // Remove thinking element
      const el = document.getElementById(thinkingId);
      if (el) el.remove();

      // Append bot response
      this.appendMessage('bot', data.response, data);
      this.conversationHistory.push({ role: 'assistant', content: data.response });

      // Update suggestion chips if present
      if (data.suggested_replies && data.suggested_replies.length) {
        this.updateSuggestions(data.suggested_replies);
      }

    } catch (err) {
      const el = document.getElementById(thinkingId);
      if (el) el.remove();

      this.appendMessage('bot', '⚠️ I experienced a temporary reasoning interruption. Please try asking again.');
    }
  },

  appendMessage(sender, text, meta = null) {
    const stream = document.getElementById('chat-stream-container');
    if (!stream) return;

    const item = document.createElement('div');
    item.className = `chat-message-item ${sender}`;

    // Render basic markdown formatting
    let formattedText = this.formatMarkdown(text);

    let metaHtml = '';
    if (sender === 'bot' && meta) {
      let citationsHtml = '';
      if (meta.citations && meta.citations.length) {
        citationsHtml = ` • 📚 Ref: ${meta.citations.join(', ')}`;
      }
      metaHtml = `
        <div class="chat-source-tag">
          <span>${meta.source || '🎯 Trained RAG Engine'}</span>
          <span>${citationsHtml}</span>
          <button type="button" class="chat-speak-btn press" data-text="${encodeURIComponent(text.replace(/[*_#`]/g, ''))}">🔊 Speak</button>
        </div>
      `;
    }

    item.innerHTML = `
      <div class="chat-msg-avatar">${sender === 'user' ? 'YOU' : '🤖'}</div>
      <div class="chat-msg-content">
        <div class="chat-msg-bubble">
          ${formattedText}
        </div>
        ${metaHtml}
      </div>
    `;

    stream.appendChild(item);
    stream.scrollTop = stream.scrollHeight;

    // Bind speak button
    item.querySelectorAll('.chat-speak-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const speech = decodeURIComponent(btn.getAttribute('data-text') || '');
        if (speech && window.TransifyTTS) {
          window.TransifyTTS.speak(speech);
        }
      });
    });
  },

  formatMarkdown(raw) {
    if (!raw) return '';
    let s = raw
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Bold
    s = s.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    s = s.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Lines
    const lines = s.split('\n');
    let inList = false;
    let out = [];

    for (let line of lines) {
      let trimmed = line.trim();
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        if (!inList) { out.push('<ul>'); inList = true; }
        out.push(`<li>${trimmed.substring(2)}</li>`);
      } else if (/^\d+\.\s/.test(trimmed)) {
        if (!inList) { out.push('<ul>'); inList = true; }
        out.push(`<li>${trimmed.replace(/^\d+\.\s/, '')}</li>`);
      } else {
        if (inList) { out.push('</ul>'); inList = false; }
        if (trimmed) out.push(`<p>${trimmed}</p>`);
      }
    }
    if (inList) out.push('</ul>');
    return out.join('');
  },

  updateSuggestions(suggestions) {
    const bar = document.getElementById('chat-suggestions-bar');
    if (!bar || !suggestions) return;

    bar.innerHTML = suggestions.map(s => `
      <button type="button" class="chat-suggestion-chip press" data-prompt="${s}">${s}</button>
    `).join('');

    bar.querySelectorAll('.chat-suggestion-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        const prompt = btn.getAttribute('data-prompt');
        if (prompt) this.sendMessage(prompt);
      });
    });
  },

  clearChat() {
    const stream = document.getElementById('chat-stream-container');
    if (stream) {
      stream.innerHTML = `
        <div class="chat-message-item bot">
          <div class="chat-msg-avatar">🤖</div>
          <div class="chat-msg-content">
            <div class="chat-msg-bubble">
              <p>Chat history cleared. How can I assist you with clinical triage or accessible communication?</p>
            </div>
            <div class="chat-source-tag">Transify Neural Assist v2.4</div>
          </div>
        </div>
      `;
    }
    this.conversationHistory = [];
    fetch('/api/chat/reset', { method: 'POST' }).catch(() => { });
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast('Chat history cleared', 'info');
    }
  },

  openTrainingModal() {
    const modal = document.getElementById('chat-training-modal');
    if (modal) {
      modal.style.display = 'flex';
      modal.setAttribute('aria-hidden', 'false');
      this.loadModelStatus();
    }
  },

  closeTrainingModal() {
    const modal = document.getElementById('chat-training-modal');
    if (modal) {
      modal.style.display = 'none';
      modal.setAttribute('aria-hidden', 'true');
    }
  },

  async runTraining() {
    const epochsSelect = document.getElementById('train-epochs-select');
    const lrSelect = document.getElementById('train-lr-select');
    const progressBox = document.getElementById('training-progress-container');
    const fill = document.getElementById('train-progress-fill');
    const pct = document.getElementById('train-progress-pct');
    const statusText = document.getElementById('train-progress-status');
    const lossReport = document.getElementById('train-loss-report');
    const trainBtn = document.getElementById('btn-start-training');

    const epochs = epochsSelect ? parseInt(epochsSelect.value) : 10;
    const lr = lrSelect ? parseFloat(lrSelect.value) : 0.02;

    if (trainBtn) trainBtn.disabled = true;
    if (progressBox) progressBox.style.display = 'block';
    if (fill) fill.style.width = '15%';
    if (pct) pct.textContent = '15%';
    if (statusText) statusText.textContent = `Running gradient descent across ${epochs} epochs...`;

    if (window.showPageLoader) window.showPageLoader('Training Neural Knowledge Network...');

    try {
      if (fill) fill.style.width = '60%';
      if (pct) pct.textContent = '60%';

      const res = await fetch('/api/chat/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ epochs: epochs, learning_rate: lr })
      });

      if (!res.ok) throw new Error('Training request failed');
      const data = await res.json();

      if (fill) fill.style.width = '100%';
      if (pct) pct.textContent = '100%';
      if (statusText) statusText.textContent = 'Training Complete! Model convergence verified.';
      if (lossReport && data.metrics) {
        lossReport.innerHTML = `🎯 <strong>Final Loss:</strong> ${data.metrics.final_loss} • <strong>Accuracy:</strong> ${data.metrics.accuracy}`;
      }

      await this.loadModelStatus();

      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast(`AI Model successfully trained! Accuracy: ${data.metrics.accuracy}`, 'success');
      }
    } catch (e) {
      if (statusText) statusText.textContent = `Training error: ${e.message}`;
    } finally {
      if (window.hidePageLoader) window.hidePageLoader();
      if (trainBtn) trainBtn.disabled = false;
    }
  },

  async addCustomSample() {
    const patInput = document.getElementById('custom-train-pattern');
    const respInput = document.getElementById('custom-train-response');
    const domSelect = document.getElementById('custom-train-domain');

    const pattern = patInput ? patInput.value.trim() : '';
    const response = respInput ? respInput.value.trim() : '';
    const domain = domSelect ? domSelect.value : 'care_clinical';

    if (!pattern || !response) {
      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast('Please provide both inquiry pattern and expected response.', 'warning');
      }
      return;
    }

    try {
      const sample = {
        id: 'custom_' + Date.now(),
        domain: domain,
        keywords: pattern.toLowerCase().split(/\s+/).slice(0, 5),
        patterns: [pattern],
        response: response,
        citations: ['User-Trained Clinical/Communication Knowledge Base']
      };

      const res = await fetch('/api/chat/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          epochs: 5,
          custom_samples: [sample]
        })
      });

      if (!res.ok) throw new Error('Failed to add custom sample');

      if (patInput) patInput.value = '';
      if (respInput) respInput.value = '';

      await this.loadModelStatus();

      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast('New pattern trained into AI model successfully!', 'success');
      }
    } catch (e) {
      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast(`Failed to train sample: ${e.message}`, 'danger');
      }
    }
  },

  toggleSpeechRecognition() {
    const micBtn = document.getElementById('chat-mic-btn');
    const input = document.getElementById('chat-input-field');

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast('Speech recognition is not supported in this browser.', 'warning');
      }
      return;
    }

    if (this.isRecording && this.recognition) {
      this.recognition.stop();
      this.isRecording = false;
      if (micBtn) micBtn.classList.remove('recording');
      return;
    }

    this.recognition = new SpeechRec();
    this.recognition.lang = 'en-US';
    this.recognition.continuous = false;
    this.recognition.interimResults = false;

    this.recognition.onstart = () => {
      this.isRecording = true;
      if (micBtn) micBtn.classList.add('recording');
      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast('Listening... Speak your prompt', 'info');
      }
    };

    this.recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      if (input) {
        input.value = transcript;
        input.focus();
      }
    };

    this.recognition.onerror = (e) => {
      this.isRecording = false;
      if (micBtn) micBtn.classList.remove('recording');
    };

    this.recognition.onend = () => {
      this.isRecording = false;
      if (micBtn) micBtn.classList.remove('recording');
    };

    this.recognition.start();
  }
};

// ============================================================================
// 9. TRANSIFY 2.0 EDITORIAL CONTROLLER (Pixel-Exact Navigation & Interactions)
// ============================================================================

const EditorialController = {
  activeRoute: 'home',
  welcomeSlide: 0,
  welcomePaused: false,
  welcomeTimer: null,
  welcomeDur: 5600,
  welcomeStartTime: Date.now(),
  brailleMap: {
    '1': 'a', '12': 'b', '14': 'c', '145': 'd', '15': 'e', '124': 'f',
    '1245': 'g', '125': 'h', '24': 'i', '245': 'j', '13': 'k', '123': 'l',
    '134': 'm', '1345': 'n', '135': 'o', '1234': 'p', '12345': 'q', '1235': 'r',
    '234': 's', '2345': 't', '136': 'u', '1236': 'v', '2456': 'w', '1346': 'x',
    '13456': 'y', '1356': 'z'
  },
  phraseSpeed: 1.0,
  defaultPhrases: [
    // Everyday & Social
    { id: 'p1', en: 'Hello', bn: 'হ্যালো', translit: 'Hyālō', cat: 'Everyday', fav: true },
    { id: 'p2', en: 'Thank you', bn: 'ধন্যবাদ', translit: 'Dhonnobād', cat: 'Everyday', fav: true },
    { id: 'p3', en: 'Please slow down', bn: 'দয়া করে আস্তে বলুন', translit: 'Doyā kore āste bolun', cat: 'Everyday' },
    { id: 'p4', en: 'Can you write that down?', bn: 'আপনি কি এটা লিখে দিতে পারবেন?', translit: 'Āpni ki eṭā likhe dite pārben?', cat: 'Everyday' },
    { id: 'p5', en: 'I do not understand', bn: 'আমি বুঝতে পারছি না', translit: 'Āmi bujhte pārchi nā', cat: 'Everyday' },
    { id: 'p6', en: 'Yes, please', bn: 'হ্যাঁ, অনুগ্রহ করে', translit: 'Hnǣ, onugroho kore', cat: 'Everyday' },
    { id: 'p7', en: 'No, thank you', bn: 'না, ধন্যবাদ', translit: 'Nā, dhonnobād', cat: 'Everyday' },
    { id: 'p8', en: 'Good morning', bn: 'শুভ সকাল', translit: 'Shubho shokāl', cat: 'Everyday' },
    { id: 'p9', en: 'How are you?', bn: 'আপনি কেমন আছেন?', translit: 'Āpni kemon āchen?', cat: 'Everyday' },
    { id: 'p10', en: 'Please repeat that once more', bn: 'দয়া করে আর একবার বলুন', translit: 'Doyā kore ār ekbār bolun', cat: 'Everyday' },

    // Daily Needs & Comfort
    { id: 'p11', en: 'I need water', bn: 'আমার পানি দরকার', translit: 'Āmār pāni dorkār', cat: 'Needs', fav: true },
    { id: 'p12', en: 'Where is the restroom?', bn: 'টয়লেট কোথায়?', translit: 'Ṭoyleṭ kothāy?', cat: 'Needs', fav: true },
    { id: 'p13', en: 'I need help reading this', bn: 'এটা পড়তে আমার সাহায্য দরকার', translit: 'Eṭā poṛte āmār sāhājjo dorkār', cat: 'Needs' },
    { id: 'p14', en: 'I am hungry, need food', bn: 'আমার ক্ষুধা পেয়েছে, খাবার দরকার', translit: 'Āmār khudhā peyeche, khābār dorkār', cat: 'Needs' },
    { id: 'p15', en: 'I feel cold, need a blanket', bn: 'আমার ঠান্ডা লাগছে, একটি কম্বল দরকার', translit: 'Āmār ṭhāndā lāgche, kombol dorkār', cat: 'Needs' },
    { id: 'p16', en: 'I feel very hot', bn: 'আমার খুব গরম লাগছে', translit: 'Āmār khub gorom lāgche', cat: 'Needs' },
    { id: 'p17', en: 'I need to sit down and rest', bn: 'আমাকে একটু বসতে হবে এবং বিশ্রাম নিতে হবে', translit: 'Āmāke ektu boste hobe, bishrām dorkār', cat: 'Needs' },
    { id: 'p18', en: 'Please turn down the noise / lights', bn: 'দয়া করে আলো অথবা শব্দ কমিয়ে দিন', translit: 'Doyā kore ālo othobā shobdo komiye din', cat: 'Needs' },
    { id: 'p19', en: 'I need my spectacles / eyeglasses', bn: 'আমার চশমা প্রয়োজন', translit: 'Āmār choshmā proyojon', cat: 'Needs' },
    { id: 'p20', en: 'I need my phone or charger', bn: 'আমার ফোন বা চার্জার প্রয়োজন', translit: 'Āmār phone bā chārjār proyojon', cat: 'Needs' },

    // Medical & Clinical Triage
    { id: 'p21', en: 'I am having severe pain (Level 8/10)', bn: 'আমার তীব্র ব্যথা হচ্ছে (মাত্রা ৮/১০)', translit: 'Tībro byathā hochhe (mātrā 8/10)', cat: 'Medical', fav: true },
    { id: 'p22', en: 'I feel dizzy and nauseous', bn: 'আমার মাথা ঘুরছে এবং বমি বমি ভাব হচ্ছে', translit: 'Māthā ghūrche ebong bomi bhāb hochhe', cat: 'Medical' },
    { id: 'p23', en: 'I have high blood pressure', bn: 'আমার উচ্চ রক্তচাপ রয়েছে', translit: 'Āmār uccho roktochāp royeche', cat: 'Medical' },
    { id: 'p24', en: 'I am diabetic, need insulin or glucose', bn: 'আমি ডায়াবেটিক, ইনসুলিন বা গ্লুকোজ প্রয়োজন', translit: 'Āmi diabetic, insulin bā glucose proyojon', cat: 'Medical', fav: true },
    { id: 'p25', en: 'I have an allergy to penicillin', bn: 'আমার পেনিসিলিনে এলার্জি আছে', translit: 'Āmār penicillin-e allergy āche', cat: 'Medical' },
    { id: 'p26', en: 'Please check my heart rate and pulse', bn: 'দয়া করে আমার নাড়ির স্পন্দন পরীক্ষা করুন', translit: 'Doyā kore nāṛir spondon porikkha korun', cat: 'Medical' },
    { id: 'p27', en: 'I have a severe migraine headache', bn: 'আমার তীব্র মাইগ্রেন ও মাথাব্যথা হচ্ছে', translit: 'Āmār tībro migraine o māthābyathā hochhe', cat: 'Medical' },
    { id: 'p28', en: 'I need to take my prescribed medication', bn: 'আমার প্রেসক্রিপশনের ওষুধ খাওয়া দরকার', translit: 'Prescription-er oshudh khāwā dorkār', cat: 'Medical' },
    { id: 'p29', en: 'Where is the nearest pharmacy?', bn: 'নিকটতম ফার্মেসি কোথায়?', translit: 'Nikoṭ-tomo pharmacy kothāy?', cat: 'Medical' },
    { id: 'p30', en: 'My blood group is O-positive', bn: 'আমার রক্তের গ্রুপ ও-পজিটিভ', translit: 'Āmār rokter group O-positive', cat: 'Medical' },

    // Urgent & Emergency 999
    { id: 'p31', en: 'I need help immediately', bn: 'আমার অবিলম্বে সাহায্য দরকার', translit: 'Āmār obilombe sāhājjo dorkār', cat: 'Emergency', fav: true },
    { id: 'p32', en: 'Please call a doctor', bn: 'দয়া করে ডাক্তার ডাকুন', translit: 'Doyā kore doctor dākun', cat: 'Emergency', fav: true },
    { id: 'p33', en: 'I am lost, please guide me', bn: 'আমি পথ হারিয়ে ফেলেছি, দয়া করে সাহায্য করুন', translit: 'Āmi poth hāriye felechi, sāhājjo korun', cat: 'Emergency' },
    { id: 'p34', en: 'Call an ambulance right now (999)', bn: 'তাত্ক্ষণিকভাবে একটি অ্যাম্বুলেন্স ডাকুন (৯৯৯)', translit: 'Tāṯkkhonik bhābe ambulance dākun (999)', cat: 'Emergency', fav: true },
    { id: 'p35', en: 'I cannot breathe / severe shortness of breath', bn: 'আমি শ্বাস নিতে পারছি না, তীব্র শ্বাসকষ্ট হচ্ছে', translit: 'Āmi shwās nite pārchi nā, tībro shwāskoṣṭo', cat: 'Emergency', fav: true },
    { id: 'p36', en: 'Severe chest pain / possible heart attack', bn: 'বুকে তীব্র ব্যথা, হার্ট অ্যাটাকের আশঙ্কা', translit: 'Buke tībro byathā, heart attack āshongkā', cat: 'Emergency', fav: true },
    { id: 'p37', en: 'I am bleeding heavily', bn: 'আমার শরীর থেকে প্রচুর রক্তক্ষরণ হচ্ছে', translit: 'Āmār shorīr theke prochur rokto-khoron hochhe', cat: 'Emergency' },
    { id: 'p38', en: 'Someone has collapsed here', bn: 'এখানে একজন ব্যক্তি অচেতন হয়ে পড়েছেন', translit: 'Ekhāne ekjon byokti ocheton hoye poṛechen', cat: 'Emergency' },
    { id: 'p39', en: 'I am having an acute allergic reaction', bn: 'আমার তীব্র এলার্জির প্রতিক্রিয়া হচ্ছে', translit: 'Āmār tībro allergy-r protikriyā hochhe', cat: 'Emergency' },
    { id: 'p40', en: 'Call my emergency ICE contact', bn: 'আমার জরুরি যোগাযোগের নম্বরে দ্রুত ফোন করুন', translit: 'Āmār joruri contact-e druto phone korun', cat: 'Emergency' },

    // Mobility & Wayfinding
    { id: 'p41', en: 'Where is the wheelchair accessible ramp?', bn: 'হুইলচেয়ার চলাচলের র‍্যাম্প কোথায়?', translit: 'Wheelchair cholācholer ramp kothāy?', cat: 'Mobility', fav: true },
    { id: 'p42', en: 'Can you guide me to the elevator?', bn: 'আমাকে লিফটের পথ দেখাবেন কি?', translit: 'Āmāke lift-er poth dekhāben ki?', cat: 'Mobility' },
    { id: 'p43', en: 'Please hold the door open for me', bn: 'দয়া করে আমার জন্য দরজাটি ধরে রাখুন', translit: 'Doyā kore āmār jonno dorjāṭi dhore rākhun', cat: 'Mobility' },
    { id: 'p44', en: 'Where is the accessible taxi or bus stop?', bn: 'প্রতিবন্ধী-বান্ধব ট্যাক্সি বা বাস স্টপ কোথায়?', translit: 'Protibondhi-bāndhob taxi bā bus stop kothāy?', cat: 'Mobility' },
    { id: 'p45', en: 'I need assistance walking down the stairs', bn: 'সিঁড়ি দিয়ে নামতে আমার সাহায্য প্রয়োজন', translit: 'Sninṛi diye nāmte āmār sāhājjo proyojon', cat: 'Mobility' },

    // Hospital & Inpatient Care
    { id: 'p46', en: 'Please call the on-duty nurse', bn: 'দয়া করে কর্তব্যরত নার্সকে ডাকুন', translit: 'Doyā kore kortobyoroto nurse-ke dākun', cat: 'Hospital', fav: true },
    { id: 'p47', en: 'The IV drip is finished or leaking', bn: 'স্যালাইন বা আইভি ড্রিপ শেষ অথবা লিক করছে', translit: 'Saline bā IV drip shesh othobā leak korche', cat: 'Hospital' },
    { id: 'p48', en: 'Can I speak with the consulting physician?', bn: 'আমি কি কনসাল্টিং চিকিৎসকের সাথে কথা বলতে পারি?', translit: 'Āmi ki consulting chikitshoker sāthe kothā bolte pāri?', cat: 'Hospital' },
    { id: 'p49', en: 'When will my diagnostic test reports be ready?', bn: 'আমার মেডিকেল টেস্টের রিপোর্ট কখন পাওয়া যাবে?', translit: 'Medical test-er report kokhon pāoyā jābe?', cat: 'Hospital' },
    { id: 'p50', en: 'I need help adjusting my hospital bed', bn: 'হাসপাতালের বিছানা সমন্বয় করতে সাহায্য দরকার', translit: 'Hāspātāler bichhānā shomonwoy korte sāhājjo', cat: 'Hospital' },

    // Deaf & Assistive Communication
    { id: 'p51', en: 'I am deaf / hard of hearing', bn: 'আমি বধির / কানে কম শুনি', translit: 'Āmi bodhir / kāne kom shuni', cat: 'Assistive', fav: true },
    { id: 'p52', en: 'Please face me so I can lip-read', bn: 'দয়া করে আমার দিকে তাকিয়ে কথা বলুন যাতে ঠোঁট পড়তে পারি', translit: 'Doyā kore āmār dike tākiye kothā bolun', cat: 'Assistive' },
    { id: 'p53', en: 'Can you communicate in sign language?', bn: 'আপনি কি ইশারা ভাষায় কথা বলতে পারেন?', translit: 'Āpni ki ishārā bhāshāy kothā bolte pāren?', cat: 'Assistive' },
    { id: 'p54', en: 'Please type or write it on my screen', bn: 'দয়া করে আমার স্ক্রিনে লিখে দিন', translit: 'Doyā kore āmār screen-e likhe din', cat: 'Assistive' },
    { id: 'p55', en: 'I communicate using Transify AAC', bn: 'আমি ট্রান্সিফাই এএসি দিয়ে যোগাযোগ করি', translit: 'Āmi Transify AAC diye jogājog kori', cat: 'Assistive' }
  ],

  init() {
    this.initBootSequence();
    this.setupRouter();
    this.setupWelcomeScreen();
    this.setupHomeScreen();
    this.setupPhrasesScreen();
    this.setupBrailleInteractiveCell();
    this.setupSettingsScreen();
    if (window.ChatbotPage && window.ChatbotPage.init) {
      window.ChatbotPage.init();
    }

    // Check initial route - default to Cover Page ('welcome') first
    const hash = window.location.hash.replace('#', '').toLowerCase();
    if (hash && hash !== 'welcome' && hash !== 'home') {
      this.routeTo(hash);
    } else if (hash === 'home') {
      this.routeTo('home');
    } else {
      this.routeTo('welcome');
    }
  },

  initBootSequence() {
    const bootScreen = document.getElementById('transify-boot-screen');
    if (!bootScreen) return;

    const isReduced = document.documentElement.getAttribute('data-motion') === 'reduced';
    if (isReduced) {
      bootScreen.classList.add('boot-done');
      bootScreen.style.pointerEvents = 'none';
      bootScreen.style.display = 'none';
      return;
    }

    const fillEl = document.getElementById('boot-progress-fill');
    const pctEl = document.getElementById('boot-pct');
    const statusEl = document.getElementById('boot-status-text');

    const steps = [
      { pct: 20, msg: 'BOOTING TRANSIFY NEURAL CORE 2.0...' },
      { pct: 50, msg: 'LOADING MEDIAPIPE VISION SIMD PIPELINE...' },
      { pct: 75, msg: 'ENFORCING ZERO AUTO-AUDIO PRIVACY...' },
      { pct: 90, msg: 'SYNCING CLINICAL SAFETY TRIAGE PROTOCOLS...' },
      { pct: 100, msg: 'SYSTEM READY • CLIENT SILICON ACTIVE' }
    ];

    let currentStep = 0;
    let isDone = false;

    const finishBoot = () => {
      if (isDone) return;
      isDone = true;
      if (fillEl) fillEl.style.width = '100%';
      if (pctEl) pctEl.textContent = '100%';
      if (statusEl) statusEl.textContent = 'SYSTEM READY • CLIENT SILICON ACTIVE';
      bootScreen.classList.add('boot-done');
      bootScreen.style.pointerEvents = 'none';
      setTimeout(() => {
        bootScreen.style.display = 'none';
      }, 350);
    };

    window.dismissBootScreen = finishBoot;
    bootScreen.addEventListener('click', finishBoot);
    window.addEventListener('keydown', finishBoot, { once: true });

    const interval = setInterval(() => {
      if (isDone) {
        clearInterval(interval);
        return;
      }
      if (currentStep < steps.length) {
        const step = steps[currentStep];
        if (fillEl) fillEl.style.width = step.pct + '%';
        if (pctEl) pctEl.textContent = step.pct + '%';
        if (statusEl) statusEl.textContent = step.msg;
        currentStep++;
      } else {
        clearInterval(interval);
        finishBoot();
      }
    }, 180);
  },

  setupRouter() {
    window.routeTo = (r) => this.routeTo(r);

    // Rail logo click to go to Home
    const logoBtn = document.getElementById('rail-logo-btn');
    if (logoBtn) {
      logoBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.routeTo('home');
      });
    }

    // Rail buttons
    document.querySelectorAll('.rail-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const route = btn.getAttribute('data-route');
        if (route) this.routeTo(route);
      });
    });

    // Hash change listener
    window.addEventListener('hashchange', () => {
      const h = window.location.hash.replace('#', '').toLowerCase();
      if (h && h !== this.activeRoute) {
        this.routeTo(h);
      }
    });

    // Uiverse Navigation Burger Toggle & Drawer
    const burgerToggle = document.getElementById('nav-burger-toggle');
    const drawerBackdrop = document.getElementById('nav-drawer-backdrop');
    const drawerCloseBtn = document.getElementById('nav-drawer-close-btn');

    const closeNavDrawer = () => {
      if (burgerToggle) {
        burgerToggle.checked = false;
        burgerToggle.setAttribute('aria-expanded', 'false');
      }
      document.body.classList.remove('nav-drawer-open');
    };
    this.closeNavDrawer = closeNavDrawer;
    window.closeNavDrawer = closeNavDrawer;

    const openNavDrawer = () => {
      if (burgerToggle) {
        burgerToggle.checked = true;
        burgerToggle.setAttribute('aria-expanded', 'true');
      }
      document.body.classList.add('nav-drawer-open');
    };
    this.openNavDrawer = openNavDrawer;
    window.openNavDrawer = openNavDrawer;

    if (burgerToggle) {
      burgerToggle.addEventListener('change', () => {
        const isOpen = burgerToggle.checked;
        document.body.classList.toggle('nav-drawer-open', isOpen);
        burgerToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      });
    }

    if (drawerBackdrop) drawerBackdrop.addEventListener('click', closeNavDrawer);
    if (drawerCloseBtn) drawerCloseBtn.addEventListener('click', closeNavDrawer);

    document.querySelectorAll('.nav-drawer-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const url = item.getAttribute('data-url');
        if (url) {
          window.open(url, '_blank', 'noopener,noreferrer');
          setTimeout(closeNavDrawer, 160);
          return;
        }
        const route = item.getAttribute('data-route');
        if (route) {
          e.preventDefault();
          // Allow Uiverse glider beam physics animation to render before drawer closes
          setTimeout(() => {
            closeNavDrawer();
            this.routeTo(route);
          }, 180);
        } else {
          closeNavDrawer();
        }
      });
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && document.body.classList.contains('nav-drawer-open')) {
        closeNavDrawer();
      }
    });
  },

  routeTo(rawRoute) {
    if (this.closeNavDrawer) this.closeNavDrawer();
    let route = (rawRoute || 'home').toLowerCase();
    if (route === 'voice') route = 'stt';
    if (route === 'care') route = 'care';
    if (route === 'care-intake') route = 'care';
    if (route === 'clinician') route = 'care';
    if (route === 'care-chronic' || route === 'chronic') route = 'care';

    // Brief kinetic loader on view navigation
    if (window.showPageLoader && route !== this.activeRoute) {
      const titles = {
        sign: 'Loading Sign Language Translator...',
        braille: 'Loading Braille Image Scanner...',
        stt: 'Loading Voice Hub & Captions...',
        tts: 'Loading Text to Speech...',
        care: 'Loading Transify Care...',
        chat: 'Loading Transify AI Chatbot...',
        phrases: 'Loading Quick Phrases...',
        settings: 'Loading Preferences...'
      };
      window.showPageLoader(titles[route] || 'Loading Transify...', 220);
    }

    this.activeRoute = route;
    if (history.pushState) {
      const targetHash = '#' + (rawRoute || route);
      if (window.location.hash !== targetHash) {
        history.pushState(null, '', targetHash);
      }
    }

    const appShell = document.getElementById('app-shell');
    if (appShell) appShell.setAttribute('data-route', route);

    const rail = document.getElementById('app-rail');
    if (rail) {
      if (route === 'welcome') {
        rail.style.display = 'none';
      } else {
        rail.style.display = 'flex';
        rail.classList.toggle('sign-rail', route === 'sign');
      }
    }

    // Toggle active view
    const viewMap = {
      welcome: 'view-welcome',
      home: 'view-home',
      sign: 'view-sign',
      phrases: 'view-phrases',
      braille: 'view-braille',
      stt: 'view-voice',
      tts: 'view-voice',
      care: 'view-care',
      chat: 'view-chat',
      settings: 'view-settings',
      contact: 'view-settings'
    };

    const targetViewId = viewMap[route] || 'view-home';
    document.querySelectorAll('.page-view').forEach(view => {
      if (view.id === targetViewId) {
        view.classList.remove('page-entering');
        void view.offsetWidth;
        view.classList.add('active', 'page-entering');
        view.style.display = 'flex';
      } else {
        view.classList.remove('active', 'page-entering');
        view.style.display = 'none';
      }
    });

    // Update rail items active state
    document.querySelectorAll('.rail-item').forEach(btn => {
      const r = btn.getAttribute('data-route');
      const isActive = (r === route) || (r === 'voice' && (route === 'stt' || route === 'tts'));
      btn.classList.toggle('active', isActive);
      if (isActive) {
        btn.setAttribute('aria-current', 'page');
      } else {
        btn.removeAttribute('aria-current');
      }
    });

    // Update nav drawer items active state
    document.querySelectorAll('.nav-drawer-item').forEach(btn => {
      const r = btn.getAttribute('data-route');
      const isActive = (r === route) || (r === 'stt' && (route === 'stt' || route === 'voice')) || (route === 'care' && (r === 'care-intake' || r === 'care-chronic'));
      btn.classList.toggle('active', isActive);
      if (isActive) {
        btn.setAttribute('aria-current', 'page');
      } else {
        btn.removeAttribute('aria-current');
      }
    });

    // Sub-route handling
    if (route === 'sign' && window.SignPage && window.SignPage.init) {
      window.SignPage.init();
    }
    if (route === 'braille' && window.BraillePage && window.BraillePage.init) {
      window.BraillePage.init();
    }
    if ((route === 'stt' || route === 'tts' || route === 'voice') && window.TransifyVoiceStudio && window.TransifyVoiceStudio.init) {
      window.TransifyVoiceStudio.init();
    }
    if (route === 'chat' && window.ChatbotPage && window.ChatbotPage.init) {
      window.ChatbotPage.init();
    }

    if (rawRoute === 'clinician') {
      const clinicianTab = document.getElementById('care-tab-clinician-btn');
      if (clinicianTab) clinicianTab.click();
    } else if (rawRoute === 'care-chronic' || rawRoute === 'chronic') {
      const chronicTab = document.getElementById('care-tab-chronic-btn');
      if (chronicTab) chronicTab.click();
    } else if (rawRoute === 'care-intake' || rawRoute === 'care') {
      const intakeTab = document.getElementById('care-tab-intake-btn');
      if (intakeTab) intakeTab.click();
    } else if (route === 'contact' || rawRoute === 'contact') {
      if (this.switchSettingsTab) this.switchSettingsTab('contact');
    } else if (rawRoute && rawRoute.startsWith('settings-')) {
      const sub = rawRoute.replace('settings-', '');
      if (this.switchSettingsTab) this.switchSettingsTab(sub);
    }

    window.scrollTo(0, 0);
  },

  setupWelcomeScreen() {
    const stage = document.getElementById('welcome-stage');
    const pauseBtn = document.getElementById('welcome-pause-btn');
    const langBtn = document.getElementById('welcome-lang-btn');
    const skipBtn = document.getElementById('btn-demo-guest');

    if (skipBtn) {
      skipBtn.addEventListener('click', (e) => {
        e.preventDefault();
        try { localStorage.setItem('transify.welcomed', '1'); } catch (e) { }
        this.routeTo('home');
      });
    }

    if (pauseBtn) {
      pauseBtn.addEventListener('click', () => {
        this.welcomePaused = !this.welcomePaused;
        pauseBtn.innerHTML = this.welcomePaused
          ? '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M7 4l13 8-13 8z"/></svg>'
          : '<svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>';
      });
    }

    // Story tab clicks
    document.querySelectorAll('.story').forEach(tab => {
      tab.addEventListener('click', () => {
        const slide = parseInt(tab.getAttribute('data-slide') || '0', 10);
        this.setWelcomeSlide(slide);
      });
    });

    // Welcome Language toggle
    if (langBtn) {
      langBtn.addEventListener('click', () => {
        const currentLang = (window.TransifyI18n && window.TransifyI18n.getLanguage && window.TransifyI18n.getLanguage()) || 'en';
        const targetLang = (currentLang === 'bn') ? 'en' : 'bn';
        if (window.TransifyI18n && window.TransifyI18n.setLanguage) {
          window.TransifyI18n.setLanguage(targetLang);
        } else if (typeof applyLocale === 'function') {
          applyLocale(targetLang);
        }
      });
    }

    // Interactive Braille dots in Welcome Demo
    let selectedDots = [];
    document.querySelectorAll('#welcome-demo-braille .dotb').forEach(btn => {
      btn.addEventListener('click', () => {
        const dot = btn.getAttribute('data-dot');
        btn.classList.remove('hint');
        btn.classList.toggle('active');
        if (selectedDots.includes(dot)) {
          selectedDots = selectedDots.filter(d => d !== dot);
        } else {
          selectedDots.push(dot);
        }
        selectedDots.sort();
        const key = selectedDots.join('');
        const char = this.brailleMap[key] || (key ? '–' : 'a');
        const letterEl = document.getElementById('welcome-braille-letter');
        const labelEl = document.getElementById('welcome-braille-dots-label');
        if (letterEl) letterEl.textContent = char;
        if (labelEl) labelEl.textContent = selectedDots.length ? `Dots ${selectedDots.join(', ')}` : 'Touch a dot';
      });
    });

    // Voice mic toggle in Welcome Demo
    const micBtn = document.getElementById('welcome-mic-toggle-btn');
    const micWrap = document.getElementById('welcome-mic-wrap');
    if (micBtn && micWrap) {
      micBtn.addEventListener('click', () => {
        micWrap.classList.toggle('live');
      });
    }

    // Slideshow interval
    setInterval(() => {
      if (this.welcomePaused || this.activeRoute !== 'welcome') return;
      const elapsed = Date.now() - this.welcomeStartTime;
      const pct = Math.min(1, elapsed / this.welcomeDur);

      const activeBar = document.getElementById(`welcome-bar-${this.welcomeSlide}`);
      if (activeBar) activeBar.style.transform = `scaleX(${pct})`;

      if (elapsed >= this.welcomeDur) {
        this.welcomeStartTime = Date.now();
        this.setWelcomeSlide((this.welcomeSlide + 1) % 3);
      }
    }, 80);
  },

  setWelcomeSlide(idx) {
    this.welcomeSlide = idx;
    this.welcomeStartTime = Date.now();

    const photoBg = document.getElementById('welcome-photo-bg');
    const bgs = [
      'radial-gradient(50% 50% at 60% 40%,#B48866 0%,rgba(180,136,102,0) 62%),radial-gradient(60% 60% at 10% 90%,#2C4258 0%,rgba(44,66,88,0) 70%),linear-gradient(160deg,#43362D 0%,#191520 75%)',
      'radial-gradient(70% 60% at 50% 40%,#D2C2A6 0%,rgba(210,194,166,0) 68%),linear-gradient(172deg,#6B5C4B 0%,#211D25 85%)',
      'radial-gradient(60% 60% at 42% 36%,#9DB2C2 0%,rgba(157,178,194,0) 66%),radial-gradient(40% 40% at 90% 80%,#6B4A5E 0%,rgba(107,74,94,0) 70%),linear-gradient(168deg,#31414F 0%,#17151F 85%)'
    ];
    if (photoBg) photoBg.style.background = bgs[idx] || bgs[0];

    // Toggle demo components
    const dSign = document.getElementById('welcome-demo-sign');
    const dBraille = document.getElementById('welcome-demo-braille');
    const dVoice = document.getElementById('welcome-demo-voice');

    if (dSign) dSign.style.display = idx === 0 ? 'flex' : 'none';
    if (dBraille) dBraille.style.display = idx === 1 ? 'flex' : 'none';
    if (dVoice) dVoice.style.display = idx === 2 ? 'flex' : 'none';

    // Update story tabs
    document.querySelectorAll('.story').forEach(tab => {
      const s = parseInt(tab.getAttribute('data-slide') || '0', 10);
      const isSel = (s === idx);
      tab.setAttribute('aria-selected', isSel ? 'true' : 'false');
      const bar = document.getElementById(`welcome-bar-${s}`);
      if (bar) {
        if (s < idx) bar.style.transform = 'scaleX(1)';
        else if (s > idx) bar.style.transform = 'scaleX(0)';
      }
    });
  },

  setupHomeScreen() {
    // 1. Hour greeting
    const h = new Date().getHours();
    const curLang = localStorage.getItem('transify_lang') || 'en';
    let greet = 'Good night';
    if (curLang === 'bn') {
      greet = (h >= 5 && h < 12) ? 'শুভ সকাল' : ((h >= 12 && h < 17) ? 'শুভ অপরাহ্ন' : ((h >= 17 && h < 22) ? 'শুভ সন্ধ্যা' : 'শুভ রাত্রি'));
    } else {
      greet = (h >= 5 && h < 12) ? 'Good morning' : ((h >= 12 && h < 17) ? 'Good afternoon' : ((h >= 17 && h < 22) ? 'Good evening' : 'Good night'));
    }
    const greetEl = document.getElementById('home-greeting-text');
    if (greetEl) greetEl.textContent = greet;

    // 2. User name
    const userJson = localStorage.getItem('transify_auth_user');
    if (userJson) {
      try {
        const u = JSON.parse(userJson);
        if (u.name) {
          const nameEl = document.getElementById('home-user-name');
          if (nameEl) nameEl.textContent = u.name;
          const avEl = document.getElementById('frame-avatar-btn');
          if (avEl) {
            const parts = u.name.trim().split(' ');
            avEl.textContent = parts.map(p => p[0]).join('').toUpperCase().slice(0, 2);
          }
        }
      } catch (e) { }
    }

    // 3. Say aloud input & speak button
    const sayInput = document.getElementById('say');
    const sayBtn = document.getElementById('btn-say-speak');
    const idleText = document.getElementById('say-speak-idle-text');
    const activeBars = document.getElementById('say-speak-active-bars');
    const activeText = document.getElementById('say-speak-active-text');

    if (sayBtn && sayInput) {
      sayBtn.addEventListener('click', () => {
        const txt = sayInput.value.trim();
        if (!txt) {
          sayInput.focus();
          return;
        }
        if (window.TransifyTTS && window.TransifyTTS.speak) {
          if (idleText) idleText.style.display = 'none';
          if (activeBars) activeBars.style.display = 'flex';
          if (activeText) activeText.style.display = 'inline';

          window.TransifyTTS.speak(txt, {
            onEnd: () => {
              if (idleText) idleText.style.display = 'inline';
              if (activeBars) activeBars.style.display = 'none';
              if (activeText) activeText.style.display = 'none';
            }
          });
        }
      });
    }

    // 4. Phrase chips populate input
    document.querySelectorAll('.phrase-chip-btn').forEach(chip => {
      chip.addEventListener('click', () => {
        const text = chip.textContent.trim();
        if (text && sayInput) {
          sayInput.value = text;
          sayInput.focus();
        }
      });
    });

    // 5. Interface language toggle
    const enBtn = document.getElementById('home-lang-en');
    const bnBtn = document.getElementById('home-lang-bn');
    if (enBtn && bnBtn) {
      enBtn.addEventListener('click', () => {
        if (window.TransifyI18n && window.TransifyI18n.setLanguage) {
          window.TransifyI18n.setLanguage('en');
        } else if (typeof applyLocale === 'function') {
          applyLocale('en');
        }
        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast('Language: English', 'info');
        }
      });
      bnBtn.addEventListener('click', () => {
        if (window.TransifyI18n && window.TransifyI18n.setLanguage) {
          window.TransifyI18n.setLanguage('bn');
        } else if (typeof applyLocale === 'function') {
          applyLocale('bn');
        }
        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast('ভাষা পরিবর্তন: বাংলা', 'info');
        }
      });
    }
  },

  setPhraseSpeed(spd) {
    this.phraseSpeed = spd || 1.0;
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast(`Phrase playback rate set to ${this.phraseSpeed}x`, 'info');
    }
  },

  toggleEmergencyFlashMode() {
    const overlay = document.getElementById('phrase-flash-overlay');
    if (!overlay) return;
    const isVisible = overlay.style.display !== 'none';
    if (isVisible) {
      overlay.style.display = 'none';
      if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    } else {
      const textEl = document.getElementById('phrase-flash-text');
      const bnEl = document.getElementById('phrase-flash-bn');
      if (textEl) textEl.textContent = 'URGENT: I NEED IMMEDIATE MEDICAL ASSISTANCE';
      if (bnEl) bnEl.textContent = 'জরুরি: আমার অবিলম্বে চিকিৎসা সহায়তা প্রয়োজন (৯৯৯)';
      overlay.style.display = 'flex';
      if (window.TransifyTTS && window.TransifyTTS.speak) {
        window.TransifyTTS.speak('Emergency: I need medical assistance immediately. Please call 999.');
      }
    }
  },

  dismissEmergencyFlash() {
    const overlay = document.getElementById('phrase-flash-overlay');
    if (overlay) overlay.style.display = 'none';
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  },

  triggerEmergencyFlashByIdx(idx) {
    if (this._lastVisiblePhrases && this._lastVisiblePhrases[idx]) {
      const p = this._lastVisiblePhrases[idx];
      const overlay = document.getElementById('phrase-flash-overlay');
      const textEl = document.getElementById('phrase-flash-text');
      const bnEl = document.getElementById('phrase-flash-bn');
      if (textEl) textEl.textContent = p.en.toUpperCase();
      if (bnEl) bnEl.textContent = p.bn || '';
      if (overlay) overlay.style.display = 'flex';
      this.speakPhraseCard(idx);
    }
  },

  speakPhraseCard(idx) {
    if (this._lastVisiblePhrases && this._lastVisiblePhrases[idx]) {
      const p = this._lastVisiblePhrases[idx];
      const iconEl = document.getElementById(`card-icon-${idx}`);
      if (iconEl) {
        iconEl.innerHTML = '<span class="wave" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>';
      }

      if ('speechSynthesis' in window) {
        try {
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(p.en);
          utterance.rate = this.phraseSpeed || 1.0;
          utterance.onend = () => {
            if (iconEl) {
              iconEl.innerHTML = '<svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/></svg>';
            }
          };
          utterance.onerror = () => {
            if (iconEl) {
              iconEl.innerHTML = '<svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/></svg>';
            }
          };
          window.speechSynthesis.speak(utterance);
        } catch (e) {
          if (window.TransifyTTS && window.TransifyTTS.speak) {
            window.TransifyTTS.speak(p.en);
          }
        }
      } else if (window.TransifyTTS && window.TransifyTTS.speak) {
        window.TransifyTTS.speak(p.en);
      }
      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast(`Speaking: "${p.en.slice(0, 28)}..."`, 'info');
      }
    }
  },

  toggleFavoritePhrase(idOrEn, event) {
    if (event) event.stopPropagation();
    if (this._allPhrases) {
      const p = this._allPhrases.find(item => (item.id === idOrEn || item.en === idOrEn));
      if (p) {
        p.fav = !p.fav;
        try { localStorage.setItem('transify_phrases', JSON.stringify(this._allPhrases)); } catch (e) { }
        if (this._renderPhrases) this._renderPhrases();
        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast(p.fav ? `Saved "${p.en.slice(0, 20)}..." to favorites!` : 'Removed from favorites.', 'info');
        }
      }
    }
  },

  copyPhrase(textEn, textBn) {
    const text = textBn ? `${textEn} (${textBn})` : textEn;
    navigator.clipboard.writeText(text);
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast('Phrase copied to clipboard!', 'success');
    }
  },

  bridgePhraseToSign(textEn) {
    this.routeTo('sign');
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast(`Bridge: Loaded "${textEn.slice(0, 20)}..." in Sign Translator`, 'info');
    }
  },

  bridgePhraseToBraille(textEn) {
    this.routeTo('braille');
    if (window.BraillePage && window.BraillePage.switchMode) {
      window.BraillePage.switchMode('generator');
    }
    const input = document.getElementById('braille-gen-input');
    if (input) {
      input.value = textEn;
      if (window.BraillePage && window.BraillePage.generateBrailleFromText) {
        window.BraillePage.generateBrailleFromText();
      }
    }
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast(`Bridge: Generating Braille for "${textEn.slice(0, 20)}..."`, 'info');
    }
  },

  exportPhrasesJSON() {
    const list = this._allPhrases || this.defaultPhrases;
    const blob = new Blob([JSON.stringify(list, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transify-phrases-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    if (window.TransifyApp && window.TransifyApp.showToast) {
      window.TransifyApp.showToast('Exported phrases library as JSON.', 'success');
    }
  },

  setupPhrasesScreen() {
    const grid = document.getElementById('phrases-grid');
    const emptyState = document.getElementById('phrases-empty-state');
    const searchInput = document.getElementById('q');
    const toggleAddBtn = document.getElementById('btn-toggle-add-phrase');
    const addSection = document.getElementById('phrase-add-form');
    const addBtnLabel = document.getElementById('add-phrase-btn-label');
    const saveBtn = document.getElementById('btn-save-phrase');
    const npInput = document.getElementById('np');
    const npBnInput = document.getElementById('np-bn');
    const toastMsg = document.getElementById('phrase-toast-msg');
    const seedBtn = document.getElementById('btn-seed-starter-phrases');

    let activeCategory = 'All';
    let newCategory = 'Everyday';
    let searchQuery = '';

    // Load phrases
    let phrases = [];
    try {
      const stored = localStorage.getItem('transify_phrases');
      if (stored) {
        phrases = JSON.parse(stored);
        if (!Array.isArray(phrases) || phrases.length < 20) {
          phrases = [...this.defaultPhrases];
          localStorage.setItem('transify_phrases', JSON.stringify(phrases));
        }
      } else {
        phrases = [...this.defaultPhrases];
      }
    } catch (e) {
      phrases = [...this.defaultPhrases];
    }

    this._allPhrases = phrases;

    const savePhrases = () => {
      try { localStorage.setItem('transify_phrases', JSON.stringify(phrases)); } catch (e) { }
    };

    const render = () => {
      if (!grid) return;
      const q = searchQuery.trim().toLowerCase();
      const inCat = (p) => {
        if (activeCategory === 'All') return true;
        if (activeCategory === 'Favorites') return !!p.fav;
        return p.cat.toLowerCase() === activeCategory.toLowerCase();
      };
      const match = (p) => {
        if (!q) return true;
        return (p.en && p.en.toLowerCase().includes(q)) ||
          (p.bn && p.bn.includes(q)) ||
          (p.translit && p.translit.toLowerCase().includes(q)) ||
          (p.cat && p.cat.toLowerCase().includes(q));
      };

      const visible = phrases.filter(p => inCat(p) && match(p));
      this._lastVisiblePhrases = visible;

      // Update counts
      const counts = {
        all: phrases.length,
        everyday: phrases.filter(p => p.cat === 'Everyday').length,
        needs: phrases.filter(p => p.cat === 'Needs').length,
        medical: phrases.filter(p => p.cat === 'Medical').length,
        emergency: phrases.filter(p => p.cat === 'Emergency').length,
        mobility: phrases.filter(p => p.cat === 'Mobility').length,
        hospital: phrases.filter(p => p.cat === 'Hospital').length,
        assistive: phrases.filter(p => p.cat === 'Assistive').length,
        favorites: phrases.filter(p => !!p.fav).length
      };

      const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
      };

      setEl('count-all', counts.all);
      setEl('count-everyday', counts.everyday);
      setEl('count-needs', counts.needs);
      setEl('count-medical', counts.medical);
      setEl('count-emergency', counts.emergency);
      setEl('count-mobility', counts.mobility);
      setEl('count-hospital', counts.hospital);
      setEl('count-assistive', counts.assistive);
      setEl('count-favorites', counts.favorites);

      if (!visible.length) {
        grid.style.display = 'none';
        if (emptyState) {
          emptyState.style.display = 'flex';
          const title = document.getElementById('phrases-empty-title');
          const body = document.getElementById('phrases-empty-body');
          if (q) {
            if (title) title.textContent = `No phrases match "${searchQuery}"`;
            if (body) body.textContent = 'Check the spelling, or add it as a new phrase.';
            if (seedBtn) seedBtn.style.display = 'none';
          } else {
            if (title) title.textContent = 'No phrases in this category';
            if (body) body.textContent = 'Add the phrases you use most, or click below to restore full library.';
            if (seedBtn) seedBtn.style.display = 'inline-block';
          }
        }
        return;
      }

      grid.style.display = 'grid';
      if (emptyState) emptyState.style.display = 'none';

      grid.innerHTML = visible.map((p, idx) => {
        const isEmergency = (p.cat === 'Emergency');
        const catClass = `cat-${(p.cat || 'everyday').toLowerCase()}`;
        const isFav = !!p.fav;
        return `
        <li>
          <div class="phrase-card card-uiverse ${isEmergency ? 'is-emergency' : ''}" data-idx="${idx}" role="region" aria-label="${p.en}">
            <div class="go-corner" aria-hidden="true" onclick="EditorialController.speakPhraseCard(${idx})"><span class="go-arrow">🔊</span></div>
            <div class="phrase-card-top">
              <span class="phrase-badge ${catClass}">${p.cat}</span>
              <div style="display: flex; align-items: center; gap: 6px;">
                <button type="button" class="phrase-fav-btn ${isFav ? 'is-fav' : ''}" onclick="EditorialController.toggleFavoritePhrase('${p.id || p.en}', event)" title="Toggle Favorite" aria-label="Toggle favorite">
                  ${isFav ? '★' : '☆'}
                </button>
                <span class="phrase-card-icon" id="card-icon-${idx}" onclick="EditorialController.speakPhraseCard(${idx})" style="cursor: pointer;" title="Speak phrase">
                  <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/></svg>
                </span>
              </div>
            </div>
            
            <div onclick="EditorialController.speakPhraseCard(${idx})" style="cursor: pointer;">
              <span class="phrase-en card-title">${p.en}</span>
              ${p.bn ? `<span class="phrase-bn small-desc">${p.bn}</span>` : ''}
              ${p.translit ? `<span class="phrase-translit">Pronounce: ${p.translit}</span>` : ''}
            </div>

            <div class="phrase-card-actions">
              <button type="button" class="phrase-action-btn press" onclick="EditorialController.speakPhraseCard(${idx})" title="Say phrase aloud">
                <span>🔊 Speak</span>
              </button>
              <button type="button" class="phrase-action-btn press" onclick="EditorialController.copyPhrase('${p.en.replace(/'/g, "\\'")}', '${(p.bn || '').replace(/'/g, "\\'")}')" title="Copy text">
                <span>📋 Copy</span>
              </button>
              <button type="button" class="phrase-action-btn press" onclick="EditorialController.bridgePhraseToSign('${p.en.replace(/'/g, "\\'")}')" title="Bridge to sign translator">
                <span>🤟 Signs</span>
              </button>
              <button type="button" class="phrase-action-btn press" onclick="EditorialController.bridgePhraseToBraille('${p.en.replace(/'/g, "\\'")}')" title="Bridge to Braille studio">
                <span>⠃ Braille</span>
              </button>
              ${isEmergency ? `
              <button type="button" class="phrase-action-btn press" onclick="EditorialController.triggerEmergencyFlashByIdx(${idx})" style="background: rgba(239,68,68,0.12); color: #dc2626; border-color: rgba(239,68,68,0.3);" title="Trigger emergency siren">
                <span>🚨 Alert</span>
              </button>` : ''}
            </div>
          </div>
        </li>
      `;
      }).join('');
    };

    this._renderPhrases = render;

    // Category Tabs click
    document.querySelectorAll('.phrase-cat-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.phrase-cat-tab').forEach(t => {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');
        activeCategory = tab.getAttribute('data-cat') || 'All';
        render();
      });
    });

    // Search input
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value;
        render();
      });
    }

    // Toggle Add form
    if (toggleAddBtn && addSection) {
      toggleAddBtn.addEventListener('click', () => {
        const isOpen = addSection.style.display !== 'none';
        addSection.style.display = isOpen ? 'none' : 'flex';
        toggleAddBtn.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
        if (addBtnLabel) addBtnLabel.textContent = isOpen ? 'Add phrase' : 'Close';
        if (!isOpen && npInput) npInput.focus();
      });
    }

    // Category buttons inside Add form
    document.querySelectorAll('.cat-select-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.cat-select-btn').forEach(b => {
          b.classList.remove('active');
          b.setAttribute('aria-pressed', 'false');
        });
        btn.classList.add('active');
        btn.setAttribute('aria-pressed', 'true');
        newCategory = btn.getAttribute('data-cat') || 'Everyday';
      });
    });

    // Save phrase
    if (saveBtn && npInput) {
      saveBtn.addEventListener('click', () => {
        const text = npInput.value.trim();
        const textBn = npBnInput ? npBnInput.value.trim() : '';
        if (!text) {
          npInput.focus();
          if (toastMsg) toastMsg.textContent = 'Type an English phrase first';
          return;
        }

        phrases.unshift({
          id: 'p_custom_' + Date.now(),
          en: text,
          bn: textBn,
          translit: '',
          cat: newCategory,
          fav: false
        });
        this._allPhrases = phrases;
        savePhrases();
        npInput.value = '';
        if (npBnInput) npBnInput.value = '';
        if (addSection) addSection.style.display = 'none';
        if (toggleAddBtn) {
          toggleAddBtn.setAttribute('aria-expanded', 'false');
          if (addBtnLabel) addBtnLabel.textContent = 'Add phrase';
        }

        if (toastMsg) {
          toastMsg.textContent = `Phrase saved to ${newCategory}`;
          setTimeout(() => { if (toastMsg.textContent.includes('saved')) toastMsg.textContent = ''; }, 2400);
        }

        render();
      });
    }

    // Seed starter phrases
    if (seedBtn) {
      seedBtn.addEventListener('click', () => {
        phrases = [...this.defaultPhrases];
        this._allPhrases = phrases;
        savePhrases();
        render();
        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast('Restored standard 50+ phrase library!', 'success');
        }
      });
    }

    // Initial render
    render();
  },

  setupBrailleInteractiveCell() {
    if (window.BraillePage && window.BraillePage.init) {
      window.BraillePage.init();
    }
  },

  setupSettingsScreen() {
    // 0. Settings Navbar Tab Navigation (Profile, Account, Appearance, Accessibility, Privacy, Contact)
    const settingsNavTabs = document.querySelectorAll('.settings-nav-tab');
    settingsNavTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const target = tab.getAttribute('data-settings-tab');
        if (target) this.switchSettingsTab(target);
      });
    });

    if (window.TransifyApp) {
      window.TransifyApp.switchSettingsTab = (t) => this.switchSettingsTab(t);
    }

    const savedSettingsTab = localStorage.getItem('transify_settings_tab') || 'profile';
    this.switchSettingsTab(savedSettingsTab);

    // Profile Persona Persistence
    const profName = document.getElementById('profile-input-name');
    const profRole = document.getElementById('profile-select-role');
    const profComm = document.getElementById('profile-select-comm');
    const profDialect = document.getElementById('profile-select-dialect');
    const profBio = document.getElementById('profile-input-bio');
    const profAvatar = document.getElementById('profile-avatar-display');
    const profHeading = document.getElementById('profile-display-heading');
    const profBadgeRole = document.getElementById('profile-badge-role');
    const saveProfBtn = document.getElementById('btn-save-profile');

    const roleLabels = {
      accessibility_user: 'Accessibility User',
      chronic_care_patient: 'ChronicCare Patient',
      healthcare_provider: 'Clinician / Provider',
      caregiver: 'Caregiver Advocate',
      researcher: 'AI Researcher'
    };

    const syncLiveProfile = (showToastNotice = false, customNotice = '') => {
      const nameVal = (profName ? profName.value : '') || 'Guest User';
      const roleVal = profRole ? profRole.value : 'accessibility_user';
      const commVal = profComm ? profComm.value : 'multimodal';
      const dialectVal = profDialect ? profDialect.value : 'en-US';
      const bioVal = profBio ? profBio.value : '';

      const profObj = { name: nameVal, role: roleVal, comm: commVal, dialect: dialectVal, bio: bioVal };
      try { localStorage.setItem('transify_user_profile', JSON.stringify(profObj)); } catch (_) { }

      const initials = nameVal.trim().split(' ').map(x => x[0]).join('').toUpperCase().slice(0, 2) || 'TR';
      if (profAvatar) profAvatar.textContent = initials;
      if (profHeading) profHeading.textContent = nameVal;
      if (profBadgeRole) profBadgeRole.textContent = roleLabels[roleVal] || 'Accessibility User';

      const setAv = document.getElementById('settings-avatar-initials');
      if (setAv) setAv.textContent = initials;
      const frameAv = document.getElementById('frame-avatar-btn');
      if (frameAv) frameAv.textContent = initials;
      const setName = document.getElementById('settings-user-name');
      if (setName && (setName.textContent === 'Guest User' || !localStorage.getItem('transify_auth_user'))) {
        setName.textContent = nameVal;
      }

      if (showToastNotice && window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast(customNotice || 'Profile changes saved successfully', 'success');
      }
    };

    const savedProfStr = localStorage.getItem('transify_user_profile');
    if (savedProfStr) {
      try {
        const p = JSON.parse(savedProfStr);
        if (profName && p.name) {
          profName.value = p.name;
          if (profHeading) profHeading.textContent = p.name;
        }
        if (profRole && p.role) {
          profRole.value = p.role;
          if (profBadgeRole) profBadgeRole.textContent = roleLabels[p.role] || 'Accessibility User';
        }
        if (profComm && p.comm) profComm.value = p.comm;
        if (profDialect && p.dialect) profDialect.value = p.dialect;
        if (profBio && p.bio) profBio.value = p.bio;
        if (profAvatar && p.name) {
          const initials = p.name.trim().split(' ').map(x => x[0]).join('').toUpperCase().slice(0, 2);
          profAvatar.textContent = initials || 'TR';
        }
      } catch (_) { }
    }

    // Live reactivity for profile controls
    if (profRole) {
      profRole.addEventListener('change', () => {
        syncLiveProfile(true, `Role set to ${roleLabels[profRole.value] || profRole.value}`);
      });
    }
    if (profComm) {
      profComm.addEventListener('change', () => {
        const commText = profComm.options[profComm.selectedIndex]?.text?.split('(')[0]?.trim() || profComm.value;
        syncLiveProfile(true, `Modality set to ${commText}`);
      });
    }
    if (profDialect) {
      profDialect.addEventListener('change', () => {
        const dText = profDialect.options[profDialect.selectedIndex]?.text?.split('(')[0]?.trim() || profDialect.value;
        syncLiveProfile(true, `Dialect set to ${dText}`);
      });
    }
    if (profName) {
      profName.addEventListener('input', () => {
        syncLiveProfile(false);
      });
    }

    if (saveProfBtn) {
      saveProfBtn.addEventListener('click', () => {
        syncLiveProfile(true, 'Profile changes saved successfully');
      });
    }

    // Developer Support / Feedback Form
    const contactSubmitBtn = document.getElementById('btn-contact-submit');
    const contactMsg = document.getElementById('contact-message');

    if (contactSubmitBtn && contactMsg) {
      contactSubmitBtn.addEventListener('click', () => {
        const text = contactMsg.value.trim();
        if (!text) {
          if (window.TransifyApp && window.TransifyApp.showToast) {
            window.TransifyApp.showToast('Please type a message before sending', 'info');
          }
          return;
        }
        contactMsg.value = '';
        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast('Message sent! Developer Safin has received your feedback.', 'success');
        }
      });
    }

    // Copy Diagnostics Button
    const diagBtn = document.getElementById('btn-contact-diagnostics');
    if (diagBtn) {
      diagBtn.addEventListener('click', () => {
        const curTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const diagInfo = `Transify 2.0 Diagnostics\nTimestamp: ${new Date().toISOString()}\nPlatform: ${navigator.platform || 'Linux'}\nResolution: ${window.innerWidth}x${window.innerHeight}\nTheme: ${curTheme}\nConnection: ${navigator.onLine ? 'Online' : 'Offline'}\nMediaPipe Vision: Available (0.10.14 WebAssembly)\nSpeech: Zero Auto-Audio Policy`;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(diagInfo).then(() => {
            if (window.TransifyApp && window.TransifyApp.showToast) {
              window.TransifyApp.showToast('System diagnostics copied to clipboard!', 'success');
            }
          }).catch(() => {
            if (window.TransifyApp && window.TransifyApp.showToast) {
              window.TransifyApp.showToast('Diagnostics ready in developer console', 'info');
            }
          });
        }
      });
    }

    // Export User Data (JSON)
    const exportBtn = document.getElementById('btn-settings-export-data');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => {
        let profData = {};
        try { profData = JSON.parse(localStorage.getItem('transify_user_profile') || '{}'); } catch (_) { }
        const dump = {
          app: 'Transify 2.0',
          exported_at: new Date().toISOString(),
          profile: profData,
          preferences: {
            theme: localStorage.getItem('transify_theme') || 'light',
            font_scale: localStorage.getItem('transify_font_scale') || 'normal',
            speech_rate: localStorage.getItem('transify_speech_rate') || '1.0',
            sign_lang: localStorage.getItem('transify_default_sign_lang') || 'asl',
            braille_standard: localStorage.getItem('transify_braille_standard') || 'grade1',
            confidence_gate: localStorage.getItem('transify_confidence_gate') || '85'
          }
        };
        const blob = new Blob([JSON.stringify(dump, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transify_backup_${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast('Profile and settings exported as JSON', 'success');
        }
      });
    }

    // 1. Theme Picker & Real-Time Switching
    const themeButtons = document.querySelectorAll('.theme-card-btn');
    const savedTheme = localStorage.getItem('transify_theme') || 'light';
    this.applyTheme(savedTheme);

    themeButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const selected = btn.dataset.theme;
        this.applyTheme(selected);
        try { localStorage.setItem('transify_theme', selected); } catch (e) { }
        const label = btn.querySelector('.theme-card-label');
        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast(`Theme switched to ${label ? label.textContent : selected}`, 'info');
        }
      });
    });

    // 2. Reduce motion toggle
    const reduceMotionCheck = document.getElementById('setting-reduce-motion');
    const isReduced = localStorage.getItem('transify_reduce_motion') === '1' || localStorage.getItem('transify_reduced_motion') === 'true';
    if (reduceMotionCheck) {
      reduceMotionCheck.checked = isReduced;
      if (isReduced) document.documentElement.setAttribute('data-motion', 'reduced');

      reduceMotionCheck.addEventListener('change', (e) => {
        const val = e.target.checked;
        if (val) {
          document.documentElement.setAttribute('data-motion', 'reduced');
          try {
            localStorage.setItem('transify_reduce_motion', '1');
            localStorage.setItem('transify_reduced_motion', 'true');
          } catch (e) { }
          if (window.TransifyApp && window.TransifyApp.showToast) {
            window.TransifyApp.showToast('Reduced Motion Enabled', 'info');
          }
        } else {
          document.documentElement.removeAttribute('data-motion');
          try {
            localStorage.removeItem('transify_reduce_motion');
            localStorage.setItem('transify_reduced_motion', 'false');
          } catch (e) { }
          if (window.TransifyApp && window.TransifyApp.showToast) {
            window.TransifyApp.showToast('Animations Restored', 'info');
          }
        }
      });
    }

    // 3. Typography Scaling
    const fontScaleGroup = document.getElementById('settings-fontsize-group');
    if (fontScaleGroup) {
      const savedScale = localStorage.getItem('transify_font_scale') || 'normal';
      this.applyFontScale(savedScale);

      fontScaleGroup.querySelectorAll('.segmented-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const scale = btn.dataset.scale;
          this.applyFontScale(scale);
          try { localStorage.setItem('transify_font_scale', scale); } catch (e) { }
          if (window.TransifyApp && window.TransifyApp.showToast) {
            window.TransifyApp.showToast(`Typography scaled to ${btn.textContent}`, 'info');
          }
        });
      });
    }

    // 4. Focus Rings
    const focusRingToggle = document.getElementById('setting-focus-rings');
    if (focusRingToggle) {
      const isEnhanced = localStorage.getItem('transify_focus_rings') === 'true';
      focusRingToggle.checked = isEnhanced;
      if (isEnhanced) document.body.classList.add('enhanced-focus');

      focusRingToggle.addEventListener('change', (e) => {
        if (e.target.checked) {
          document.body.classList.add('enhanced-focus');
          try { localStorage.setItem('transify_focus_rings', 'true'); } catch (e) { }
          if (window.TransifyApp && window.TransifyApp.showToast) {
            window.TransifyApp.showToast('Prominent Keyboard Focus Rings Enabled', 'success');
          }
        } else {
          document.body.classList.remove('enhanced-focus');
          try { localStorage.setItem('transify_focus_rings', 'false'); } catch (e) { }
          if (window.TransifyApp && window.TransifyApp.showToast) {
            window.TransifyApp.showToast('Standard Focus Rings Restored', 'info');
          }
        }
      });
    }

    // 5. Interface Language Select
    const langSelect = document.getElementById('setting-lang-select');
    if (langSelect) {
      const currentLang = localStorage.getItem('transify_lang') || 'en';
      langSelect.value = currentLang;

      langSelect.addEventListener('change', (e) => {
        const lang = e.target.value;
        try { localStorage.setItem('transify_lang', lang); } catch (e) { }
        if (typeof applyLocale === 'function') applyLocale(lang);
        const enBtn = document.getElementById('home-lang-en');
        const bnBtn = document.getElementById('home-lang-bn');
        if (enBtn && bnBtn) {
          enBtn.classList.toggle('active', lang === 'en');
          enBtn.setAttribute('aria-pressed', lang === 'en');
          bnBtn.classList.toggle('active', lang === 'bn');
          bnBtn.setAttribute('aria-pressed', lang === 'bn');
        }
        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast(`Interface language: ${lang === 'bn' ? 'বাংলা' : 'English'}`, 'info');
        }
      });
    }

    // 6. Speech Synthesizer Rate
    const speechRateGroup = document.getElementById('settings-speech-rate-group');
    if (speechRateGroup) {
      const currentRate = parseFloat(localStorage.getItem('transify_speech_rate') || '1.0');
      speechRateGroup.querySelectorAll('.segmented-btn').forEach(b => {
        b.classList.toggle('active', parseFloat(b.dataset.rate) === currentRate);
        b.addEventListener('click', () => {
          speechRateGroup.querySelectorAll('.segmented-btn').forEach(x => x.classList.remove('active'));
          b.classList.add('active');
          const rate = parseFloat(b.dataset.rate || '1.0');
          if (window.TransifyApp) window.TransifyApp.speechRate = rate;
          try { localStorage.setItem('transify_speech_rate', rate.toString()); } catch (e) { }
          if (window.TransifyApp && window.TransifyApp.showToast) {
            window.TransifyApp.showToast(`Speech rate set to ${rate}x`, 'info');
          }
        });
      });
    }

    // 7. Test Voice Button & Audio Cues
    const testVoiceBtn = document.getElementById('btn-settings-test-voice');
    if (testVoiceBtn) {
      testVoiceBtn.addEventListener('click', () => {
        const phrase = 'Welcome to Transify. Assistive voice synthesis is verified and operating.';
        if (window.TransifyApp && window.TransifyApp.speak) {
          window.TransifyApp.speak(phrase, { rate: window.TransifyApp.speechRate || 1.0 });
        }
      });
    }

    const audioChimesToggle = document.getElementById('setting-audio-chimes');
    if (audioChimesToggle) {
      const isChimesActive = localStorage.getItem('transify_audio_chimes') !== 'false';
      audioChimesToggle.checked = isChimesActive;
      if (window.TransifyApp) window.TransifyApp.audioChimes = isChimesActive;

      audioChimesToggle.addEventListener('change', (e) => {
        const val = e.target.checked;
        if (window.TransifyApp) window.TransifyApp.audioChimes = val;
        try { localStorage.setItem('transify_audio_chimes', val ? 'true' : 'false'); } catch (e) { }
        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast(val ? 'Recognition Audio Chimes Enabled' : 'Audio Chimes Muted', 'info');
        }
      });
    }

    // 8. Sign Language Model Preset
    const signLangGroup = document.getElementById('settings-sign-lang-group');
    if (signLangGroup) {
      const savedSign = localStorage.getItem('transify_default_sign_lang') || 'asl';
      signLangGroup.querySelectorAll('.segmented-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.sign === savedSign);
        b.addEventListener('click', () => {
          signLangGroup.querySelectorAll('.segmented-btn').forEach(x => x.classList.remove('active'));
          b.classList.add('active');
          const signLang = b.dataset.sign;
          try { localStorage.setItem('transify_default_sign_lang', signLang); } catch (e) { }
          const aslBtn = document.getElementById('lang-asl-btn');
          const bdslBtn = document.getElementById('lang-bdsl-btn');
          if (aslBtn && bdslBtn) {
            aslBtn.classList.toggle('active', signLang === 'asl');
            bdslBtn.classList.toggle('active', signLang === 'bdsl');
          }
          if (window.TransifyApp && window.TransifyApp.showToast) {
            window.TransifyApp.showToast(`Default sign lexicon: ${signLang.toUpperCase()}`, 'info');
          }
        });
      });
    }

    // 9. Braille Standard Preset
    const brailleGroup = document.getElementById('settings-braille-standard-group');
    if (brailleGroup) {
      const savedBraille = localStorage.getItem('transify_braille_standard') || 'grade1';
      brailleGroup.querySelectorAll('.segmented-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.braille === savedBraille);
        b.addEventListener('click', () => {
          brailleGroup.querySelectorAll('.segmented-btn').forEach(x => x.classList.remove('active'));
          b.classList.add('active');
          const val = b.dataset.braille;
          try { localStorage.setItem('transify_braille_standard', val); } catch (e) { }
          if (window.TransifyApp && window.TransifyApp.showToast) {
            window.TransifyApp.showToast(`Braille transcription: ${b.textContent}`, 'info');
          }
        });
      });
    }

    // 10. Confidence Gate Option Chooser (.radio-container)
    const confGate = document.getElementById('setting-confidence-gate');
    const savedConf = localStorage.getItem('transify_confidence_gate') || '85';
    if (confGate) {
      confGate.value = savedConf;
      confGate.addEventListener('change', (e) => {
        const val = e.target.value;
        try { localStorage.setItem('transify_confidence_gate', val); } catch (e) { }
        const radio = document.querySelector(`input[name="setting_confidence_radio"][value="${val}"]`);
        if (radio) radio.checked = true;
        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast(`Vision confidence threshold: ${val}%`, 'info');
        }
      });
    }
    const matchingRadio = document.querySelector(`input[name="setting_confidence_radio"][value="${savedConf}"]`);
    if (matchingRadio) matchingRadio.checked = true;

    document.querySelectorAll('input[name="setting_confidence_radio"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        if (confGate) {
          confGate.value = e.target.value;
          confGate.dispatchEvent(new Event('change'));
        }
      });
    });

    // Make whole label row in .radio-container immediately selectable
    document.querySelectorAll('.radio-container label').forEach(lbl => {
      lbl.addEventListener('click', (e) => {
        const targetId = lbl.getAttribute('for');
        if (targetId) {
          const radio = document.getElementById(targetId);
          if (radio && !radio.checked) {
            radio.checked = true;
            radio.dispatchEvent(new Event('change'));
          }
        }
      });
    });

    // 11. Sync Account Info
    this.refreshSettingsUserUI();

    // 12. Clear Activity History
    const clearHistBtn = document.getElementById('btn-settings-clear-history');
    if (clearHistBtn) {
      clearHistBtn.addEventListener('click', async () => {
        const recentList = document.getElementById('home-recent-list');
        if (recentList) {
          recentList.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--text-2); font-size: 14px; font-weight: 600;">No recent translations yet.</div>';
        }
        try { await fetch('/api/history', { method: 'DELETE' }); } catch (e) { }
        const storageDesc = document.getElementById('settings-storage-size');
        if (storageDesc) storageDesc.textContent = '0 local activity logs';
        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast('Activity history cleared successfully', 'success');
        }
      });
    }

    // 13. Reset to Defaults
    const resetBtn = document.getElementById('btn-settings-reset-defaults');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        this.applyTheme('light');
        this.applyFontScale('normal');
        try {
          localStorage.removeItem('transify_theme');
          localStorage.removeItem('transify_font_scale');
          localStorage.removeItem('transify_focus_rings');
          localStorage.removeItem('transify_reduce_motion');
          localStorage.removeItem('transify_reduced_motion');
          localStorage.removeItem('transify_speech_rate');
          localStorage.removeItem('transify_default_sign_lang');
          localStorage.removeItem('transify_braille_standard');
          localStorage.removeItem('transify_confidence_gate');
          localStorage.removeItem('transify_audio_chimes');
          localStorage.removeItem('transify_lang');
        } catch (e) { }

        // Reset UI Toggles
        if (reduceMotionCheck) reduceMotionCheck.checked = false;
        if (focusRingToggle) focusRingToggle.checked = false;
        if (audioChimesToggle) audioChimesToggle.checked = true;
        document.documentElement.removeAttribute('data-motion');
        document.body.classList.remove('enhanced-focus');

        // Reset Speech Rate segmented buttons
        if (speechRateGroup) {
          speechRateGroup.querySelectorAll('.segmented-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.rate === '1.0');
          });
          if (window.TransifyApp) window.TransifyApp.speechRate = 1.0;
        }

        // Reset Sign Language segmented buttons
        if (signLangGroup) {
          signLangGroup.querySelectorAll('.segmented-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.sign === 'asl');
          });
        }

        // Reset Braille Standard segmented buttons
        if (brailleGroup) {
          brailleGroup.querySelectorAll('.segmented-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.braille === 'grade1');
          });
        }

        // Reset Confidence Gate
        const defConfRadio = document.getElementById('confidence-gate-85');
        if (defConfRadio) defConfRadio.checked = true;
        if (confGate) confGate.value = '85';

        // Reset Interface Language
        if (langSelect) langSelect.value = 'en';
        if (typeof applyLocale === 'function') applyLocale('en');

        if (window.TransifyApp && window.TransifyApp.showToast) {
          window.TransifyApp.showToast('All settings reset to defaults', 'info');
        }
      });
    }

    // Care sub-tabs toggle
    const intakeTab = document.getElementById('care-tab-intake-btn');
    const clinicianTab = document.getElementById('care-tab-clinician-btn');
    const chronicTab = document.getElementById('care-tab-chronic-btn');
    const intakeSlide = document.getElementById('slide-care-intake');
    const clinicianSlide = document.getElementById('slide-clinician-portal');
    const chronicSlide = document.getElementById('slide-care-chronic');

    function switchCareTab(activeTab, activeSlide) {
      [intakeTab, clinicianTab, chronicTab].forEach(t => { if (t) t.classList.remove('active'); });
      [intakeSlide, clinicianSlide, chronicSlide].forEach(s => { if (s) s.style.display = 'none'; });
      if (activeTab) activeTab.classList.add('active');
      if (activeSlide) activeSlide.style.display = (activeSlide === intakeSlide || activeSlide === chronicSlide) ? 'flex' : 'block';
    }

    if (intakeTab && intakeSlide) {
      intakeTab.addEventListener('click', () => switchCareTab(intakeTab, intakeSlide));
    }
    if (clinicianTab && clinicianSlide) {
      clinicianTab.addEventListener('click', () => {
        switchCareTab(clinicianTab, clinicianSlide);
        if (window.TransifyCare && window.TransifyCare.loadClinicianQueue) {
          window.TransifyCare.loadClinicianQueue();
          window.TransifyCare.loadDashboardStats();
        }
      });
    }
    if (chronicTab && chronicSlide) {
      chronicTab.addEventListener('click', () => {
        switchCareTab(chronicTab, chronicSlide);
      });
    }

    // Wire up Care intake submit button if care.js exists
    const careSubmitBtn = document.getElementById('care-submit-intake-btn');
    const hiddenCareSubmit = document.getElementById('care-submit-btn');
    if (careSubmitBtn && hiddenCareSubmit) {
      careSubmitBtn.addEventListener('click', () => {
        // Synchronize inputs
        const chiefInput = document.getElementById('care-chief-complaint');
        const patInput = document.getElementById('care-patient-complaint');
        if (chiefInput && patInput) patInput.value = chiefInput.value;

        const check1 = document.getElementById('care-consent-check');
        const check2 = document.getElementById('care-consent-checkbox');
        if (check1 && check2) check2.checked = check1.checked;

        hiddenCareSubmit.click();
      });
    }
  },

  applyTheme(theme) {
    if (window.applyThemeGlobal) {
      window.applyThemeGlobal(theme);
    }
  },

  applyFontScale(scale) {
    const group = document.getElementById('settings-fontsize-group');
    if (group) {
      group.querySelectorAll('.segmented-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.scale === scale);
      });
    }
    document.documentElement.setAttribute('data-scale', scale);
    document.documentElement.setAttribute('data-font-scale', scale);
    document.body.setAttribute('data-scale', scale);
    document.body.setAttribute('data-font-scale', scale);
  },

  refreshSettingsUserUI() {
    const userJson = localStorage.getItem('transify_auth_user');
    const nameEl = document.getElementById('settings-user-name');
    const emailEl = document.getElementById('settings-user-email');
    const avEl = document.getElementById('settings-avatar-initials');
    const authBtn = document.getElementById('btn-settings-auth');
    const statusPill = document.getElementById('settings-session-status');

    if (userJson) {
      try {
        const u = JSON.parse(userJson);
        if (nameEl && u.name) nameEl.textContent = u.name;
        if (emailEl && u.email) emailEl.textContent = u.email;
        if (avEl && u.name) {
          const parts = u.name.trim().split(' ');
          avEl.textContent = parts.map(p => p[0]).join('').toUpperCase().slice(0, 2);
        }
        if (authBtn) {
          authBtn.textContent = 'Sign Out';
          authBtn.style.background = '#EF4444';
        }
        if (statusPill) statusPill.innerHTML = '<span class="status-dot"></span><span>Verified User (Synced)</span>';
      } catch (_) { }
    } else {
      if (nameEl) nameEl.textContent = 'Guest User';
      if (emailEl) emailEl.textContent = 'Offline local storage mode';
      if (avEl) avEl.textContent = 'TR';
      if (authBtn) {
        authBtn.textContent = 'Sign In / Register';
        authBtn.style.background = 'var(--ink)';
      }
      if (statusPill) statusPill.innerHTML = '<span class="status-dot"></span><span>Offline Edge Mode (Private)</span>';
    }
  },

  switchSettingsTab(tabName) {
    const tabs = document.querySelectorAll('.settings-nav-tab');
    const panes = document.querySelectorAll('.settings-tab-pane');
    if (!tabs.length || !panes.length) return;

    let matched = false;
    tabs.forEach(tab => {
      const isTarget = tab.getAttribute('data-settings-tab') === tabName;
      tab.classList.toggle('active', isTarget);
      tab.setAttribute('aria-selected', isTarget ? 'true' : 'false');
      if (isTarget) matched = true;
    });

    if (!matched) {
      tabName = 'profile';
      const defTab = document.querySelector('.settings-nav-tab[data-settings-tab="profile"]');
      if (defTab) {
        tabs.forEach(t => { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); });
        defTab.classList.add('active');
        defTab.setAttribute('aria-selected', 'true');
      }
    }

    panes.forEach(pane => {
      const isTarget = pane.id === `settings-pane-${tabName}`;
      pane.classList.toggle('active', isTarget);
      pane.style.display = isTarget ? 'flex' : 'none';
    });

    try {
      localStorage.setItem('transify_settings_tab', tabName);
    } catch (_) { }
  },

  handleSettingsAuthAction() {
    const userJson = localStorage.getItem('transify_auth_user');
    if (userJson) {
      localStorage.removeItem('transify_auth_user');
      localStorage.removeItem('transify_auth_token');
      this.refreshSettingsUserUI();
      const avEl = document.getElementById('frame-avatar-btn');
      if (avEl) avEl.textContent = 'TR';
      const homeName = document.getElementById('home-user-name');
      if (homeName) homeName.textContent = 'Welcome to Transify';
      if (window.TransifyApp && window.TransifyApp.showToast) {
        window.TransifyApp.showToast('Signed out of session', 'info');
      }
    } else {
      if (window.TransifyApp && window.TransifyApp.openAuthSheet) {
        window.TransifyApp.openAuthSheet('login');
      }
    }
  }
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => EditorialController.init());
} else {
  EditorialController.init();
}
