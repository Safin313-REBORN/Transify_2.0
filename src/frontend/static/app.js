/**
 * Transify Assistive Platform - Client Application
 * Handles accessible themes, text-to-speech, real-time sign recognition,
 * Braille image processing, history management, and screen-reader announcements.
 */

// ==========================================
// 1. Accessibility & Preferences Engine
// ==========================================

var TransifyApp = window.TransifyApp = Object.assign(window.TransifyApp || {}, {
  theme: 'light',
  fontSize: 'medium',
  autoTTS: localStorage.getItem('transify_auto_tts') === 'true',
  speechRate: parseFloat(localStorage.getItem('transify_speech_rate') || '1.0'),

  init() {
    if (this._isInitialized) return;
    this._isInitialized = true;
    this.applyTheme('light', false);
    this.applyFontSize('medium', false);
    this.initAuthGateway();
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
    } catch (_) {}

    if (isAuthCompleted && !authUser) {
      authUser = { name: 'Sarah Ahmed', email: 'demo@transify.ai', provider: 'login' };
      try {
        localStorage.setItem('transify_auth_user', JSON.stringify(authUser));
        localStorage.setItem('transify_auth_token', 'jwt_' + Date.now());
      } catch (_) {}
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
    } catch (_) {}

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
      const isContrast = localStorage.getItem('transify_high_contrast') === 'true';
      toggleContrast.checked = isContrast;
      if (isContrast) document.body.classList.add('high-contrast');
      toggleContrast.addEventListener('change', () => {
        if (toggleContrast.checked) {
          document.body.classList.add('high-contrast');
          localStorage.setItem('transify_high_contrast', 'true');
          this.showToast('High Contrast Mode Enabled', 'success');
        } else {
          document.body.classList.remove('high-contrast');
          localStorage.setItem('transify_high_contrast', 'false');
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
        } catch (_) {}
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
      } catch (_) {}
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
    } catch (_) {}

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

  applyTheme(theme, save = false) {
    this.theme = 'light';
    document.documentElement.setAttribute('data-theme', 'light');
  },

  cycleTheme() {
    // Theme switching disabled per user request
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
    const onStart = options.onStart || (() => {});
    const onEnd = options.onEnd || (() => {});

    // Prefer native SpeechSynthesis for natural voice and zero network latency
    if ('speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
        window.speechSynthesis.resume();
      } catch (e) {}

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = rate;
      const targetLang = options.lang || 'en-US';
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
  roiPosition: 'right',
  lastFrameData: null,
  detectionState: {
    isDetected: false,
    label: '',
    confidence: 0,
    timestamp: 0
  },

  setRoiPosition(pos) {
    if (['right', 'center', 'left'].includes(pos)) {
      this.roiPosition = pos;
      ['right', 'center', 'left'].forEach(p => {
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
    if (this.roiPosition === 'left') {
      return [0.06, 0.08, 0.58, 0.92];
    } else if (this.roiPosition === 'right') {
      return [0.42, 0.08, 0.94, 0.92];
    }
    // Default broad centered zone: natural hand placement in front of camera
    return [0.15, 0.08, 0.85, 0.92];
  },

  setLanguageMode(mode) {
    this.currentLanguageMode = 'asl';
    this.detectionState = { isDetected: false, label: '', confidence: 0, timestamp: 0 };
    fetch('/api/sign/reset', { method: 'POST' }).catch(() => {});
  },

  setDetectionFeedback(label, confidence = 0.95) {
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

    const banner = document.getElementById('sign-prediction-banner');
    const spellPanel = document.getElementById('fingerspelling-panel');
    const sentPanel = document.getElementById('sentence-builder-panel');
    const vocabPanel = document.getElementById('sign-vocab-section');

    // Reset button states
    [exprBtn, spellBtn, sentBtn].forEach(b => {
      if (b) {
        b.classList.remove('btn-primary');
        b.classList.add('btn-secondary');
      }
    });

    // In all modes, Word Banner and Sentence Builder are ALWAYS VISIBLE underneath!
    if (banner) banner.style.display = 'flex';
    if (sentPanel) sentPanel.style.display = 'block';

    if (mode === 'expressions') {
      if (exprBtn) { exprBtn.classList.remove('btn-secondary'); exprBtn.classList.add('btn-primary'); }
      if (spellPanel) spellPanel.style.display = 'none';
      if (vocabPanel) vocabPanel.style.display = 'none';
      TransifyApp.announce('Switched to Live Words and Sentences Mode');
    } else if (mode === 'fingerspell') {
      if (spellBtn) { spellBtn.classList.remove('btn-secondary'); spellBtn.classList.add('btn-primary'); }
      if (spellPanel) spellPanel.style.display = 'block';
      if (vocabPanel) vocabPanel.style.display = 'none';
      TransifyApp.announce('Expanded A-Z Manual Alphabet Grid');
    } else if (mode === 'sentence' || mode === 'vocab') {
      if (sentBtn) { sentBtn.classList.remove('btn-secondary'); sentBtn.classList.add('btn-primary'); }
      if (spellPanel) spellPanel.style.display = 'none';
      if (vocabPanel) vocabPanel.style.display = 'block';
      TransifyApp.announce('Expanded Common Signs and Words');
    }
  },

  initFingerspellingUI() {
    const grid = document.getElementById('alphabet-grid');
    if (!grid) return;

    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    grid.innerHTML = alphabet.map(l => `
      <button type="button" class="btn btn-secondary btn-sm letter-btn" data-letter="${l}" style="font-weight: 700; padding: 6px 0; font-family: var(--font-mono);">
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
          this.setDetectionFeedback(word, 1.0);
          this.updatePredictionUI({
            label: word,
            display_text: word.replace(/_/g, ' '),
            bdsl_gloss: word,
            confidence: 0.99,
            confirmed: true,
            engine_info: {
              badge: 'Quick Sign Word',
              is_fallback: false,
              notes: 'Selected quick expressive vocabulary word.'
            }
          });
          TransifyApp.showToast(`Added "${word.replace(/_/g, ' ')}" to sentence!`, 'success');
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
        if (this.lastPrediction) {
          TransifyTTS.speak(this.lastPrediction);
        } else {
          TransifyApp.showToast('No confirmed sign to speak.', 'warning');
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

    const roi = this.getTargetRoi();
    const boxX = roi[0] * w;
    const boxY = roi[1] * h;
    const boxW = (roi[2] - roi[0]) * w;
    const boxH = (roi[3] - roi[1]) * h;

    // 1. Ambient Vignette / Semi-transparent focus mask outside the Target Box
    this.ctx.save();
    this.ctx.fillStyle = 'rgba(10, 12, 24, 0.38)';
    // Top band
    this.ctx.fillRect(0, 0, w, boxY);
    // Bottom band
    this.ctx.fillRect(0, boxY + boxH, w, h - (boxY + boxH));
    // Left band
    this.ctx.fillRect(0, boxY, boxX, boxH);
    // Right band
    this.ctx.fillRect(boxX + boxW, boxY, w - (boxX + boxW), boxH);
    this.ctx.restore();

    // Check live state
    const data = this.lastFrameData;
    const isRecentlyDetected = this.detectionState.isDetected && (Date.now() - this.detectionState.timestamp < 2500);
    const isAnalyzing = (data && data.hand_detected && data.status === 'ANALYZING');
    const isHandInRoi = (data && data.hand_detected && data.in_roi !== false);
    const isHandOutsideRoi = (data && !data.hand_detected && data.hand_outside_roi === true);

    if (isRecentlyDetected) {
      // -------------------------------------------------------------
      // STATE 1: GESTURE / WORD RECOGNIZED & CONFIRMED! (VIBRANT EMERALD GREEN)
      // -------------------------------------------------------------
      const greenColor = '#22c55e';
      this.ctx.save();
      this.ctx.strokeStyle = greenColor;
      this.ctx.lineWidth = 4;
      this.ctx.shadowColor = greenColor;
      this.ctx.shadowBlur = 14;

      // Soft emerald wash inside target box
      this.ctx.fillStyle = 'rgba(34, 197, 94, 0.12)';
      this.ctx.fillRect(boxX, boxY, boxW, boxH);
      this.ctx.strokeRect(boxX, boxY, boxW, boxH);

      // Corner target brackets
      this._drawTargetBrackets(boxX, boxY, boxW, boxH, '#4ade80', 32, 6);

      // Top Detected Header Badge
      const modelTag = (this.detectionState && this.detectionState.model_name && this.detectionState.model_name.includes('HaGRID')) ? 'HaGRID' : 'ASL';
      const badgeText = `✓ [${modelTag}] DETECTED: ${this.detectionState.label} (${Math.round(this.detectionState.confidence * 100)}%)`;
      this._drawPillBadge(boxX + 12, boxY + 12, badgeText, '#22c55e', '#ffffff');

      // Bottom confirmation ribbon inside target box
      const bottomText = `🎯 Hand Sign Confirmed: "${this.detectionState.label}"`;
      this._drawPillBadge(boxX + 12, boxY + boxH - 38, bottomText, 'rgba(15, 23, 42, 0.85)', '#4ade80');
      this.ctx.restore();

    } else if (isAnalyzing) {
      // -------------------------------------------------------------
      // STATE 2: ANALYZING HAND SIGN (PULSING ELECTRIC CYAN)
      // -------------------------------------------------------------
      const cyanColor = '#06b6d4';
      this.ctx.save();
      this.ctx.strokeStyle = cyanColor;
      this.ctx.lineWidth = 3.5;
      this.ctx.shadowColor = cyanColor;
      this.ctx.shadowBlur = 12;

      // Soft cyan wash
      this.ctx.fillStyle = 'rgba(6, 182, 212, 0.09)';
      this.ctx.fillRect(boxX, boxY, boxW, boxH);
      this.ctx.strokeRect(boxX, boxY, boxW, boxH);

      // Corner brackets
      this._drawTargetBrackets(boxX, boxY, boxW, boxH, '#22d3ee', 28, 5);

      // Top Status Pill
      const pct = data.analysis_pct || 40;
      const statusText = `🔍 Analyzing Sign (${pct}%)... Hold Steady ✋`;
      this._drawPillBadge(boxX + 12, boxY + 12, statusText, '#0891b2', '#ffffff');

      // Center guide message
      this.ctx.font = 'bold 14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      this.ctx.fillStyle = '#a5f3fc';
      this.ctx.textAlign = 'center';
      this.ctx.fillText(`⏳ Evaluating Signal Stability (${data.consensus_progress || ''})`, boxX + boxW / 2, boxY + boxH / 2);

      // Bottom candidate preview
      if (data.candidate_label) {
        const candidateText = `Candidate: [${data.candidate_label}]`;
        this._drawPillBadge(boxX + 12, boxY + boxH - 38, candidateText, 'rgba(15, 23, 42, 0.80)', '#67e8f9');
      }

      // Hand Bounding Box Tracking if present
      if (this.lastHandBBox) {
        const sX = w / (this.lastFrameDims ? this.lastFrameDims[0] : 640);
        const sY = h / (this.lastFrameDims ? this.lastFrameDims[1] : 480);
        const hX = this.lastHandBBox[0] * sX;
        const hY = this.lastHandBBox[1] * sY;
        const hW = this.lastHandBBox[2] * sX;
        const hH = this.lastHandBBox[3] * sY;

        this.ctx.strokeStyle = '#67e8f9';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(hX, hY, hW, hH);
      }
      this.ctx.restore();

    } else if (isHandInRoi) {
      // -------------------------------------------------------------
      // STATE 3: HAND IN POSITION INSIDE TARGET BOX (EMERALD / READY)
      // -------------------------------------------------------------
      const activeColor = '#10b981';
      this.ctx.save();
      this.ctx.strokeStyle = activeColor;
      this.ctx.lineWidth = 2.5;
      this.ctx.shadowColor = activeColor;
      this.ctx.shadowBlur = 8;

      // Soft active wash
      this.ctx.fillStyle = 'rgba(16, 185, 129, 0.06)';
      this.ctx.fillRect(boxX, boxY, boxW, boxH);
      this.ctx.strokeRect(boxX, boxY, boxW, boxH);

      // Corner brackets
      this._drawTargetBrackets(boxX, boxY, boxW, boxH, '#34d399', 28, 4);

      // Top Status Pill
      const statusText = `✋ Hand In Position — Ready To Sign`;
      this._drawPillBadge(boxX + 12, boxY + 12, statusText, '#10b981', '#ffffff');

      // Center guide message
      this.ctx.font = '600 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      this.ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
      this.ctx.textAlign = 'center';
      this.ctx.fillText(`Show a hand sign (e.g. Thumbs Up, Peace, OK, Fist, Hello)`, boxX + boxW / 2, boxY + boxH / 2);

      // Hand Bounding Box Tracking if present
      if (this.lastHandBBox) {
        const sX = w / (this.lastFrameDims ? this.lastFrameDims[0] : 640);
        const sY = h / (this.lastFrameDims ? this.lastFrameDims[1] : 480);
        const hX = this.lastHandBBox[0] * sX;
        const hY = this.lastHandBBox[1] * sY;
        const hW = this.lastHandBBox[2] * sX;
        const hH = this.lastHandBBox[3] * sY;

        this.ctx.strokeStyle = '#6ee7b7';
        this.ctx.lineWidth = 2;
        this.ctx.shadowBlur = 4;
        this.ctx.strokeRect(hX, hY, hW, hH);
      }
      this.ctx.restore();

    } else if (isHandOutsideRoi) {
      // -------------------------------------------------------------
      // STATE 4: HAND DETECTED OUTSIDE TARGET BOX (AMBER WARNING)
      // -------------------------------------------------------------
      const amberColor = '#f59e0b';
      this.ctx.save();
      this.ctx.strokeStyle = amberColor;
      this.ctx.lineWidth = 3;
      this.ctx.setLineDash([8, 6]);
      this.ctx.shadowColor = amberColor;
      this.ctx.shadowBlur = 8;
      this.ctx.strokeRect(boxX, boxY, boxW, boxH);
      this.ctx.setLineDash([]);

      this._drawTargetBrackets(boxX, boxY, boxW, boxH, '#fbbf24', 26, 5);

      const warnText = `⚠️ Hand Outside Box — Place Hand Inside ✋`;
      this._drawPillBadge(boxX + 12, boxY + 12, warnText, '#f59e0b', '#ffffff');

      // Center guide message
      this.ctx.font = 'bold 15px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      this.ctx.fillStyle = '#fef08a';
      this.ctx.textAlign = 'center';
      this.ctx.fillText(`👉 Move Hand Inside This Target Box`, boxX + boxW / 2, boxY + boxH / 2);
      this.ctx.restore();

    } else {
      // -------------------------------------------------------------
      // STATE 5: WAITING / IDLE TARGET BOX (PURPLE HUD)
      // -------------------------------------------------------------
      const purpleColor = '#8338ec';
      this.ctx.save();
      this.ctx.strokeStyle = purpleColor;
      this.ctx.lineWidth = 2.5;
      this.ctx.setLineDash([8, 6]);
      this.ctx.shadowColor = purpleColor;
      this.ctx.shadowBlur = 8;
      this.ctx.strokeRect(boxX, boxY, boxW, boxH);
      this.ctx.setLineDash([]);

      this._drawTargetBrackets(boxX, boxY, boxW, boxH, '#a855f7', 28, 5);

      // Top Title Pill
      const guideText = `🎯 Fixed Hand Sign Zone — Place Hand Here`;
      this._drawPillBadge(boxX + 12, boxY + 12, guideText, '#8338ec', '#ffffff');

      // Center Holographic Hand Icon & Subtext
      this.ctx.textAlign = 'center';
      this.ctx.font = '38px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      this.ctx.fillStyle = 'rgba(255, 255, 255, 0.55)';
      this.ctx.fillText(`✋`, boxX + boxW / 2, boxY + boxH / 2 - 8);

      this.ctx.font = '600 13px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      this.ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
      this.ctx.fillText(`Hold hand here for ASL & HaGRID recognition`, boxX + boxW / 2, boxY + boxH / 2 + 22);

      // Sub-note explaining face is ignored
      this.ctx.font = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      this.ctx.fillStyle = 'rgba(216, 180, 254, 0.75)';
      this.ctx.fillText(`(Face & background outside box are ignored)`, boxX + boxW / 2, boxY + boxH / 2 + 42);
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
      if (labelEl) labelEl.textContent = 'Signing...';
      if (glossEl) glossEl.textContent = `[Filtering: ${result.rejection_reason || 'Low motion / Idle'}]`;
      if (progressFill) progressFill.style.width = '20%';
      if (engineNote) engineNote.style.display = 'none';
      return;
    }

    const confPct = (result.confidence * 100).toFixed(1);
    const confVal = Math.round((result.confidence || 0) * 100);

    // Auto-fit recognized word (§6.4)
    if (labelEl) {
      const rawText = result.label || '—';
      let letters = [];
      if (typeof Intl !== 'undefined' && Intl.Segmenter) {
        try {
          const seg = new Intl.Segmenter('en', { granularity: 'grapheme' });
          for (const s of seg.segment(rawText)) {
            letters.push(s.segment);
          }
        } catch(e) {
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
    }

    if (glossEl) glossEl.textContent = `[ASL: ${result.gloss || defaultGloss || result.label}]`;
    if (confEl) {
      confEl.textContent = `${confVal}%`;
      confEl.className = result.confidence > 0.85 ? 'ring-pct badge-success' : 'ring-pct badge-warning';
    }

    // Confidence Ring SVG (104x104)
    const ringCircle = document.getElementById('confidence-ring-circle');
    if (ringCircle) {
      const offset = 201 * (1 - Math.min(1, Math.max(0, result.confidence || 0)));
      ringCircle.style.strokeDashoffset = offset;
      ringCircle.setAttribute('stroke', result.confirmed ? '#0F9D74' : '#8338EC');
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
      if (result.confirmed) {
        statusLine.textContent = 'Confirmed after 3 matching frames';
      } else if (result.status === 'ANALYZING') {
        statusLine.textContent = `Checking frame ${count} of 3`;
      } else if (result.label && result.label !== 'IDLE') {
        statusLine.textContent = `Observing ${result.label}`;
      } else {
        statusLine.textContent = 'Show your hand in the box';
      }
    }

    // Speak word button
    const speakWordBtn = document.getElementById('speak-pred-btn');
    if (speakWordBtn) {
      speakWordBtn.textContent = 'Speak ' + (result.label || 'word');
      speakWordBtn.disabled = !result.confirmed;
    }

    // ROI Beam
    const roiBox = document.getElementById('sign-roi-box');
    if (roiBox) {
      roiBox.classList.toggle('analyzing', !result.confirmed && result.status === 'ANALYZING');
    }

    // Unified Translation Layer display
    const englishText = result.english_text || result.display_text || result.label;
    if (unifiedOutputEl && englishText) {
      unifiedOutputEl.textContent = `"${englishText}"`;
    }
    if (sourceTagEl) {
      sourceTagEl.textContent = 'SignFrame AI (ASL)';
      sourceTagEl.style.color = '#8338ec';
      sourceTagEl.style.background = 'rgba(131, 56, 236, 0.15)';
    }

    // Engine Info and Latency Display
    if (engineNote && result.engine_info) {
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
    }

    // Trigger GREEN BOX on camera overlay whenever word / sign is detected
    this.setDetectionFeedback(result.label, result.confidence || 0.95);

    // Update consensus debounce progress bar
    if (progressFill) {
      const count = result.debounce_count || 1;
      const target = result.debounce_target || 3;
      const pct = Math.min(100, Math.round((count / target) * 100));
      progressFill.style.width = `${pct}%`;
    }

    if (result.confirmed) {
      const now = Date.now();
      const isNewSign = (result.label !== this.lastConfirmedSign);
      const isTimeElapsed = (now - this.lastConfirmedSpeechTime > 2500);

      this.lastPrediction = result.label;

      if (isNewSign || isTimeElapsed) {
        this.lastConfirmedSign = result.label;
        this.lastConfirmedSpeechTime = now;

        TransifyApp.announce(`Recognized ASL Sign: ${result.label}`);
        if (statusNote) statusNote.textContent = `Confirmed expression: ${result.label}`;

        // Automatically append confirmed sign token to Sentence Builder
        this.addTokenToSentence(result.label);

        if (this.autoSpeak) {
          TransifyTTS.speak(englishText);
        }
      }
    } else {
      if (statusNote) statusNote.textContent = `Debouncing consensus (${result.debounce_count}/${result.debounce_target})...`;
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

var BraillePage = window.BraillePage = {
  currentFile: null,
  currentImageSrc: null,
  isInitialized: false,

  init() {
    if (this.isInitialized) return;
    this.isInitialized = true;
    this.setupDropzone();
    this.setupActionButtons();
  },

  setupDropzone() {
    const dropzone = document.getElementById('braille-dropzone');
    const fileInput = document.getElementById('braille-file-input');

    if (!dropzone || !fileInput) return;

    dropzone.addEventListener('click', () => fileInput.click());

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
      // Also update dropzone visual state
      const dropzone = document.getElementById('braille-dropzone');
      if (dropzone) {
        dropzone.style.border = '2px solid #22c55e';
        dropzone.style.background = 'rgba(34, 197, 94, 0.05)';
      }
    };
    reader.readAsDataURL(file);

    // Update dropzone text
    const dropzoneText = document.getElementById('dropzone-text');
    if (dropzoneText) {
      dropzoneText.innerHTML = `<strong>✅ Selected:</strong> ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    }

    // Hide old results
    const resultsSection = document.getElementById('braille-results-section');
    if (resultsSection) resultsSection.style.display = 'none';

    TransifyApp.showToast(`Translating ${file.name}...`, 'info');
    // Auto-translate immediately upon selection or sample click
    this.runTranslation();
  },

  setupActionButtons() {
    const translateBtn = document.getElementById('translate-braille-btn');
    if (translateBtn) {
      translateBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.runTranslation();
      });
    }

    // Also bind the form submit to prevent page reload
    const uploadForm = document.getElementById('braille-upload-form');
    if (uploadForm) {
      uploadForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.runTranslation();
      });
    }

    const iqaBtn = document.getElementById('check-iqa-btn');
    if (iqaBtn) {
      iqaBtn.addEventListener('click', () => this.runIQACheck());
    }

    const speakBtn = document.getElementById('speak-braille-btn');
    if (speakBtn) {
      speakBtn.addEventListener('click', () => {
        const textarea = document.getElementById('braille-text-output');
        const text = textarea ? textarea.value.trim() : '';
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
        if (textarea && textarea.value) {
          navigator.clipboard.writeText(textarea.value).then(() => {
            TransifyApp.showToast('Copied to clipboard!', 'success');
          }).catch(() => {
            TransifyApp.showToast('Copy failed. Please select and copy manually.', 'warning');
          });
        }
      });
    }

    const downloadBtn = document.getElementById('download-braille-btn');
    if (downloadBtn) {
      downloadBtn.addEventListener('click', () => {
        const textarea = document.getElementById('braille-text-output');
        const text = textarea ? textarea.value : '';
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
    if (translateBtn) {
      translateBtn.disabled = true;
      translateBtn.innerHTML = '⏳ Analyzing Braille Dots...';
    }

    // Show loading state in results
    const resultsSection = document.getElementById('braille-results-section');
    const outputTextarea = document.getElementById('braille-text-output');
    if (resultsSection) resultsSection.style.display = 'block';
    if (outputTextarea) outputTextarea.value = 'Translating... please wait.';

    const formData = new FormData();
    formData.append('file', this.currentFile);
    formData.append('speak_tts', 'false');

    try {
      const res = await fetch('/api/braille/translate', { method: 'POST', body: formData });
      const data = await res.json();

      if (!res.ok || !data.success) {
        // Show IQA rejection details
        const errorObj = data.error || {};
        this.displayIQAResult({
          accepted: false,
          rejection_reason: errorObj.rejection_reason || data.detail || 'Translation failed: could not read Braille from this image.',
          metrics: errorObj.metrics || {},
          remediation_guidance: errorObj.user_guidance || 'Please upload a clear photograph of physical embossed Braille.'
        });
        if (outputTextarea) outputTextarea.value = 'Translation failed. See quality report above.';
        TransifyApp.showToast('Image rejected: ' + (errorObj.rejection_reason || 'Could not translate Braille.'), 'danger');
        return;
      }

      const result = data.data;

      // Show translated text
      if (outputTextarea) {
        outputTextarea.value = result.text || '(No text detected)';
      }

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

      // Show IQA as passed
      this.displayIQAResult({ accepted: true, metrics: result.qa_metrics || {}, is_usable: true });

      TransifyApp.showToast('Braille translated successfully!', 'success');
      TransifyApp.announce('Translation complete: ' + result.text);

      // Auto-speak the translation
      if (result.text && result.text.trim()) {
        setTimeout(() => TransifyTTS.speak(result.text), 500);
      }

    } catch (e) {
      TransifyApp.showToast('Error during Braille translation: ' + e.message, 'danger');
      if (outputTextarea) outputTextarea.value = 'Translation error. Check server connection.';
    } finally {
      if (translateBtn) {
        translateBtn.disabled = false;
        translateBtn.innerHTML = '✨ Translate Braille Image';
      }
    }
  }
};

// ==========================================
// 6. Speech-to-Text (STT) Module
// ==========================================

var TransifySTT = window.TransifySTT = {
  recognition: null,
  isListening: false,
  lang: 'en-US',
  finalTranscript: '',
  isLargeFont: false,
  isInitialized: false,

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
          }
          if (typeof openSlide === 'function') {
            openSlide('slide-tts');
          }
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
        this.updateUI(true);
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
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (e) {}
    }
    this.updateUI(false);
    TransifyApp.announce('Speech recognition stopped');
  },

  clear() {
    this.finalTranscript = '';
    this.renderText('', '');
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
  },

  updateUI(listening) {
    const btn = document.getElementById('stt-toggle-btn');
    const icon = document.getElementById('stt-mic-icon');
    const hint = document.getElementById('stt-mic-hint');
    const pill = document.getElementById('stt-status-pill');

    if (listening) {
      if (btn) btn.classList.add('listening');
      if (icon) icon.textContent = '⏹️';
      if (hint) {
        hint.textContent = 'Listening... Speak now';
        hint.style.color = '#dc2626';
      }
      if (pill) {
        pill.textContent = '🔴 Listening Live...';
        pill.className = 'badge badge-danger';
      }
    } else {
      if (btn) btn.classList.remove('listening');
      if (icon) icon.textContent = '🎙️';
      if (hint) {
        hint.textContent = 'Tap to Speak';
        hint.style.color = '#4b1a11';
      }
      if (pill) {
        pill.textContent = '🎙️ Ready to Listen';
        pill.className = 'badge badge-info';
      }
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
        TransifyApp.showToast('Voice playback stopped.', 'info');
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (textarea) textarea.value = '';
        if (charCount) charCount.textContent = '0 chars';
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

    if ('speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
        window.speechSynthesis.resume();
      } catch (e) {}

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
      };
      utterance.onend = () => {
        if (speakBtn) {
          speakBtn.innerHTML = '🔊 Speak Voice';
          speakBtn.classList.remove('btn-success');
        }
      };
      utterance.onerror = (e) => {
        console.warn('TTS utterance error:', e);
        if (speakBtn) {
          speakBtn.innerHTML = '🔊 Speak Voice';
          speakBtn.classList.remove('btn-success');
        }
        TransifyTTS.fallbackServerTTS(cleanText);
      };

      try {
        window.speechSynthesis.speak(utterance);
      } catch (e) {
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
  window.openAuthSheet = (m) => TransifyApp.openAuthSheet(m);
  window.closeAuthSheet = () => TransifyApp.closeAuthSheet();
  window.handleDirectLogin = () => TransifyApp.handleDirectLogin();
  window.handleDemoLogin = () => TransifyApp.handleDemoLogin();
  window.handleAuthSubmit = (e) => TransifyApp.handleAuthSubmit(e);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTransifyAllModules);
} else {
  initTransifyAllModules();
}

// Expose global helper for custom duration or manual splash testing
window.showTransifySplashScreen = function(durationMs = 3500) {
  const splash = document.getElementById('transify-splash-screen');
  if (!splash) return;
  splash.style.display = 'flex';
  splash.classList.remove('splash-hidden');
  const fill = document.getElementById('splash-progress-fill');
  if (fill) fill.style.width = '0%';
  TransifyApp.initSplashScreen(durationMs);
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
  defaultPhrases: [
    { en: 'Hello', bn: 'হ্যালো', cat: 'Everyday' },
    { en: 'Thank you', bn: 'ধন্যবাদ', cat: 'Everyday' },
    { en: 'Please slow down', bn: 'দয়া করে আস্তে বলুন', cat: 'Everyday' },
    { en: 'Can you write that down?', bn: 'আপনি কি এটা লিখে দিতে পারবেন?', cat: 'Everyday' },
    { en: 'I do not understand', bn: 'আমি বুঝতে পারছি না', cat: 'Everyday' },
    { en: 'I need water', bn: 'আমার পানি দরকার', cat: 'Needs' },
    { en: 'Where is the restroom?', bn: 'টয়লেট কোথায়?', cat: 'Needs' },
    { en: 'I need help reading this', bn: 'এটা পড়তে আমার সাহায্য দরকার', cat: 'Needs' },
    { en: 'I need help', bn: 'আমার সাহায্য দরকার', cat: 'Emergency' },
    { en: 'Please call a doctor', bn: 'দয়া করে ডাক্তার ডাকুন', cat: 'Emergency' },
    { en: 'I am lost', bn: 'আমি পথ হারিয়ে ফেলেছি', cat: 'Emergency' }
  ],

  init() {
    this.setupRouter();
    this.setupWelcomeScreen();
    this.setupHomeScreen();
    this.setupPhrasesScreen();
    this.setupBrailleInteractiveCell();
    this.setupSettingsScreen();

    // Check initial route
    const hash = window.location.hash.replace('#', '').toLowerCase();
    if (hash) {
      this.routeTo(hash);
    } else {
      const welcomed = localStorage.getItem('transify.welcomed');
      if (!welcomed) {
        this.routeTo('welcome');
      } else {
        this.routeTo('home');
      }
    }
  },

  setupRouter() {
    window.routeTo = (r) => this.routeTo(r);

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
  },

  routeTo(rawRoute) {
    let route = (rawRoute || 'home').toLowerCase();
    if (route === 'voice') route = 'stt';
    if (route === 'care') route = 'care';
    if (route === 'care-intake') route = 'care';
    if (route === 'clinician') route = 'care';

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
      settings: 'view-settings'
    };

    const targetViewId = viewMap[route] || 'view-home';
    document.querySelectorAll('.page-view').forEach(view => {
      if (view.id === targetViewId) {
        view.classList.add('active');
        view.style.display = 'flex';
      } else {
        view.classList.remove('active');
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

    // Sub-route handling
    if (route === 'sign' && window.SignPage && window.SignPage.init) {
      window.SignPage.init();
    }

    if (rawRoute === 'clinician') {
      const clinicianTab = document.getElementById('care-tab-clinician-btn');
      if (clinicianTab) clinicianTab.click();
    } else if (rawRoute === 'care-intake' || rawRoute === 'care') {
      const intakeTab = document.getElementById('care-tab-intake-btn');
      if (intakeTab) intakeTab.click();
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
        try { localStorage.setItem('transify.welcomed', '1'); } catch(e) {}
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
    let isBn = false;
    if (langBtn) {
      langBtn.addEventListener('click', () => {
        isBn = !isBn;
        langBtn.textContent = isBn ? 'English' : 'বাংলা';
        const line1 = document.getElementById('welcome-line-1');
        const line2 = document.getElementById('welcome-line-2');
        const sub = document.getElementById('welcome-subtext');
        if (isBn) {
          if (line1) line1.textContent = 'ইশারা থেকে কথা,';
          if (line2) line2.textContent = 'সরাসরি শুনুন।';
          if (sub) sub.textContent = 'ক্যামেরার সামনে ইশারা করুন। ট্রান্সিফাই বাংলা ও আমেরিকান সাইন ল্যাঙ্গুয়েজ চিনে তাৎক্ষণিক অনুবাদ শোনায়।';
        } else {
          if (line1) line1.textContent = 'Signs to words,';
          if (line2) line2.textContent = 'spoken aloud.';
          if (sub) sub.textContent = 'Hold a sign to the camera. Transify recognizes Bengali and American Sign Language and speaks the translation.';
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
    const greet = h < 12 ? 'Good morning' : (h < 18 ? 'Good afternoon' : 'Good evening');
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
      } catch(e) {}
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
        const phrase = chip.getAttribute('data-phrase');
        if (phrase && sayInput) {
          sayInput.value = phrase;
          sayInput.focus();
        }
      });
    });

    // 5. Interface language toggle
    const enBtn = document.getElementById('home-lang-en');
    const bnBtn = document.getElementById('home-lang-bn');
    if (enBtn && bnBtn) {
      enBtn.addEventListener('click', () => {
        enBtn.classList.add('active');
        enBtn.setAttribute('aria-pressed', 'true');
        bnBtn.classList.remove('active');
        bnBtn.setAttribute('aria-pressed', 'false');
      });
      bnBtn.addEventListener('click', () => {
        bnBtn.classList.add('active');
        bnBtn.setAttribute('aria-pressed', 'true');
        enBtn.classList.remove('active');
        enBtn.setAttribute('aria-pressed', 'false');
      });
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
    const toastMsg = document.getElementById('phrase-toast-msg');
    const seedBtn = document.getElementById('btn-seed-starter-phrases');

    let activeCategory = 'All';
    let newCategory = 'Everyday';
    let searchQuery = '';
    let playingIdx = -1;

    // Load phrases
    let phrases = [];
    try {
      const stored = localStorage.getItem('transify_phrases');
      if (stored) phrases = JSON.parse(stored);
      else phrases = [...this.defaultPhrases];
    } catch(e) {
      phrases = [...this.defaultPhrases];
    }

    const savePhrases = () => {
      try { localStorage.setItem('transify_phrases', JSON.stringify(phrases)); } catch(e) {}
    };

    const render = () => {
      if (!grid) return;
      const q = searchQuery.trim().toLowerCase();
      const inCat = (p) => activeCategory === 'All' || p.cat === activeCategory;
      const match = (p) => !q || p.en.toLowerCase().includes(q) || (p.bn && p.bn.includes(q));

      const visible = phrases.filter(p => inCat(p) && match(p));

      // Update counts
      const counts = {
        all: phrases.length,
        everyday: phrases.filter(p => p.cat === 'Everyday').length,
        needs: phrases.filter(p => p.cat === 'Needs').length,
        emergency: phrases.filter(p => p.cat === 'Emergency').length
      };

      const cAll = document.getElementById('count-all');
      const cEv = document.getElementById('count-everyday');
      const cNd = document.getElementById('count-needs');
      const cEm = document.getElementById('count-emergency');
      if (cAll) cAll.textContent = counts.all;
      if (cEv) cEv.textContent = counts.everyday;
      if (cNd) cNd.textContent = counts.needs;
      if (cEm) cEm.textContent = counts.emergency;

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
            if (title) title.textContent = 'No phrases here yet';
            if (body) body.textContent = 'Add the phrases you say most. They will appear here.';
            if (seedBtn) seedBtn.style.display = 'inline-block';
          }
        }
        return;
      }

      grid.style.display = 'grid';
      if (emptyState) emptyState.style.display = 'none';

      grid.innerHTML = visible.map((p, idx) => `
        <li>
          <button type="button" class="phrase-card press" data-idx="${idx}" aria-label="Say aloud: ${p.en}">
            <span class="phrase-card-top ${p.cat === 'Emergency' ? 'emergency-tag' : ''}">
              <span>${p.cat}</span>
              <span class="phrase-card-icon" id="card-icon-${idx}">
                <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4A4860" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/></svg>
              </span>
            </span>
            <span class="phrase-en">${p.en}</span>
            ${p.bn ? `<span class="phrase-bn">${p.bn}</span>` : ''}
          </button>
        </li>
      `).join('');

      // Wire card click speech
      grid.querySelectorAll('.phrase-card').forEach(card => {
        card.addEventListener('click', () => {
          const i = parseInt(card.getAttribute('data-idx') || '0', 10);
          const p = visible[i];
          if (!p) return;

          const iconEl = document.getElementById(`card-icon-${i}`);
          if (iconEl) {
            iconEl.innerHTML = '<span class="wave" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></span>';
          }

          if (window.TransifyTTS && window.TransifyTTS.speak) {
            window.TransifyTTS.speak(p.en, {
              onEnd: () => {
                if (iconEl) {
                  iconEl.innerHTML = '<svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4A4860" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/></svg>';
                }
              }
            });
          }
        });
      });
    };

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
        if (!text) {
          npInput.focus();
          if (toastMsg) toastMsg.textContent = 'Type a phrase first';
          return;
        }

        phrases.unshift({ en: text, bn: '', cat: newCategory });
        savePhrases();
        npInput.value = '';
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
        savePhrases();
        render();
      });
    }

    // Initial render
    render();
  },

  setupBrailleInteractiveCell() {
    let activeDots = [];
    const charDisplay = document.getElementById('braille-interactive-char');
    document.querySelectorAll('[data-braille-dot]').forEach(btn => {
      btn.addEventListener('click', () => {
        const dot = btn.getAttribute('data-braille-dot');
        btn.classList.toggle('active');
        if (activeDots.includes(dot)) {
          activeDots = activeDots.filter(d => d !== dot);
        } else {
          activeDots.push(dot);
        }
        activeDots.sort();
        const key = activeDots.join('');
        const char = this.brailleMap[key] || (key ? '–' : '—');
        if (charDisplay) {
          charDisplay.textContent = `Character: ${char}`;
        }
      });
    });
  },

  setupSettingsScreen() {
    // Reduce motion toggle
    const reduceMotionCheck = document.getElementById('setting-reduce-motion');
    const isReduced = localStorage.getItem('transify_reduce_motion') === '1';
    if (reduceMotionCheck) {
      reduceMotionCheck.checked = isReduced;
      if (isReduced) document.documentElement.setAttribute('data-motion', 'reduced');

      reduceMotionCheck.addEventListener('change', (e) => {
        const val = e.target.checked;
        if (val) {
          document.documentElement.setAttribute('data-motion', 'reduced');
          try { localStorage.setItem('transify_reduce_motion', '1'); } catch(e) {}
        } else {
          document.documentElement.removeAttribute('data-motion');
          try { localStorage.removeItem('transify_reduce_motion'); } catch(e) {}
        }
      });
    }

    // Care sub-tabs toggle
    const intakeTab = document.getElementById('care-tab-intake-btn');
    const clinicianTab = document.getElementById('care-tab-clinician-btn');
    const intakeSlide = document.getElementById('slide-care-intake');
    const clinicianSlide = document.getElementById('slide-clinician-portal');

    if (intakeTab && clinicianTab && intakeSlide && clinicianSlide) {
      intakeTab.addEventListener('click', () => {
        intakeTab.classList.add('active');
        clinicianTab.classList.remove('active');
        intakeSlide.style.display = 'flex';
        clinicianSlide.style.display = 'none';
      });

      clinicianTab.addEventListener('click', () => {
        clinicianTab.classList.add('active');
        intakeTab.classList.remove('active');
        clinicianSlide.style.display = 'block';
        intakeSlide.style.display = 'none';

        if (window.TransifyCare && window.TransifyCare.loadClinicianQueue) {
          window.TransifyCare.loadClinicianQueue();
          window.TransifyCare.loadDashboardStats();
        }
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
  }
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => EditorialController.init());
} else {
  EditorialController.init();
}
