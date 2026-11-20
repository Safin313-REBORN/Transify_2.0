/**
 * Transify 2.0 Internationalization (i18n) Engine
 * Provides seamless English and Bengali translations with zero tracking corruption.
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
      nav_settings: "Settings",

      // Cover
      cover_title: "Sign. It speaks.",
      cover_subtitle: "Hold a hand sign in the box. Live camera AI recognizes ASL and BdSL in real time.",
      cover_braille_title: "Tactile dots. Plain text.",
      cover_braille_subtitle: "Scan embossed Braille paper sheets under natural light with instant UEB OCR.",
      cover_voice_title: "Every conversation captioned.",
      cover_voice_subtitle: "Continuous offline speech-to-text with clear, readable live captions.",
      btn_create_account: "Create account",
      btn_login: "Log in",
      btn_skip_guest: "Skip for now",
      btn_pause_stories: "Pause auto-advance",
      btn_play_stories: "Play auto-advance",

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
      home_greeting: "Good evening",
      say_aloud_placeholder: "Type something to say",
      btn_speak: "Speak",
      btn_speaking: "Speaking...",
      phrase_help: "I need help",
      phrase_thanks: "Thank you",
      phrase_where_restroom: "Where is the restroom?",
      phrase_how_much: "How much is this?",
      phrase_nice_to_meet: "Nice to meet you",

      // Bento Tiles
      bento_sign_title: "Translate signs",
      bento_sign_sub: "Real-time ASL & BdSL camera recognition",
      bento_braille_title: "Read Braille",
      bento_braille_sub: "Unified English Braille OCR scanner",
      bento_voice_title: "Voice hub",
      bento_voice_sub: "Real-time speech captions and natural voice",

      // Sign Translator
      sign_status_in_box: "Hand in the box",
      sign_status_out_box: "Move your hand into the box",
      sign_mode_words: "Words",
      sign_mode_letters: "Letters",
      sign_mode_sentence: "Sentence",
      sign_speak_word: "Speak",
      sign_add_sentence: "Add to sentence",
      sign_sentence_title: "Sentence builder",
      sign_start_camera: "Start camera",
      sign_stop_camera: "Stop camera",
      sign_reset: "Reset gesture",

      // Braille
      braille_header_title: "Read Braille",
      braille_header_sub: "Unified English Braille, Grade 1",
      braille_scan_page: "Scan page",
      braille_upload_photo: "Upload photo",
      braille_dropzone_hint: "Drop a Braille page photo here, or browse",
      braille_text_found: "Text found",
      braille_copy: "Copy",
      braille_copied: "Copied",
      braille_download: "Save .txt",

      // Voice Hub
      voice_tab_listen: "Listen",
      voice_tab_speak: "Speak",
      voice_listening_en: "Listening in English",
      voice_listening_bn: "Listening in Bengali",
      voice_mic_hint_idle: "Tap microphone to start listening",
      voice_mic_hint_active: "Listening actively... tap to stop",
      voice_speak_placeholder: "Type what you would like to speak aloud...",
      voice_speed_normal: "1.0x Normal",
      voice_speed_slow: "0.8x Slow",
      voice_speed_fast: "1.2x Fast",

      // Settings
      settings_title: "Preferences & Accessibility",
      settings_text_size: "Text size",
      settings_theme: "Theme",
      theme_light: "Light",
      theme_dark: "Dark",
      theme_hc: "High contrast",
      settings_reduce_motion: "Reduce motion",
      settings_haptics: "Haptic feedback"
    },
    bn: {
      brand_tagline: "যোগাযোগের দূরত্ব ঘুচিয়ে",
      nav_home: "হোম",
      nav_sign: "ইশারা",
      nav_braille: "ব্রেইল",
      nav_voice: "ভয়েস",
      nav_settings: "সেটিংস",

      // Cover
      cover_title: "ইশারা। যা কথা বলে।",
      cover_subtitle: "বক্সের মধ্যে হাত রাখুন। লাইভ ক্যামেরা এআই তাৎক্ষণিকভাবে এএসএল এবং বিডিএসএল চিনতে পারে।",
      cover_braille_title: "স্পর্শের ডট। স্পষ্ট লেখা।",
      cover_braille_subtitle: "স্বাভাবিক আলোয় ব্রেইল কাগজ স্ক্যান করুন এবং নিমেষেই ইউইবি ওসিআর অনুবাদ পান।",
      cover_voice_title: "প্রতিটি কথোপকথনের লাইভ ক্যাপশন।",
      cover_voice_subtitle: "অফলাইনে নির্ভরযোগ্য স্পিচ-টু-টেক্সটের মাধ্যমে স্পষ্ট ও পাঠযোগ্য ক্যাপশন।",
      btn_create_account: "অ্যাকাউন্ট তৈরি করুন",
      btn_login: "লগ ইন",
      btn_skip_guest: "আপাতত এড়িয়ে যান",
      btn_pause_stories: "স্বয়ংক্রিয় স্লাইড থামান",
      btn_play_stories: "স্বয়ংক্রিয় স্লাইড চালু করুন",

      // Auth Sheet
      auth_signin_title: "স্বাগতম",
      auth_signin_sub: "আপনার ট্রান্সসিফাই অ্যাকাউন্টে সাইন ইন করুন",
      auth_signup_title: "নতুন অ্যাকাউন্ট",
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
      home_greeting: "শুভ সন্ধ্যা",
      say_aloud_placeholder: "বলার জন্য কিছু লিখুন...",
      btn_speak: "বলুন",
      btn_speaking: "বলা হচ্ছে...",
      phrase_help: "আমার সাহায্য দরকার",
      phrase_thanks: "ধন্যবাদ",
      phrase_where_restroom: "টয়লেট কোথায়?",
      phrase_how_much: "এটির দাম কত?",
      phrase_nice_to_meet: "আপনার সাথে দেখা হয়ে ভালো লাগলো",

      // Bento Tiles
      bento_sign_title: "ইশারা অনুবাদ",
      bento_sign_sub: "ক্যামেরা এআই দ্বারা এএসএল ও বিডিএসএল শনাক্তকরণ",
      bento_braille_title: "ব্রেইল পড়ুন",
      bento_braille_sub: "ইউইবি গ্রেড ১ ব্রেইল ওসিআর স্ক্যানার",
      bento_voice_title: "ভয়েস হাব",
      bento_voice_sub: "রিয়েল-টাইম লাইভ ক্যাপশন ও ভয়েস সিন্থেসিস",

      // Sign Translator
      sign_status_in_box: "বক্সের ভেতর হাত রাখুন",
      sign_status_out_box: "আপনার হাতটি বক্সের মধ্যে আনুন",
      sign_mode_words: "শব্দ",
      sign_mode_letters: "অক্ষর",
      sign_mode_sentence: "বাক্য",
      sign_speak_word: "বলুন",
      sign_add_sentence: "বাক্যে যোগ করুন",
      sign_sentence_title: "বাক্য গঠন",
      sign_start_camera: "ক্যামেরা চালু করুন",
      sign_stop_camera: "ক্যামেরা বন্ধ করুন",
      sign_reset: "রিসেট",

      // Braille
      braille_header_title: "ব্রেইল পড়ুন",
      braille_header_sub: "ইউনিফাইড ইংলিশ ব্রেইল, গ্রেড ১",
      braille_scan_page: "পৃষ্ঠা স্ক্যান করুন",
      braille_upload_photo: "ছবি আপলোড করুন",
      braille_dropzone_hint: "ব্রেইল পাতার ছবি এখানে রাখুন অথবা ব্রাউজ করুন",
      braille_text_found: "প্রাপ্ত লেখা",
      braille_copy: "কপি",
      braille_copied: "কপি হয়েছে",
      braille_download: "সংরক্ষণ (.txt)",

      // Voice Hub
      voice_tab_listen: "শুনুন",
      voice_tab_speak: "বলুন",
      voice_listening_en: "ইংরেজিতে শোনা হচ্ছে...",
      voice_listening_bn: "বাংলায় শোনা হচ্ছে...",
      voice_mic_hint_idle: "শোনা শুরু করতে মাইকে চাপুন",
      voice_mic_hint_active: "শোনা হচ্ছে... থামাতে আবার চাপুন",
      voice_speak_placeholder: "যা বলতে চান তা এখানে লিখুন...",
      voice_speed_normal: "১.০x স্বাভাবিক",
      voice_speed_slow: "০.৮x ধীর",
      voice_speed_fast: "১.২x দ্রুত",

      // Settings
      settings_title: "পছন্দ ও অ্যাক্সেসিবিলিটি",
      settings_text_size: "লেখার আকার",
      settings_theme: "থিম",
      theme_light: "লাইট",
      theme_dark: "ডার্ক",
      theme_hc: "হাই কনট্রাস্ট",
      settings_reduce_motion: "মোশন কমান",
      settings_haptics: "হ্যাপটিক ফিডব্যাক"
    }
  };

  let currentLang = 'en';

  try {
    const saved = localStorage.getItem('transify_lang');
    if (saved === 'bn' || saved === 'en') {
      currentLang = saved;
    }
  } catch (e) {}

  function applyLanguage(lang) {
    if (lang !== 'en' && lang !== 'bn') lang = 'en';
    currentLang = lang;
    document.documentElement.setAttribute('lang', lang);

    try {
      localStorage.setItem('transify_lang', lang);
    } catch (e) {}

    const dict = DICTIONARY[lang] || DICTIONARY.en;
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

    // Update active state on any language switch buttons
    document.querySelectorAll('[data-lang-btn]').forEach(btn => {
      const bLang = btn.getAttribute('data-lang-btn');
      const active = (bLang === lang);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
      btn.classList.toggle('active', active);
    });
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

  document.addEventListener('DOMContentLoaded', function() {
    applyLanguage(currentLang);
  });
})();
