package com.abrarafick.transify

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import android.util.Log
import android.webkit.ConsoleMessage
import android.webkit.PermissionRequest
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebView
import androidx.core.content.ContextCompat

/**
 * WebChromeClient for Transify Android Application.
 *
 * Implements:
 * 1. Hardware permission handling for Camera (Sign Language) and Microphone (Speech-to-Text).
 * 2. Strict origin check ensuring only the trusted Transify domain receives hardware permissions.
 * 3. Granting only explicitly requested, safe resources (rejecting unexpected permission types).
 * 4. File chooser for Braille image uploads (supporting gallery, file picker, JPEG/PNG/WebP).
 * 5. Progress bar reporting.
 */
class TransifyWebChromeClient(
    private val activity: MainActivity,
    private val isTrustedOrigin: (Uri) -> Boolean,
    private val onProgressChanged: (Int) -> Unit
) : WebChromeClient() {

    companion object {
        private const val TAG = "TransifyChromeClient"
    }

    override fun onProgressChanged(view: WebView?, newProgress: Int) {
        super.onProgressChanged(view, newProgress)
        onProgressChanged(newProgress)
    }

    override fun onPermissionRequest(request: PermissionRequest?) {
        if (request == null) return
        val originUri = request.origin

        Log.i(TAG, "WebView permission requested for origin: $originUri, resources: ${request.resources.joinToString()}")

        // Security check: Only permit the verified Transify website domain
        if (!isTrustedOrigin(originUri)) {
            Log.w(TAG, "Rejected hardware permission request from untrusted origin: $originUri")
            request.deny()
            return
        }

        val requestedResources = request.resources
        val allowedResources = mutableListOf<String>()

        var needsCamera = false
        var needsAudio = false

        for (res in requestedResources) {
            when (res) {
                PermissionRequest.RESOURCE_VIDEO_CAPTURE -> {
                    needsCamera = true
                    allowedResources.add(res)
                }
                PermissionRequest.RESOURCE_AUDIO_CAPTURE -> {
                    needsAudio = true
                    allowedResources.add(res)
                }
                else -> {
                    Log.w(TAG, "Rejecting unexpected WebView permission resource: $res")
                }
            }
        }

        if (allowedResources.isEmpty()) {
            Log.w(TAG, "No supported permission resources in request. Denying.")
            request.deny()
            return
        }

        val hasCamera = !needsCamera || ContextCompat.checkSelfPermission(
            activity,
            Manifest.permission.CAMERA
        ) == PackageManager.PERMISSION_GRANTED

        val hasAudio = !needsAudio || ContextCompat.checkSelfPermission(
            activity,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED

        if (hasCamera && hasAudio) {
            Log.i(TAG, "Granting WebView hardware resources: $allowedResources")
            request.grant(allowedResources.toTypedArray())
        } else {
            activity.handleWebViewPermissionRequest(request, needsCamera, needsAudio)
        }
    }

    override fun onPermissionRequestCanceled(request: PermissionRequest?) {
        super.onPermissionRequestCanceled(request)
        Log.d(TAG, "WebView permission request was canceled")
        activity.clearPendingPermissionRequest(request)
    }

    override fun onShowFileChooser(
        webView: WebView?,
        filePathCallback: ValueCallback<Array<Uri>>?,
        fileChooserParams: FileChooserParams?
    ): Boolean {
        if (filePathCallback == null) return false

        // Security check: Ensure file chooser was initiated from the exact trusted origin
        val currentUrl = webView?.url
        val currentUri = if (currentUrl != null) try { Uri.parse(currentUrl) } catch (e: Exception) { null } else null
        if (currentUri == null || !isTrustedOrigin(currentUri)) {
            Log.w(TAG, "Blocked onShowFileChooser from untrusted URL: $currentUrl")
            filePathCallback.onReceiveValue(null)
            return false
        }

        Log.d(TAG, "onShowFileChooser triggered on trusted origin. AcceptTypes: ${fileChooserParams?.acceptTypes?.joinToString()}")
        return activity.launchFileChooser(filePathCallback, fileChooserParams)
    }

    override fun onConsoleMessage(consoleMessage: ConsoleMessage?): Boolean {
        if (consoleMessage != null && BuildConfig.DEBUG) {
            Log.d("TransifyWebConsole", "[${consoleMessage.messageLevel()}] ${consoleMessage.message()} -- line ${consoleMessage.lineNumber()} of ${consoleMessage.sourceId()}")
        }
        return super.onConsoleMessage(consoleMessage)
    }
}
