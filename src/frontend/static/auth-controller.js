/**
 * Transify 2.0 Unified Authentication Controller
 * Single source of truth for authentication across landing page (/) and standalone login (/login).
 * Enforces real server authentication, strict cookie sessions, genuine password recovery,
 * zero fake guest states, no invented default names, and accessible keyboard & screen reader interactions.
 */

(function(window, document) {
  'use strict';

  var AuthController = {
    _initialized: false,
    _isSubmitting: false,
    activeMode: 'login', // 'login' | 'signup' | 'forgot' | 'reset'
    lastFocusedElement: null,
    googleOAuthConfig: null,

    init: function() {
      if (this._initialized) return;
      this._initialized = true;

      this.bindDOMEvents();
      this.checkGoogleConfig();
      this.bindArtworkErrorHandling();
      this.checkUrlResetToken();
    },

    /**
     * Bulletproof Artwork Error Handling:
     * Activates CSS fallback immediately if welcome SVG/image fails to decode.
     */
    bindArtworkErrorHandling: function() {
      var self = this;
      window.handleArtworkError = function(img) {
        var artwork = img || document.getElementById('auth-welcome-artwork');
        if (artwork) {
          artwork.style.display = 'none';
          artwork.setAttribute('aria-hidden', 'true');
          artwork.setAttribute('alt', '');
        }
        var card = document.getElementById('auth-welcome-card');
        if (card) {
          card.classList.add('auth-fallback-active');
        }
      };

      window.addEventListener('error', function(e) {
        if (e.target && (e.target.id === 'auth-welcome-artwork' || (e.target.classList && e.target.classList.contains('auth-welcome-exact-artwork')))) {
          window.handleArtworkError(e.target);
        }
      }, true);
    },

    /**
     * Queries Google OAuth availability without fabricating logins.
     */
    checkGoogleConfig: async function() {
      var self = this;
      try {
        var res = await fetch('/api/auth/oauth/google/config', {
          method: 'GET',
          headers: { 'Accept': 'application/json' }
        });
        if (res.ok) {
          self.googleOAuthConfig = await res.json();
          var googleBtn = document.getElementById('google-login-btn');
          if (googleBtn && !self.googleOAuthConfig.available) {
            googleBtn.setAttribute('title', 'Google Sign-In is not configured in this deployment.');
            googleBtn.setAttribute('aria-disabled', 'true');
            googleBtn.style.opacity = '0.7';
          }
        }
      } catch (e) {
        // Network or offline: keep conservative disabled state
      }
    },

    /**
     * Binds event listeners exactly once to prevent duplicated clicks or handlers.
     */
    bindDOMEvents: function() {
      var self = this;

      // Hotspot Welcome Buttons
      var btnRegister = document.getElementById('btn-open-register');
      var btnLogin = document.getElementById('btn-open-login');
      var btnGuest = document.getElementById('btn-demo-guest');

      if (btnRegister) {
        btnRegister.onclick = function(e) { e.preventDefault(); self.openSheet('signup'); };
      }
      if (btnLogin) {
        btnLogin.onclick = function(e) { e.preventDefault(); self.openSheet('login'); };
      }
      if (btnGuest) {
        btnGuest.onclick = function(e) { e.preventDefault(); self.submitGuest(); };
      }

      // Sheet Back & Backdrop
      var btnBack = document.getElementById('auth-back-btn');
      var backdrop = document.getElementById('auth-sheet-backdrop');
      if (btnBack) {
        btnBack.onclick = function(e) { e.preventDefault(); self.closeSheet(); };
      }
      if (backdrop) {
        backdrop.onclick = function(e) { e.preventDefault(); self.closeSheet(); };
      }

      // Tabs
      var tabLogin = document.getElementById('tab-login');
      var tabSignup = document.getElementById('tab-signup');
      if (tabLogin) {
        tabLogin.onclick = function(e) { e.preventDefault(); self.switchTab('login'); };
      }
      if (tabSignup) {
        tabSignup.onclick = function(e) { e.preventDefault(); self.switchTab('signup'); };
      }

      // Password Toggle
      var pwdToggle = document.getElementById('toggle-pwd-btn');
      if (pwdToggle) {
        pwdToggle.onclick = function(e) { e.preventDefault(); self.togglePasswordVisibility(); };
      }

      // Form Submit (Enter key or Submit button)
      var form = document.getElementById('auth-form');
      if (form) {
        form.onsubmit = function(e) { self.submitAuth(e); };
      }

      // Forgot Password Link
      var forgotLink = document.getElementById('forgot-password-link');
      if (forgotLink) {
        forgotLink.onclick = function(e) { e.preventDefault(); self.openForgotPassword(); };
      }

      // Google Sign-In Button
      var googleBtn = document.getElementById('google-login-btn');
      if (googleBtn) {
        googleBtn.onclick = function(e) { e.preventDefault(); self.handleGoogleClick(); };
      }

      // Mode Switch Prompt Link
      var switchLink = document.getElementById('switch-prompt-link');
      if (switchLink) {
        switchLink.onclick = function(e) {
          e.preventDefault();
          if (self.activeMode === 'signup') {
            self.switchTab('login');
          } else {
            self.switchTab('signup');
          }
        };
      }

      // Global Keyboard Accessibility: Escape key closes the sheet
      document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
          var sheet = document.getElementById('auth-sheet-container');
          if (sheet && sheet.classList.contains('active')) {
            self.closeSheet();
          }
        }
      });
    },

    openSheet: function(mode) {
      mode = mode || 'login';
      this.lastFocusedElement = document.activeElement;
      this.switchTab(mode);

      var sheet = document.getElementById('auth-sheet-container');
      if (sheet) {
        sheet.classList.add('active');
        sheet.setAttribute('aria-hidden', 'false');
      }

      this.hideAlert();

      // Focus management: place cursor inside first visible input
      setTimeout(function() {
        if (mode === 'signup') {
          var nameInput = document.getElementById('input-fullname');
          if (nameInput) nameInput.focus();
        } else {
          var emailInput = document.getElementById('input-email');
          if (emailInput) emailInput.focus();
        }
      }, 100);
    },

    closeSheet: function() {
      var sheet = document.getElementById('auth-sheet-container');
      if (sheet) {
        sheet.classList.remove('active');
        sheet.setAttribute('aria-hidden', 'true');
      }
      this.hideAlert();

      // Restore focus
      if (this.lastFocusedElement && typeof this.lastFocusedElement.focus === 'function') {
        try { this.lastFocusedElement.focus(); } catch (e) {}
      }
    },

    switchTab: function(mode) {
      this.activeMode = mode;
      this.hideAlert();

      var tabLogin = document.getElementById('tab-login');
      var tabSignup = document.getElementById('tab-signup');
      var title = document.getElementById('auth-heading-title');
      var subtitle = document.getElementById('auth-heading-subtitle');
      var groupFullname = document.getElementById('group-fullname');
      var inputFullname = document.getElementById('input-fullname');
      var groupEmail = document.getElementById('group-email') || (document.getElementById('input-email') ? (document.getElementById('input-email').closest('.input-group') || document.getElementById('input-email').closest('.auth-input-row')) : null);
      var groupPassword = document.getElementById('group-password') || (document.getElementById('input-password') ? (document.getElementById('input-password').closest('.input-group') || document.getElementById('input-password').closest('.auth-input-row')) : null);
      var inputPassword = document.getElementById('input-password');
      var groupTerms = document.getElementById('group-terms');
      var groupRemember = document.getElementById('auth-options-row');
      var inputRemember = document.getElementById('input-remember');
      var inputTerms = document.getElementById('input-terms');
      var btnText = document.getElementById('btn-text');
      var switchPrompt = document.getElementById('auth-switch-prompt');
      var switchPromptText = document.getElementById('switch-prompt-text');
      var switchPromptLink = document.getElementById('switch-prompt-link');
      var divider = document.querySelector('.auth-divider') || document.querySelector('.auth-split-line');
      var googleBtn = document.getElementById('google-login-btn');
      var forgotFields = document.getElementById('auth-forgot-fields');

      if (forgotFields) forgotFields.style.display = 'none';
      if (groupEmail) groupEmail.style.display = 'flex';
      if (groupPassword) groupPassword.style.display = 'flex';
      if (inputPassword) inputPassword.setAttribute('required', 'required');
      if (divider) divider.style.display = 'flex';
      if (googleBtn) googleBtn.style.display = 'flex';
      if (switchPrompt) switchPrompt.style.display = 'block';

      if (mode === 'signup') {
        if (tabSignup) { tabSignup.classList.add('active'); tabSignup.setAttribute('aria-selected', 'true'); }
        if (tabLogin) { tabLogin.classList.remove('active'); tabLogin.setAttribute('aria-selected', 'false'); }
        if (title) title.textContent = 'Join Transify!';
        if (subtitle) subtitle.textContent = 'Create your account to start communicating';

        if (groupFullname) groupFullname.style.display = 'flex';
        if (inputFullname) {
          inputFullname.setAttribute('required', 'required');
          // STRICT RULE: Never autofill with "Sarah Ahmed" or any invented name
          if (inputFullname.value === 'Sarah Ahmed') inputFullname.value = '';
        }

        // Show Terms checkbox, hide Remember Me
        if (groupTerms) groupTerms.style.display = 'flex';
        if (groupRemember) groupRemember.style.display = 'none';
        if (inputTerms) inputTerms.checked = false; // Unchecked by default

        if (btnText) btnText.textContent = 'Register & Open Slides';
        if (switchPromptText) switchPromptText.textContent = 'Already have an account?';
        if (switchPromptLink) switchPromptLink.textContent = 'Login';
      } else {
        // mode === 'login'
        if (tabLogin) { tabLogin.classList.add('active'); tabLogin.setAttribute('aria-selected', 'true'); }
        if (tabSignup) { tabSignup.classList.remove('active'); tabSignup.setAttribute('aria-selected', 'false'); }
        if (title) title.textContent = 'Welcome Back!';
        if (subtitle) subtitle.textContent = 'Login to your Transify account';

        if (groupFullname) groupFullname.style.display = 'none';
        if (inputFullname) inputFullname.removeAttribute('required');

        // Show Remember Me, hide Terms checkbox
        if (groupTerms) groupTerms.style.display = 'none';
        if (groupRemember) groupRemember.style.display = 'flex';

        if (btnText) btnText.textContent = 'Login';
        if (switchPromptText) switchPromptText.textContent = "Don't have an account?";
        if (switchPromptLink) switchPromptLink.textContent = 'Sign Up';
      }
    },

    openForgotPassword: function() {
      this.activeMode = 'forgot';
      this.hideAlert();

      var title = document.getElementById('auth-heading-title');
      var subtitle = document.getElementById('auth-heading-subtitle');
      var groupFullname = document.getElementById('group-fullname');
      var inputFullname = document.getElementById('input-fullname');
      var groupPassword = document.getElementById('group-password') || (document.getElementById('input-password') ? (document.getElementById('input-password').closest('.input-group') || document.getElementById('input-password').closest('.auth-input-row')) : null);
      var inputPassword = document.getElementById('input-password');
      var groupTerms = document.getElementById('group-terms');
      var groupRemember = document.getElementById('auth-options-row');
      var btnText = document.getElementById('btn-text');
      var divider = document.querySelector('.auth-divider') || document.querySelector('.auth-split-line');
      var googleBtn = document.getElementById('google-login-btn');
      var switchPromptText = document.getElementById('switch-prompt-text');
      var switchPromptLink = document.getElementById('switch-prompt-link');
      var forgotFields = document.getElementById('auth-forgot-fields');

      if (title) title.textContent = 'Recover Password';
      if (subtitle) subtitle.textContent = 'Enter your email to receive recovery instructions';
      if (groupFullname) groupFullname.style.display = 'none';
      if (inputFullname) inputFullname.removeAttribute('required');
      if (groupPassword) groupPassword.style.display = 'none';
      if (inputPassword) inputPassword.removeAttribute('required');
      if (groupTerms) groupTerms.style.display = 'none';
      if (groupRemember) groupRemember.style.display = 'none';
      if (divider) divider.style.display = 'none';
      if (googleBtn) googleBtn.style.display = 'none';
      if (forgotFields) forgotFields.style.display = 'none';

      if (btnText) btnText.textContent = 'Send Reset Instructions';
      if (switchPromptText) switchPromptText.textContent = 'Remembered your password?';
      if (switchPromptLink) switchPromptLink.textContent = 'Back to Login';
    },

    handleGoogleClick: function() {
      this.showAlert('Google Sign-In is currently disabled in this release. Please sign in with email and password or use Demo Guest.', false);
    },

    togglePasswordVisibility: function() {
      var pwdInput = document.getElementById('input-password');
      var eyeIcon = document.getElementById('eye-icon');
      if (!pwdInput) return;

      if (pwdInput.type === 'password') {
        pwdInput.type = 'text';
        if (eyeIcon) {
          eyeIcon.innerHTML =
            '<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/>' +
            '<path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/>' +
            '<path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/>' +
            '<line x1="2" x2="22" y1="2" y2="22"/>';
        }
      } else {
        pwdInput.type = 'password';
        if (eyeIcon) {
          eyeIcon.innerHTML =
            '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>' +
            '<circle cx="12" cy="12" r="3"/>';
        }
      }
    },

    showAlert: function(msg, isSuccess) {
      var alertBox = document.getElementById('auth-alert');
      if (!alertBox) return;
      alertBox.textContent = msg;
      alertBox.className = 'auth-status-alert ' + (isSuccess ? 'success' : 'error');
      alertBox.style.display = 'block';
      alertBox.setAttribute('aria-live', isSuccess ? 'polite' : 'assertive');
    },

    hideAlert: function() {
      var alertBox = document.getElementById('auth-alert');
      if (alertBox) {
        alertBox.style.display = 'none';
        alertBox.textContent = '';
      }
    },

    setSubmittingState: function(submitting, customText) {
      this._isSubmitting = submitting;
      var submitBtn = document.getElementById('auth-submit-btn');
      var btnText = document.getElementById('btn-text');
      if (submitBtn) {
        submitBtn.disabled = submitting;
        submitBtn.style.opacity = submitting ? '0.75' : '1';
      }
      if (btnText && customText) {
        btnText.textContent = customText;
      }
    },

    /**
     * Handles Form Submission for Login, Registration, and Password Reset.
     * Prevents duplicate in-flight requests.
     */
    submitAuth: async function(e) {
      if (e && typeof e.preventDefault === 'function') e.preventDefault();
      if (this._isSubmitting) return;

      var emailInput = document.getElementById('input-email');
      var pwdInput = document.getElementById('input-password');
      var nameInput = document.getElementById('input-fullname');
      var inputRemember = document.getElementById('input-remember');
      var inputTerms = document.getElementById('input-terms');

      var email = emailInput ? emailInput.value.trim() : '';
      var password = pwdInput ? pwdInput.value : '';
      var name = nameInput ? nameInput.value.trim() : '';
      var rememberMe = inputRemember ? inputRemember.checked : false;
      var consentTerms = inputTerms ? inputTerms.checked : false;

      // 1. FORGOT PASSWORD WORKFLOW
      if (this.activeMode === 'forgot') {
        if (!email) {
          this.showAlert('Please enter your email address.', false);
          return;
        }
        if (!/^\S+@\S+\.\S+$/.test(email)) {
          this.showAlert('Please enter a valid email address.', false);
          return;
        }

        this.setSubmittingState(true, 'Processing...');
        try {
          var resForgot = await fetch('/api/auth/forgot-password', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
          });
          var dataForgot = await resForgot.json().catch(function() { return {}; });

          if (resForgot.status === 429) {
            this.showAlert(dataForgot.detail || 'Too many attempts. Please wait 5 minutes.', false);
          } else if (resForgot.ok) {
            this.showAlert(dataForgot.message || 'If an account exists, instructions have been sent.', true);
            // Reveal token and new password fields
            this.revealResetForm(email, dataForgot.test_token);
          } else {
            this.showAlert(dataForgot.detail || 'Password recovery request failed.', false);
          }
        } catch (err) {
          this.showAlert('Unable to reach server. Please check your network connection.', false);
        } finally {
          this.setSubmittingState(false, 'Send Reset Instructions');
        }
        return;
      }

      // 2. RESET PASSWORD WORKFLOW
      if (this.activeMode === 'reset') {
        var tokenInput = document.getElementById('input-reset-token');
        var newPwdInput = document.getElementById('input-new-password');
        var tokenVal = tokenInput ? tokenInput.value.trim() : '';
        var newPwdVal = newPwdInput ? newPwdInput.value : '';

        if (!tokenVal || !newPwdVal) {
          this.showAlert('Please provide both reset code and new password.', false);
          return;
        }
        if (newPwdVal.length < 15) {
          this.showAlert('New password must be at least 15 characters long.', false);
          return;
        }

        this.setSubmittingState(true, 'Updating Password...');
        try {
          var resReset = await fetch('/api/auth/reset-password', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: tokenVal, new_password: newPwdVal })
          });
          var dataReset = await resReset.json().catch(function() { return {}; });

          if (resReset.ok) {
            this.showAlert('Password reset successful! Please login with your new password.', true);
            var self = this;
            setTimeout(function() {
              self.switchTab('login');
              if (emailInput) emailInput.focus();
            }, 800);
          } else {
            this.showAlert(dataReset.detail || 'Password reset failed. Invalid or expired code.', false);
          }
        } catch (err) {
          this.showAlert('Unable to reach server. Please check your network connection.', false);
        } finally {
          this.setSubmittingState(false, 'Set New Password');
        }
        return;
      }

      // 3. LOGIN & SIGNUP VALIDATION
      if (!email || !password) {
        this.showAlert('Please fill in both email and password.', false);
        return;
      }
      if (!/^\S+@\S+\.\S+$/.test(email)) {
        this.showAlert('Please enter a valid email address.', false);
        return;
      }

      if (this.activeMode === 'signup') {
        if (!name || name.length < 2) {
          this.showAlert('Please enter your full name (at least 2 characters).', false);
          return;
        }
        if (password.length < 15) {
          this.showAlert('Password must be at least 15 characters long.', false);
          return;
        }
        if (!consentTerms) {
          this.showAlert('Consent to Terms of Service & Privacy Policy is required to create an account.', false);
          return;
        }
      }

      var isSignup = (this.activeMode === 'signup');
      this.setSubmittingState(true, isSignup ? 'Registering...' : 'Authenticating...');

      try {
        var endpoint = isSignup ? '/api/auth/register' : '/api/auth/login';
        var payload = isSignup
          ? { name: name, email: email, password: password, consent_terms: true }
          : { email: email, password: password, remember_me: rememberMe };

        var res = await fetch(endpoint, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        var data = await res.json().catch(function() { return {}; });

        if (res.status === 429) {
          this.showAlert(data.detail || 'Too many failed attempts. Please wait 5 minutes.', false);
          this.setSubmittingState(false, isSignup ? 'Register & Open Slides' : 'Login');
          return;
        }

        if (res.ok && data.status === 'success' && data.user) {
          // Store minimal profile in localStorage, NEVER raw session tokens
          try {
            localStorage.setItem('transify_auth_user', JSON.stringify(data.user));
            localStorage.removeItem('transify_guest_mode');
            localStorage.removeItem('transify_session_token');
            localStorage.removeItem('transify_auth_token');
          } catch (e) {}

          this.showAlert(isSignup ? 'Account registered! Opening Transify...' : 'Login successful! Opening Transify...', true);
          var self = this;
          setTimeout(function() {
            self.completeAuthSuccess(data.user);
          }, 350);
        } else {
          var errDetail = data.detail || (isSignup ? 'Registration failed. Please try again.' : 'Invalid email or password.');
          this.showAlert(errDetail, false);
          this.setSubmittingState(false, isSignup ? 'Register & Open Slides' : 'Login');
        }
      } catch (err) {
        this.showAlert('Unable to reach server. Please check your network connection.', false);
        this.setSubmittingState(false, isSignup ? 'Register & Open Slides' : 'Login');
      }
    },

    checkUrlResetToken: function() {
      // 1. Fragment-based reset token flow (#reset_token=...)
      // Tokens are strictly accepted via URL fragment to prevent inclusion in HTTP requests,
      // browser referer headers, access logs, or proxy caches.
      var token = null;
      var hash = window.location.hash || '';
      if (hash) {
        var match = hash.match(/reset_token=([A-Za-z0-9_-]+)/);
        if (match && match[1]) {
          token = match[1];
        }
      }

      // Legacy query-string tokens (?reset_token=...) are explicitly REJECTED
      // to eliminate query-string credential leakage. If present in query, sanitize the address bar.
      if (window.location.search && window.history && window.history.replaceState) {
        try {
          var sp = new URLSearchParams(window.location.search);
          if (sp.has('reset_token')) {
            sp.delete('reset_token');
            var rem = sp.toString();
            var sanitizedUrl = window.location.pathname + (rem ? '?' + rem : '') + (window.location.hash || '');
            window.history.replaceState(null, document.title, sanitizedUrl);
          }
        } catch (e) {}
      }

      if (token) {
        // Strip the token from visible browser URL without reloading page or logging token
        if (window.history && window.history.replaceState) {
          var cleanPath = window.location.pathname + (window.location.search || '');
          window.history.replaceState(null, document.title, cleanPath);
        }

        // Open sheet if on landing page
        var sheet = document.getElementById('auth-sheet-container');
        if (sheet) {
          sheet.classList.add('active');
          sheet.setAttribute('aria-hidden', 'false');
        }

        this.revealResetForm(null, token);
      }
    },

    revealResetForm: function(email, testToken) {
      this.activeMode = 'reset';
      var title = document.getElementById('auth-heading-title');
      var subtitle = document.getElementById('auth-heading-subtitle');
      var groupFullname = document.getElementById('group-fullname');
      var inputFullname = document.getElementById('input-fullname');
      var groupEmail = document.getElementById('group-email') || (document.getElementById('input-email') ? (document.getElementById('input-email').closest('.input-group') || document.getElementById('input-email').closest('.auth-input-row')) : null);
      var inputEmail = document.getElementById('input-email');
      var groupPassword = document.getElementById('group-password') || (document.getElementById('input-password') ? (document.getElementById('input-password').closest('.input-group') || document.getElementById('input-password').closest('.auth-input-row')) : null);
      var inputPassword = document.getElementById('input-password');
      var groupTerms = document.getElementById('group-terms');
      var groupRemember = document.getElementById('auth-options-row');
      var divider = document.querySelector('.auth-divider') || document.querySelector('.auth-split-line');
      var googleBtn = document.getElementById('google-login-btn');
      var forgotFields = document.getElementById('auth-forgot-fields');
      var btnText = document.getElementById('btn-text');
      var switchPromptText = document.getElementById('switch-prompt-text');
      var switchPromptLink = document.getElementById('switch-prompt-link');

      if (title) title.textContent = 'Set New Password';
      if (subtitle) subtitle.textContent = 'Enter the reset code and choose a secure password (15+ chars)';
      if (groupFullname) groupFullname.style.display = 'none';
      if (inputFullname) inputFullname.removeAttribute('required');
      if (groupEmail) groupEmail.style.display = 'none';
      if (inputEmail) inputEmail.removeAttribute('required');
      if (groupPassword) groupPassword.style.display = 'none';
      if (inputPassword) inputPassword.removeAttribute('required');
      if (groupTerms) groupTerms.style.display = 'none';
      if (groupRemember) groupRemember.style.display = 'none';
      if (divider) divider.style.display = 'none';
      if (googleBtn) googleBtn.style.display = 'none';
      if (forgotFields) forgotFields.style.display = 'block';
      if (btnText) btnText.textContent = 'Set New Password';
      if (switchPromptText) switchPromptText.textContent = 'Remembered your password?';
      if (switchPromptLink) switchPromptLink.textContent = 'Back to Login';

      var tokenInput = document.getElementById('input-reset-token');
      if (tokenInput && testToken) {
        tokenInput.value = testToken;
      }
      var newPwdInput = document.getElementById('input-new-password');
      if (newPwdInput) newPwdInput.focus();
    },

    /**
     * Genuine Guest Mode:
     * MUST succeed via /api/auth/guest with valid JSON.
     * NEVER fakes a local guest identity on failure.
     */
    submitGuest: async function() {
      if (this._isSubmitting) return;
      this.setSubmittingState(true, 'Entering Guest Mode...');
      this.showAlert('Connecting guest session...', true);

      try {
        var res = await fetch('/api/auth/guest', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' }
        });

        var data = await res.json().catch(function() { return {}; });

        // STRICT VALIDATION: Must be real server-acknowledged guest session
        if (res.ok && data.status === 'success' && data.user && data.user.is_guest === true) {
          try {
            localStorage.setItem('transify_guest_mode', 'true');
            localStorage.setItem('transify_auth_user', JSON.stringify(data.user));
            localStorage.removeItem('transify_session_token');
            localStorage.removeItem('transify_auth_token');
          } catch (e) {}

          this.showAlert('Guest mode active. Opening Transify...', true);
          var self = this;
          setTimeout(function() {
            self.completeAuthSuccess(data.user);
          }, 250);
        } else {
          var errDetail = data.detail || 'Guest mode initialization failed on server. Please try again.';
          this.showAlert(errDetail, false);
          this.setSubmittingState(false, 'Login');
        }
      } catch (err) {
        // STRICT RULE: Do not grant guest mode when network fails!
        this.showAlert('Unable to reach server for guest session. Please check your network connection.', false);
        this.setSubmittingState(false, 'Login');
      }
    },

    completeAuthSuccess: function(userObj) {
      this.closeSheet();

      // If on standalone login page (/login), navigate to main application
      if (window.location.pathname.indexOf('/login') !== -1) {
        window.location.href = '/?auth_completed=1';
        return;
      }

      // On landing page (/): dismiss auth overlay and reveal main application
      var authOverlay = document.getElementById('transify-auth-screen');
      if (authOverlay) {
        authOverlay.style.display = 'none';
        authOverlay.style.pointerEvents = 'none';
        authOverlay.style.zIndex = '-99999';
        authOverlay.classList.add('auth-hidden');
      }

      var splash = document.getElementById('transify-splash-screen');
      if (splash) {
        splash.style.display = 'none';
        splash.classList.add('splash-hidden');
      }

      // Update global app user profile if main app.js is loaded
      if (window.TransifyApp && typeof window.TransifyApp.updateProfileUI === 'function') {
        window.TransifyApp.updateProfileUI(userObj);
      }
    }
  };

  // Expose global aliases for backward compatibility with existing layout & tests
  window.AuthController = AuthController;
  window.openAuthSheet = function(m) { AuthController.openSheet(m); };
  window.closeAuthSheet = function() { AuthController.closeSheet(); };
  window.switchAuthTab = function(m) { AuthController.switchTab(m); };
  window.setMode = function(m) { AuthController.switchTab(m); };
  window.handleDemoGuest = function() { AuthController.submitGuest(); };
  window.handleDemoLogin = function() { AuthController.submitGuest(); };
  window.handleDirectLogin = function() { AuthController.submitGuest(); };
  window.handleAuthSubmit = function(e) { AuthController.submitAuth(e); };
  window.togglePasswordVisibility = function() { AuthController.togglePasswordVisibility(); };
  window.handleForgotPassword = function(e) { if (e) e.preventDefault(); AuthController.openForgotPassword(); };
  window.handleGoogleLogin = function() { AuthController.handleGoogleClick(); };

  // Ensure window.TransifyApp delegates auth methods to AuthController
  window.TransifyApp = window.TransifyApp || {};
  window.TransifyApp.openAuthSheet = window.openAuthSheet;
  window.TransifyApp.closeAuthSheet = window.closeAuthSheet;
  window.TransifyApp.switchAuthTab = window.switchAuthTab;
  window.TransifyApp.setMode = window.switchAuthTab;
  window.TransifyApp.handleDemoGuest = window.handleDemoGuest;
  window.TransifyApp.handleDemoLogin = window.handleDemoGuest;
  window.TransifyApp.handleDirectLogin = window.handleDirectLogin;
  window.TransifyApp.handleAuthSubmit = window.handleAuthSubmit;
  window.TransifyApp.togglePasswordVisibility = window.togglePasswordVisibility;
  window.TransifyApp.handleForgotPassword = window.handleForgotPassword;
  window.TransifyApp.handleGoogleLogin = window.handleGoogleLogin;

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { AuthController.init(); });
  } else {
    AuthController.init();
  }

})(window, document);
