package com.abrarafick.transify

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.util.Log
import android.view.View
import android.webkit.CookieManager
import android.webkit.PermissionRequest
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.webkit.JavaScriptReplyProxy
import androidx.webkit.WebMessageCompat
import androidx.webkit.WebViewCompat
import androidx.webkit.WebViewFeature
import com.abrarafick.transify.databinding.ActivityMainBinding
import java.io.File

/**
 * MainActivity — Native Full-Screen Android Host for Transify.
 *
 * Hosts the exact Transify web application without UI alteration.
 * Connects native mobile sensors:
 * - Camera for Sign Language Translator (MediaPipe / HaGRID ASL)
 * - Microphone for Speech-to-Text (Native SpeechRecognizer with continuous loop)
 * - Storage for Braille image uploads and translation downloads
 *
 * Enforces strict HTTPS origin security, origin-restricted WebMessageListener,
 * strict SSL certificate validation, and clean lifecycle management.
 */
class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "TransifyMainActivity"
        const val REQ_PERM_AUDIO = 2001
        private const val PREFS_NAME = "transify_native_prefs"
        private const val KEY_CUSTOM_URL = "custom_base_url"

        fun isPlaceholderUrl(url: String): Boolean = OriginValidator.isPlaceholderUrl(url)

        fun isValidTargetUrl(url: String): Boolean =
            OriginValidator.isValidTargetUrl(url, allowHttpLocal = BuildConfig.DEBUG)
    }

    private lateinit var binding: ActivityMainBinding
    private lateinit var prefs: SharedPreferences

    private var activeBaseUrl: String = ""
    private var trustedScheme: String = "https"
    private var trustedHost: String = ""
    private var trustedPort: Int = 443

    private var pendingPermissionRequest: PermissionRequest? = null
    private var pendingFileChooserCallback: ValueCallback<Array<Uri>>? = null

    private lateinit var speechBridge: TransifySpeechBridge
    private lateinit var downloadBridge: TransifyDownloadBridge
    private lateinit var ttsBridge: TransifyTTSBridge
    private lateinit var networkMonitor: NetworkMonitor

    private var cameraCaptureUri: Uri? = null
    private var lastBackPressTime: Long = 0L

    // Runtime permission launcher for Camera and Audio
    private val mediaPermissionLauncher: ActivityResultLauncher<Array<String>> =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { _ ->
            val cameraGranted = ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.CAMERA
            ) == PackageManager.PERMISSION_GRANTED

            val audioGranted = ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.RECORD_AUDIO
            ) == PackageManager.PERMISSION_GRANTED

            Log.i(TAG, "Runtime permissions evaluated: Camera=$cameraGranted, Audio=$audioGranted")

            if (audioGranted) {
                speechBridge.resumePendingStart()
            }

            val request = pendingPermissionRequest
            if (request != null) {
                val requested = request.resources.toList()
                val grantedResources = mutableListOf<String>()

                if (requested.contains(PermissionRequest.RESOURCE_VIDEO_CAPTURE) && cameraGranted) {
                    grantedResources.add(PermissionRequest.RESOURCE_VIDEO_CAPTURE)
                }
                if (requested.contains(PermissionRequest.RESOURCE_AUDIO_CAPTURE) && audioGranted) {
                    grantedResources.add(PermissionRequest.RESOURCE_AUDIO_CAPTURE)
                }

                if (grantedResources.isNotEmpty()) {
                    Log.i(TAG, "Granting WebView hardware resources: $grantedResources")
                    request.grant(grantedResources.toTypedArray())
                } else {
                    Log.w(TAG, "Denying WebView permission request: Required system permissions not granted")
                    request.deny()
                }
                pendingPermissionRequest = null
            }
        }

    // File chooser launcher for Braille image uploads (supporting gallery and direct camera capture)
    private val fileChooserLauncher: ActivityResultLauncher<Intent> =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            val callback = pendingFileChooserCallback
            pendingFileChooserCallback = null

            if (callback == null) return@registerForActivityResult

            if (result.resultCode == Activity.RESULT_OK) {
                val dataIntent = result.data
                val clipData = dataIntent?.clipData
                val singleUri = dataIntent?.data

                val results: Array<Uri>? = when {
                    singleUri != null -> arrayOf(singleUri)
                    clipData != null && clipData.itemCount > 0 -> {
                        Array(clipData.itemCount) { i -> clipData.getItemAt(i).uri }
                    }
                    cameraCaptureUri != null -> {
                        val uri = cameraCaptureUri
                        cameraCaptureUri = null
                        if (uri != null) arrayOf(uri) else null
                    }
                    else -> null
                }

                callback.onReceiveValue(results)
                Log.d(TAG, "File chooser received: ${results?.joinToString()}")
            } else {
                Log.d(TAG, "File chooser canceled by user")
                cameraCaptureUri = null
                callback.onReceiveValue(null)
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

        setupBackNavigation()
        setupSwipeRefresh()
        setupWebView()
        setupErrorViewActions()

        resolveAndLoadTargetUrl()
    }

    private fun setupBackNavigation() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (binding.errorView.visibility == View.VISIBLE || binding.missingConfigView.visibility == View.VISIBLE) {
                    finish()
                } else if (binding.webView.canGoBack()) {
                    binding.webView.goBack()
                } else {
                    val currentTime = System.currentTimeMillis()
                    if (currentTime - lastBackPressTime < 2000) {
                        finish()
                    } else {
                        lastBackPressTime = currentTime
                        Toast.makeText(
                            this@MainActivity,
                            getString(R.string.toast_back_exit),
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }
            }
        })
    }

    private fun setupSwipeRefresh() {
        binding.swipeRefresh.setColorSchemeResources(
            R.color.brand_primary,
            R.color.brand_secondary
        )
        binding.swipeRefresh.setOnRefreshListener {
            binding.webView.reload()
        }
    }

    private fun setupWebView() {
        val webView = binding.webView
        val settings = webView.settings

        // JavaScript & DOM Storage
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true

        // Viewport & Responsive Scaling
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = true
        settings.displayZoomControls = false
        settings.builtInZoomControls = false

        // Media Playback Gesture Requirement
        // Enforce user gesture requirement to block unprompted autoplay audio elements.
        // Muted camera video preview (<video autoplay muted playsinline>) from getUserMedia()
        // triggered by the user's explicit "Start Camera" tap continues to function properly.
        settings.mediaPlaybackRequiresUserGesture = true

        // File and Content Access Security
        // Keep file:// filesystem access disabled, but allow content:// access for Gallery / File Picker uploads
        settings.allowFileAccess = false
        settings.allowContentAccess = true
        @Suppress("DEPRECATION")
        settings.allowFileAccessFromFileURLs = false
        @Suppress("DEPRECATION")
        settings.allowUniversalAccessFromFileURLs = false
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
        settings.cacheMode = WebSettings.LOAD_DEFAULT

        // Cookie Management
        val cookieManager = CookieManager.getInstance()
        cookieManager.setAcceptCookie(true)
        cookieManager.setAcceptThirdPartyCookies(webView, true)

        // Native Bridges
        speechBridge = TransifySpeechBridge(this, webView)
        downloadBridge = TransifyDownloadBridge(this, webView)
        ttsBridge = TransifyTTSBridge(this, webView) { uri -> isTrustedOrigin(uri) }
        networkMonitor = NetworkMonitor(this)

        webView.setDownloadListener(downloadBridge)

        // WebChromeClient
        webView.webChromeClient = TransifyWebChromeClient(
            activity = this,
            isTrustedOrigin = { uri -> isTrustedOrigin(uri) },
            onProgressChanged = { progress ->
                binding.progressBar.progress = progress
                binding.progressBar.visibility = if (progress in 1..99) View.VISIBLE else View.GONE
            }
        )
    }

    private fun setupWebMessageBridge(targetOrigin: String) {
        val webView = binding.webView
        val originRule = OriginValidator.getOriginRule(targetOrigin)

        if (originRule.isNotEmpty() && WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            Log.i(TAG, "Configuring AndroidX WebMessageListener for origin rule: $originRule")
            try {
                WebViewCompat.addWebMessageListener(
                    webView,
                    "transifyNativeBridge",
                    setOf(originRule)
                ) { _, message: WebMessageCompat, sourceOrigin: Uri, isMainFrame: Boolean, _: JavaScriptReplyProxy ->
                    handleWebMessage(message, sourceOrigin, isMainFrame)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error adding WebMessageListener; privileged native operations disabled for security", e)
                showUnsupportedBridgeNotice()
            }
        } else {
            Log.w(TAG, "WEB_MESSAGE_LISTENER not supported on this WebView provider; privileged native operations disabled for security")
            showUnsupportedBridgeNotice()
        }
    }

    private fun showUnsupportedBridgeNotice() {
        runOnUiThread {
            android.widget.Toast.makeText(
                this,
                "Please update Android System WebView to enable speech recognition and download features.",
                android.widget.Toast.LENGTH_LONG
            ).show()
        }
    }

    private fun handleWebMessage(message: WebMessageCompat, sourceOrigin: Uri, isMainFrame: Boolean) {
        // Security Rule 1: Reject messages originating from iframes
        if (!isMainFrame) {
            Log.w(TAG, "Rejected bridge message: Not from main frame")
            return
        }

        // Security Rule 2: Verify source origin matches exact trusted origin
        if (!isTrustedOrigin(sourceOrigin)) {
            Log.w(TAG, "Rejected bridge message from untrusted origin: $sourceOrigin")
            return
        }

        val rawData = message.data ?: return

        // Security Rule 3: Validate action, parameters, and payload size
        when (val result = OriginValidator.validateMessagePayload(rawData)) {
            is OriginValidator.ValidationResult.Error -> {
                Log.e(TAG, "Rejected invalid bridge message: ${result.reason}")
            }
            is OriginValidator.ValidationResult.Success -> {
                val json = result.json
                when (result.action) {
                    "stt_start" -> {
                        val lang = json.optString("lang", "en-US")
                        val interim = json.optBoolean("interim", true)
                        val continuous = json.optBoolean("continuous", true)
                        speechBridge.startListening(lang, interim, continuous)
                    }
                    "stt_stop" -> {
                        speechBridge.stopListening()
                    }
                    "stt_abort" -> {
                        speechBridge.abortListening()
                    }
                    "download_blob" -> {
                        val filename = json.optString("filename", "Transify_Export.txt")
                        val mimeType = json.optString("mimeType", "text/plain")
                        val data = json.optString("data", "")
                        downloadBridge.saveDataUri(data, mimeType, filename)
                    }
                    "tts_speak" -> {
                        val text = json.optString("text", "")
                        val lang = json.optString("lang", "en-US")
                        ttsBridge.speak(text, lang)
                    }
                    "tts_stop" -> {
                        ttsBridge.stop()
                    }
                    "get_network_status" -> {
                        val isOnline = networkMonitor.isOnline
                        val type = networkMonitor.networkType
                        val quotedType = org.json.JSONObject.quote(type)
                        binding.webView.evaluateJavascript(
                            "window._transifyNetworkCallback && window._transifyNetworkCallback($isOnline, $quotedType);",
                            null
                        )
                    }
                }
            }
        }
    }

    private fun setupErrorViewActions() {
        binding.btnRetry.setOnClickListener {
            hideErrorViews()
            binding.webView.reload()
        }

        binding.btnChangeUrl.setOnClickListener {
            showMissingConfigView()
        }

        binding.btnSaveAndConnect.setOnClickListener {
            val inputUrl = binding.etServerUrl.text?.toString()?.trim().orEmpty()
            if (isValidTargetUrl(inputUrl)) {
                binding.urlInputLayout.error = null
                prefs.edit().putString(KEY_CUSTOM_URL, inputUrl).apply()
                loadApplicationUrl(inputUrl)
            } else {
                binding.urlInputLayout.error = "Please enter a valid HTTPS URL (e.g. https://your-server.com)"
            }
        }
    }

    private fun resolveAndLoadTargetUrl() {
        // Priority 1: BuildConfig property passed via Gradle (-PTRANSIFY_BASE_URL=https://...)
        val buildConfigUrl = BuildConfig.TRANSIFY_BASE_URL.trim()

        // Priority 2: Stored preference from previous manual entry (development only)
        val savedUrl = prefs.getString(KEY_CUSTOM_URL, "")?.trim().orEmpty()

        val candidateUrl = when {
            isValidTargetUrl(buildConfigUrl) -> buildConfigUrl
            isValidTargetUrl(savedUrl) -> savedUrl
            else -> ""
        }

        if (candidateUrl.isNotEmpty()) {
            loadApplicationUrl(candidateUrl)
        } else {
            showMissingConfigView()
        }
    }

    private fun loadApplicationUrl(url: String) {
        activeBaseUrl = url.removeSuffix("/")
        val uri = Uri.parse(activeBaseUrl)

        trustedScheme = uri.scheme?.lowercase() ?: "https"
        trustedHost = uri.host?.lowercase().orEmpty()
        trustedPort = if (uri.port != -1) uri.port else (if (trustedScheme == "https") 443 else 80)

        Log.i(TAG, "Configured trusted origin: $trustedScheme://$trustedHost:$trustedPort")

        setupWebMessageBridge(activeBaseUrl)

        binding.webView.webViewClient = TransifyWebViewClient(
            activity = this,
            onPageLoadingState = { isLoading ->
                binding.swipeRefresh.isRefreshing = isLoading
                if (!isLoading) hideErrorViews()
            },
            onErrorReceived = { description ->
                showConnectionError(description)
            }
        )

        hideErrorViews()
        binding.webView.loadUrl(activeBaseUrl)
    }

    /**
     * Exact trusted HTTPS origin check.
     * Does NOT automatically trust arbitrary subdomains or protocol downgrades.
     */
    fun isTrustedOrigin(originUri: Uri): Boolean {
        return OriginValidator.isExactTrustedOrigin(
            originUri,
            trustedScheme,
            trustedHost,
            trustedPort
        )
    }

    fun handleWebViewPermissionRequest(
        request: PermissionRequest,
        needsCamera: Boolean,
        needsAudio: Boolean
    ) {
        pendingPermissionRequest = request

        val permissionsToAsk = mutableListOf<String>()
        if (needsCamera && ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            permissionsToAsk.add(Manifest.permission.CAMERA)
        }
        if (needsAudio && ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            permissionsToAsk.add(Manifest.permission.RECORD_AUDIO)
        }

        if (permissionsToAsk.isNotEmpty()) {
            Log.i(TAG, "Requesting Android system permissions: $permissionsToAsk")
            mediaPermissionLauncher.launch(permissionsToAsk.toTypedArray())
        } else {
            request.grant(request.resources)
            pendingPermissionRequest = null
        }
    }

    fun clearPendingPermissionRequest(request: PermissionRequest?) {
        if (pendingPermissionRequest == request) {
            pendingPermissionRequest = null
        }
    }

    fun launchFileChooser(
        callback: ValueCallback<Array<Uri>>,
        params: WebChromeClient.FileChooserParams?
    ): Boolean {
        pendingFileChooserCallback?.onReceiveValue(null)
        pendingFileChooserCallback = callback

        return try {
            val cameraIntents = mutableListOf<Intent>()
            try {
                val captureDir = File(cacheDir, "camera_captures").apply { mkdirs() }
                val photoFile = File(captureDir, "braille_${System.currentTimeMillis()}.jpg")
                val photoUri = FileProvider.getUriForFile(
                    this,
                    "${packageName}.fileprovider",
                    photoFile
                )
                cameraCaptureUri = photoUri

                val captureIntent = Intent(MediaStore.ACTION_IMAGE_CAPTURE).apply {
                    putExtra(MediaStore.EXTRA_OUTPUT, photoUri)
                    addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION or Intent.FLAG_GRANT_READ_URI_PERMISSION)
                }
                cameraIntents.add(captureIntent)
            } catch (e: Exception) {
                Log.w(TAG, "Unable to prepare camera capture intent: ${e.message}")
            }

            val galleryIntent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP && params != null) {
                params.createIntent().apply {
                    putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("image/jpeg", "image/png", "image/webp"))
                }
            } else {
                Intent(Intent.ACTION_GET_CONTENT).apply {
                    type = "image/*"
                    putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("image/jpeg", "image/png", "image/webp"))
                    addCategory(Intent.CATEGORY_OPENABLE)
                }
            }

            val chooserIntent = Intent.createChooser(galleryIntent, "Select or Capture Braille Image").apply {
                if (cameraIntents.isNotEmpty()) {
                    putExtra(Intent.EXTRA_INITIAL_INTENTS, cameraIntents.toTypedArray())
                }
            }

            fileChooserLauncher.launch(chooserIntent)
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to launch file chooser", e)
            pendingFileChooserCallback?.onReceiveValue(null)
            pendingFileChooserCallback = null
            false
        }
    }

    private fun setupNetworkMonitoring() {
        networkMonitor.startMonitoring { isOnline, type ->
            runOnUiThread {
                if (isOnline) {
                    binding.offlineBanner.visibility = View.GONE
                } else {
                    binding.offlineBanner.visibility = View.VISIBLE
                }
            }
        }
    }

    private fun cleanupOldCameraCaptures() {
        try {
            val captureDir = File(cacheDir, "camera_captures")
            if (captureDir.exists()) {
                val cutoff = System.currentTimeMillis() - (24 * 60 * 60 * 1000)
                captureDir.listFiles()?.forEach { file ->
                    if (file.lastModified() < cutoff) {
                        file.delete()
                    }
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error cleaning old camera captures", e)
        }
    }

    private fun showConnectionError(desc: String) {
        binding.swipeRefresh.isRefreshing = false
        binding.progressBar.visibility = View.GONE
        binding.webView.visibility = View.GONE
        binding.missingConfigView.visibility = View.GONE

        binding.errorDesc.text = getString(R.string.error_connection_desc) + "\n\n(" + desc + ")"
        binding.errorView.visibility = View.VISIBLE
    }

    private fun showMissingConfigView() {
        binding.swipeRefresh.isRefreshing = false
        binding.progressBar.visibility = View.GONE
        binding.webView.visibility = View.GONE
        binding.errorView.visibility = View.GONE

        binding.missingConfigView.visibility = View.VISIBLE
        if (activeBaseUrl.isNotEmpty()) {
            binding.etServerUrl.setText(activeBaseUrl)
        }
    }

    private fun hideErrorViews() {
        binding.errorView.visibility = View.GONE
        binding.missingConfigView.visibility = View.GONE
        binding.webView.visibility = View.VISIBLE
    }

    override fun onResume() {
        super.onResume()
        binding.webView.onResume()
        setupNetworkMonitoring()
    }

    override fun onPause() {
        // Stop speech recognition listening
        speechBridge.stopListening()

        // Stop TTS playback immediately
        ttsBridge.stop()

        // Safely stop web camera capture if active
        binding.webView.evaluateJavascript(
            "if (window.SignPage && typeof window.SignPage.stopCamera === 'function') { window.SignPage.stopCamera(); }",
            null
        )

        // Cancel any pending speech synthesis audio
        binding.webView.evaluateJavascript(
            "if (window.speechSynthesis) { window.speechSynthesis.cancel(); }",
            null
        )

        networkMonitor.stopMonitoring()
        binding.webView.onPause()
        super.onPause()
    }

    override fun onDestroy() {
        networkMonitor.stopMonitoring()
        speechBridge.destroy()
        ttsBridge.destroy()
        cleanupOldCameraCaptures()
        binding.webView.loadUrl("about:blank")
        binding.webView.stopLoading()
        binding.webView.destroy()
        super.onDestroy()
    }
}
