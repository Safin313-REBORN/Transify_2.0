/**
 * Transify Neural Boot & Declarative Event Dispatcher
 * RC1.4.5: Strict CSP Compliant (Zero Inline Scripts / Handlers)
 */

(function () {
  'use strict';

  // 1. Bulletproof routing & auth initialization (formerly inline in index.html)
  window.openAuthSheet = function (mode) {
    if (window.TransifyApp && window.TransifyApp.openAuthSheet) {
      window.TransifyApp.openAuthSheet(mode);
    } else {
      var sheet = document.getElementById('auth-sheet-container');
      if (sheet) sheet.classList.add('active');
    }
  };

  window.closeAuthSheet = function () {
    if (window.TransifyApp && window.TransifyApp.closeAuthSheet) {
      window.TransifyApp.closeAuthSheet();
    } else {
      var sheet = document.getElementById('auth-sheet-container');
      if (sheet) sheet.classList.remove('active');
    }
  };

  window.handleDirectLogin = function () {
    try {
      localStorage.setItem('transify_auth_user', JSON.stringify({ name: 'Transify Member', email: 'member@transify.ai' }));
      localStorage.setItem('transify.welcomed', '1');
    } catch (e) { }
    window.closeAuthSheet();
    if (window.routeTo) window.routeTo('home');
  };

  window.handleDemoLogin = function () {
    try { localStorage.setItem('transify.welcomed', '1'); } catch (e) { }
    window.closeAuthSheet();
    if (window.routeTo) window.routeTo('home');
  };

  window.openSlide = function (slideId) {
    if (slideId === 'slide-care-intake') {
      if (window.routeTo) window.routeTo('care-intake');
      if (window.TransifyCare && window.TransifyCare.switchTab) {
        window.TransifyCare.switchTab('intake');
      } else {
        var tab = document.getElementById('care-tab-intake-btn');
        if (tab) tab.click();
      }
    } else if (slideId === 'slide-clinician-portal') {
      if (window.routeTo) window.routeTo('clinician');
      if (window.TransifyCare && window.TransifyCare.switchTab) {
        window.TransifyCare.switchTab('clinician');
      } else {
        var tab = document.getElementById('care-tab-clinician-btn');
        if (tab) tab.click();
      }
    } else if (slideId === 'slide-care-chronic') {
      if (window.routeTo) window.routeTo('care');
      if (window.TransifyCare && window.TransifyCare.switchTab) {
        window.TransifyCare.switchTab('chronic');
      } else {
        var tab = document.getElementById('care-tab-chronic-btn');
        if (tab) tab.click();
      }
    } else if (slideId === 'slide-hand-signal') {
      if (window.routeTo) window.routeTo('sign');
    } else if (slideId === 'slide-braille') {
      if (window.routeTo) window.routeTo('braille');
    } else if (slideId === 'slide-stt' || slideId === 'slide-tts') {
      if (window.routeTo) window.routeTo(slideId.replace('slide-', ''));
    }
  };

  var TransifyApp = window.TransifyApp = window.TransifyApp || {};
  TransifyApp.openAuthSheet = window.openAuthSheet;
  TransifyApp.closeAuthSheet = window.closeAuthSheet;
  TransifyApp.handleDirectLogin = window.handleDirectLogin;
  TransifyApp.handleDemoLogin = window.handleDemoLogin;

  // 2. Declarative Event Delegation Dispatcher
  document.addEventListener('click', function (e) {
    var target = e.target.closest('[data-action], [data-route], [data-click]');
    if (!target || target.id === 'app-shell' || target.tagName === 'BODY' || target.tagName === 'HTML') return;

    // Handle stop-propagation
    if (target.getAttribute('data-action') === 'stop-propagation') {
      e.stopPropagation();
      return;
    }

    // Handle routing
    var route = target.getAttribute('data-route');
    if (route) {
      if (target.tagName.toLowerCase() === 'a') e.preventDefault();
      if (window.routeTo) window.routeTo(route);
      var afterClick = target.getAttribute('data-after-route');
      if (afterClick === 'demo-login' && window.TransifyApp && window.TransifyApp.handleDemoLogin) {
        window.TransifyApp.handleDemoLogin();
      } else if (afterClick && window.TransifyApp && window.TransifyApp.closeAuthSheet) {
        window.TransifyApp.closeAuthSheet();
      }
      return;
    }

    var action = target.getAttribute('data-action');
    if (!action) return;

    switch (action) {
      // Auth Actions
      case 'open-auth':
        e.preventDefault();
        window.openAuthSheet(target.getAttribute('data-mode') || 'login');
        break;
      case 'close-auth':
        e.preventDefault();
        window.closeAuthSheet();
        break;
      case 'direct-login':
        e.preventDefault();
        window.handleDirectLogin();
        break;
      case 'demo-login':
        e.preventDefault();
        window.handleDemoLogin();
        break;
      case 'settings-auth-action':
        e.preventDefault();
        if (window.TransifyApp && window.TransifyApp.handleSettingsAuthAction) {
          window.TransifyApp.handleSettingsAuthAction();
        }
        break;
      case 'profile-auth-action':
        e.preventDefault();
        if (window.TransifyApp && window.TransifyApp.handleProfileAuthAction) {
          window.TransifyApp.handleProfileAuthAction();
        }
        break;
      case 'auth-toggle-password':
        e.preventDefault();
        var p = document.getElementById('input-password');
        if (p) {
          var isPw = (p.type === 'password');
          p.type = isPw ? 'text' : 'password';
          target.textContent = isPw ? 'Hide' : 'Show';
        }
        break;
      case 'auth-forgot-password':
        e.preventDefault();
        alert('Password reset link sent to demo email.');
        break;
      case 'auth-switch-tab':
        e.preventDefault();
        var targetTabId = target.getAttribute('data-tab-id') || 'tab-signup';
        var tabEl = document.getElementById(targetTabId);
        if (tabEl) tabEl.click();
        break;

      // Dashboard Actions
      case 'dashboard-speak':
        e.preventDefault();
        if (window.TransifyTTS && window.TransifyTTS.speak) {
          window.TransifyTTS.speak(decodeURIComponent(target.getAttribute('data-text') || ''));
        }
        break;
      case 'dashboard-feedback':
        e.preventDefault();
        if (window.DashboardPage && window.DashboardPage.giveFeedback) {
          window.DashboardPage.giveFeedback(
            parseInt(target.getAttribute('data-rec-id'), 10),
            parseInt(target.getAttribute('data-rating'), 10)
          );
        }
        break;

      // Phrase Card Actions
      case 'phrase-speak':
        e.preventDefault();
        if (window.EditorialController && window.EditorialController.speakPhraseCard) {
          window.EditorialController.speakPhraseCard(parseInt(target.getAttribute('data-idx'), 10));
        }
        break;
      case 'phrase-toggle-fav':
        e.preventDefault();
        if (window.EditorialController && window.EditorialController.toggleFavoritePhrase) {
          window.EditorialController.toggleFavoritePhrase(target.getAttribute('data-phrase-id'), e);
        }
        break;
      case 'phrase-copy':
        e.preventDefault();
        var cardIdx = parseInt(target.getAttribute('data-idx'), 10);
        var cardEl = document.querySelector('.phrase-card[data-idx="' + cardIdx + '"]');
        if (cardEl && window.EditorialController && window.EditorialController.copyPhrase) {
          var enText = cardEl.querySelector('.phrase-en') ? cardEl.querySelector('.phrase-en').textContent : '';
          var bnText = cardEl.querySelector('.phrase-bn') ? cardEl.querySelector('.phrase-bn').textContent : '';
          window.EditorialController.copyPhrase(enText, bnText);
        }
        break;
      case 'phrase-bridge-sign':
        e.preventDefault();
        var sIdx = parseInt(target.getAttribute('data-idx'), 10);
        var sCard = document.querySelector('.phrase-card[data-idx="' + sIdx + '"]');
        if (sCard && window.EditorialController && window.EditorialController.bridgePhraseToSign) {
          var sEn = sCard.querySelector('.phrase-en') ? sCard.querySelector('.phrase-en').textContent : '';
          window.EditorialController.bridgePhraseToSign(sEn);
        }
        break;
      case 'phrase-bridge-braille':
        e.preventDefault();
        var bIdx = parseInt(target.getAttribute('data-idx'), 10);
        var bCard = document.querySelector('.phrase-card[data-idx="' + bIdx + '"]');
        if (bCard && window.EditorialController && window.EditorialController.bridgePhraseToBraille) {
          var bEn = bCard.querySelector('.phrase-en') ? bCard.querySelector('.phrase-en').textContent : '';
          window.EditorialController.bridgePhraseToBraille(bEn);
        }
        break;
      case 'phrase-alert':
        e.preventDefault();
        if (window.EditorialController && window.EditorialController.triggerEmergencyFlashByIdx) {
          window.EditorialController.triggerEmergencyFlashByIdx(parseInt(target.getAttribute('data-idx'), 10));
        }
        break;

      // Editorial / Phrases Actions
      case 'editorial-toggle-flash':
        e.preventDefault();
        if (window.EditorialController && window.EditorialController.toggleEmergencyFlashMode) {
          window.EditorialController.toggleEmergencyFlashMode();
        }
        break;
      case 'editorial-export-json':
        e.preventDefault();
        if (window.EditorialController && window.EditorialController.exportPhrasesJSON) {
          window.EditorialController.exportPhrasesJSON();
        }
        break;
      case 'editorial-dismiss-flash':
        e.preventDefault();
        if (window.EditorialController && window.EditorialController.dismissEmergencyFlash) {
          window.EditorialController.dismissEmergencyFlash();
        }
        break;

      // Braille Page Actions
      case 'braille-switch-mode':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.switchMode) {
          window.BraillePage.switchMode(target.getAttribute('data-mode'));
        }
        break;
      case 'braille-load-sample':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.loadSample) {
          window.BraillePage.loadSample(
            target.getAttribute('data-sample'),
            target.getAttribute('data-sample-name') || ''
          );
        }
        break;
      case 'braille-open-camera':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.openCamera) {
          window.BraillePage.openCamera(e);
        }
        break;
      case 'braille-run-iqa':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.runIQACheck) {
          window.BraillePage.runIQACheck();
        }
        break;
      case 'braille-run-translation':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.runTranslation) {
          window.BraillePage.runTranslation();
        }
        break;
      case 'braille-clear-cell-dots':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.clearCellDots) {
          window.BraillePage.clearCellDots();
        }
        break;
      case 'braille-speak-active-cell':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.speakActiveCell) {
          window.BraillePage.speakActiveCell();
        }
        break;
      case 'braille-invert-cell-dots':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.invertCellDots) {
          window.BraillePage.invertCellDots();
        }
        break;
      case 'braille-random-cell-pattern':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.randomCellPattern) {
          window.BraillePage.randomCellPattern();
        }
        break;
      case 'braille-copy-unicode':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.copyUnicodeBraille) {
          window.BraillePage.copyUnicodeBraille();
        }
        break;
      case 'braille-download-brf':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.downloadBRF) {
          window.BraillePage.downloadBRF();
        }
        break;
      case 'braille-load-preset':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.loadGeneratorPreset) {
          window.BraillePage.loadGeneratorPreset(target.getAttribute('data-preset'));
        }
        break;
      case 'braille-clear-generator-input':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.clearGeneratorInput) {
          window.BraillePage.clearGeneratorInput();
        }
        break;
      case 'braille-speak-generator':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.speakGeneratorText) {
          window.BraillePage.speakGeneratorText();
        }
        break;
      case 'braille-copy-generator-unicode':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.copyGeneratorUnicode) {
          window.BraillePage.copyGeneratorUnicode();
        }
        break;
      case 'braille-copy-generator-dots':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.copyGeneratorDots) {
          window.BraillePage.copyGeneratorDots();
        }
        break;
      case 'braille-download-generator-brf':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.downloadGeneratorBRF) {
          window.BraillePage.downloadGeneratorBRF();
        }
        break;
      case 'braille-filter-reference':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.filterReference) {
          window.BraillePage.filterReference(target.getAttribute('data-filter'));
        }
        break;
      case 'braille-close-camera':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.closeCamera) {
          window.BraillePage.closeCamera();
        }
        break;
      case 'braille-switch-camera-facing':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.switchCameraFacing) {
          window.BraillePage.switchCameraFacing();
        }
        break;
      case 'braille-capture-camera':
        e.preventDefault();
        if (window.BraillePage && window.BraillePage.captureCamera) {
          window.BraillePage.captureCamera();
        }
        break;

      // Voice Studio Actions
      case 'voice-switch-mode':
        e.preventDefault();
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.switchMode) {
          window.TransifyVoiceStudio.switchMode(target.getAttribute('data-mode'));
        }
        break;
      case 'voice-load-sample':
        e.preventDefault();
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.loadSample) {
          window.TransifyVoiceStudio.loadSample(
            target.getAttribute('data-sample'),
            target.getAttribute('data-lang') || 'en-US'
          );
        }
        break;
      case 'voice-download-txt':
        e.preventDefault();
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.downloadCaptionsTXT) {
          window.TransifyVoiceStudio.downloadCaptionsTXT();
        }
        break;
      case 'voice-download-srt':
        e.preventDefault();
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.downloadCaptionsSRT) {
          window.TransifyVoiceStudio.downloadCaptionsSRT();
        }
        break;
      case 'voice-bridge-sign':
        e.preventDefault();
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.bridgeToSign) {
          window.TransifyVoiceStudio.bridgeToSign();
        }
        break;
      case 'voice-bridge-braille':
        e.preventDefault();
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.bridgeToBraille) {
          window.TransifyVoiceStudio.bridgeToBraille();
        }
        break;
      case 'voice-set-tts-speed':
        e.preventDefault();
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.setTTSSpeed) {
          window.TransifyVoiceStudio.setTTSSpeed(parseFloat(target.getAttribute('data-speed')));
        }
        break;
      case 'voice-insert-phrase':
        e.preventDefault();
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.insertTTSPhrase) {
          window.TransifyVoiceStudio.insertTTSPhrase(target.getAttribute('data-phrase'));
        }
        break;
      case 'voice-pause-tts':
        e.preventDefault();
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.pauseTTS) {
          window.TransifyVoiceStudio.pauseTTS();
        }
        break;
      case 'voice-copy-tts':
        e.preventDefault();
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.copyTTSText) {
          window.TransifyVoiceStudio.copyTTSText();
        }
        break;
      case 'voice-sync-bridge':
        e.preventDefault();
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.syncActiveSpeechToBridge) {
          window.TransifyVoiceStudio.syncActiveSpeechToBridge();
        }
        break;

      // Settings Actions
      case 'settings-reset-defaults':
        e.preventDefault();
        if (window.resetSettingsToDefaults) window.resetSettingsToDefaults();
        break;
      case 'settings-tab':
        e.preventDefault();
        if (window.switchSettingsTab) window.switchSettingsTab(target.getAttribute('data-tab'));
        break;
      case 'settings-save-profile':
        e.preventDefault();
        if (window.saveUserProfile) window.saveUserProfile();
        break;
      case 'settings-apply-theme':
        e.preventDefault();
        if (window.applyThemeGlobal) window.applyThemeGlobal(target.getAttribute('data-theme'));
        break;
      case 'settings-font-scale':
        e.preventDefault();
        if (window.applyFontScale) window.applyFontScale(target.getAttribute('data-scale'));
        break;
      case 'settings-speech-rate':
        e.preventDefault();
        if (window.setSpeechRate) window.setSpeechRate(parseFloat(target.getAttribute('data-rate')));
        break;
      case 'settings-test-voice':
        e.preventDefault();
        if (window.testVoicePreview) window.testVoicePreview();
        break;
      case 'settings-sign-lang':
        e.preventDefault();
        if (window.setDefaultSignLang) window.setDefaultSignLang(target.getAttribute('data-lang'));
        break;
      case 'settings-braille-standard':
        e.preventDefault();
        if (window.setBrailleStandard) window.setBrailleStandard(target.getAttribute('data-standard'));
        break;
      case 'settings-confidence-gate':
        e.preventDefault();
        if (window.setConfidenceGate) window.setConfidenceGate(parseInt(target.getAttribute('data-gate'), 10));
        break;
      case 'settings-export-data':
        e.preventDefault();
        if (window.exportSettingsData) window.exportSettingsData();
        break;
      case 'settings-clear-history':
        e.preventDefault();
        if (window.clearActivityHistory) window.clearActivityHistory();
        break;
      case 'settings-copy-diagnostics':
        e.preventDefault();
        if (window.copySystemDiagnostics) window.copySystemDiagnostics();
        break;
      case 'settings-submit-feedback':
        e.preventDefault();
        if (window.submitDeveloperFeedback) window.submitDeveloperFeedback();
        break;
    }
  });

  // Change Event Delegation
  document.addEventListener('change', function (e) {
    var target = e.target.closest('[data-action]');
    if (!target) return;
    var action = target.getAttribute('data-action');

    switch (action) {
      case 'editorial-phrase-speed':
        if (window.EditorialController && window.EditorialController.setPhraseSpeed) {
          window.EditorialController.setPhraseSpeed(parseFloat(target.value));
        }
        break;
      case 'voice-caption-font':
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.changeCaptionFont) {
          window.TransifyVoiceStudio.changeCaptionFont(target.value);
        }
        break;
      case 'voice-persona':
        if (window.TransifyVoiceStudio && window.TransifyVoiceStudio.changeVoicePersona) {
          window.TransifyVoiceStudio.changeVoicePersona(target.value);
        }
        break;
      case 'settings-language':
        if (window.setAppLanguage) window.setAppLanguage(target.value);
        break;
      case 'settings-reduce-motion':
        if (window.toggleReduceMotion) window.toggleReduceMotion(target.checked);
        break;
      case 'settings-focus-rings':
        if (window.toggleFocusRings) window.toggleFocusRings(target.checked);
        break;
      case 'settings-audio-chimes':
        if (window.toggleAudioChimes) window.toggleAudioChimes(target.checked);
        break;
    }
  });

  // Input Event Delegation
  document.addEventListener('input', function (e) {
    var target = e.target.closest('[data-action]');
    if (!target) return;
    var action = target.getAttribute('data-action');

    if (action === 'braille-generator-input') {
      if (window.BraillePage && window.BraillePage.onGeneratorInput) {
        window.BraillePage.onGeneratorInput(target.value);
      }
    }
  });

  // Submit Event Delegation
  document.addEventListener('submit', function (e) {
    var target = e.target.closest('form[data-action], form#auth-form');
    if (!target) return;
    var action = target.getAttribute('data-action');
    if (action === 'auth-form-submit' || target.id === 'auth-form') {
      e.preventDefault();
      if (window.TransifyApp && window.TransifyApp.handleDirectLogin) {
        window.TransifyApp.handleDirectLogin();
      }
    }
  });

})();
