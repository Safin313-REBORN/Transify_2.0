/**
 * Transify 2.0 Internationalization (i18n) Engine
 * Provides seamless English and Bengali translations across all app views.
 */
(function() {
  'use strict';

  const DICTIONARY = {
    en: {
      brand_tagline: "Breaking Communication Barriers",
      nav_home: "Home",
      nav_sign: "Sign",
      nav_braille: "Braille",
      nav_voice: "Voice",
      nav_phrases: "Phrases",
      nav_care: "Care",
      nav_chat: "AI Chat",
      nav_settings: "Settings",
      nav_more: "More",

      // Cover & Welcome
      cover_title: "Signs to words, spoken aloud.",
      cover_subtitle: "Hold a sign to the camera. Transify recognizes Bengali and American Sign Language and speaks the translation.",
      btn_create_account: "Create account",
      btn_login: "Log in",
      btn_skip_guest: "Skip for now",
      welcome_lang_btn: "বাংলা",

      // Auth Sheet
      auth_signin_title: "Welcome back",
      auth_signin_sub: "Sign in to your Transify assistive account",
      auth_signup_title: "Create an account",
      auth_signup_sub: "Get started with full offline assistive translation",
      label_fullname: "Full name",
      label_email: "Email address",
      label_password: "Password",
      label_remember: "Remember me",
      link_forgot: "Forgot password?",
      btn_submit_signin: "Sign in",
      btn_submit_signup: "Create account",
      prompt_need_account: "Don't have an account?",
      prompt_have_account: "Already have an account?",
      link_create_one: "Sign up",
      link_sign_in: "Sign in",

      // Home
      home_greeting_night: "Good night",
      home_greeting_morn: "Good morning",
      home_greeting_aft: "Good afternoon",
      home_greeting_eve: "Good evening",
      home_welcome: "Welcome to Transify",
      say_aloud_placeholder: "Type something to say aloud",
      btn_speak: "Speak",
      btn_speaking: "Speaking...",
      phrase_help: "I need help",
      phrase_thanks: "Thank you",
      phrase_exit: "Where is the exit?",
      phrase_slow: "Please slow down",
      phrase_write: "Can you write that down?",

      // Bento Tiles
      bento_sign_title: "Translate signs",
      bento_sign_sub: "BdSL and ASL, spoken as you sign",
      bento_braille_title: "Read Braille",
      bento_braille_sub: "Scan a page, hear it read",
      bento_voice_title: "Voice hub",
      bento_voice_sub: "Live captions and read aloud",

      // Transify Care Tile
      care_badge_intake: "Healthcare Intake",
      care_badge_offline: "Offline-First",
      care_badge_ai: "🤖 AI Trained",
      care_card_title: "Transify Care & AI Assistant",
      care_card_desc: "Accessible clinical symptom triage, WHO/Merck guidelines & AI consultation.",
      btn_ai_chatbot: "🤖 AI Chatbot",
      btn_care_intake: "Symptom Intake",
      btn_clinician_portal: "Clinician Portal",

      // Recent
      recent_title: "Recent",

      // Floating Chat Trigger
      floating_chat_label: "AI Assistant",

      // Settings
      settings_title: "Preferences & Accessibility",
      settings_lang_label: "Interface Language",
      settings_lang_desc: "Choose English or বাংলা as the primary application language",
      settings_speed_label: "Speech Synthesizer Speed",
      settings_motion_label: "Reduce Motion",
      settings_privacy_banner: "100% On-Device Processing Guaranteed"
    },
    bn: {
      brand_tagline: "যোগাযোগের দূরত্ব ঘুচিয়ে",
      nav_home: "হোম",
      nav_sign: "ইশারা",
      nav_braille: "ব্রেইল",
      nav_voice: "ভয়েস",
      nav_phrases: "বাক্য",
      nav_care: "কেয়ার",
      nav_chat: "এআই চ্যাট",
      nav_settings: "সেটিংস",
      nav_more: "আরও",

      // Cover & Welcome
      cover_title: "ইশারা থেকে কথা, সরাসরি শুনুন।",
      cover_subtitle: "ক্যামেরার সামনে ইশারা করুন। ট্রান্সিফাই বাংলা ও আমেরিকান সাইন ল্যাঙ্গুয়েজ চিনে তাৎক্ষণিক অনুবাদ শোনায়।",
      btn_create_account: "অ্যাকাউন্ট তৈরি করুন",
      btn_login: "সাইন ইন",
      btn_skip_guest: "আপাতত এড়িয়ে যান",
      welcome_lang_btn: "English",

      // Auth Sheet
      auth_signin_title: "স্বাগতম",
      auth_signin_sub: "আপনার ট্রান্সিফাই অ্যাকাউন্টে সাইন ইন করুন",
      auth_signup_title: "নতুন অ্যাকাউন্ট তৈরি করুন",
      auth_signup_sub: "অফলাইন সহায়ক অনুবাদের পূর্ণ সুবিধা নিন",
      label_fullname: "পুরো নাম",
      label_email: "ইমেইল ঠিকানা",
      label_password: "পাসওয়ার্ড",
      label_remember: "মনে রাখুন",
      link_forgot: "পাসওয়ার্ড ভুলে গেছেন?",
      btn_submit_signin: "সাইন ইন",
      btn_submit_signup: "অ্যাকাউন্ট তৈরি করুন",
      prompt_need_account: "অ্যাকাউন্ট নেই?",
      prompt_have_account: "ইতিমধ্যে অ্যাকাউন্ট আছে?",
      link_create_one: "সাইন আপ",
      link_sign_in: "সাইন ইন",

      // Home
      home_greeting_night: "শুভ রাত্রি",
      home_greeting_morn: "শুভ সকাল",
      home_greeting_aft: "শুভ অপরাহ্ন",
      home_greeting_eve: "শুভ সন্ধ্যা",
      home_welcome: "ট্রান্সিফাইতে স্বাগতম",
      say_aloud_placeholder: "উচ্চস্বরে বলার জন্য কিছু লিখুন...",
      btn_speak: "বলুন",
      btn_speaking: "বলা হচ্ছে...",
      phrase_help: "আমার সাহায্য দরকার",
      phrase_thanks: "ধন্যবাদ",
      phrase_exit: "বের হওয়ার রাস্তা কোথায়?",
      phrase_slow: "দয়া করে আস্তে বলুন",
      phrase_write: "লিখে দিতে পারবেন?",

      // Bento Tiles
      bento_sign_title: "ইশারা অনুবাদ",
      bento_sign_sub: "বিডিএসএল ও এএসএল, সাইন করার সাথে সাথে বলা হবে",
      bento_braille_title: "ব্রেইল পড়ুন",
      bento_braille_sub: "পৃষ্ঠা স্ক্যান করুন, শুনে নিন",
      bento_voice_title: "ভয়েস হাব",
      bento_voice_sub: "লাইভ ক্যাপশন ও ভয়েস সিন্থেসিস",

      // Transify Care Tile
      care_badge_intake: "স্বাস্থ্যসেবা ইনটেক",
      care_badge_offline: "অফলাইন প্রথম",
      care_badge_ai: "🤖 এআই প্রশিক্ষিত",
      care_card_title: "ট্রান্সিফাই কেয়ার ও এআই সহকারী",
      care_card_desc: "ক্লিনিক্যাল লক্ষণ ট্রায়াজ, ডব্লিউএইচও নির্দেশিকা ও এআই পরামর্শ।",
      btn_ai_chatbot: "🤖 এআই চ্যাটবট",
      btn_care_intake: "লক্ষণ ট্রায়াজ",
      btn_clinician_portal: "ক্লিনিশিয়ান পোর্টাল",

      // Recent
      recent_title: "সাম্প্রতিক",

      // Floating Chat Trigger
      floating_chat_label: "এআই সহকারী",

      // Settings
      settings_title: "পছন্দ ও অ্যাক্সেসিবিলিটি",
      settings_lang_label: "ইন্টারফেসের ভাষা",
      settings_lang_desc: "অ্যাপ্লিকেশনের মূল ভাষা হিসেবে English অথবা বাংলা নির্বাচন করুন",
      settings_speed_label: "স্পিচ সংশ্লেষণের গতি",
      settings_motion_label: "মোশন কমান",
      settings_privacy_banner: "১০০% অন-ডিভাইস প্রক্রিয়াকরণ নিশ্চিত"
    }
  };

  let currentLang = 'en';

  try {
    const saved = localStorage.getItem('transify_lang');
    if (saved === 'bn' || saved === 'en') {
      currentLang = saved;
    }
  } catch (e) {}

  function updateDomTranslations(lang) {
    const isBn = (lang === 'bn');
    const dict = DICTIONARY[lang] || DICTIONARY.en;

    // 1. Data-i18n attributes
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (dict[key]) {
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
          el.setAttribute('placeholder', dict[key]);
        } else {
          el.textContent = dict[key];
        }
      }
    });

    // 2. Left Navigation Rail
    const railHome = document.querySelector('#rail-btn-home span');
    if (railHome) railHome.textContent = dict.nav_home;
    const railSign = document.querySelector('#rail-btn-sign span');
    if (railSign) railSign.textContent = dict.nav_sign;
    const railBraille = document.querySelector('#rail-btn-braille span');
    if (railBraille) railBraille.textContent = dict.nav_braille;
    const railVoice = document.querySelector('#rail-btn-voice span');
    if (railVoice) railVoice.textContent = dict.nav_voice;
    const railPhrases = document.querySelector('#rail-btn-phrases span');
    if (railPhrases) railPhrases.textContent = dict.nav_phrases;
    const railCare = document.querySelector('#rail-btn-care span');
    if (railCare) railCare.textContent = dict.nav_care;
    const railChat = document.querySelector('#rail-btn-chat span');
    if (railChat) railChat.textContent = dict.nav_chat;
    const railSettings = document.querySelector('#rail-btn-settings span');
    if (railSettings) railSettings.textContent = dict.nav_settings;
    const railMore = document.querySelector('#rail-btn-more span');
    if (railMore) railMore.textContent = dict.nav_more;

    // 3. Home Screen Greeting & Headline
    const h = new Date().getHours();
    const greetEl = document.getElementById('home-greeting-text');
    if (greetEl) {
      if (h >= 5 && h < 12) greetEl.textContent = dict.home_greeting_morn;
      else if (h >= 12 && h < 17) greetEl.textContent = dict.home_greeting_aft;
      else if (h >= 17 && h < 22) greetEl.textContent = dict.home_greeting_eve;
      else greetEl.textContent = dict.home_greeting_night || dict.home_greeting_eve;
    }

    const nameEl = document.getElementById('home-user-name');
    if (nameEl) {
      try {
        const userJson = localStorage.getItem('transify_auth_user');
        if (userJson) {
          const u = JSON.parse(userJson);
          if (u.name || u.full_name) {
            const userName = u.name || u.full_name;
            nameEl.textContent = isBn ? `${userName}, স্বাগতম` : `Welcome, ${userName}`;
          } else {
            nameEl.textContent = dict.home_welcome;
          }
        } else {
          nameEl.textContent = dict.home_welcome;
        }
      } catch (e) {
        nameEl.textContent = dict.home_welcome;
      }
    }

    // 4. Say Aloud Input & Buttons
    const sayInput = document.getElementById('say');
    if (sayInput) {
      sayInput.setAttribute('placeholder', dict.say_aloud_placeholder);
    }
    const idleSpeakText = document.getElementById('say-speak-idle-text');
    if (idleSpeakText) idleSpeakText.textContent = dict.btn_speak;
    const activeSpeakText = document.getElementById('say-speak-active-text');
    if (activeSpeakText) activeSpeakText.textContent = dict.btn_speaking;

    // 5. Quick Phrase Chips
    const chips = document.querySelectorAll('#home-phrase-chips .phrase-chip-btn');
    if (chips && chips.length >= 5) {
      chips[0].textContent = dict.phrase_help;
      chips[1].textContent = dict.phrase_thanks;
      chips[2].textContent = dict.phrase_exit;
      chips[3].textContent = dict.phrase_slow;
      chips[4].textContent = dict.phrase_write;
    }

    // 6. Bento Grid Tiles
    // Tile 1: Sign
    const t1Title = document.querySelector('a.tile.t1 .cap b');
    if (t1Title) t1Title.textContent = dict.bento_sign_title;
    const t1Sub = document.querySelector('a.tile.t1 .cap span');
    if (t1Sub) t1Sub.textContent = dict.bento_sign_sub;

    // Tile 2: Braille
    const t2Title = document.querySelector('a.tile.t2 .cap b');
    if (t2Title) t2Title.textContent = dict.bento_braille_title;
    const t2Sub = document.querySelector('a.tile.t2 .cap span');
    if (t2Sub) t2Sub.textContent = dict.bento_braille_sub;

    // Tile 3: Voice
    const t3Title = document.querySelector('a.tile.t3 .cap b');
    if (t3Title) t3Title.textContent = dict.bento_voice_title;
    const t3Sub = document.querySelector('a.tile.t3 .cap span');
    if (t3Sub) t3Sub.textContent = dict.bento_voice_sub;

    // 7. Transify Care Card (Full Width)
    const careTitle = document.querySelector('.home-care-tile .care-title');
    if (careTitle) careTitle.textContent = dict.care_card_title;
    const careDesc = document.querySelector('.home-care-tile .care-desc');
    if (careDesc) careDesc.textContent = dict.care_card_desc;

    const careBadges = document.querySelectorAll('.home-care-tile .care-badge');
    if (careBadges && careBadges.length >= 3) {
      careBadges[0].textContent = dict.care_badge_intake;
      careBadges[1].textContent = dict.care_badge_offline;
      careBadges[2].textContent = dict.care_badge_ai;
    }

    const careChatBtn = document.getElementById('btn-open-ai-chat');
    if (careChatBtn) careChatBtn.textContent = dict.btn_ai_chatbot;
    const careIntakeBtn = document.getElementById('btn-open-care-intake');
    if (careIntakeBtn) careIntakeBtn.textContent = dict.btn_care_intake;
    const careClinicianBtn = document.getElementById('btn-open-clinician-portal');
    if (careClinicianBtn) careClinicianBtn.textContent = dict.btn_clinician_portal;

    // 8. Recent Header
    const recentH2 = document.querySelector('.recent-h2');
    if (recentH2) recentH2.textContent = dict.recent_title;

    // 9. Floating Chat Trigger
    const floatingLabel = document.querySelector('.floating-chat-label');
    if (floatingLabel) floatingLabel.textContent = dict.floating_chat_label;

    // 10. Welcome Screen
    const welcomeLine1 = document.getElementById('welcome-line-1');
    if (welcomeLine1) welcomeLine1.textContent = isBn ? 'ইশারা থেকে কথা,' : 'Signs to words,';
    const welcomeLine2 = document.getElementById('welcome-line-2');
    if (welcomeLine2) welcomeLine2.textContent = isBn ? 'সরাসরি শুনুন।' : 'spoken aloud.';
    const welcomeSub = document.getElementById('welcome-subtext');
    if (welcomeSub) welcomeSub.textContent = dict.cover_subtitle;
    const welcomeLangBtn = document.getElementById('welcome-lang-btn');
    if (welcomeLangBtn) welcomeLangBtn.textContent = dict.welcome_lang_btn;
    const welcomeAccountBtn = document.getElementById('btn-open-register') || document.getElementById('btn-welcome-account');
    if (welcomeAccountBtn) welcomeAccountBtn.textContent = dict.btn_create_account;
    const welcomeSigninBtn = document.getElementById('btn-open-login') || document.getElementById('btn-welcome-signin');
    if (welcomeSigninBtn) welcomeSigninBtn.textContent = dict.btn_login;
    const welcomeGuestBtn = document.getElementById('btn-demo-guest');
    if (welcomeGuestBtn) welcomeGuestBtn.textContent = dict.btn_skip_guest;

    // 11. Language Toggle Buttons Sync
    const enBtn = document.getElementById('home-lang-en');
    const bnBtn = document.getElementById('home-lang-bn');
    if (enBtn && bnBtn) {
      enBtn.classList.toggle('active', !isBn);
      enBtn.setAttribute('aria-pressed', !isBn ? 'true' : 'false');
      bnBtn.classList.toggle('active', isBn);
      bnBtn.setAttribute('aria-pressed', isBn ? 'true' : 'false');
    }

    const langSelect = document.getElementById('setting-lang-select');
    if (langSelect && langSelect.value !== lang) {
      langSelect.value = lang;
    }
  }

  function applyLanguage(lang) {
    if (lang !== 'en' && lang !== 'bn') lang = 'en';
    currentLang = lang;
    document.documentElement.setAttribute('lang', lang);

    try {
      localStorage.setItem('transify_lang', lang);
    } catch (e) {}

    updateDomTranslations(lang);

    try {
      window.dispatchEvent(new CustomEvent('transify:languagechange', { detail: { lang: lang } }));
    } catch (e) {}
  }

  function t(key) {
    const dict = DICTIONARY[currentLang] || DICTIONARY.en;
    return dict[key] || key;
  }

  window.TransifyI18n = {
    setLanguage: applyLanguage,
    getLanguage: function() { return currentLang; },
    t: t,
    dictionary: DICTIONARY
  };

  // Global alias for compatibility
  window.applyLocale = applyLanguage;

  // Rule L11: Virtual keyboard detection via visualViewport
  if (window.visualViewport) {
    var onViewportResize = function() {
      var isKbd = window.visualViewport.height < window.innerHeight * 0.75;
      document.body.setAttribute('data-kbd', isKbd ? 'open' : 'closed');
      if (isKbd && document.activeElement && typeof document.activeElement.scrollIntoView === 'function') {
        document.activeElement.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
    };
    window.visualViewport.addEventListener('resize', onViewportResize);
  }

  // Auto-apply on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      applyLanguage(currentLang);
    });
  } else {
    applyLanguage(currentLang);
  }
})();
