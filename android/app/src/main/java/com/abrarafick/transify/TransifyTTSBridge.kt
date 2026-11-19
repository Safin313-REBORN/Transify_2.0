package com.abrarafick.transify

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import android.webkit.WebView
import org.json.JSONObject
import java.util.Locale

/**
 * Native Text-To-Speech (TTS) Bridge for Transify Android.
 *
 * Provides native speech synthesis for:
 * 1. Communication Hub and Phraseboard composed sentences.
 * 2. Braille translation text results.
 * 3. Speech-to-Text translation playback.
 * 4. Sign Language translation output.
 *
 * CRITICAL ARCHITECTURAL RULES:
 * - Audio must NEVER play automatically. Speech synthesis is only initiated
 *   upon explicit user action (button tap routed through WebMessageListener).
 * - Manages AudioManager audio focus appropriately (ducking/pausing background media).
 * - Multi-language support: English (en-US, en-GB) and Bengali (bn-BD, bn-IN).
 * - Complete lifecycle management: releases engine and abandons audio focus on pause/destroy.
 * - Dispatches onStart, onDone, and onError callbacks to the WebView layer for UI sync.
 */
class TransifyTTSBridge(
    private val context: Context,
    private val webView: WebView,
    private val isTrustedOrigin: (Uri) -> Boolean
) : TextToSpeech.OnInitListener {

    companion object {
        private const val TAG = "TransifyTTSBridge"
        const val MAX_TEXT_LENGTH = 5000
    }

    private val mainHandler = Handler(Looper.getMainLooper())
    private var tts: TextToSpeech? = null
    private var isInitialized = false
    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
    private var audioFocusRequest: AudioFocusRequest? = null

    private var pendingSpeakText: String? = null
    private var pendingSpeakLang: String? = null

    init {
        try {
            tts = TextToSpeech(context.applicationContext, this)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to instantiate Android TextToSpeech engine", e)
        }
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            isInitialized = true
            Log.i(TAG, "Native TextToSpeech engine initialized successfully")
            setupUtteranceListener()

            val text = pendingSpeakText
            val lang = pendingSpeakLang
            if (!text.isNullOrBlank()) {
                pendingSpeakText = null
                pendingSpeakLang = null
                speak(text, lang)
            }
        } else {
            isInitialized = false
            Log.e(TAG, "TextToSpeech initialization failed with status: $status")
            dispatchJsError("TTS initialization failed on this device")
        }
    }

    private fun setupUtteranceListener() {
        tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {
                Log.d(TAG, "TTS playback started: $utteranceId")
                dispatchJsStart(utteranceId.orEmpty())
            }

            override fun onDone(utteranceId: String?) {
                Log.d(TAG, "TTS playback completed: $utteranceId")
                abandonAudioFocus()
                dispatchJsDone(utteranceId.orEmpty())
            }

            @Deprecated("Deprecated in Java", ReplaceWith("onError(utteranceId, -1)"))
            override fun onError(utteranceId: String?) {
                Log.e(TAG, "TTS playback error for: $utteranceId")
                abandonAudioFocus()
                dispatchJsError("Speech synthesis playback error")
            }

            override fun onError(utteranceId: String?, errorCode: Int) {
                Log.e(TAG, "TTS playback error ($errorCode) for: $utteranceId")
                abandonAudioFocus()
                val message = when (errorCode) {
                    TextToSpeech.ERROR_SYNTHESIS -> "Synthesis error"
                    TextToSpeech.ERROR_SERVICE -> "Service error"
                    TextToSpeech.ERROR_OUTPUT -> "Audio output error"
                    TextToSpeech.ERROR_NETWORK -> "Network error"
                    TextToSpeech.ERROR_NOT_INSTALLED_YET -> "Language voice data not installed"
                    else -> "TTS Error code: $errorCode"
                }
                dispatchJsError(message)
            }
        })
    }

    /**
     * Primary speech invocation.
     * STRICT NO-AUTO-AUDIO: Must only be invoked following explicit user click/tap.
     */
    fun speak(text: String, lang: String? = "en-US") {
        mainHandler.post {
            if (!isOriginSecure()) {
                Log.w(TAG, "Blocked speak request from untrusted origin: ${webView.url}")
                dispatchJsError("Untrusted origin")
                return@post
            }

            val cleanText = text.trim()
            if (cleanText.isEmpty()) {
                Log.w(TAG, "Empty text provided to speak()")
                return@post
            }

            if (cleanText.length > MAX_TEXT_LENGTH) {
                Log.w(TAG, "Text exceeds maximum length of $MAX_TEXT_LENGTH characters")
                dispatchJsError("Text exceeds maximum allowed length")
                return@post
            }

            if (!isInitialized || tts == null) {
                Log.i(TAG, "TTS engine not yet ready; queueing single pending utterance")
                pendingSpeakText = cleanText
                pendingSpeakLang = lang
                return@post
            }

            // Resolve Locale
            val targetLocale = resolveLocale(lang)
            val langResult = tts?.setLanguage(targetLocale)
            if (langResult == TextToSpeech.LANG_MISSING_DATA || langResult == TextToSpeech.LANG_NOT_SUPPORTED) {
                Log.w(TAG, "Locale $targetLocale not fully supported or missing voice data (code $langResult). Falling back to default.")
                tts?.language = Locale.US
            }

            // Request Audio Focus
            if (!requestAudioFocus()) {
                Log.w(TAG, "Failed to obtain audio focus; proceeding with speech")
            }

            val utteranceId = "transify_tts_${System.currentTimeMillis()}"

            val params = Bundle().apply {
                putString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, utteranceId)
            }

            val result = tts?.speak(cleanText, TextToSpeech.QUEUE_FLUSH, params, utteranceId)
            if (result != TextToSpeech.SUCCESS) {
                Log.e(TAG, "tts.speak() failed with return code $result")
                abandonAudioFocus()
                dispatchJsError("Failed to start speech synthesis")
            } else {
                Log.i(TAG, "Started speech synthesis (utterance: $utteranceId, locale: $targetLocale)")
            }
        }
    }

    /**
     * Explicit stop method invoked when user presses stop or pauses.
     * Clears any pending queue and abandons audio focus immediately.
     */
    fun stop() {
        mainHandler.post {
            pendingSpeakText = null
            pendingSpeakLang = null
            try {
                if (tts?.isSpeaking == true) {
                    tts?.stop()
                    Log.i(TAG, "Explicitly stopped active TTS playback")
                }
            } catch (e: Exception) {
                Log.w(TAG, "Error stopping TTS", e)
            } finally {
                abandonAudioFocus()
                dispatchJsDone("stopped")
            }
        }
    }

    fun isSpeaking(): Boolean = tts?.isSpeaking == true

    private fun resolveLocale(langTag: String?): Locale {
        val tag = langTag?.trim().orEmpty()
        return when {
            tag.startsWith("bn", ignoreCase = true) -> {
                if (tag.contains("IN", ignoreCase = true)) Locale("bn", "IN") else Locale("bn", "BD")
            }
            tag.startsWith("en-GB", ignoreCase = true) -> Locale.UK
            tag.startsWith("en", ignoreCase = true) -> Locale.US
            tag.isNotBlank() -> Locale.forLanguageTag(tag)
            else -> Locale.US
        }
    }

    private fun requestAudioFocus(): Boolean {
        if (audioManager == null) return false
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val playbackAttributes = AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()

                audioFocusRequest = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                    .setAudioAttributes(playbackAttributes)
                    .setAcceptsDelayedFocusGain(false)
                    .setOnAudioFocusChangeListener { focusChange ->
                        if (focusChange == AudioManager.AUDIOFOCUS_LOSS ||
                            focusChange == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT
                        ) {
                            stop()
                        }
                    }
                    .build()

                audioFocusRequest?.let {
                    audioManager.requestAudioFocus(it) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
                } ?: false
            } else {
                @Suppress("DEPRECATION")
                audioManager.requestAudioFocus(
                    { focusChange ->
                        if (focusChange == AudioManager.AUDIOFOCUS_LOSS ||
                            focusChange == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT
                        ) {
                            stop()
                        }
                    },
                    AudioManager.STREAM_MUSIC,
                    AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK
                ) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error requesting audio focus", e)
            false
        }
    }

    private fun abandonAudioFocus() {
        if (audioManager == null) return
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                audioFocusRequest?.let { audioManager.abandonAudioFocusRequest(it) }
            } else {
                @Suppress("DEPRECATION")
                audioManager.abandonAudioFocus(null)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error abandoning audio focus", e)
        }
    }

    private fun isOriginSecure(): Boolean {
        val currentUrl = webView.url ?: return false
        val uri = try {
            Uri.parse(currentUrl)
        } catch (e: Exception) {
            return false
        }
        return isTrustedOrigin(uri)
    }

    private fun dispatchJsStart(utteranceId: String) {
        val quoted = JSONObject.quote(utteranceId)
        runOnWebView("window._transifyTTSCallback && window._transifyTTSCallback.onStart($quoted);")
    }

    private fun dispatchJsDone(utteranceId: String) {
        val quoted = JSONObject.quote(utteranceId)
        runOnWebView("window._transifyTTSCallback && window._transifyTTSCallback.onDone($quoted);")
    }

    private fun dispatchJsError(errorMessage: String) {
        val quoted = JSONObject.quote(errorMessage)
        runOnWebView("window._transifyTTSCallback && window._transifyTTSCallback.onError($quoted);")
    }

    private fun runOnWebView(script: String) {
        mainHandler.post {
            webView.evaluateJavascript(script, null)
        }
    }

    fun destroy() {
        try {
            stop()
            tts?.shutdown()
        } catch (e: Exception) {
            Log.w(TAG, "Error shutting down TTS engine", e)
        } finally {
            tts = null
            isInitialized = false
        }
    }
}
