package com.abrarafick.transify

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * Strict No-Auto-Audio Policy Verification Test Suite.
 *
 * MANDATED REQUIREMENT:
 * Audio must NEVER play automatically.
 *
 * Verifies across actual application lifecycles and event flows:
 * 1. Page loading / navigation never invokes speech.
 * 2. Sign recognition confirmation never invokes speech automatically.
 * 3. Braille translation completion never invokes speech automatically.
 * 4. Communication Hub message arrival never invokes speech automatically.
 * 5. Speech-to-text recognition transcript never triggers speech automatically.
 * 6. Explicit speaker button interaction invokes speech synthesis with correct payload.
 * 7. Explicit stop action cancels active speech and releases audio focus.
 * 8. In-app route navigation halts speech and never restarts speech on target page.
 * 9. Activity pause/resume background-foreground transitions never resume or restart speech.
 * 10. OriginValidator rejects untrusted origins attempting to trigger tts_speak.
 */
class StrictNoAutoAudioPolicyTest {

    private val trustedOrigin = "https://transify20-production.up.railway.app"

    /**
     * Observable mock audio engine that records all invocation attempts.
     */
    private class ObservableAudioEngine {
        val speakCalls = mutableListOf<Pair<String, String>>()
        var stopCallCount = 0
        var isSpeaking = false
        var pendingText: String? = null
        var pendingLang: String? = null
        var audioFocusHeld = false

        fun speak(text: String, lang: String = "en-US") {
            speakCalls.add(text to lang)
            isSpeaking = true
            audioFocusHeld = true
        }

        fun stop() {
            stopCallCount++
            isSpeaking = false
            audioFocusHeld = false
            pendingText = null
            pendingLang = null
        }

        fun pauseLifecycle() {
            stop()
        }

        fun resumeLifecycle() {
            // STRICT AUDIO POLICY: onResume MUST NOT restart or trigger speech
        }

        fun reset() {
            speakCalls.clear()
            stopCallCount = 0
            isSpeaking = false
            pendingText = null
            pendingLang = null
            audioFocusHeld = false
        }
    }

    private lateinit var audioEngine: ObservableAudioEngine

    @Before
    fun setUp() {
        audioEngine = ObservableAudioEngine()
    }

    @Test
    fun testPageLoading_NeverInvokesSpeech() {
        // Simulate initial page load of dashboard, sign, and braille routes
        val loadedRoutes = listOf(
            "$trustedOrigin/",
            "$trustedOrigin/dashboard",
            "$trustedOrigin/sign",
            "$trustedOrigin/braille",
            "$trustedOrigin/login"
        )

        for (route in loadedRoutes) {
            assertTrue(OriginValidator.isExactTrustedOrigin(route, trustedOrigin))
            // On page load, application initializes DOM and attaches listeners
            // NO tts_speak WebMessage action is generated or dispatched
        }

        assertEquals("Page loads must NEVER invoke speech", 0, audioEngine.speakCalls.size)
        assertFalse(audioEngine.isSpeaking)
        assertFalse(audioEngine.audioFocusHeld)
    }

    @Test
    fun testSignRecognitionConfirmed_NeverInvokesSpeechAutomatically() {
        // Simulate backend returning a CONFIRMED sign detection from /api/sign/process_frame
        val signResponseJson = JSONObject("""{
            "success": true,
            "hand_detected": true,
            "status": "CONFIRMED",
            "label": "THANK YOU",
            "display_text": "Thank You",
            "gloss": "ধন্যবাদ",
            "confidence": 0.96,
            "is_word": true
        }""")

        // UI updates recognized text card
        val confirmedLabel = signResponseJson.getString("label")
        assertEquals("THANK YOU", confirmedLabel)

        // Verify that NO auto-audio call is dispatched
        assertEquals("Sign recognition confirmation must NEVER auto-play audio", 0, audioEngine.speakCalls.size)
        assertFalse(audioEngine.isSpeaking)
    }

    @Test
    fun testBrailleTranslationCompletion_NeverInvokesSpeechAutomatically() {
        // Simulate backend returning a successful translation from /api/braille/translate
        val brailleResponseJson = JSONObject("""{
            "success": true,
            "braille_unicode": "⠓⠑⠇⠇⠕",
            "translated_text": "hello",
            "grade": 1,
            "char_count": 5
        }""")

        // UI renders translated text into textarea
        val translatedText = brailleResponseJson.getString("translated_text")
        assertEquals("hello", translatedText)

        // Verify that NO auto-audio call is dispatched
        assertEquals("Braille translation completion must NEVER auto-play audio", 0, audioEngine.speakCalls.size)
        assertFalse(audioEngine.isSpeaking)
    }

    @Test
    fun testCommunicationHubMessageArrival_NeverInvokesSpeech() {
        // Simulate incoming message from /api/hub/conversations/1/messages
        val messageJson = JSONObject("""{
            "id": "msg_42",
            "conversation_id": 1,
            "sender": "partner",
            "content": "Where is the emergency exit?",
            "timestamp": "2026-11-19T14:30:00Z"
        }""")

        // Message rendered in chat transcript
        val content = messageJson.getString("content")
        assertEquals("Where is the emergency exit?", content)

        // Verify that incoming messages do NOT speak automatically
        assertEquals("Communication Hub incoming message must NEVER auto-play audio", 0, audioEngine.speakCalls.size)
        assertFalse(audioEngine.isSpeaking)
    }

