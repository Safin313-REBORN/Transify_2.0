/**
 * Transify 2.0 — Motion, Micro-Interactions, & Shell Animation System
 * Source of Truth: DESIGN_BRIEF.md & reference/transify-full.html
 * WCAG 2.1 AAA Compliant | Strict Reduced Motion Support
 */

(() => {
  'use strict';

  // Reduced motion query
  const isReducedMotion = () => {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches ||
           document.documentElement.classList.contains('rm') ||
           document.body.classList.contains('rm');
  };

  // 1. Sliding Navigation Indicator
  let ind = document.querySelector('.ind');
  const rail = document.querySelector('aside, .rail');
  if (!ind && rail) {
    ind = document.createElement('i');
    ind.className = 'ind';
    rail.prepend(ind);
  }

  function updateNavIndicator() {
    if (!ind || window.innerWidth <= 760) return;
    const activeLink = document.querySelector('.rail-item.active, .rail a.active, aside a[aria-current="page"]');
    if (activeLink && activeLink.offsetParent !== null && !activeLink.classList.contains('rail-logo-link') && activeLink.id !== 'rail-logo-btn') {
      ind.style.height = `${activeLink.offsetHeight}px`;
      ind.style.transform = `translateY(${activeLink.offsetTop}px)`;
      ind.style.opacity = '1';
    } else {
      ind.style.opacity = '0';
    }
  }

  // 2. Count-Up Numbers for Stat Cards
  function countUpStats() {
    const rmq = isReducedMotion();
    document.querySelectorAll('[data-to]').forEach((el) => {
      const target = parseFloat(el.getAttribute('data-to')) || 0;
      const suffix = el.getAttribute('data-suf') || '';
      if (rmq) {
        el.textContent = `${target}${suffix}`;
        return;
      }
      let startTime = null;
      const duration = 1100;
      const step = (timestamp) => {
        startTime = startTime || timestamp;
        const progress = Math.min((timestamp - startTime) / duration, 1);
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(target * easeOut);
        el.textContent = `${current}${suffix}`;
        if (progress < 1) {
          requestAnimationFrame(step);
        }
      };
      requestAnimationFrame(step);
    });
  }

  // 3. View Entrance & Stagger Orchestration
  function onRouteEnter() {
    const activeView = document.querySelector('.v.on, .page-view.active');
    if (!activeView) return;

    let n = 0;
    const staggerTargets = activeView.querySelectorAll(':scope > *, .grid > *, .stats > *, .home-bento > *');
    staggerTargets.forEach((child) => {
      child.style.setProperty('--n', Math.min(n++, 9));
    });

    updateNavIndicator();
    countUpStats();
  }

  // 4. Cursor Spotlight on Cards
  function setupSpotlight() {
    document.querySelectorAll('.card, .tile, [data-s]').forEach((card) => {
      if (card.__hasSpotlight) return;
      card.__hasSpotlight = true;
      card.addEventListener('pointermove', (e) => {
        const rect = card.getBoundingClientRect();
        card.style.setProperty('--x', `${e.clientX - rect.left}px`);
        card.style.setProperty('--y', `${e.clientY - rect.top}px`);
      });
    });
  }

  // 5. Toast System
  let toastTimer = null;
  function showToast(message, type) {
    let toast = document.getElementById('toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'toast';
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.className = 'show' + (type ? ' ' + type : '');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.className = '';
    }, 2400);
  }
  window.showToast = showToast;

  // 6. Click Ripple & Action Feedback
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn, .chip');
    if (!btn) return;

    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 2;
    const ripple = document.createElement('span');
    ripple.className = 'rip';
    ripple.style.width = `${size}px`;
    ripple.style.height = `${size}px`;
    ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
    ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 700);

    // Contextual toast announcements for actions
    const toastMap = {
      'btn-say-speak': 'Speaking text',
      'btn-clear-say': 'Cleared',
      'ssay': 'Speaking your sentence',
      'scp': 'Sentence copied',
      'sclr': 'Sentence cleared',
      'bcp': 'Braille copied',
      'bsay': 'Speaking text',
      'rsay': 'Speaking',
      'rstop': 'Stopped speech',
      'pa': 'Phrase saved',
      'clr': 'Local data cleared',
      'btn-save-emergency-note': 'Emergency note saved'
    };
    if (btn.id && toastMap[btn.id]) {
      showToast(toastMap[btn.id]);
    }
  });

  // 7. Subtle Magnetic Pull for Pointer-Fine Devices
  if (window.matchMedia('(pointer: fine)').matches) {
    document.addEventListener('pointermove', (e) => {
      if (isReducedMotion()) return;
      const btn = e.target.closest && e.target.closest('.btn');
      if (!btn) return;
      const rect = btn.getBoundingClientRect();
      const dx = (e.clientX - rect.left - rect.width / 2) * 0.14;
      const dy = (e.clientY - rect.top - rect.height / 2) * 0.22;
      btn.style.transform = `translate(${dx}px, ${dy}px)`;
    });

    document.addEventListener('pointerout', (e) => {
      const btn = e.target.closest && e.target.closest('.btn');
      if (btn) btn.style.transform = '';
    });
  }

  // 8. Sticky Top Bar Scroll Detection
  const topBar = document.querySelector('.top, .top-bar');
  if (topBar) {
    window.addEventListener('scroll', () => {
      topBar.classList.toggle('sc', window.scrollY > 8);
    }, { passive: true });
  }

  // 9. Boot Sequence Overlay
  function initBootSequence() {
    const bootEl = document.getElementById('boot') || document.getElementById('transify-boot-screen');
    if (!bootEl) return;

    const played = sessionStorage.getItem('transify_boot_played') === '1';
    const rmq = isReducedMotion();

    const endBoot = () => {
      bootEl.classList.add('out');
      document.body.classList.remove('lock');
      sessionStorage.setItem('transify_boot_played', '1');
      setTimeout(() => {
        bootEl.style.display = 'none';
        onRouteEnter();
      }, 850);
    };

    if (played || rmq) {
      bootEl.style.display = 'none';
      document.body.classList.remove('lock');
      onRouteEnter();
      return;
    }

    document.body.classList.add('lock');
    bootEl.style.display = 'grid';

    const statusLines = [
      'TRANSIFY 2.0 INITIALIZING NEURAL CORE...',
      'LOADING VISION PIPELINE (21 LANDMARKS)...',
      'SYNCHRONIZING EMBOSSED BRAILLE MATRIX...',
      'ZERO AUTO-AUDIO PRIVACY INVARIANT SECURED...',
      'CORE ONLINE — READY FOR ACCESSIBLE INTERACTION.'
    ];

    const logEl = document.getElementById('bl') || document.getElementById('boot-log');
    const fillEl = document.getElementById('bp') || document.getElementById('boot-progress-fill');
    const pctEl = document.getElementById('boot-pct');
    const statusEl = document.getElementById('boot-status-text');
    const skipBtn = document.getElementById('skip') || document.getElementById('btn-boot-skip');

    let idx = 0;
    if (logEl) logEl.textContent = '';
    if (fillEl) fillEl.style.width = '0%';
    if (pctEl) pctEl.textContent = '0%';

    const timer = setInterval(() => {
      if (idx < statusLines.length) {
        const line = statusLines[idx++];
        if (logEl) logEl.textContent += line + '\n';
        const pct = Math.round((idx / statusLines.length) * 100);
        if (fillEl) fillEl.style.width = `${pct}%`;
        if (pctEl) pctEl.textContent = `${pct}%`;
        if (statusEl) statusEl.textContent = line;
      } else {
        clearInterval(timer);
        setTimeout(endBoot, 350);
      }
    }, 380);

    if (skipBtn) {
      skipBtn.onclick = () => {
        clearInterval(timer);
        endBoot();
      };
    }

    window.addEventListener('keydown', (e) => {
      if (!bootEl.classList.contains('out') && (e.key === 'Enter' || e.key === 'Escape')) {
        clearInterval(timer);
        endBoot();
      }
    });
  }

  // 10. Replay Intro Trigger (Settings)
  window.replayIntro = function() {
    sessionStorage.removeItem('transify_boot_played');
    window.location.hash = '#home';
    const bootEl = document.getElementById('boot') || document.getElementById('transify-boot-screen');
    if (bootEl) {
      bootEl.classList.remove('out', 'boot-done');
      bootEl.style.display = 'grid';
      bootEl.style.pointerEvents = 'auto';
      bootEl.style.opacity = '1';
      bootEl.style.visibility = 'visible';
      initBootSequence();
    }
  };

  function initReplayButton() {
    document.querySelectorAll('#rep, .btn-rep-intro').forEach(btn => {
      btn.onclick = (e) => {
        e.preventDefault();
        window.replayIntro();
      };
    });
  }

  // 11. Top Bar, Emergency SOS & Language Integration
  function initTopBarAndEmergency() {
    const sosBtn = document.getElementById('sosb');
    const emModal = document.getElementById('em');
    const emDismiss = document.getElementById('emx');
    const emSay = document.getElementById('emsay');

    const speakEmergency = () => {
      try {
        window.speechSynthesis.cancel();
        const text = 'Medical emergency. Please help this person, or call 999. Emergency health helpline: 16263.';
        const utter = new SpeechSynthesisUtterance(text);
        utter.rate = 1.0;
        utter.lang = 'en-US';
        window.speechSynthesis.speak(utter);
      } catch (e) {}
    };

    if (sosBtn && emModal) {
      sosBtn.addEventListener('click', () => {
        emModal.style.display = 'grid';
        emModal.classList.add('on');
        speakEmergency();
      });
    }

    if (emDismiss && emModal) {
      emDismiss.addEventListener('click', () => {
        emModal.classList.remove('on');
        emModal.style.display = 'none';
      });
    }

    if (emSay) {
      emSay.addEventListener('click', speakEmergency);
    }

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && emModal && emModal.classList.contains('on')) {
        emModal.classList.remove('on');
        emModal.style.display = 'none';
      }
    });

    // Language switcher
    const langEn = document.getElementById('btn-lang-en');
    const langBn = document.getElementById('btn-lang-bn');
    if (langEn && langBn) {
      langEn.addEventListener('click', () => {
        langEn.setAttribute('aria-pressed', 'true');
        langBn.setAttribute('aria-pressed', 'false');
        if (window.TransifyI18n && window.TransifyI18n.setLanguage) {
          window.TransifyI18n.setLanguage('en');
        }
      });
      langBn.addEventListener('click', () => {
        langBn.setAttribute('aria-pressed', 'true');
        langEn.setAttribute('aria-pressed', 'false');
        if (window.TransifyI18n && window.TransifyI18n.setLanguage) {
          window.TransifyI18n.setLanguage('bn');
        }
      });
    }

    // Sign Language toggle (BdSL vs ASL)
    const bdslBtn = document.getElementById('lang-bdsl-btn');
    const aslBtn = document.getElementById('lang-asl-btn');
    if (bdslBtn) {
      bdslBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (window.SignPage && typeof window.SignPage.setLanguageMode === 'function') {
          window.SignPage.setLanguageMode('bdsl');
        } else if (window.setDefaultSignLang) {
          window.setDefaultSignLang('bdsl');
        }
      });
    }
    if (aslBtn) {
      aslBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (window.SignPage && typeof window.SignPage.setLanguageMode === 'function') {
          window.SignPage.setLanguageMode('asl');
        } else if (window.setDefaultSignLang) {
          window.setDefaultSignLang('asl');
        }
      });
    }

    // Camera header control buttons
    const stopCamBtn = document.getElementById('stop-camera-btn');
    if (stopCamBtn) {
      stopCamBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (window.SignPage && typeof window.SignPage.stopCamera === 'function') {
          window.SignPage.stopCamera();
        }
      });
    }

    const focusBtn = document.getElementById('toggle-roi-focus-btn');
    if (focusBtn) {
      focusBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (window.SignPage && typeof window.SignPage.setRoiPosition === 'function') {
          const nextPos = (window.SignPage.roiPosition === 'fullscreen') ? 'center' : 'fullscreen';
          window.SignPage.setRoiPosition(nextPos);
        }
      });
    }

    // User profile chip
    const userChip = document.getElementById('rail-user-chip');
    if (userChip) {
      userChip.addEventListener('click', () => {
        if (window.TransifyApp && window.TransifyApp.openAuthSheet) {
          window.TransifyApp.openAuthSheet('login');
        } else {
          const authModal = document.getElementById('auth-sheet-container');
          if (authModal) authModal.classList.add('active');
        }
      });
    }
  }

  // Update Page Title based on active route
  function updatePageTitle() {
    const titleEl = document.getElementById('ttl');
    if (!titleEl) return;
    const hash = (window.location.hash || '#home').replace('#', '').toLowerCase();
    const titles = {
      welcome: 'Welcome',
      home: 'Home',
      sign: 'Sign Translator',
      braille: 'Braille Studio',
      stt: 'Voice & Captions',
      voice: 'Voice & Captions',
      tts: 'Voice & Captions',
      phrases: 'Phrases',
      care: 'Transify Care',
      chat: 'AI Assistant',
      settings: 'Settings'
    };
    titleEl.textContent = titles[hash] || 'Transify';
  }

  // Wire Event Listeners
  window.addEventListener('hashchange', () => {
    updatePageTitle();
    onRouteEnter();
  });
  window.addEventListener('resize', updateNavIndicator);
  window.addEventListener('DOMContentLoaded', () => {
    initBootSequence();
    initReplayButton();
    initTopBarAndEmergency();
    setupSpotlight();
    initHeroSignCard();
    updatePageTitle();
    onRouteEnter();
    // Re-run spotlight on DOM changes
    new MutationObserver(() => setupSpotlight()).observe(document.body, { childList: true, subtree: true });
  });

  // 12. Hero Sign Hand Skeleton & Typing Loop
  const BRL_MAP = {a:'1',b:'12',c:'14',d:'145',e:'15',f:'124',g:'1245',h:'125',i:'24',j:'245',k:'13',l:'123',m:'134',n:'1345',o:'135',p:'1234',q:'12345',r:'1235',s:'234',t:'2345',u:'136',v:'1236',w:'2456',x:'1346',y:'13456',z:'1356'};
  function makeCell(dots) {
    const span = document.createElement('span');
    span.className = 'cell';
    for (let i = 1; i <= 6; i++) {
      const dot = document.createElement('i');
      if (dots.includes(i)) dot.className = 'on';
      span.appendChild(dot);
    }
    return span;
  }
  function renderBraille(el, text) {
    if (!el) return;
    el.textContent = '';
    for (const ch of text.toLowerCase()) {
      const d = BRL_MAP[ch] || '';
      el.appendChild(makeCell(d));
    }
  }

  function initHeroSignCard() {
    const hh = document.getElementById('hh');
    if (hh && !hh.children.length) {
      const PT = [[150,310],[118,285],[92,255],[78,225],[68,198],[125,205],[122,160],[120,128],[118,100],[150,200],[152,150],[153,115],[154,82],[175,205],[182,160],[186,128],[190,102],[197,222],[210,190],[220,166],[228,144]];
      const LN = [[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[17,18],[18,19],[19,20],[0,17]];
      const NS = 'http://www.w3.org/2000/svg';
      LN.forEach(([a, b]) => {
        const l = document.createElementNS(NS, 'line');
        l.setAttribute('x1', PT[a][0]); l.setAttribute('y1', PT[a][1]);
        l.setAttribute('x2', PT[b][0]); l.setAttribute('y2', PT[b][1]);
        hh.appendChild(l);
      });
      PT.forEach((p, k) => {
        const c = document.createElementNS(NS, 'circle');
        c.setAttribute('cx', p[0]); c.setAttribute('cy', p[1]); c.setAttribute('r', 5);
        c.style.setProperty('--k', k);
        hh.appendChild(c);
      });
    }

    const WORDS = [['Hello', 98.7], ['Help', 97.2], ['Thank you', 96.4], ['Doctor', 95.8]];
    let wIdx = 0;
    const hw = document.getElementById('hw');
    const hb = document.getElementById('hb');
    const hp = document.getElementById('hp');
    const hc = document.getElementById('hc');
    if (!hw) return;

    function heroLoop() {
      if (!hw) return;
      const [w, conf] = WORDS[wIdx++ % WORDS.length];
      hw.textContent = '';
      if (hb) hb.style.width = '0%';
      if (hp) hp.textContent = 'Reading sign';
      if (hc) renderBraille(hc, '');
      let charIdx = 0;
      const rmq = isReducedMotion();
      const stepInterval = rmq ? 0 : 120;
      const t = setInterval(() => {
        hw.textContent = w.slice(0, ++charIdx);
        if (charIdx >= w.length) {
          clearInterval(t);
          if (hb) hb.style.width = `${conf}%`;
          if (hp) hp.textContent = `${conf}% sure`;
          if (hc) renderBraille(hc, w.replace(/ /g, ''));
        }
      }, stepInterval);
    }

    heroLoop();
    setInterval(heroLoop, 5200);
  }

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(updateNavIndicator);
  }
})();
