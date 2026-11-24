#!/usr/bin/env python3
"""
Migrate all inline JavaScript and inline event handlers from src/frontend/index.html
to declarative data attributes and /static/boot.js for RC1.4.5 strict CSP compliance.
"""

import re
import sys

def migrate_index_html():
    with open('src/frontend/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Replace inline bootstrap script with <script src="/static/boot.js..."></script>
    inline_script_regex = re.compile(
        r'  <script>\s*// Bulletproof routing & auth initialization.*?  </script>',
        re.DOTALL
    )
    if inline_script_regex.search(content):
        content = inline_script_regex.sub(
            '  <script src="/static/boot.js?v=20261124_rc1_4_5"></script>',
            content
        )

    # 2. Migration rules for inline event handlers
    replacements = [
        # Navigation / Auth in welcome
        (r'onclick="window\.routeTo\(\'home\'\);\s*if\s*\(window\.TransifyApp\)\s*window\.TransifyApp\.handleDemoLogin\(\);"',
         'data-route="home" data-after-route="demo-login"'),
        (r'onclick="window\.routeTo\(\'home\'\);\s*if\s*\(window\.TransifyApp\)\s*window\.TransifyApp\.closeAuthSheet\(\);"',
         'data-route="home" data-after-route="close-auth"'),
        (r'onclick="window\.TransifyApp\.openAuthSheet\(\'login\'\)"',
         'data-action="open-auth" data-mode="login"'),
        (r'onclick="window\.TransifyApp\.openAuthSheet\(\'signup\'\)"',
         'data-action="open-auth" data-mode="signup"'),

        # EditorialController
        (r'onclick="EditorialController\.toggleEmergencyFlashMode\(\)"',
         'data-action="editorial-toggle-flash"'),
        (r'onchange="EditorialController\.setPhraseSpeed\(parseFloat\(this\.value\)\)"',
         'data-action="editorial-phrase-speed"'),
        (r'onclick="EditorialController\.exportPhrasesJSON\(\)"',
         'data-action="editorial-export-json"'),
        (r'onclick="EditorialController\.dismissEmergencyFlash\(\)"',
         'data-action="editorial-dismiss-flash"'),
        (r'onclick="event\.stopPropagation\(\)"',
         'data-action="stop-propagation"'),

        # BraillePage modes & samples
        (r'onclick="BraillePage\.switchMode\(\'scan\'\)"',
         'data-action="braille-switch-mode" data-mode="scan"'),
        (r'onclick="BraillePage\.switchMode\(\'generator\'\)"',
         'data-action="braille-switch-mode" data-mode="generator"'),
        (r'onclick="BraillePage\.switchMode\(\'reference\'\)"',
         'data-action="braille-switch-mode" data-mode="reference"'),
        (r'onclick="BraillePage\.loadSample\(\'([^\']+)\',\s*\'([^\']+)\'\)"',
         r'data-action="braille-load-sample" data-sample="\1" data-sample-name="\2"'),
        (r'onclick="BraillePage\.loadSample\(\'([^\']+)\'\)"',
         r'data-action="braille-load-sample" data-sample="\1"'),
        (r'onclick="BraillePage\.openCamera\(event\)"',
         'data-action="braille-open-camera"'),
        (r'onclick="BraillePage\.runIQACheck\(\)"',
         'data-action="braille-run-iqa"'),
        (r'onclick="BraillePage\.runTranslation\(\)"',
         'data-action="braille-run-translation"'),
        (r'onclick="BraillePage\.clearCellDots\(\)"',
         'data-action="braille-clear-cell-dots"'),
        (r'onclick="BraillePage\.speakActiveCell\(\)"',
         'data-action="braille-speak-active-cell"'),
        (r'onclick="BraillePage\.invertCellDots\(\)"',
         'data-action="braille-invert-cell-dots"'),
        (r'onclick="BraillePage\.randomCellPattern\(\)"',
         'data-action="braille-random-cell-pattern"'),
        (r'onclick="BraillePage\.copyUnicodeBraille\(\)"',
         'data-action="braille-copy-unicode"'),
        (r'onclick="BraillePage\.downloadBRF\(\)"',
         'data-action="braille-download-brf"'),
        (r'onclick="BraillePage\.loadGeneratorPreset\(\'([^\']+)\'\)"',
         r'data-action="braille-load-preset" data-preset="\1"'),
        (r'onclick="BraillePage\.clearGeneratorInput\(\)"',
         'data-action="braille-clear-generator-input"'),
        (r'oninput="BraillePage\.onGeneratorInput\(this\.value\)"',
         'data-action="braille-generator-input"'),
        (r'onclick="BraillePage\.speakGeneratorText\(\)"',
         'data-action="braille-speak-generator"'),
        (r'onclick="BraillePage\.copyGeneratorUnicode\(\)"',
         'data-action="braille-copy-generator-unicode"'),
        (r'onclick="BraillePage\.copyGeneratorDots\(\)"',
         'data-action="braille-copy-generator-dots"'),
        (r'onclick="BraillePage\.downloadGeneratorBRF\(\)"',
         'data-action="braille-download-generator-brf"'),
        (r'onclick="BraillePage\.filterReference\(\'([^\']+)\'\)"',
         r'data-action="braille-filter-reference" data-filter="\1"'),
        (r'onclick="BraillePage\.closeCamera\(\)"',
         'data-action="braille-close-camera"'),
        (r'onclick="BraillePage\.switchCameraFacing\(\)"',
         'data-action="braille-switch-camera-facing"'),
        (r'onclick="BraillePage\.captureCamera\(\)"',
         'data-action="braille-capture-camera"'),

        # TransifyVoiceStudio
        (r'onclick="TransifyVoiceStudio\.switchMode\(\'([^\']+)\'\)"',
         r'data-action="voice-switch-mode" data-mode="\1"'),
        (r'onclick="TransifyVoiceStudio\.loadSample\(\'([^\']+)\',\s*\'([^\']+)\'\)"',
         r'data-action="voice-load-sample" data-sample="\1" data-lang="\2"'),
        (r'onclick="TransifyVoiceStudio\.loadSample\(\'([^\']+)\'\)"',
         r'data-action="voice-load-sample" data-sample="\1"'),
        (r'onchange="TransifyVoiceStudio\.changeCaptionFont\(this\.value\)"',
         'data-action="voice-caption-font"'),
        (r'onclick="TransifyVoiceStudio\.downloadCaptionsTXT\(\)"',
         'data-action="voice-download-txt"'),
        (r'onclick="TransifyVoiceStudio\.downloadCaptionsSRT\(\)"',
         'data-action="voice-download-srt"'),
        (r'onclick="TransifyVoiceStudio\.bridgeToSign\(\)"',
         'data-action="voice-bridge-sign"'),
        (r'onclick="TransifyVoiceStudio\.bridgeToBraille\(\)"',
         'data-action="voice-bridge-braille"'),
        (r'onchange="TransifyVoiceStudio\.changeVoicePersona\(this\.value\)"',
         'data-action="voice-persona"'),
        (r'onclick="TransifyVoiceStudio\.setTTSSpeed\(([0-9\.]+)\)"',
         r'data-action="voice-set-tts-speed" data-speed="\1"'),
        (r'onclick="TransifyVoiceStudio\.insertTTSPhrase\(\'([^\']+)\'\)"',
         r'data-action="voice-insert-phrase" data-phrase="\1"'),
        (r'onclick="TransifyVoiceStudio\.pauseTTS\(\)"',
         'data-action="voice-pause-tts"'),
        (r'onclick="TransifyVoiceStudio\.copyTTSText\(\)"',
         'data-action="voice-copy-tts"'),
        (r'onclick="TransifyVoiceStudio\.syncActiveSpeechToBridge\(\)"',
         'data-action="voice-sync-bridge"'),

        # Window navigation
        (r'onclick="window\.routeTo\(\'([^\']+)\'\)"',
         r'data-route="\1"'),

        # Settings
        (r'onclick="window\.resetSettingsToDefaults\(\)"',
         'data-action="settings-reset-defaults"'),
        (r'onclick="window\.switchSettingsTab\(\'([^\']+)\'\)"',
         r'data-action="settings-tab" data-tab="\1"'),
        (r'onclick="window\.saveUserProfile\(\)"',
         'data-action="settings-save-profile"'),
        (r'onclick="window\.TransifyApp\.handleSettingsAuthAction\(\)"',
         'data-action="settings-auth-action"'),
        (r'onclick="window\.applyThemeGlobal\(\'([^\']+)\'\)"',
         r'data-action="settings-apply-theme" data-theme="\1"'),
        (r'onchange="window\.setAppLanguage\(this\.value\)"',
         'data-action="settings-language"'),
        (r'onclick="window\.applyFontScale\(\'([^\']+)\'\)"',
         r'data-action="settings-font-scale" data-scale="\1"'),
        (r'onchange="window\.toggleReduceMotion\(this\.checked\)"',
         'data-action="settings-reduce-motion"'),
        (r'onchange="window\.toggleFocusRings\(this\.checked\)"',
         'data-action="settings-focus-rings"'),
        (r'onclick="window\.setSpeechRate\(([0-9\.]+)\)"',
         r'data-action="settings-speech-rate" data-rate="\1"'),
        (r'onclick="window\.testVoicePreview\(\)"',
         'data-action="settings-test-voice"'),
        (r'onchange="window\.toggleAudioChimes\(this\.checked\)"',
         'data-action="settings-audio-chimes"'),
        (r'onclick="window\.setDefaultSignLang\(\'([^\']+)\'\)"',
         r'data-action="settings-sign-lang" data-lang="\1"'),
        (r'onclick="window\.setBrailleStandard\(\'([^\']+)\'\)"',
         r'data-action="settings-braille-standard" data-standard="\1"'),
        (r'onclick="window\.setConfidenceGate\(([0-9]+)\)"',
         r'data-action="settings-confidence-gate" data-gate="\1"'),
        (r'onclick="window\.exportSettingsData\(\)"',
         'data-action="settings-export-data"'),
        (r'onclick="window\.clearActivityHistory\(\)"',
         'data-action="settings-clear-history"'),
        (r'onclick="window\.copySystemDiagnostics\(\)"',
         'data-action="settings-copy-diagnostics"'),
        (r'onclick="window\.submitDeveloperFeedback\(\)"',
         'data-action="settings-submit-feedback"'),

        # Auth Sheet Controls
        (r'onclick="window\.TransifyApp\.closeAuthSheet\(\)"',
         'data-action="close-auth"'),
        (r'onsubmit="event\.preventDefault\(\);\s*window\.TransifyApp\.handleDirectLogin\(\);"',
         'data-action="auth-form-submit"'),
        (r'onclick="var p = document\.getElementById\(\'input-password\'\);\s*p\.type = \(p\.type === \'password\' \? \'text\' : \'password\'\);\s*this\.textContent = \(p\.type === \'password\' \? \'Show\' : \'Hide\'\);"',
         'data-action="auth-toggle-password"'),
        (r'onclick="event\.preventDefault\(\);\s*alert\(\'Password reset link sent to demo email\.\'\);"',
         'data-action="auth-forgot-password"'),
        (r'onclick="event\.preventDefault\(\);\s*document\.getElementById\(\'tab-signup\'\)\.click\(\);"',
         'data-action="auth-switch-tab" data-tab-id="tab-signup"'),
        (r'onclick="window\.TransifyApp\.handleProfileAuthAction\(\)"',
         'data-action="profile-auth-action"'),
    ]

    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content)

    # Verify if any inline on* attributes remain
    remaining = re.findall(r'\s(on[a-z]+)=([\"\'][^\"\']*[\"\'])', content, re.IGNORECASE)
    print(f"Remaining inline handlers after migration: {len(remaining)}")
    if remaining:
        for attr, val in remaining:
            print(f"  REMAINING: {attr}={val[:60]}")
        sys.exit(1)

    # Verify script tags
    scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE)
    non_empty = [s for s in scripts if s.strip()]
    print(f"Remaining non-empty inline script blocks: {len(non_empty)}")
    if non_empty:
        for s in non_empty:
            print("  REMAINING SCRIPT:", s[:100])
        sys.exit(1)

    with open('src/frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(content)

    print("SUCCESS: src/frontend/index.html fully migrated to 0 inline scripts and 0 inline event attributes!")

if __name__ == '__main__':
    migrate_index_html()
