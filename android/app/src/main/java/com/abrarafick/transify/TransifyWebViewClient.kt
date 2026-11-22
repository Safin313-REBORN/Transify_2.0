package com.abrarafick.transify

import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.net.http.SslError
import android.util.Log
import android.webkit.SslErrorHandler
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient

/**
 * WebViewClient for Transify Android Application.
 *
 * Implements:
 * 1. Strict origin boundary enforcement (only exact trusted HTTPS Transify origin stays inside WebView).
 * 2. External intent routing (external links opened in system browser, mailto/tel in respective apps).
 * 3. Blocking of dangerous schemes (javascript:, file:, content:, etc.).
 * 4. Strict SSL enforcement (never bypass certificate failures).
 * 5. Error state delegation to native retry UI on connection loss.
 * 6. Injection of Web Speech API and Blob download compatibility polyfill only on trusted pages.
 */
class TransifyWebViewClient(
    private val activity: MainActivity,
    private val onPageLoadingState: (isLoading: Boolean) -> Unit,
    private val onErrorReceived: (description: String) -> Unit
) : WebViewClient() {

    companion object {
        private const val TAG = "TransifyWebViewClient"
    }

    private fun handleNavigation(uri: Uri): Boolean {
        val scheme = uri.scheme?.lowercase() ?: ""

        // Handle external protocols like email, phone dialer, SMS
        if (scheme == "mailto" || scheme == "tel" || scheme == "sms") {
            try {
                val intent = Intent(Intent.ACTION_VIEW, uri)
                activity.startActivity(intent)
            } catch (e: Exception) {
                Log.w(TAG, "No handler found for external scheme: $scheme", e)
            }
            return true
        }

        // Reject dangerous / non-web schemes
        if (scheme != "http" && scheme != "https") {
            Log.w(TAG, "Blocked navigation to non-web scheme: $scheme ($uri)")
            return true
        }

        // Exact trusted origin check (preserves internal navigation like /dashboard, /sign, /braille)
        if (activity.isTrustedOrigin(uri)) {
            return false // Stay inside WebView
        }

        // External domain -> route outside WebView to system browser
        Log.i(TAG, "Navigating to external domain outside WebView: $uri")
        try {
            val browserIntent = Intent(Intent.ACTION_VIEW, uri).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            activity.startActivity(browserIntent)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to launch external browser for $uri", e)
        }
        return true
    }

    override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
        val uri = request?.url ?: return false
        return handleNavigation(uri)
    }

    @Deprecated("Deprecated in Java", ReplaceWith("shouldOverrideUrlLoading(view, request)"))
    override fun shouldOverrideUrlLoading(view: WebView?, url: String?): Boolean {
        val uri = if (url != null) Uri.parse(url) else return false
        return handleNavigation(uri)
    }

    override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
        super.onPageStarted(view, url, favicon)
        Log.d(TAG, "Page started loading: $url")
        onPageLoadingState(true)
    }

    override fun onPageFinished(view: WebView?, url: String?) {
        super.onPageFinished(view, url)
        Log.d(TAG, "Page finished loading: $url")
        onPageLoadingState(false)

        val currentUri = if (url != null) Uri.parse(url) else null
        if (currentUri != null && activity.isTrustedOrigin(currentUri)) {
            // Inject the SpeechRecognition and download polyfill into trusted page
            view?.evaluateJavascript(TransifySpeechBridge.POLYFILL_JS) { result ->
                Log.d(TAG, "Polyfill injection evaluated: $result")
            }
        } else {
            Log.w(TAG, "Skipping polyfill injection for untrusted page: $url")
        }
    }

    override fun onReceivedError(
        view: WebView?,
        request: WebResourceRequest?,
        error: WebResourceError?
    ) {
        super.onReceivedError(view, request, error)
        if (request?.isForMainFrame == true) {
            val description = error?.description?.toString() ?: "Connection failed"
            val errorCode = error?.errorCode ?: -1
            Log.e(TAG, "Main frame error ($errorCode): $description for ${request.url}")
            onErrorReceived(description)
        }
    }

    override fun onReceivedHttpError(
        view: WebView?,
        request: WebResourceRequest?,
        errorResponse: WebResourceResponse?
    ) {
        super.onReceivedHttpError(view, request, errorResponse)
        if (request?.isForMainFrame == true) {
            val statusCode = errorResponse?.statusCode ?: 0
            if (statusCode >= 500) {
                Log.e(TAG, "Main frame HTTP server error: $statusCode for ${request.url}")
                onErrorReceived("Server returned status $statusCode")
            }
        }
    }

    override fun onReceivedSslError(view: WebView?, handler: SslErrorHandler?, error: SslError?) {
        // SECURITY REQUIREMENT: Never bypass SSL certificate errors
        Log.e(TAG, "Strict SSL error: $error. Connection blocked.")
        handler?.cancel()
        onErrorReceived("Security Violation: SSL Certificate validation failed for this domain. Insecure connections are blocked.")
    }
}
