package com.abrarafick.transify

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log
import android.webkit.JavascriptInterface
import android.webkit.WebView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject

/**
 * Native Speech Recognition Bridge for Android WebView.
 *
 * Android System WebView does not provide a native window.SpeechRecognition implementation.
 * This bridge connects the web interface to Android's native SpeechRecognizer service,
 * supporting:
 * 1. True continuous recognition (restarting recognizer between utterances while active).
 * 2. Real interim/partial transcripts and final results.
 * 3. Multi-language support (English "en-US", Bengali "bn-BD"/"bn-IN", etc.).
 * 4. Genuine confidence reporting (no fabricated 0.95/0.98 numbers).
 * 5. Audio permission resumption upon grant.
 * 6. Clean lifecycle and speech resource teardown.
 */
class TransifySpeechBridge(
    private val activity: MainActivity,
    private val webView: WebView
) {
    companion object {
        private const val TAG = "TransifySpeechBridge"
        const val INTERFACE_NAME = "TransifySpeechBridge"

        val POLYFILL_JS = """
            (function() {
                if (window.SpeechRecognition || window.webkitSpeechRecognition) {
                    return; // Native browser speech already available
                }
                console.log("[Transify] Initializing Android WebView SpeechRecognition bridge...");

                class WebViewSpeechRecognition {
                    constructor() {
                        this.continuous = false;
                        this.interimResults = false;
                        this.lang = 'en-US';
                        this.maxAlternatives = 1;
                        this.onstart = null;
                        this.onresult = null;
                        this.onerror = null;
                        this.onend = null;
                        this._id = 'stt_' + Math.random().toString(36).substring(2, 9);
                        window._transifyActiveSTT = this;
                    }

                    start() {
                        const payload = JSON.stringify({
                            action: 'stt_start',
                            lang: this.lang || 'en-US',
                            interim: !!this.interimResults,
                            continuous: !!this.continuous
                        });

                        if (window.transifyNativeBridge && typeof window.transifyNativeBridge.postMessage === 'function') {
                            window.transifyNativeBridge.postMessage(payload);
                        } else if (window.TransifySpeechBridge) {
                            window.TransifySpeechBridge.startListening(this.lang, this.interimResults, this.continuous);
                        } else {
                            if (this.onerror) {
                                this.onerror({ error: 'service-not-allowed', message: 'Native bridge unavailable' });
                            }
                        }
                    }

                    stop() {
                        const payload = JSON.stringify({ action: 'stt_stop' });
                        if (window.transifyNativeBridge && typeof window.transifyNativeBridge.postMessage === 'function') {
                            window.transifyNativeBridge.postMessage(payload);
                        } else if (window.TransifySpeechBridge) {
                            window.TransifySpeechBridge.stopListening();
                        }
                    }

                    abort() {
                        const payload = JSON.stringify({ action: 'stt_abort' });
                        if (window.transifyNativeBridge && typeof window.transifyNativeBridge.postMessage === 'function') {
                            window.transifyNativeBridge.postMessage(payload);
                        } else if (window.TransifySpeechBridge) {
                            window.TransifySpeechBridge.abortListening();
                        }
                    }
                }

                // Global callbacks invoked by native Android Kotlin code
                window._transifySpeechCallback = {
                    onStart: function() {
                        const rec = window._transifyActiveSTT;
                        if (rec && typeof rec.onstart === 'function') {
                            rec.onstart(new Event('start'));
                        }
                    },
                    onResult: function(resultsJson) {
                        const rec = window._transifyActiveSTT;
                        if (!rec || typeof rec.onresult !== 'function') return;
                        try {
                            const parsed = JSON.parse(resultsJson);
                            const event = {
                                resultIndex: parsed.resultIndex || 0,
                                results: parsed.results.map(r => {
                                    const alt = [{
                                        transcript: r.transcript,
                                        confidence: (r.confidence !== null && r.confidence !== undefined) ? r.confidence : 1.0
                                    }];
                                    alt.isFinal = !!r.isFinal;
                                    return alt;
                                })
                            };
                            rec.onresult(event);
                        } catch(e) {
                            console.error("[Transify] Error parsing STT result:", e);
                        }
                    },
                    onError: function(errCode) {
                        const rec = window._transifyActiveSTT;
                        if (rec && typeof rec.onerror === 'function') {
                            let errorName = 'network';
                            if (errCode === 'not-allowed') errorName = 'not-allowed';
                            else if (errCode === 'no-speech') errorName = 'no-speech';
                            else if (errCode === 'audio-capture') errorName = 'audio-capture';
                            rec.onerror({ error: errorName });
                        }
                    },
                    onEnd: function() {
                        const rec = window._transifyActiveSTT;
                        if (rec && typeof rec.onend === 'function') {
                            rec.onend(new Event('end'));
                        }
                    }
                };

                // Intercept download anchors with blob URLs to ensure reliable Android saving
                document.addEventListener('click', function(e) {
                    const target = e.target.closest('a[download]');
                    if (target && target.href && target.href.startsWith('blob:')) {
                        const filename = target.getAttribute('download') || 'Transify_Export.txt';
                        fetch(target.href)
                            .then(res => res.blob())
                            .then(blob => {
                                const reader = new FileReader();
                                reader.onloadend = function() {
                                    const base64Data = reader.result;
                                    const payload = JSON.stringify({
                                        action: 'download_blob',
                                        filename: filename,
                                        mimeType: blob.type || 'text/plain',
                                        data: base64Data
                                    });
                                    if (window.transifyNativeBridge && typeof window.transifyNativeBridge.postMessage === 'function') {
                                        window.transifyNativeBridge.postMessage(payload);
                                    } else if (window.TransifyDownloadBridge) {
                                        window.TransifyDownloadBridge.saveDataUri(base64Data, blob.type || 'text/plain', filename);
                                    }
                                };
                                reader.readAsDataURL(blob);
                            })
                            .catch(err => {
                                console.error("[Transify] Blob download intercept error:", err);
                            });
                    }
                }, true);

                window.SpeechRecognition = WebViewSpeechRecognition;
                window.webkitSpeechRecognition = WebViewSpeechRecognition;
                console.log("[Transify] Web Speech API polyfill registered successfully.");
            })();
        """.trimIndent()
    }

    private val mainHandler = Handler(Looper.getMainLooper())
    private var speechRecognizer: SpeechRecognizer? = null

    private var isListening = false
    private var isContinuous = false
    private var interimResults = true
    private var currentLang = "en-US"
    private var consecutiveErrorCount = 0

    private var pendingStartRequest: Boolean = false

    private fun isOriginSecure(): Boolean {
        val currentUrl = webView.url ?: return false
        val uri = try {
            Uri.parse(currentUrl)
        } catch (e: Exception) {
            return false
        }
        return activity.isTrustedOrigin(uri)
    }

    /**
     * Primary entry point invoked via WebMessageListener or fallback JavascriptInterface.
     */
    @JavascriptInterface
    fun startListening(lang: String?, interim: Boolean, continuous: Boolean) {
        mainHandler.post {
            if (!isOriginSecure()) {
                Log.w(TAG, "Blocked startListening from untrusted URL: ${webView.url}")
                dispatchJsError("not-allowed")
                return@post
            }

            currentLang = if (lang.isNullOrBlank()) "en-US" else lang.trim()
            interimResults = interim
            isContinuous = continuous
            consecutiveErrorCount = 0

            if (ContextCompat.checkSelfPermission(activity, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED
            ) {
                pendingStartRequest = true
                ActivityCompat.requestPermissions(
                    activity,
                    arrayOf(Manifest.permission.RECORD_AUDIO),
                    MainActivity.REQ_PERM_AUDIO
                )
                return@post
            }

            pendingStartRequest = false
            startRecognizerSession()
        }
    }

    /**
     * Called by MainActivity when RECORD_AUDIO permission has been granted at runtime.
     */
    fun resumePendingStart() {
        mainHandler.post {
            if (pendingStartRequest) {
                pendingStartRequest = false
                Log.i(TAG, "Resuming pending speech recognition request after audio permission grant")
                startRecognizerSession()
            }
        }
    }

    @JavascriptInterface
    fun stopListening() {
        mainHandler.post {
            if (!isOriginSecure()) return@post
            Log.d(TAG, "Explicit stop requested by web client")
            isContinuous = false
            isListening = false
            pendingStartRequest = false
            try {
                speechRecognizer?.stopListening()
            } catch (e: Exception) {
                Log.w(TAG, "Error stopping recognizer", e)
            }
        }
    }

    @JavascriptInterface
    fun abortListening() {
        mainHandler.post {
            if (!isOriginSecure()) return@post
            Log.d(TAG, "Explicit abort requested by web client")
            isContinuous = false
            isListening = false
            pendingStartRequest = false
            try {
                speechRecognizer?.cancel()
            } catch (e: Exception) {
                Log.w(TAG, "Error cancelling recognizer", e)
            }
            dispatchJsEnd()
        }
    }

    private fun startRecognizerSession() {
        if (!SpeechRecognizer.isRecognitionAvailable(activity)) {
            Log.e(TAG, "SpeechRecognizer is not available on this device")
            dispatchJsError("network")
            return
        }

        try {
            cleanupRecognizer()

            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(activity).apply {
                setRecognitionListener(createListener())
            }

            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
                )
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, currentLang)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, currentLang)
                putExtra(RecognizerIntent.EXTRA_ONLY_RETURN_LANGUAGE_PREFERENCE, true)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, interimResults)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, activity.packageName)
            }

            isListening = true
            speechRecognizer?.startListening(intent)
            dispatchJsStart()
            Log.d(TAG, "Started speech recognition session (lang=$currentLang, continuous=$isContinuous)")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start speech recognizer session", e)
            isListening = false
            dispatchJsError("network")
            dispatchJsEnd()
        }
    }

    private fun createListener(): RecognitionListener {
        return object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                Log.d(TAG, "SpeechRecognizer ready for input (lang: $currentLang)")
            }

            override fun onBeginningOfSpeech() {
                Log.d(TAG, "Beginning of speech detected")
            }

            override fun onRmsChanged(rmsdB: Float) {}

            override fun onBufferReceived(buffer: ByteArray?) {}

            override fun onEndOfSpeech() {
                Log.d(TAG, "End of utterance detected")
            }

            override fun onError(error: Int) {
                val errorName = when (error) {
                    SpeechRecognizer.ERROR_AUDIO -> "audio-capture"
                    SpeechRecognizer.ERROR_CLIENT -> "network"
                    SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "not-allowed"
                    SpeechRecognizer.ERROR_NETWORK, SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "network"
                    SpeechRecognizer.ERROR_NO_MATCH, SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "no-speech"
                    else -> "network"
                }

                Log.w(TAG, "Speech recognition error: $error ($errorName)")
                dispatchJsError(errorName)

                // Continuous recognition error recovery
                if (isContinuous && (error == SpeechRecognizer.ERROR_NO_MATCH || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT)) {
                    consecutiveErrorCount++
                    if (consecutiveErrorCount < 3 && isListening) {
                        Log.d(TAG, "Continuous mode: Scheduling recognizer restart after timeout/no-match (retry $consecutiveErrorCount)")
                        mainHandler.postDelayed({
                            if (isContinuous && isListening) {
                                startRecognizerSession()
                            }
                        }, 250)
                        return
                    }
                }

                isListening = false
                dispatchJsEnd()
            }

            override fun onResults(results: Bundle?) {
                consecutiveErrorCount = 0
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!matches.isNullOrEmpty()) {
                    val text = matches[0]
                    val scores = results.getFloatArray(SpeechRecognizer.CONFIDENCE_SCORES)
                    val confidence = if (scores != null && scores.isNotEmpty() && scores[0] >= 0f) scores[0] else null
                    dispatchJsResult(text, isFinal = true, confidence = confidence)
                }

                // If continuous mode is enabled and recognition was not explicitly stopped, restart for next utterance
                if (isContinuous && isListening) {
                    Log.d(TAG, "Continuous mode active: Restarting listener for next utterance")
                    mainHandler.postDelayed({
                        if (isContinuous && isListening) {
                            startRecognizerSession()
                        }
                    }, 100)
                } else {
                    isListening = false
                    dispatchJsEnd()
                }
            }

            override fun onPartialResults(partialResults: Bundle?) {
                val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (!matches.isNullOrEmpty()) {
                    val text = matches[0]
                    dispatchJsResult(text, isFinal = false, confidence = null)
                }
            }

            override fun onEvent(eventType: Int, params: Bundle?) {}
        }
    }

    private fun dispatchJsStart() {
        runOnWebView("window._transifySpeechCallback && window._transifySpeechCallback.onStart();")
    }

    private fun dispatchJsResult(transcript: String, isFinal: Boolean, confidence: Float?) {
        try {
            val json = JSONObject().apply {
                put("resultIndex", 0)
                val resultsArray = JSONArray().apply {
                    put(JSONObject().apply {
                        put("transcript", transcript)
                        if (confidence != null) {
                            put("confidence", confidence.toDouble())
                        }
                        put("isFinal", isFinal)
                    })
                }
                put("results", resultsArray)
            }
            val quoted = JSONObject.quote(json.toString())
            runOnWebView("window._transifySpeechCallback && window._transifySpeechCallback.onResult($quoted);")
        } catch (e: Exception) {
            Log.e(TAG, "Error formatting STT JSON result", e)
        }
    }

    private fun dispatchJsError(errorName: String) {
        runOnWebView("window._transifySpeechCallback && window._transifySpeechCallback.onError('$errorName');")
    }

    private fun dispatchJsEnd() {
        runOnWebView("window._transifySpeechCallback && window._transifySpeechCallback.onEnd();")
    }

    private fun runOnWebView(script: String) {
        mainHandler.post {
            webView.evaluateJavascript(script, null)
        }
    }

    private fun cleanupRecognizer() {
        try {
            speechRecognizer?.destroy()
        } catch (e: Exception) {
            Log.w(TAG, "Error cleaning up previous speech recognizer", e)
        }
        speechRecognizer = null
    }

    fun destroy() {
        isListening = false
        isContinuous = false
        pendingStartRequest = false
        cleanupRecognizer()
    }
}
