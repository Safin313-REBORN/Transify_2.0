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
    const savedTheme = localStorage.getItem('transify_theme') || 'light';
    this.applyTheme(savedTheme, false);
    const savedFontSize = localStorage.getItem('transify_font_size') || 'medium';
    this.applyFontSize(savedFontSize, false);
    this.setupAccessibilityListeners();
    this.initAuthGateway();
    this.initScrollProgressBar();
    this.initCookieBanner();
    this.initUtmTracking();
    this.initKeyboardShortcuts();
  },

  async initAuthGateway() {
    const authOverlay = document.getElementById('transify-auth-screen');
    const splash = document.getElementById('transify-splash-screen');
    if (!authOverlay) {
      if (splash) splash.style.display = 'none';
      return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const forceLogin = urlParams.get('view') === 'login' || urlParams.get('logout') === '1';

    if (forceLogin) {
      try {
        localStorage.removeItem('transify_auth_user');
        localStorage.removeItem('transify_session_token');
        localStorage.removeItem('transify_auth_token');
        localStorage.removeItem('transify_guest_mode');
      } catch (_) {}
    }

    const isGuest = localStorage.getItem('transify_guest_mode') === 'true';
    let authUser = null;
    try {
      authUser = JSON.parse(localStorage.getItem('transify_auth_user') || 'null');
    } catch (_) {}

    // 1. If in explicit guest mode and not forced to login:
    if (isGuest && !forceLogin) {
      authOverlay.style.display = 'none';
      authOverlay.classList.add('auth-hidden');
      authOverlay.style.pointerEvents = 'none';
      authOverlay.style.zIndex = '-99999';
      this.updateProfileUI(authUser || { name: 'Guest User (Demo Mode)', email: 'guest@transify.ai', is_guest: true });
      if (splash) {
        splash.style.display = 'none';
        splash.classList.add('splash-hidden');
      }
      this.checkUrlSlide();
      this.bindProfileModal();
      return;
    }

    // 2. If user profile cached, verify server session via secure HttpOnly cookie
    if (authUser && !forceLogin) {
      try {
        const checkRes = await fetch('/api/auth/me', {
          credentials: 'same-origin'
        });
        const checkData = await checkRes.json().catch(() => ({}));
        if (checkRes.ok && checkData.authenticated && checkData.user) {
          authUser = checkData.user;
          localStorage.setItem('transify_auth_user', JSON.stringify(authUser));
          authOverlay.style.display = 'none';
          authOverlay.classList.add('auth-hidden');
          authOverlay.style.pointerEvents = 'none';
          authOverlay.style.zIndex = '-99999';
          this.updateProfileUI(authUser);
          if (splash) {
            splash.style.display = 'none';
            splash.classList.add('splash-hidden');
          }
          this.checkUrlSlide();
          this.bindProfileModal();
          return;
        } else {
          // Session expired or revoked: require re-authentication
          localStorage.removeItem('transify_auth_user');
          authUser = null;
        }
      } catch (netErr) {
        // Offline / network failure: NEVER grant authenticated access to private account data
        console.warn('Network error during session check:', netErr);
        this.showAuthAlert('Unable to verify session with authentication server. Please check your connection or continue as Demo Guest.', false);
      }
    }

    // 3. User is NOT logged in: Show Auth Screen FIRST!
    if (splash) {
      splash.style.display = 'none';
      splash.classList.add('splash-hidden');
    }
    authOverlay.style.display = 'flex';
    authOverlay.classList.remove('auth-hidden');
    authOverlay.style.pointerEvents = 'auto';
    authOverlay.style.zIndex = '1000000';
    this.bindAuthEvents();
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
    if (window.AuthController) return window.AuthController.openSheet(mode);
    const sheetContainer = document.getElementById('auth-sheet-container');
    if (sheetContainer) sheetContainer.classList.add('active');
  },

  closeAuthSheet() {
    if (window.AuthController) return window.AuthController.closeSheet();
    const sheetContainer = document.getElementById('auth-sheet-container');
    if (sheetContainer) sheetContainer.classList.remove('active');
  },

  switchAuthTab(mode = 'login') {
    if (window.AuthController) return window.AuthController.switchTab(mode);
    this.activeAuthMode = mode;
  },

  handleDirectLogin() {
    if (window.AuthController) return window.AuthController.submitGuest();
  },

  handleDemoLogin() {
    if (window.AuthController) return window.AuthController.submitGuest();
  },

  handleDemoGuest() {
    if (window.AuthController) return window.AuthController.submitGuest();
  },

  togglePasswordVisibility() {
    if (window.AuthController) return window.AuthController.togglePasswordVisibility();
  },

  showAuthAlert(msg, isSuccess = true) {
    if (window.AuthController) return window.AuthController.showAlert(msg, isSuccess);
    const alertBox = document.getElementById('auth-alert');
    if (!alertBox) return;
    alertBox.textContent = msg;
    alertBox.className = `auth-status-alert ${isSuccess ? 'success' : 'error'}`;
    alertBox.style.display = 'block';
  },

  hideAuthAlert() {
    if (window.AuthController) return window.AuthController.hideAlert();
    const alertBox = document.getElementById('auth-alert');
    if (alertBox) {
      alertBox.style.display = 'none';
      alertBox.textContent = '';
    }
  },

  handleForgotPassword(e) {
    if (e && typeof e.preventDefault === 'function') e.preventDefault();
    if (window.AuthController) return window.AuthController.openForgotPassword();
  },

  quickFillDemo() {
    if (window.AuthController) return window.AuthController.submitGuest();
  },

  async handleAuthSubmit(e) {
    if (e && typeof e.preventDefault === 'function') e.preventDefault();
    if (window.AuthController) return window.AuthController.submitAuth(e);
  },

  handleGoogleLogin() {
    if (window.AuthController) return window.AuthController.handleGoogleClick();
  },

  completeAuthentication(userObj, isGuest = false) {
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
    } else if (window.location.hash === '#hub') {
      if (typeof openSlide === 'function') openSlide('slide-communication-hub');
    } else if (window.location.hash === '#phrases') {
      if (typeof openSlide === 'function') openSlide('slide-phraseboard');
    } else if (window.location.hash === '#dashboard') {
      if (typeof openSlide === 'function') openSlide('slide-dashboard');
    }
  },

  updateProfileUI(userObj) {
    if (!userObj) return;
    const nameText = document.getElementById('profile-name-text');
    const emailText = document.getElementById('profile-email-text');
    if (nameText && userObj.name) {
      nameText.textContent = userObj.is_guest ? 'Guest User (Demo Mode)' : userObj.name;
    }
    if (emailText && userObj.email) {
      emailText.textContent = userObj.is_guest ? 'demo-guest@transify.ai' : userObj.email;
    }
  },

  bindProfileModal() {
    const avatarBtn = document.getElementById('frame-avatar-btn');
    if (avatarBtn) {
      avatarBtn.style.cursor = 'pointer';
      avatarBtn.onclick = () => this.openProfileModal();
    }
  },

  openProfileModal() {
    const modal = document.getElementById('profile-modal-overlay');
    if (modal) modal.classList.add('open');
  },

  closeProfileModal() {
    const modal = document.getElementById('profile-modal-overlay');
    if (modal) modal.classList.remove('open');
  },

  async logoutUser() {
    this.closeProfileModal();
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json'
        }
      }).catch(() => {});
    } catch (_) {}

    try {
      localStorage.removeItem('transify_auth_user');
      localStorage.removeItem('transify_session_token');
      localStorage.removeItem('transify_auth_token');
      localStorage.removeItem('transify_guest_mode');
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
      authOverlay.style.pointerEvents = 'auto';
      authOverlay.style.zIndex = '1000000';
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

  async handleDeleteAccount() {
    this.closeProfileModal();
    if (!confirm('Are you absolutely sure you want to permanently delete your Transify account? All your saved phrases, sessions, and translation history will be permanently erased. This action cannot be undone.')) {
      return;
    }
    try {
      const res = await fetch('/api/auth/me', {
        method: 'DELETE',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      if (res.ok) {
        alert('Your account and all associated data have been permanently deleted.');
        try {
          localStorage.clear();
        } catch (_) {}
        window.location.href = '/login';
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || 'Failed to delete account. Please try again.');
      }
    } catch (e) {
      alert('Network error while attempting to delete account.');
    }
  },

  onboardingStep: 1,
  onboardingTotalSteps: 4,
  onboardingStepsData: [
    {
      title: "Welcome to Transify 2.0",
      badge: "Step 1 of 4",
      desc: "Transify bridges critical communication divides through AI. Seamlessly translate between Bangladesh Sign Language (BdSL), ASL, Optical Braille (UEB Grade 1), Speech Captions, and Text-to-Speech in one unified assistive app."
    },
    {
      title: "Camera Target Box Guide",
      badge: "Step 2 of 4",
      desc: "In Live Sign Translation, keep your hand inside the visible Camera Target Box. Hold your gesture steady for 30 consecutive frames so our consensus filter confirms your translation with 98%+ confidence."
    },
    {
      title: "Optical Braille & CLAHE Vision",
      badge: "Step 3 of 4",
      desc: "Capture or upload unconstrained photos of embossed Braille documents. Our ExtraTrees classifier decodes standard ICEB 2024 UEB Grade 1 cells with adaptive illumination correction."
    },
    {
      title: "Audio Safety & Communication Hub",
      badge: "Step 4 of 4",
      desc: "We enforce a strict Zero Auto-Audio policy: audio never plays automatically in public. Translations appear as text first, and audio plays strictly when you tap the 🔊 speaker button. All conversations sync to your private Hub."
    }
  ],

  openOnboarding() {
    this.onboardingStep = 1;
    this.renderOnboardingStep();
    const modal = document.getElementById('onboarding-modal-overlay');
    if (modal) modal.style.display = 'flex';
  },

  closeOnboarding() {
    const modal = document.getElementById('onboarding-modal-overlay');
    if (modal) modal.style.display = 'none';
    try {
      localStorage.setItem('transify_onboarding_completed', 'true');
    } catch (_) {}
  },

  nextOnboardingStep() {
    if (this.onboardingStep < this.onboardingTotalSteps) {
      this.onboardingStep++;
      this.renderOnboardingStep();
    } else {
      this.closeOnboarding();
      this.showToast('Onboarding complete! Enjoy Transify.', 'success');
    }
  },

  prevOnboardingStep() {
    if (this.onboardingStep > 1) {
      this.onboardingStep--;
      this.renderOnboardingStep();
    }
  },

  renderOnboardingStep() {
    const data = this.onboardingStepsData[this.onboardingStep - 1];
    if (!data) return;
    const badge = document.getElementById('onboarding-step-badge');
    const content = document.getElementById('onboarding-step-content');
    const prevBtn = document.getElementById('onboarding-prev-btn');
    const nextBtn = document.getElementById('onboarding-next-btn');

    if (badge) badge.textContent = data.badge;
    if (content) {
      content.innerHTML = `
        <h4 style="font-size: 17px; font-weight: 800; color: #1e1b4b; margin: 0 0 8px 0;">${data.title}</h4>
        <p style="font-size: 13.5px; color: #64748b; line-height: 1.6; margin: 0 0 16px 0;">${data.desc}</p>
      `;
    }
    if (prevBtn) prevBtn.style.display = this.onboardingStep > 1 ? 'inline-block' : 'none';
    if (nextBtn) nextBtn.textContent = this.onboardingStep === this.onboardingTotalSteps ? 'Finish & Explore 🚀' : 'Next →';
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
    const validTheme = (theme === 'dark') ? 'dark' : 'light';
    this.theme = validTheme;
    document.documentElement.setAttribute('data-theme', validTheme);
    const toggleBtn = document.getElementById('dark-mode-toggle-btn');
    if (toggleBtn) {
      toggleBtn.textContent = validTheme === 'dark' ? '☀️' : '🌙';
      toggleBtn.setAttribute('aria-label', validTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
      toggleBtn.setAttribute('title', validTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    }
    if (save) {
      try {
        localStorage.setItem('transify_theme', validTheme);
        this.saveServerPreference('theme', validTheme);
      } catch (_) {}
    }
  },

  toggleDarkMode() {
    const current = document.documentElement.getAttribute('data-theme') || this.theme || 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    this.applyTheme(next, true);
    this.announce(`Switched to ${next} mode`);
  },

  cycleTheme() {
    this.toggleDarkMode();
  },

  initScrollProgressBar() {
    const bar = document.getElementById('scroll-progress-bar');
    const topBtn = document.getElementById('back-to-top-btn');
    const header = document.getElementById('frame-top-header');

    window.addEventListener('scroll', () => {
      const scrollTop = window.scrollY || document.documentElement.scrollTop;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? Math.min(100, Math.max(0, (scrollTop / docHeight) * 100)) : 0;
      
      if (bar) {
        bar.style.width = `${progress}%`;
        bar.setAttribute('aria-valuenow', Math.round(progress));
      }
      if (topBtn) {
        if (scrollTop > 220) {
          topBtn.classList.add('visible');
        } else {
          topBtn.classList.remove('visible');
        }
      }
      if (header) {
        if (scrollTop > 20) {
          header.classList.add('scrolled');
        } else {
          header.classList.remove('scrolled');
        }
      }
    }, { passive: true });
  },

  initCookieBanner() {
    const banner = document.getElementById('cookie-consent-banner');
    if (!banner) return;
    try {
      const consent = localStorage.getItem('transify_cookie_consent');
      if (consent) {
        banner.classList.add('cookie-hidden');
      }
    } catch (_) {}
  },

  acceptCookies() {
    try {
      localStorage.setItem('transify_cookie_consent', 'accepted');
    } catch (_) {}
    const banner = document.getElementById('cookie-consent-banner');
    if (banner) banner.classList.add('cookie-hidden');
    this.announce('Essential cookies accepted');
    this.showToast('Cookie preferences saved', 'info', 2500);
  },

  declineCookies() {
    try {
      localStorage.setItem('transify_cookie_consent', 'declined');
    } catch (_) {}
    const banner = document.getElementById('cookie-consent-banner');
    if (banner) banner.classList.add('cookie-hidden');
    this.announce('Non-essential cookies declined');
  },

  toggleMobileMenu(forceState) {
    const drawer = document.getElementById('mobile-nav-drawer');
    const overlay = document.getElementById('mobile-nav-overlay');
    const btn = document.getElementById('mobile-menu-toggle-btn');
    if (!drawer || !overlay) return;

    const isOpen = drawer.classList.contains('open');
    const shouldOpen = typeof forceState === 'boolean' ? forceState : !isOpen;

    if (shouldOpen) {
      drawer.classList.add('open');
      overlay.classList.add('open');
      if (btn) btn.setAttribute('aria-expanded', 'true');
    } else {
      drawer.classList.remove('open');
      overlay.classList.remove('open');
      if (btn) btn.setAttribute('aria-expanded', 'false');
    }
  },

  _searchIndex: [
    { title: '🖐️ Hand Signal Translator', desc: 'Real-time camera recognition for BdSL and ASL gestures', action: () => openSlide('slide-hand-signal') },
    { title: '⠃ Optical Braille Converter', desc: 'UEB Grade 1 Braille photo translation to English text', action: () => openSlide('slide-braille') },
    { title: '🎙️ Speech to Text & Captions', desc: 'Live accessible speech transcription and large font captions', action: () => openSlide('slide-stt') },
    { title: '🔊 Text to Speech Synthesizer', desc: 'Natural voice synthesis with explicit user speaker controls', action: () => openSlide('slide-tts') },
    { title: '💬 Communication Hub', desc: 'Real-time accessible messaging between signers and speakers', action: () => openSlide('slide-communication-hub') },
    { title: '⚡ Quick Phraseboard', desc: 'Curated and customizable phrases for rapid communication', action: () => openSlide('slide-phraseboard') },
    { title: '📊 Dashboard & History', desc: 'Inspect translation logs, system health, and accuracy metrics', action: () => openSlide('slide-dashboard') },
    { title: '♿ Accessibility Settings', desc: 'Adjust high contrast, reduced motion, and large targets', action: () => document.getElementById('btn-open-a11y')?.click() },
    { title: '🔒 Privacy Policy', desc: 'Learn about our on-device ephemeral processing and GDPR compliance', url: '/privacy' },
    { title: '📜 Terms of Service', desc: 'Review assistive communication platform terms and conditions', url: '/terms' },
    { title: '❓ Frequently Asked Questions', desc: 'View common questions regarding models, speech audio, and privacy', action: () => { const faq = document.getElementById('transify-faq-section'); if (faq) faq.scrollIntoView({ behavior: 'smooth' }); } }
  ],

  openSiteSearch() {
    const modal = document.getElementById('site-search-modal');
    const input = document.getElementById('site-search-input');
    if (!modal) return;
    modal.style.display = 'flex';
    this.filterSearchResults('');
    if (input) {
      input.value = '';
      setTimeout(() => input.focus(), 80);
    }
  },

  closeSiteSearch() {
    const modal = document.getElementById('site-search-modal');
    if (modal) modal.style.display = 'none';
  },

  filterSearchResults(query) {
    const list = document.getElementById('site-search-results');
    if (!list) return;
    const cleanQ = (query || '').toLowerCase().trim();

    const matches = cleanQ === '' ? this._searchIndex : this._searchIndex.filter(item => 
      item.title.toLowerCase().includes(cleanQ) || item.desc.toLowerCase().includes(cleanQ)
    );

    if (matches.length === 0) {
      list.innerHTML = `<div style="padding: 16px; text-align: center; color: #64748b; font-size: 13px;">No results found for "${query}". Try searching "sign", "braille", "speech", or "privacy".</div>`;
      return;
    }

    list.innerHTML = matches.map((item, idx) => `
      <div class="search-result-item" tabindex="0" role="button" data-index="${idx}" onclick="window.TransifyApp.executeSearchResult(${idx})">
        <div class="search-result-title">${item.title}</div>
        <div class="search-result-desc">${item.desc}</div>
      </div>
    `).join('');
    this._currentMatches = matches;
  },

  executeSearchResult(idx) {
    const item = (this._currentMatches || this._searchIndex)[idx];
    if (!item) return;
    this.closeSiteSearch();
    if (item.action) {
      item.action();
    } else if (item.url) {
      window.location.href = item.url;
    }
  },

  async copyTextFrom(elementId, btnElement) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const textToCopy = el.value || el.innerText || el.textContent || '';
    if (!textToCopy.trim()) {
      this.showToast('No text available to copy', 'warning', 2000);
      return;
    }

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(textToCopy.trim());
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = textToCopy.trim();
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }

      if (btnElement) {
        const originalText = btnElement.innerHTML;
        btnElement.classList.add('copied');
        btnElement.innerHTML = 'Copied! ✓';
        setTimeout(() => {
          btnElement.classList.remove('copied');
          btnElement.innerHTML = originalText;
        }, 2200);
      }
      this.announce('Text copied to clipboard');
      this.showToast('Copied to clipboard!', 'success', 2000);
    } catch (e) {
      this.showToast('Failed to copy to clipboard', 'danger', 2500);
    }
  },

  openContactModal() {
    const modal = document.getElementById('contact-modal-overlay');
    if (modal) {
      modal.style.display = 'flex';
      const nameInput = document.getElementById('contact-name');
      if (nameInput) setTimeout(() => nameInput.focus(), 80);
    }
  },

  closeContactModal() {
    const modal = document.getElementById('contact-modal-overlay');
    if (modal) modal.style.display = 'none';
  },

  submitContactForm(event) {
    if (event) event.preventDefault();
    const name = document.getElementById('contact-name')?.value || '';
    const email = document.getElementById('contact-email')?.value || '';
    const message = document.getElementById('contact-message')?.value || '';

    const feedback = document.getElementById('contact-form-feedback');
    if (feedback) {
      feedback.style.display = 'block';
      feedback.innerHTML = `
        <div class="form-success-banner" role="status">
          <span>✅</span>
          <span>Thank you, ${name}! Your message has been received. Our support team will get in touch at ${email}.</span>
        </div>
      `;
    }

    // First party telemetry logging
    try {
      fetch('/api/telemetry/event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event: 'contact_form_submission', metadata: { name, email, length: message.length } })
      }).catch(() => {});
    } catch (_) {}

    setTimeout(() => {
      document.getElementById('contact-support-form')?.reset();
      if (feedback) feedback.style.display = 'none';
      this.closeContactModal();
      this.showToast('Feedback submitted successfully!', 'success', 3000);
    }, 2000);
  },

  showConfirmModal({ title, message, onConfirm }) {
    const modal = document.getElementById('transify-confirm-modal');
    const titleEl = document.getElementById('confirm-modal-title');
    const msgEl = document.getElementById('confirm-modal-message');
    if (!modal) return;

    if (titleEl) titleEl.textContent = title || 'Confirm Action';
    if (msgEl) msgEl.textContent = message || 'Are you sure you want to proceed?';
    this._confirmCallback = onConfirm;
    modal.style.display = 'flex';
  },

  closeConfirmModal(proceed) {
    const modal = document.getElementById('transify-confirm-modal');
    if (modal) modal.style.display = 'none';
    if (proceed && typeof this._confirmCallback === 'function') {
      this._confirmCallback();
    }
    this._confirmCallback = null;
  },

  initUtmTracking() {
    try {
      const params = new URLSearchParams(window.location.search);
      const utm = {};
      let hasUtm = false;
      ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'].forEach(key => {
        const val = params.get(key);
        if (val) {
          utm[key] = val;
          hasUtm = true;
        }
      });
      if (hasUtm) {
        sessionStorage.setItem('transify_utm_params', JSON.stringify(utm));
      }
    } catch (_) {}
  },

  initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Ctrl+K or Cmd+K: Open Search
      if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        const searchModal = document.getElementById('site-search-modal');
        if (searchModal && searchModal.style.display === 'flex') {
          this.closeSiteSearch();
        } else {
          this.openSiteSearch();
        }
      }
      // Escape closes open modals or drawers
      if (e.key === 'Escape') {
        this.closeSiteSearch();
        this.closeContactModal();
        this.toggleMobileMenu(false);
        this.closeConfirmModal(false);
      }
    });
  },

  applyFontSize(size, save = false) {
    const validSizes = ['small', 'medium', 'large', 'xlarge'];
    const validSize = validSizes.includes(size) ? size : 'medium';
    this.fontSize = validSize;
    document.documentElement.setAttribute('data-font-size', validSize);
    const fontSelector = document.getElementById('font-size-select');
    if (fontSelector) {
      fontSelector.value = validSize;
    }
    const fontToggleBtn = document.getElementById('font-size-toggle-btn');
    if (fontToggleBtn) {
      const labels = { small: 'A-', medium: 'A', large: 'A+', xlarge: 'A++' };
      fontToggleBtn.textContent = labels[validSize] || 'A';
      fontToggleBtn.setAttribute('title', `Text Size: ${validSize}`);
      fontToggleBtn.setAttribute('aria-label', `Text Size: ${validSize}`);
    }
    if (save) {
      try {
        localStorage.setItem('transify_font_size', validSize);
        this.saveServerPreference('font_size', validSize);
      } catch (_) {}
    }
  },

  cycleFontSize() {
    const order = ['medium', 'large', 'xlarge'];
    const current = document.documentElement.getAttribute('data-font-size') || this.fontSize || 'medium';
    const idx = order.indexOf(current);
    const next = order[(idx + 1) % order.length];
    this.applyFontSize(next, true);
    this.announce(`Text size set to ${next}`);
  },

  announce(text) {
    const region = document.getElementById('sr-announcements');
    if (region) {
      region.textContent = '';
      setTimeout(() => { region.textContent = text; }, 50);
    }
    const a11yAnnouncer = document.getElementById('a11y-announcer');
    if (a11yAnnouncer) {
      a11yAnnouncer.textContent = '';
      setTimeout(() => { a11yAnnouncer.textContent = text; }, 50);
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
      const res = await fetch('/api/preferences', { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        if (data.theme && !localStorage.getItem('transify_theme')) {
          this.applyTheme(data.theme, false);
        }
        if (data.font_size && !localStorage.getItem('transify_font_size')) {
          this.applyFontSize(data.font_size, false);
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
        credentials: 'same-origin',
        body: JSON.stringify({ key, value: String(value) })
      });
    } catch (e) {
      // Best effort background sync
    }
  },

  setupAccessibilityListeners() {
    const themeToggle = document.getElementById('dark-mode-toggle-btn');
    if (themeToggle && !themeToggle._bound) {
      themeToggle._bound = true;
      if (!themeToggle.getAttribute('onclick')) {
        themeToggle.addEventListener('click', (e) => {
          e.preventDefault();
          this.toggleDarkMode();
        });
      }
    }
    const fontToggle = document.getElementById('font-size-toggle-btn');
    if (fontToggle && !fontToggle._bound) {
      fontToggle._bound = true;
      if (!fontToggle.getAttribute('onclick')) {
        fontToggle.addEventListener('click', (e) => {
          e.preventDefault();
          this.cycleFontSize();
        });
      }
    }
    const a11yBtn = document.getElementById('btn-open-a11y');
    if (a11yBtn && !a11yBtn._bound) {
      a11yBtn._bound = true;
      a11yBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (typeof this.openA11yModal === 'function') {
          this.openA11yModal();
        }
      });
    }

    // Close any active slide or modal on Escape key
    if (!window._escListenerAttached) {
      window._escListenerAttached = true;
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' || e.keyCode === 27) {
          const activeSlide = document.querySelector('.slide-screen.active');
          if (activeSlide && typeof window.closeSlide === 'function') {
            window.closeSlide(activeSlide.id);
          }
          if (typeof window.closeAuthSheet === 'function') {
            window.closeAuthSheet();
          }
          if (typeof TransifyApp.closeA11yModal === 'function') {
            TransifyApp.closeA11yModal();
          }
        }
      });
    }
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
window.switchAuthTab = (m) => TransifyApp.switchAuthTab(m);
window.setMode = (m) => TransifyApp.switchAuthTab(m);
window.handleDirectLogin = () => TransifyApp.handleDirectLogin();
window.handleDemoLogin = () => TransifyApp.handleDemoLogin();
window.handleDemoGuest = () => TransifyApp.handleDemoLogin();
window.handleAuthSubmit = (e) => TransifyApp.handleAuthSubmit(e);
window.handleGoogleLogin = () => TransifyApp.handleGoogleLogin();
window.handleForgotPassword = (e) => TransifyApp.handleForgotPassword(e);
window.togglePasswordVisibility = () => TransifyApp.togglePasswordVisibility();

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
      const [readyRes, modelsRes] = await Promise.all([
        fetch('/api/ready'),
        fetch('/api/models/status')
      ]);

      const sysBadge = document.getElementById('system-status-badge');
      if (sysBadge) {
        if (readyRes.ok) {
          const readyData = await readyRes.json().catch(() => ({}));
          if (readyData.status === 'ready') {
            sysBadge.className = 'badge badge-success';
            sysBadge.innerHTML = '● All Systems Operational';
          } else {
            sysBadge.className = 'badge badge-warning';
            sysBadge.innerHTML = '● Degraded / Partial Subsystems';
          }
        } else {
          sysBadge.className = 'badge badge-danger';
          sysBadge.innerHTML = '● Service Unavailable';
        }
      }

      if (modelsRes.ok) {
        const data = await modelsRes.json().catch(() => ({}));

        const signCard = document.getElementById('sign-model-metric');
        if (signCard && data.sign_language) {
          const signAcc = (typeof data.sign_language.test_accuracy === 'number' && !isNaN(data.sign_language.test_accuracy))
            ? `${(data.sign_language.test_accuracy * 100).toFixed(1)}%`
            : (typeof data.sign_language.hagrid_test_accuracy === 'number' && !isNaN(data.sign_language.hagrid_test_accuracy))
              ? `${(data.sign_language.hagrid_test_accuracy * 100).toFixed(1)}% (HaGRID)`
              : 'Unavailable';
          const signReady = Boolean(data.sign_language.ready);
          const signBadge = signReady
            ? '<span class="badge badge-success">Ready</span>'
            : '<span class="badge badge-warning">Unavailable</span>';

          signCard.innerHTML = `
            <strong>Model:</strong> ${data.sign_language.champion_model || 'SignFrame AI'}<br>
            <strong>Accuracy:</strong> ${signAcc}<br>
            <strong>Classes:</strong> ${data.sign_language.supported_classes || 24} ASL & Gesture Signs<br>
            <strong>Status:</strong> ${signBadge}
          `;
        }

        const brailleCard = document.getElementById('braille-model-metric');
        if (brailleCard && data.braille_ocr) {
          const brailleAcc = (typeof data.braille_ocr.test_cell_accuracy === 'number' && !isNaN(data.braille_ocr.test_cell_accuracy))
            ? `${(data.braille_ocr.test_cell_accuracy * 100).toFixed(1)}%`
            : 'Unavailable';
          const brailleReady = Boolean(data.braille_ocr.ready);
          const brailleBadge = brailleReady
            ? '<span class="badge badge-success">Ready</span>'
            : '<span class="badge badge-warning">Unavailable</span>';

          brailleCard.innerHTML = `
            <strong>Model:</strong> ${data.braille_ocr.champion_model || 'Extra Trees'}<br>
            <strong>Cell Acc:</strong> ${brailleAcc}<br>
            <strong>Standard:</strong> UEB Grade 1 (Uncontracted)<br>
            <strong>Status:</strong> ${brailleBadge}
          `;
        }
      }
    } catch (e) {
      console.error('Failed to load status:', e);
      const sysBadge = document.getElementById('system-status-badge');
      if (sysBadge) {
        sysBadge.className = 'badge badge-danger';
        sysBadge.innerHTML = '● Status Check Error';
      }
    }
  },

  async loadHistory() {
    const listContainer = document.getElementById('history-records-list');
    if (!listContainer) return;

    try {
      const res = await fetch('/api/history?limit=15', { credentials: 'same-origin' });
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
        const confPercent = (typeof rec.confidence === 'number' && !isNaN(rec.confidence)) ? `${(rec.confidence * 100).toFixed(1)}%` : 'N/A';

        return `
          <div class="card" style="margin-bottom: var(--space-3); padding: var(--space-4);" data-id="${rec.id}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2);">
              <span class="badge ${badgeClass}">${icon} ${rec.module.toUpperCase()}</span>
              <span style="font-size: var(--text-xs); color: var(--text-muted);">${dateStr} • Conf: ${confPercent}</span>
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
        credentials: 'same-origin',
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
            await fetch('/api/history', { method: 'DELETE', credentials: 'same-origin' });
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

// Optional Dev-Only Camera & Pipeline Diagnostics Instrumentation
// Accessible via window.TransifySignDiagnostics.getSummary()
// Enabled only when ?diagnostics=1 query parameter is set or via window.TransifySignDiagnostics.enable()
var TransifySignDiagnostics = window.TransifySignDiagnostics = {
  enabled: false,
  maxSamples: 100,
  metrics: [],
  lastVideoTimestamp: null,
  videoFrameDeltas: [],
  rvfcHandle: null,
  activeVideoEl: null,

  init() {
    try {
      var params = new URLSearchParams(window.location.search);
      if (params.get('diagnostics') === '1' || localStorage.getItem('transify_debug_diagnostics') === '1') {
        this.enabled = true;
      }
    } catch (_) {}
  },

  enable() {
    this.enabled = true;
    try { localStorage.setItem('transify_debug_diagnostics', '1'); } catch (_) {}
    console.info('[TransifySignDiagnostics] Performance diagnostics ENABLED. Call window.TransifySignDiagnostics.getSummary() to view metrics.');
  },

  disable() {
    this.enabled = false;
    this.metrics = [];
    this.videoFrameDeltas = [];
    if (this.activeVideoEl && this.rvfcHandle && typeof this.activeVideoEl.cancelVideoFrameCallback === 'function') {
      try { this.activeVideoEl.cancelVideoFrameCallback(this.rvfcHandle); } catch (_) {}
    }
    this.detachVideo();
    try { localStorage.removeItem('transify_debug_diagnostics'); } catch (_) {}
    console.info('[TransifySignDiagnostics] Performance diagnostics DISABLED.');
  },

  attachVideo(videoEl) {
    if (!videoEl) return;
    this.activeVideoEl = videoEl;
    if (!this.enabled) return;
    var self = this;
    if (typeof videoEl.requestVideoFrameCallback === 'function') {
      var onFrame = function(now) {
        if (!self.enabled || self.activeVideoEl !== videoEl) return;
        if (self.lastVideoTimestamp !== null) {
          var delta = now - self.lastVideoTimestamp;
          if (delta > 0 && delta < 1000) {
            self.videoFrameDeltas.push(delta);
            if (self.videoFrameDeltas.length > self.maxSamples) self.videoFrameDeltas.shift();
          }
        }
        self.lastVideoTimestamp = now;
        self.rvfcHandle = videoEl.requestVideoFrameCallback(onFrame);
      };
      this.rvfcHandle = videoEl.requestVideoFrameCallback(onFrame);
    }
  },

  detachVideo() {
    if (this.activeVideoEl && this.rvfcHandle && typeof this.activeVideoEl.cancelVideoFrameCallback === 'function') {
      try { this.activeVideoEl.cancelVideoFrameCallback(this.rvfcHandle); } catch (_) {}
    }
    this.activeVideoEl = null;
    this.lastVideoTimestamp = null;
    this.rvfcHandle = null;
  },

  recordPipelineCycle(sample) {
    if (!this.enabled) return;
    this.metrics.push(sample);
    if (this.metrics.length > this.maxSamples) this.metrics.shift();
  },

  getSummary() {
    function percentile(arr, p) {
      if (!arr || !arr.length) return 0;
      var sorted = arr.slice().sort(function(a, b) { return a - b; });
      var idx = Math.min(Math.floor((p / 100) * sorted.length), sorted.length - 1);
      return Math.round(sorted[idx] * 10) / 10;
    }
    function mean(arr) {
      if (!arr || !arr.length) return 0;
      var sum = arr.reduce(function(acc, val) { return acc + val; }, 0);
      return Math.round((sum / arr.length) * 10) / 10;
    }

    var canvasDrawTimes = this.metrics.map(function(m) { return m.canvasDrawMs; });
    var jpegEncodeTimes = this.metrics.map(function(m) { return m.jpegEncodeMs; });
    var networkPostTimes = this.metrics.map(function(m) { return m.networkPostMs; });
    var serverInferenceTimes = this.metrics.map(function(m) { return m.serverInferenceMs; }).filter(function(v) { return v !== null && v !== undefined; });
    var totalRoundtripTimes = this.metrics.map(function(m) { return m.totalRoundtripMs; });

    var videoCadenceMs = mean(this.videoFrameDeltas);
    var videoFps = videoCadenceMs > 0 ? Math.round((1000 / videoCadenceMs) * 10) / 10 : null;

    var dispatchCadenceMs = mean(totalRoundtripTimes);
    var dispatchFps = dispatchCadenceMs > 0 ? Math.round((1000 / dispatchCadenceMs) * 10) / 10 : null;

    return {
      enabled: this.enabled,
      samples_recorded: this.metrics.length,
      video_frame_callback_supported: (typeof HTMLVideoElement !== 'undefined' && typeof HTMLVideoElement.prototype.requestVideoFrameCallback === 'function'),
      video_delivery: {
        metric_nature: "Estimated browser video-frame callback delivery cadence (requestVideoFrameCallback), NOT direct Camera2 hardware sensor FPS",
        samples: this.videoFrameDeltas.length,
        mean_cadence_ms: videoCadenceMs,
        estimated_fps: videoFps,
        p50_cadence_ms: percentile(this.videoFrameDeltas, 50),
        p95_cadence_ms: percentile(this.videoFrameDeltas, 95)
      },
      pipeline_latency: {
        canvas_draw_p50_ms: percentile(canvasDrawTimes, 50),
        canvas_draw_p95_ms: percentile(canvasDrawTimes, 95),
        jpeg_encode_p50_ms: percentile(jpegEncodeTimes, 50),
        jpeg_encode_p95_ms: percentile(jpegEncodeTimes, 95),
        network_post_p50_ms: percentile(networkPostTimes, 50),
        network_post_p95_ms: percentile(networkPostTimes, 95),
        server_inference_p50_ms: percentile(serverInferenceTimes, 50),
        server_inference_p95_ms: percentile(serverInferenceTimes, 95),
        total_roundtrip_p50_ms: percentile(totalRoundtripTimes, 50),
        total_roundtrip_p95_ms: percentile(totalRoundtripTimes, 95),
        estimated_dispatch_fps: dispatchFps
      }
    };
  }
};
TransifySignDiagnostics.init();

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
  sessionId: 'transify_sess_' + Math.random().toString(36).substring(2, 10),
  currentMode: 'expressions',
  currentLanguageMode: 'bdsl',
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
    const validMode = (mode === 'asl') ? 'asl' : 'bdsl';
    this.currentLanguageMode = validMode;
    this.sequenceBuffer = [];
    this.detectionState = { isDetected: false, label: '', confidence: 0, timestamp: 0 };

    const bdslBtn = document.getElementById('lang-bdsl-btn');
    const aslBtn = document.getElementById('lang-asl-btn');
    if (bdslBtn && aslBtn) {
      if (validMode === 'bdsl') {
        bdslBtn.classList.remove('btn-secondary');
        bdslBtn.classList.add('btn-primary');
        aslBtn.classList.remove('btn-primary');
        aslBtn.classList.add('btn-secondary');
      } else {
        aslBtn.classList.remove('btn-secondary');
        aslBtn.classList.add('btn-primary');
        bdslBtn.classList.remove('btn-primary');
        bdslBtn.classList.add('btn-secondary');
      }
    }

    const sourceTag = document.getElementById('trans-source-model-tag');
    if (sourceTag) {
      sourceTag.textContent = validMode === 'bdsl' ? 'BdSL 10-Class Temporal Model' : 'SignFrame AI & HaGRID (ASL)';
    }

    fetch('/api/sign/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: this.sessionId })
    }).catch(() => {});
  },

  setDetectionFeedback(label, confidence = null) {
    this.detectionState = {
      isDetected: true,
      label: label,
      confidence: (typeof confidence === 'number' && !isNaN(confidence)) ? confidence : null,
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
    this.setupLanguageSwitcher();
    this.setupModeSwitcher();
    this.initFingerspellingUI();
    this.initSentenceBuilderUI();
    this.loadSupportedClasses();
    this.loadCommunicativeDomains();
  },

  setupLanguageSwitcher() {
    const bdslBtn = document.getElementById('lang-bdsl-btn');
    const aslBtn = document.getElementById('lang-asl-btn');
    if (bdslBtn) bdslBtn.addEventListener('click', () => this.setLanguageMode('bdsl'));
    if (aslBtn) aslBtn.addEventListener('click', () => this.setLanguageMode('asl'));
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

    // Bind Quick Common Vocabulary Word buttons (Manual input - marked as MANUAL_INPUT, no AI confidence)
    document.querySelectorAll('.quick-word-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const word = btn.getAttribute('data-word');
        if (word) {
          this.setDetectionFeedback(word, null);
          this.updatePredictionUI({
            label: word,
            display_text: word.replace(/_/g, ' '),
            bdsl_gloss: word,
            confidence: null,
            confirmed: true,
            engine_info: {
              badge: 'Manual Input',
              is_fallback: false,
              notes: 'Manual vocabulary word selection (MANUAL_INPUT).'
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
          this.setDetectionFeedback(`Letter: ${data.letter}`, null);
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
// Strict accessibility rule: translations never auto-play audio
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

// User can click speaker button to hear sentence aloud
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
        if (window.TransifySignDiagnostics) {
          window.TransifySignDiagnostics.attachVideo(this.videoEl);
        }
      }
      this.isStreaming = true;
      const toggleBtn = document.getElementById('toggle-camera-btn');
      if (toggleBtn) {
        toggleBtn.innerHTML = '🛑 Stop Camera';
        toggleBtn.classList.replace('btn-primary', 'btn-secondary');
      }
      const placeholder = document.getElementById('camera-placeholder');
      if (placeholder) placeholder.style.display = 'none';

      TransifyApp.showToast('Camera started. Tracking ASL signs.', 'success');
      TransifyApp.announce('Camera active. Ready for sign language input.');

      // Start continuous landmark ingestion loop
      this.startInferenceLoop();
    } catch (err) {
      console.error('Camera access error:', err);
      TransifyApp.showToast('Camera access denied or unavailable. Use the 10 Sample Sign buttons below to test!', 'warning');
      TransifyApp.announce('Camera access failed. Sample buttons available.');
    }
  },

  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    if (this.videoEl) this.videoEl.srcObject = null;
    if (window.TransifySignDiagnostics) {
      window.TransifySignDiagnostics.detachVideo();
    }
    this.isStreaming = false;
    this.isProcessingFrame = false;
    this.lastHandBBox = null;
    if (this.predictTimer) clearInterval(this.predictTimer);
    if (this.frameCaptureTimer) clearInterval(this.frameCaptureTimer);
    this.predictTimer = null;
    this.frameCaptureTimer = null;

    const toggleBtn = document.getElementById('toggle-camera-btn');
    if (toggleBtn) {
      toggleBtn.innerHTML = '📹 Start Camera';
      toggleBtn.classList.replace('btn-secondary', 'btn-primary');
    }
    const placeholder = document.getElementById('camera-placeholder');
    if (placeholder) placeholder.style.display = 'flex';

    fetch('/api/sign/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: this.sessionId })
    }).catch(() => {});
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
        const t0_diag = (window.performance && performance.now) ? performance.now() : Date.now();
        this.offscreenCtx.drawImage(this.videoEl, 0, 0, 640, 480);
        const t1_diag = (window.performance && performance.now) ? performance.now() : Date.now();
        const b64 = this.offscreenCanvas.toDataURL('image/jpeg', 0.82);
        const t2_diag = (window.performance && performance.now) ? performance.now() : Date.now();

        const currentRoi = this.getTargetRoi();
        const clientTimestamp = (performance && performance.now) ? (performance.now() / 1000.0) : (Date.now() / 1000.0);
        const res = await fetch('/api/sign/process_frame', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            image_b64: b64,
            mode: this.currentMode,
            language_mode: this.currentLanguageMode || 'bdsl',
            roi: currentRoi,
            session_id: this.sessionId,
            timestamp: clientTimestamp
          })
        });
        const t3_diag = (window.performance && performance.now) ? performance.now() : Date.now();

        if (!res.ok) return;
        const data = await res.json();
        const t4_diag = (window.performance && performance.now) ? performance.now() : Date.now();

        if (window.TransifySignDiagnostics && window.TransifySignDiagnostics.enabled) {
          window.TransifySignDiagnostics.recordPipelineCycle({
            canvasDrawMs: Math.round((t1_diag - t0_diag) * 10) / 10,
            jpegEncodeMs: Math.round((t2_diag - t1_diag) * 10) / 10,
            networkPostMs: Math.round((t3_diag - t2_diag) * 10) / 10,
            serverInferenceMs: (data && typeof data.latency_ms === 'number') ? data.latency_ms : null,
            totalRoundtripMs: Math.round((t4_diag - t0_diag) * 10) / 10
          });
        }
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

          if (data.hand_detected && data.status === 'CONFIRMED' && data.label && data.label !== 'IDLE' && data.label !== 'ANALYZING' && data.label !== 'BUFFERING') {
            // DECISION CONFIRMED AFTER ANALYSIS! Turn camera box vibrant GREEN!
            this.setDetectionFeedback(data.label, (typeof data.confidence === 'number' && !isNaN(data.confidence)) ? data.confidence : null);

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
          } else if (data.hand_detected && data.status === 'BUFFERING') {
            // BUFFERING PHASE: Collecting 30 frames for temporal sequence model
            this.updatePredictionUI({
              label: 'BUFFERING',
              candidate_label: data.label,
              display_text: data.display_text || `Collecting frames... (${data.progress || '0/30'})`,
              bdsl_gloss: data.gloss || 'Buffering BdSL 30-frame sequence...',
              confidence: null,
              confirmed: false,
              status: 'BUFFERING',
              analysis_pct: data.progress_pct || 50,
              consensus_progress: data.progress,
              engine_info: data.engine_info
            });
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
    }, 33); // Target ~30 FPS (33ms) matching 30 FPS training data
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
      const confDisplay = (typeof this.detectionState.confidence === 'number' && !isNaN(this.detectionState.confidence)) ? ` (${Math.round(this.detectionState.confidence * 100)}%)` : '';
      const badgeText = `✓ [${modelTag}] DETECTED: ${this.detectionState.label}${confDisplay}`;
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
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sequence: sample.sequence,
          signer_id: sample.sample_id,
          language_mode: this.currentLanguageMode || 'bdsl',
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

    if (labelEl) labelEl.textContent = result.label;
    if (glossEl) glossEl.textContent = `[ASL: ${result.gloss || defaultGloss || result.label}]`;
    if (confEl) {
      if (typeof result.confidence === 'number' && !isNaN(result.confidence)) {
        const confPct = (result.confidence * 100).toFixed(1);
        confEl.textContent = `${confPct}% Confidence`;
        confEl.className = result.confidence > 0.85 ? 'badge badge-success' : 'badge badge-warning';
      } else {
        confEl.textContent = 'Confidence Unavailable';
        confEl.className = 'badge badge-info';
      }
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
    this.setDetectionFeedback(result.label, (typeof result.confidence === 'number' && !isNaN(result.confidence)) ? result.confidence : null);

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

// Strict accessibility rule: recognized signs never auto-play audio
      }
    } else {
      if (statusNote) statusNote.textContent = `Debouncing consensus (${result.debounce_count}/${result.debounce_target})...`;
    }
  },

  async resetRecognition() {
    try {
      await fetch('/api/sign/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: this.sessionId })
      });
      this.sequenceBuffer = [];
      this.lastPrediction = null;
      this.detectionState = { isDetected: false, label: '', confidence: 0, timestamp: 0 };
      this.lastHandBBox = null;
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
      const res = await fetch('/api/braille/translate', { method: 'POST', credentials: 'same-origin', body: formData });
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
        const confDisplay = (typeof result.mean_confidence === 'number' && !isNaN(result.mean_confidence))
          ? `Conf: ${(result.mean_confidence * 100).toFixed(1)}%`
          : 'Conf: Unavailable';
        const confBadgeClass = (typeof result.mean_confidence === 'number' && !isNaN(result.mean_confidence) && result.mean_confidence > 0.85)
          ? 'badge-success'
          : 'badge-info';
        statsBadge.innerHTML = `
          ${engineBadge}
          <span class="badge ${cov.percentage >= 95 ? 'badge-success' : 'badge-warning'}">📖 ${cov.percentage}% Read</span>
          <span class="badge ${confBadgeClass}">${confDisplay}</span>
          <span class="badge badge-info">${result.cell_count || 0} Cells</span>
          <span class="badge badge-info">${result.line_count || 1} Lines</span>
        `;
      }

      // Show IQA as passed
      this.displayIQAResult({ accepted: true, metrics: result.qa_metrics || {}, is_usable: true });

      TransifyApp.showToast('Braille translated successfully!', 'success');
      TransifyApp.announce('Translation complete: ' + result.text);

      // Do not auto-speak the translation (user must click speaker button)

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



// ============================================================================
// TRANSIFY 2.0 COMMUNICATION HUB CONTROLLER
// Multimodal accessible communication feed supporting sign, Braille, speech, and typed input.
// ============================================================================
window.CommunicationHub = {
  activeConversationId: null,
  messages: [],
  _initialized: false,

  async init() {
    if (!this._initialized) {
      this._initialized = true;
      this.bindEvents();
    }
    await this.ensureConversation();
    await this.loadMessages();
  },

  bindEvents() {
    const form = document.getElementById('hub-input-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const input = document.getElementById('hub-input-text');
        const text = input ? input.value.trim() : '';
        if (text) {
          this.sendMessage(text, 'typed');
          if (input) input.value = '';
        }
      });
    }

    const clearBtn = document.getElementById('hub-clear-btn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => this.clearConversation());
    }

    const copyAllBtn = document.getElementById('hub-copy-all-btn');
    if (copyAllBtn) {
      copyAllBtn.addEventListener('click', () => this.copyConversation());
    }

    const exportBtn = document.getElementById('hub-export-btn');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => this.exportTxt());
    }

    const fromSignBtn = document.getElementById('hub-import-sign-btn');
    if (fromSignBtn) {
      fromSignBtn.addEventListener('click', () => {
        const text = (window.SignPage && window.SignPage.lastPrediction) ||
                     (document.getElementById('smooth-sentence-text') && document.getElementById('smooth-sentence-text').textContent) ||
                     '';
        if (text && !text.includes('Waiting')) {
          this.sendMessage(text, 'sign');
        } else {
          TransifyApp.showToast('No sign translation available to import.', 'warning');
        }
      });
    }

    const fromBrailleBtn = document.getElementById('hub-import-braille-btn');
    if (fromBrailleBtn) {
      fromBrailleBtn.addEventListener('click', () => {
        const el = document.getElementById('braille-text-output');
        const text = el ? el.value.trim() : '';
        if (text) {
          this.sendMessage(text, 'braille');
        } else {
          TransifyApp.showToast('No Braille text available to import.', 'warning');
        }
      });
    }

    const fromSttBtn = document.getElementById('hub-import-stt-btn');
    if (fromSttBtn) {
      fromSttBtn.addEventListener('click', () => {
        const el = document.getElementById('stt-transcript-output');
        const text = el ? el.textContent.trim() : '';
        if (text && !text.includes('Listening')) {
          this.sendMessage(text, 'speech');
        } else {
          TransifyApp.showToast('No speech transcript available to import.', 'warning');
        }
      });
    }
  },

  async ensureConversation() {
    try {
      const res = await fetch('/api/hub/conversations', { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        if (data.conversations && data.conversations.length > 0) {
          this.activeConversationId = data.conversations[0].id;
          return;
        }
      }
      const createRes = await fetch('/api/hub/conversations', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'Main Conversation' })
      });
      if (createRes.ok) {
        const conv = await createRes.json();
        this.activeConversationId = conv.conversation.id;
      }
    } catch (e) {
      console.warn('Hub ensureConversation note:', e);
      this.activeConversationId = 'local_session';
    }
  },

  async loadMessages() {
    if (!this.activeConversationId) return;
    try {
      const res = await fetch(`/api/hub/conversations/${this.activeConversationId}/messages`, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        this.messages = data.messages || [];
      } else {
        this.messages = [];
      }
    } catch (e) {
      console.warn('Hub loadMessages note:', e);
    }
    this.renderFeed();
  },

  async sendMessage(content, modality = 'typed') {
    if (!content) return;
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    try {
      if (this.activeConversationId && this.activeConversationId !== 'local_session') {
        const res = await fetch(`/api/hub/conversations/${this.activeConversationId}/messages`, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: content, modality: modality })
        });
        if (res.ok) {
          const data = await res.json();
          const savedMsg = Object.assign({}, data.message, { sync_status: 'saved' });
          this.messages.push(savedMsg);
          this.renderFeed();
          TransifyApp.announce(`Message added from ${modality}: ${content}`);
          return;
        }
      }
    } catch (e) {
      console.warn('Hub sendMessage server error, falling back to local:', e);
    }

    const isGuest = (this.activeConversationId === 'local_session');
    const localMsg = {
      id: Date.now(),
      sender_name: 'You',
      content: content,
      modality: modality,
      created_at: timeStr,
      sync_status: isGuest ? 'guest' : 'unsaved'
    };
    this.messages.push(localMsg);
    this.renderFeed();
    TransifyApp.announce(`Message added from ${modality}: ${content}`);
  },

  renderFeed() {
    const container = document.getElementById('hub-feed-container');
    if (!container) return;

    // Clear feed safely without innerHTML
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }

    if (!this.messages.length) {
      const emptyDiv = document.createElement('div');
      emptyDiv.style.cssText = 'text-align: center; color: #94a3b8; font-size: 13px; padding: 24px 0;';
      emptyDiv.textContent = 'No messages yet. Send a typed message or translate from any modality.';
      container.appendChild(emptyDiv);
      return;
    }

    const badgeClasses = {
      sign: 'hub-badge-sign',
      braille: 'hub-badge-braille',
      speech: 'hub-badge-speech',
      typed: 'hub-badge-typed'
    };

    const badgeLabels = {
      sign: '🤟 Sign',
      braille: '⠃ Braille',
      speech: '🎙️ Voice',
      typed: '⌨️ Typed'
    };

    this.messages.forEach((msg, idx) => {
      const mod = msg.modality || 'typed';
      const badgeCls = badgeClasses[mod] || 'hub-badge-typed';
      const badgeLbl = badgeLabels[mod] || mod;
      const timeStr = typeof msg.created_at === 'number'
        ? new Date(msg.created_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : (msg.created_at || '');

      const card = document.createElement('div');
      card.className = 'hub-message-card';
      card.setAttribute('data-msg-idx', String(idx));

      const header = document.createElement('div');
      header.className = 'hub-msg-header';

      const leftBadges = document.createElement('div');
      leftBadges.style.cssText = 'display: flex; align-items: center; gap: 6px;';

      const modBadge = document.createElement('span');
      modBadge.className = `hub-modality-badge ${badgeCls}`;
      modBadge.textContent = badgeLbl;
      leftBadges.appendChild(modBadge);

      const statusBadge = document.createElement('span');
      const syncStatus = msg.sync_status || (this.activeConversationId === 'local_session' ? 'guest' : 'saved');
      if (syncStatus === 'saved') {
        statusBadge.className = 'hub-status-chip saved';
        statusBadge.textContent = '✓ Saved';
        statusBadge.title = 'Saved to cloud conversation';
      } else if (syncStatus === 'guest') {
        statusBadge.className = 'hub-status-chip guest';
        statusBadge.textContent = 'Temporary Guest';
        statusBadge.title = 'Guest session — not persisted';
      } else {
        statusBadge.className = 'hub-status-chip unsaved';
        statusBadge.textContent = '⚠️ Unsaved';
        statusBadge.title = 'Connection error — local copy only';
      }
      leftBadges.appendChild(statusBadge);
      header.appendChild(leftBadges);

      const timeSpan = document.createElement('span');
      timeSpan.className = 'hub-msg-time';
      timeSpan.textContent = timeStr;
      header.appendChild(timeSpan);

      const body = document.createElement('div');
      body.className = 'hub-msg-body';
      // STRICT textContent: Prevents all DOM-based XSS attacks
      body.textContent = msg.content || '';

      const actions = document.createElement('div');
      actions.className = 'hub-msg-actions';

      const copyBtn = document.createElement('button');
      copyBtn.type = 'button';
      copyBtn.className = 'hub-action-btn';
      copyBtn.title = 'Copy text';
      copyBtn.textContent = '📋 Copy';
      copyBtn.addEventListener('click', () => this.copyText(msg.content || ''));
      actions.appendChild(copyBtn);

      const speakBtn = document.createElement('button');
      speakBtn.type = 'button';
      speakBtn.className = 'hub-action-btn btn-speak-voice';
      speakBtn.title = 'Speak message aloud (user clicked)';
      speakBtn.textContent = '🔊 Speak';
      speakBtn.addEventListener('click', () => this.speakText(msg.content || ''));
      actions.appendChild(speakBtn);

      card.appendChild(header);
      card.appendChild(body);
      card.appendChild(actions);

      container.appendChild(card);
    });

    container.scrollTop = container.scrollHeight;
  },

  copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        TransifyApp.showToast('Message copied to clipboard!', 'success');
      });
    }
  },

  speakText(text) {
    if (window.TransifyTTS && window.TransifyTTS.speak) {
      window.TransifyTTS.speak(text);
    }
  },

  copyConversation() {
    if (!this.messages.length) {
      TransifyApp.showToast('No messages to copy.', 'warning');
      return;
    }
    const fullText = this.messages.map(m => `[${(m.modality||'typed').toUpperCase()}] ${m.content}`).join('\n');
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(fullText).then(() => {
        TransifyApp.showToast('Full conversation copied to clipboard!', 'success');
      });
    }
  },

  exportTxt() {
    if (!this.messages.length) {
      TransifyApp.showToast('No messages to export.', 'warning');
      return;
    }
    const fullText = "Transify 2.0 Accessible Conversation Export\nGenerated: " + new Date().toISOString() + "\n\n" +
      this.messages.map(m => `[${new Date(typeof m.created_at === 'number' ? m.created_at * 1000 : Date.now()).toLocaleTimeString()}] [${(m.modality||'typed').toUpperCase()}]: ${m.content}`).join('\n\n');
    
    const blob = new Blob([fullText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transify-conversation-${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    TransifyApp.showToast('Conversation exported successfully!', 'success');
  },

  async clearConversation() {
    if (!confirm('Are you sure you want to clear this conversation?')) return;
    try {
      if (this.activeConversationId && this.activeConversationId !== 'local_session') {
        await fetch(`/api/hub/conversations/${this.activeConversationId}/clear`, {
          method: 'POST',
          credentials: 'same-origin'
        });
      }
    } catch (e) {
      console.warn('Hub clear error:', e);
    }
    this.messages = [];
    this.renderFeed();
    TransifyApp.showToast('Conversation feed cleared.', 'success');
  }
};

// ============================================================================
// QUICK PHRASEBOARD CONTROLLER
// Bilingual Essential & Custom Phrases with user isolation and explicit-only speech.
// ============================================================================
window.Phraseboard = {
  phrases: [],
  favoritesOnly: false,
  _initialized: false,

  async init() {
    if (!this._initialized) {
      this._initialized = true;
      this.bindEvents();
    }
    await this.loadPhrases();
  },

  bindEvents() {
    const favFilter = document.getElementById('phrase-fav-filter');
    if (favFilter) {
      favFilter.addEventListener('change', (e) => {
        this.favoritesOnly = e.target.checked;
        this.renderGrid();
      });
    }

    const toggleAddBtn = document.getElementById('btn-toggle-add-phrase');
    const addForm = document.getElementById('phrase-add-form-container');
    const cancelAddBtn = document.getElementById('btn-cancel-add-phrase');
    const savePhraseBtn = document.getElementById('btn-save-phrase');

    if (toggleAddBtn && addForm) {
      toggleAddBtn.addEventListener('click', () => {
        addForm.style.display = (addForm.style.display === 'none' || !addForm.style.display) ? 'block' : 'none';
      });
    }
    if (cancelAddBtn && addForm) {
      cancelAddBtn.addEventListener('click', () => {
        addForm.style.display = 'none';
      });
    }
    if (savePhraseBtn) {
      savePhraseBtn.addEventListener('click', () => this.saveCustomPhrase());
    }
  },

  async loadPhrases() {
    try {
      const res = await fetch('/api/phrases', { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        this.phrases = data.phrases || [...(data.default_phrases || []), ...(data.custom_phrases || [])];
        if (!this.phrases.length) this.phrases = this.getDefaultFallbackPhrases();
      } else {
        this.phrases = this.getDefaultFallbackPhrases();
      }
    } catch (e) {
      console.warn('Phraseboard loadPhrases error, using defaults:', e);
      this.phrases = this.getDefaultFallbackPhrases();
    }
    this.renderGrid();
  },

  getDefaultFallbackPhrases() {
    return [
      { id: 1, text_en: "Hello, how are you?", text_bn: "হ্যালো, আপনি কেমন আছেন?", category: "greetings", is_favorite: false },
      { id: 2, text_en: "I need assistance, please.", text_bn: "দয়া করে আমাকে সাহায্য করুন।", category: "emergency", is_favorite: true },
      { id: 3, text_en: "Thank you very much.", text_bn: "আপনাকে অনেক ধন্যবাদ।", category: "courtesy", is_favorite: false },
      { id: 4, text_en: "Yes, that works for me.", text_bn: "হ্যাঁ, এটি আমার জন্য ঠিক আছে।", category: "responses", is_favorite: false },
      { id: 5, text_en: "No, thank you.", text_bn: "না, ধন্যবাদ।", category: "responses", is_favorite: false },
      { id: 6, text_en: "Please give me a moment.", text_bn: "দয়া করে আমাকে একটু সময় দিন।", category: "patience", is_favorite: false },
      { id: 7, text_en: "Where is the restroom?", text_bn: "টয়লেট কোথায়?", category: "navigation", is_favorite: false },
      { id: 8, text_en: "I communicate using this device.", text_bn: "আমি এই ডিভাইসের মাধ্যমে কথা বলি।", category: "assistive", is_favorite: true },
      { id: 9, text_en: "Could you please repeat that?", text_bn: "দয়া করে আরেকবার বলবেন?", category: "clarification", is_favorite: false },
      { id: 10, text_en: "I am deaf or hard of hearing.", text_bn: "আমি বধির বা শ্রবণ প্রতিবন্ধী।", category: "assistive", is_favorite: true },
      { id: 11, text_en: "Please write it down.", text_bn: "দয়া করে লিখে দিন।", category: "assistive", is_favorite: false },
      { id: 12, text_en: "Nice to meet you.", text_bn: "আপনার সাথে দেখা হয়ে ভালো লাগলো।", category: "courtesy", is_favorite: false }
    ];
  },

  renderGrid() {
    const grid = document.getElementById('phraseboard-grid');
    if (!grid) return;

    let items = this.phrases;
    if (this.favoritesOnly) {
      items = items.filter(p => Boolean(p.is_favorite));
    }

    while (grid.firstChild) {
      grid.removeChild(grid.firstChild);
    }

    if (!items.length) {
      const emptyDiv = document.createElement('div');
      emptyDiv.style.cssText = 'grid-column: 1 / -1; text-align: center; color: #94a3b8; font-size: 13px; padding: 24px 0;';
      emptyDiv.textContent = 'No phrases match your filter.';
      grid.appendChild(emptyDiv);
      return;
    }

    items.forEach(p => {
      const isFav = Boolean(p.is_favorite);
      const card = document.createElement('div');
      card.className = `phrase-card ${isFav ? 'favorite' : ''}`;
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');
      card.setAttribute('aria-label', `${p.text_en || ''} - ${p.text_bn || ''}`);
      card.addEventListener('click', () => this.onPhraseClick(p.text_en, p.text_bn));
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.onPhraseClick(p.text_en, p.text_bn);
        }
      });

      const textWrapper = document.createElement('div');
      const enDiv = document.createElement('div');
      enDiv.className = 'phrase-text-en';
      enDiv.textContent = p.text_en || ''; // STRICT textContent: Prevents XSS

      const bnDiv = document.createElement('div');
      bnDiv.className = 'phrase-text-bn';
      bnDiv.textContent = p.text_bn || ''; // STRICT textContent: Prevents XSS

      textWrapper.appendChild(enDiv);
      textWrapper.appendChild(bnDiv);
      card.appendChild(textWrapper);

      const controls = document.createElement('div');
      controls.className = 'phrase-controls';
      controls.addEventListener('click', (e) => e.stopPropagation());

      const speakBtn = document.createElement('button');
      speakBtn.type = 'button';
      speakBtn.className = 'phrase-icon-btn';
      speakBtn.title = 'Speak aloud (user clicked)';
      speakBtn.textContent = '🔊';
      speakBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.speakPhrase(p.text_en);
      });
      controls.appendChild(speakBtn);

      const favBtn = document.createElement('button');
      favBtn.type = 'button';
      favBtn.className = 'phrase-icon-btn';
      favBtn.title = isFav ? 'Remove from favorites' : 'Add to favorites';
      favBtn.textContent = isFav ? '⭐' : '☆';
      favBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleFavorite(p.id);
      });
      controls.appendChild(favBtn);

      if (p.is_custom) {
        const delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.className = 'phrase-icon-btn';
        delBtn.title = 'Delete phrase';
        delBtn.textContent = '🗑️';
        delBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          this.deleteCustomPhrase(p.id);
        });
        controls.appendChild(delBtn);
      }

      card.appendChild(controls);
      grid.appendChild(card);
    });
  },

  /**
   * IMPORTANT: Clicking phrase card adds text to Communication Hub without auto-playing audio!
   */
  onPhraseClick(en, bn) {
    if (window.CommunicationHub) {
      window.CommunicationHub.sendMessage(en, 'typed');
      TransifyApp.showToast(`Phrase added to Hub: "${en}"`, 'success');
      TransifyApp.announce(`Phrase selected: ${en}`);
    } else {
      const input = document.getElementById('hub-input-text');
      if (input) input.value = en;
    }
  },

  /**
   * Spoken strictly and ONLY when user explicitly clicks 🔊 button!
   */
  speakPhrase(text) {
    if (window.TransifyTTS && window.TransifyTTS.speak) {
      window.TransifyTTS.speak(text);
    }
  },

  async toggleFavorite(phraseId) {
    try {
      const res = await fetch(`/api/phrases/${phraseId}/favorite`, {
        method: 'POST',
        credentials: 'same-origin'
      });
      if (res.ok) {
        const data = await res.json();
        const p = this.phrases.find(item => item.id === phraseId);
        if (p) p.is_favorite = data.is_favorite;
        this.renderGrid();
        return;
      }
    } catch (e) {
      console.warn('Phrase favorite toggle server error, toggling locally:', e);
    }
    const p = this.phrases.find(item => item.id === phraseId);
    if (p) {
      p.is_favorite = !p.is_favorite;
      this.renderGrid();
    }
  },

  async saveCustomPhrase() {
    const enInput = document.getElementById('input-phrase-en');
    const bnInput = document.getElementById('input-phrase-bn');
    const textEn = enInput ? enInput.value.trim() : '';
    const textBn = bnInput ? bnInput.value.trim() : '';

    if (!textEn) {
      TransifyApp.showToast('Please enter English text for the phrase.', 'warning');
      return;
    }

    try {
      const res = await fetch('/api/phrases', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text_en: textEn, text_bn: textBn, category: 'custom' })
      });
      if (res.ok) {
        const data = await res.json();
        this.phrases.unshift(data.phrase);
        if (enInput) enInput.value = '';
        if (bnInput) bnInput.value = '';
        const addForm = document.getElementById('phrase-add-form-container');
        if (addForm) addForm.style.display = 'none';
        this.renderGrid();
        TransifyApp.showToast('Custom phrase saved successfully!', 'success');
        return;
      }
    } catch (e) {
      console.warn('Phraseboard save custom phrase server error:', e);
    }

    this.phrases.unshift({
      id: Date.now(),
      text_en: textEn,
      text_bn: textBn,
      category: 'custom',
      is_favorite: false,
      is_custom: true
    });
    if (enInput) enInput.value = '';
    if (bnInput) bnInput.value = '';
    const addForm = document.getElementById('phrase-add-form-container');
    if (addForm) addForm.style.display = 'none';
    this.renderGrid();
    TransifyApp.showToast('Custom phrase saved locally.', 'success');
  },

  async deleteCustomPhrase(phraseId) {
    if (!confirm('Delete this custom phrase?')) return;
    try {
      await fetch(`/api/phrases/${phraseId}`, {
        method: 'DELETE',
        credentials: 'same-origin'
      });
    } catch (e) {
      console.warn('Phraseboard delete server note:', e);
    }
    this.phrases = this.phrases.filter(p => p.id !== phraseId);
    this.renderGrid();
    TransifyApp.showToast('Phrase deleted.', 'success');
  }
};

// ============================================================================
// ACTIVITY & DIAGNOSTICS DASHBOARD CONTROLLER
// ============================================================================
window.TransifyDashboard = {
  historyRecords: [],
  _initialized: false,

  async init() {
    if (!this._initialized) {
      this._initialized = true;
      this.bindEvents();
    }
    await Promise.all([this.loadHistory(), this.loadDiagnostics()]);
  },

  bindEvents() {
    const searchInput = document.getElementById('dash-search-input');
    const modalitySelect = document.getElementById('dash-modality-select');
    const dateSelect = document.getElementById('dash-date-select');
    const favFilter = document.getElementById('dash-fav-filter');

    const triggerReload = () => this.loadHistory();

    if (searchInput) searchInput.addEventListener('input', this.debounce(triggerReload, 300));
    if (modalitySelect) modalitySelect.addEventListener('change', triggerReload);
    if (dateSelect) dateSelect.addEventListener('change', triggerReload);
    if (favFilter) favFilter.addEventListener('change', triggerReload);
  },

  debounce(fn, delay) {
    let timer;
    return function(...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  },

  async loadHistory() {
    const search = document.getElementById('dash-search-input')?.value.trim() || '';
    const modality = document.getElementById('dash-modality-select')?.value || 'all';
    const dateFilter = document.getElementById('dash-date-select')?.value || 'all';
    const favOnly = document.getElementById('dash-fav-filter')?.checked || false;

    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (modality !== 'all') params.set('modality', modality);
    if (dateFilter !== 'all') params.set('date_filter', dateFilter);
    if (favOnly) params.set('favorites_only', 'true');

    try {
      const res = await fetch(`/api/history?${params.toString()}`, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        this.historyRecords = data.history || [];
      } else {
        this.historyRecords = [];
      }
    } catch (e) {
      console.warn('Dashboard loadHistory note:', e);
      this.historyRecords = [];
    }
    this.renderHistory();
  },

  renderHistory() {
    const listEl = document.getElementById('dashboard-history-list');
    if (!listEl) return;

    if (!this.historyRecords.length) {
      listEl.innerHTML = '<div style="text-align: center; color: #94a3b8; font-size: 13px; padding: 24px 0;">No translation records found matching your filters.</div>';
      return;
    }

    listEl.innerHTML = this.historyRecords.map(rec => {
      const isFav = Boolean(rec.is_favorite);
      const textToSpeak = (rec.recognized_text || rec.translated_text || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
      const timeStr = typeof rec.timestamp === 'number' ? new Date(rec.timestamp * 1000).toLocaleString() : (rec.timestamp || '');

      return `
        <div style="background: #ffffff; border: 1px solid rgba(131,56,236,0.12); border-radius: 12px; padding: 10px 12px; display: flex; justify-content: space-between; align-items: center; gap: 8px;">
          <div style="flex: 1; min-width: 0;">
            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 2px;">
              <span class="badge badge-info" style="font-size: 10px; text-transform: uppercase;">${rec.modality || 'sign'}</span>
              <span style="font-size: 11px; color: #94a3b8;">${timeStr}</span>
            </div>
            <div style="font-size: 13.5px; font-weight: 700; color: #1e1b4b; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
              ${(rec.recognized_text || rec.translated_text || '').replace(/</g, '&lt;')}
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 4px;">
            <button type="button" class="phrase-icon-btn" onclick="TransifyDashboard.speakRecord('${textToSpeak}')" title="Speak text aloud">🔊</button>
            <button type="button" class="phrase-icon-btn" onclick="TransifyDashboard.toggleFavorite(${rec.id})" title="${isFav ? 'Unfavorite' : 'Favorite'}">${isFav ? '⭐' : '☆'}</button>
          </div>
        </div>
      `;
    }).join('');
  },

  speakRecord(text) {
    if (window.TransifyTTS && window.TransifyTTS.speak) {
      window.TransifyTTS.speak(text);
    }
  },

  async toggleFavorite(recordId) {
    try {
      const res = await fetch(`/api/history/${recordId}/favorite`, {
        method: 'POST',
        credentials: 'same-origin'
      });
      if (res.ok) {
        const data = await res.json();
        const r = this.historyRecords.find(item => item.id === recordId);
        if (r) r.is_favorite = data.is_favorite;
        this.renderHistory();
      }
    } catch (e) {
      console.warn('Dashboard favorite error:', e);
    }
  },

  async loadDiagnostics() {
    const statusVal = document.getElementById('diag-val-status');
    const dbVal = document.getElementById('diag-val-db');
    const modelVal = document.getElementById('diag-val-model');
    const latencyVal = document.getElementById('diag-val-latency');

    const t0 = performance.now();
    try {
      const res = await fetch('/api/ready');
      const roundtrip = Math.round(performance.now() - t0);
      if (latencyVal) latencyVal.textContent = `${roundtrip} ms`;

      if (res.ok) {
        const data = await res.json();
        if (statusVal) {
          statusVal.textContent = data.status === 'ready' ? 'Online' : 'Degraded';
          statusVal.style.color = data.status === 'ready' ? '#10b981' : '#f59e0b';
        }
        if (dbVal) {
          const dbOk = data.checks && data.checks.database;
          dbVal.textContent = dbOk ? 'Connected' : 'Unavailable';
          dbVal.style.color = dbOk ? '#10b981' : '#ef4444';
        }
        if (modelVal) {
          const modelOk = data.checks && data.checks.asl_model;
          modelVal.textContent = modelOk ? 'ASL Ready' : 'Fallback';
          modelVal.style.color = modelOk ? '#8338ec' : '#f59e0b';
        }
      } else {
        if (statusVal) { statusVal.textContent = 'Degraded'; statusVal.style.color = '#ef4444'; }
      }
    } catch (e) {
      if (statusVal) { statusVal.textContent = 'Offline'; statusVal.style.color = '#ef4444'; }
      if (dbVal) dbVal.textContent = 'Unreachable';
      if (modelVal) modelVal.textContent = 'Unavailable';
    }
  }
};

// ============================================================================
// ACCESSIBILITY & INTERNATIONALIZATION ENGINE
// ============================================================================
window.TransifyA11y = {
  _initialized: false,

  init() {
    if (this._initialized) return;
    this._initialized = true;

    const reducedMotion = localStorage.getItem('transify_reduced_motion') === 'true';
    const largeTargets = localStorage.getItem('transify_large_targets') === 'true';

    this.toggleReducedMotion(reducedMotion, false);
    this.toggleLargeTargets(largeTargets, false);

    const btnOpen = document.getElementById('btn-open-a11y');
    const modal = document.getElementById('a11y-modal-overlay');
    const btnClose = document.getElementById('a11y-close-btn');
    const chkMotion = document.getElementById('a11y-toggle-reduced-motion');
    const chkTargets = document.getElementById('a11y-toggle-large-targets');

    if (chkMotion) chkMotion.checked = reducedMotion;
    if (chkTargets) chkTargets.checked = largeTargets;

    if (btnOpen && modal) {
      btnOpen.addEventListener('click', () => { modal.style.display = 'flex'; });
    }
    if (btnClose && modal) {
      btnClose.addEventListener('click', () => { modal.style.display = 'none'; });
    }
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.style.display = 'none';
      });
    }

    if (chkMotion) {
      chkMotion.addEventListener('change', (e) => this.toggleReducedMotion(e.target.checked, true));
    }
    if (chkTargets) {
      chkTargets.addEventListener('change', (e) => this.toggleLargeTargets(e.target.checked, true));
    }

    document.addEventListener('keydown', (e) => {
      if (e.altKey && e.key.toLowerCase() === 'h') {
        e.preventDefault();
        if (typeof openSlide === 'function') openSlide('slide-communication-hub');
      } else if (e.altKey && e.key.toLowerCase() === 'p') {
        e.preventDefault();
        if (typeof openSlide === 'function') openSlide('slide-phraseboard');
      } else if (e.altKey && e.key.toLowerCase() === 'd') {
        e.preventDefault();
        if (typeof openSlide === 'function') openSlide('slide-dashboard');
      } else if (e.altKey && e.key.toLowerCase() === 'l') {
        e.preventDefault();
        if (window.TransifyI18n) window.TransifyI18n.toggleLanguage();
      } else if (e.key === 'Escape') {
        if (modal && modal.style.display === 'flex') modal.style.display = 'none';
      }
    });
  },

  toggleReducedMotion(enabled, save = true) {
    if (enabled) {
      document.body.classList.add('reduced-motion');
    } else {
      document.body.classList.remove('reduced-motion');
    }
    if (save) {
      localStorage.setItem('transify_reduced_motion', enabled ? 'true' : 'false');
      TransifyApp.announce(enabled ? 'Reduced motion enabled' : 'Reduced motion disabled');
    }
  },

  toggleLargeTargets(enabled, save = true) {
    if (enabled) {
      document.body.classList.add('large-targets');
    } else {
      document.body.classList.remove('large-targets');
    }
    if (save) {
      localStorage.setItem('transify_large_targets', enabled ? 'true' : 'false');
      TransifyApp.announce(enabled ? 'Large touch targets enabled' : 'Large touch targets disabled');
    }
  }
};

window.TransifyI18n = {
  currentLang: localStorage.getItem('transify_lang') || 'en',
  translations: {
    en: {
      hub_title: 'Communication Hub',
      hub_sub: 'Unified Chat',
      hub_subtitle: 'Unified Multimodal Conversation Feed',
      phrases_title: 'Quick Phraseboard',
      phrases_sub: 'Quick Phrases',
      phrases_subtitle: 'Bilingual Essential & Custom Phrases',
      dash_title: 'Dashboard',
      dash_sub: 'History & Health',
      dash_subtitle: 'History, Activity & System Diagnostics'
    },
    bn: {
      hub_title: 'যোগাযোগ কেন্দ্র',
      hub_sub: 'সমন্বিত চ্যাট',
      hub_subtitle: 'বহুমুখী সমন্বিত বার্তা আদান-প্রদান',
      phrases_title: 'দ্রুত বাক্যাবলী',
      phrases_sub: 'প্রয়োজনীয় বাক্য',
      phrases_subtitle: 'দ্বিভাষিক প্রয়োজনীয় ও কাস্টম বাক্যাবলী',
      dash_title: 'ড্যাশবোর্ড',
      dash_sub: 'ইতিহাস ও স্বাস্থ্য',
      dash_subtitle: 'কার্যক্রমের ইতিহাস ও সিস্টেমের অবস্থা'
    }
  },

  init() {
    this.applyLanguage(this.currentLang, false);
    const toggleBtn = document.getElementById('lang-toggle-btn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => this.toggleLanguage());
    }
  },

  toggleLanguage() {
    const nextLang = this.currentLang === 'en' ? 'bn' : 'en';
    this.applyLanguage(nextLang, true);
  },

  applyLanguage(lang, save = true) {
    this.currentLang = lang;
    document.documentElement.setAttribute('lang', lang);

    const toggleBtn = document.getElementById('lang-toggle-btn');
    if (toggleBtn) {
      const enOpt = toggleBtn.querySelector('.lang-en');
      const bnOpt = toggleBtn.querySelector('.lang-bn');
      if (enOpt && bnOpt) {
        if (lang === 'bn') {
          enOpt.classList.remove('lang-active');
          bnOpt.classList.add('lang-active');
        } else {
          enOpt.classList.add('lang-active');
          bnOpt.classList.remove('lang-active');
        }
      }
    }

    const dict = this.translations[lang] || this.translations.en;
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (dict[key]) el.textContent = dict[key];
    });

    if (save) {
      localStorage.setItem('transify_lang', lang);
      TransifyApp.announce(lang === 'bn' ? 'ভাষা পরিবর্তন করা হয়েছে: বাংলা' : 'Language changed to English');
    }
  }
};

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
  if (window.TransifyA11y && window.TransifyA11y.init) {
    window.TransifyA11y.init();
  }
  if (window.TransifyI18n && window.TransifyI18n.init) {
    window.TransifyI18n.init();
  }

  // Expose module APIs to window for inline onclick handlers and extensions
  window.TransifyApp = TransifyApp;
  window.SignPage = SignPage;
  window.SignLanguageModule = SignPage;
  window.TransifySign = SignPage;
  window.BraillePage = BraillePage;
  window.TransifySTT = TransifySTT;
  window.TransifyTTSPage = TransifyTTSPage;
  window.TransifyTTS = TransifyTTS;
  window.openAuthSheet = (m) => TransifyApp.openAuthSheet(m);
  window.closeAuthSheet = () => TransifyApp.closeAuthSheet();
  window.switchAuthTab = (m) => TransifyApp.switchAuthTab(m);
  window.setMode = (m) => TransifyApp.switchAuthTab(m);
  window.handleDirectLogin = () => TransifyApp.handleDirectLogin();
  window.handleDemoLogin = () => TransifyApp.handleDemoLogin();
  window.handleDemoGuest = () => TransifyApp.handleDemoLogin();
  window.handleAuthSubmit = (e) => TransifyApp.handleAuthSubmit(e);
  window.handleGoogleLogin = () => TransifyApp.handleGoogleLogin();
  window.handleForgotPassword = (e) => TransifyApp.handleForgotPassword(e);
  window.togglePasswordVisibility = () => TransifyApp.togglePasswordVisibility();
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

// Client Error Tracking (Item 15)
window.addEventListener('error', function(event) {
  if (event.filename && (event.filename.includes('app.js') || event.filename.includes('auth-controller.js'))) {
    try {
      fetch('/api/telemetry/error', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: event.message || 'Unknown Client Error',
          source: event.filename || '',
          lineno: event.lineno || 0,
          colno: event.colno || 0,
          stack: event.error ? event.error.stack : ''
        })
      }).catch(function() {});
    } catch (_) {}
  }
});