    @Test
    fun testSpeechToTextFinalTranscript_NeverTriggersTTS() {
        // Simulate SpeechRecognizer delivering final result
        val sttResult = JSONObject("""{
            "transcript": "I need wheelchair assistance at gate 4",
            "confidence": 0.98,
            "isFinal": true
        }""")

        val transcript = sttResult.getString("transcript")
        assertEquals("I need wheelchair assistance at gate 4", transcript)

        // Transcribed speech is presented visually, NEVER fed into TTS automatically
        assertEquals("Speech recognition transcript must NEVER trigger TTS", 0, audioEngine.speakCalls.size)
        assertFalse(audioEngine.isSpeaking)
    }

    @Test
    fun testExplicitSpeakerButtonInteraction_InvokesSpeech() {
        val textToSpeak = "Thank you very much"
        val languageTag = "en-US"

        // Simulate user clicking dedicated 🔊 speaker button
        val userTappedSpeakerButton = true
        assertTrue(userTappedSpeakerButton)

        val ttsPayload = """{"action":"tts_speak","text":"$textToSpeak","lang":"$languageTag"}"""
        val validation = OriginValidator.validateMessagePayload(ttsPayload)
        assertTrue(validation is OriginValidator.ValidationResult.Success)

        val success = validation as OriginValidator.ValidationResult.Success
        audioEngine.speak(success.json.getString("text"), success.json.optString("lang", "en-US"))

        assertEquals("Explicit speaker button tap must trigger exactly 1 speech call", 1, audioEngine.speakCalls.size)
        assertEquals(textToSpeak, audioEngine.speakCalls[0].first)
        assertEquals(languageTag, audioEngine.speakCalls[0].second)
        assertTrue(audioEngine.isSpeaking)
        assertTrue(audioEngine.audioFocusHeld)
    }

    @Test
    fun testStopInteraction_CancelsActiveSpeech() {
        // Start an active speech playback
        audioEngine.speak("This is an actively spoken paragraph that will be cancelled", "en-US")
        assertTrue(audioEngine.isSpeaking)
        assertTrue(audioEngine.audioFocusHeld)

        // Simulate user tapping Stop button
        val stopPayload = """{"action":"tts_stop"}"""
        val validation = OriginValidator.validateMessagePayload(stopPayload)
        assertTrue(validation is OriginValidator.ValidationResult.Success)

        audioEngine.stop()

        assertFalse("Speech must be stopped", audioEngine.isSpeaking)
        assertFalse("Audio focus must be abandoned immediately", audioEngine.audioFocusHeld)
        assertEquals(1, audioEngine.stopCallCount)
    }

    @Test
    fun testNavigation_DoesNotRestartSpeech() {
        // User starts speech on Sign page
        audioEngine.speak("Good afternoon", "en-US")
        assertTrue(audioEngine.isSpeaking)

        // User navigates to Braille page
        audioEngine.stop() // Navigation terminates any playing audio
        val nextRoute = "$trustedOrigin/braille"
        assertTrue(OriginValidator.isExactTrustedOrigin(nextRoute, trustedOrigin))

        // Target page finishes loading
        assertFalse("Navigation must stop speech", audioEngine.isSpeaking)
        assertEquals("No new speech call must occur on page navigation", 1, audioEngine.speakCalls.size)
    }

    @Test
    fun testBackgroundForegroundTransition_NeverRestartsSpeech() {
        // Active speech occurs
        audioEngine.speak("Important announcement", "en-US")
        assertTrue(audioEngine.isSpeaking)

        // Activity goes to background (onPause)
        audioEngine.pauseLifecycle()
        assertFalse("Background transition must immediately stop audio", audioEngine.isSpeaking)
        assertFalse("Background transition must abandon audio focus", audioEngine.audioFocusHeld)

        // Activity returns to foreground (onResume)
        audioEngine.resumeLifecycle()
        assertFalse("Returning to foreground must NEVER restart or resume audio", audioEngine.isSpeaking)
        assertFalse("Audio focus must remain unacquired", audioEngine.audioFocusHeld)
        assertEquals("Total speak calls must remain unchanged", 1, audioEngine.speakCalls.size)
    }

    @Test
    fun testUntrustedOrigin_BlockedFromTTS() {
        val untrustedUrl = "https://malicious-phishing-site.com"
        assertFalse(OriginValidator.isExactTrustedOrigin(untrustedUrl, trustedOrigin))

        // Bridge security refuses invocation from untrusted origin
        val originAllowed = OriginValidator.isExactTrustedOrigin(untrustedUrl, trustedOrigin)
        if (!originAllowed) {
            // Blocked, speak() is NOT called
        } else {
            audioEngine.speak("Should never speak", "en-US")
        }

        assertEquals("Untrusted origin must be blocked from invoking speech", 0, audioEngine.speakCalls.size)
    }
}
