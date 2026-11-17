package com.abrarafick.transify

import android.app.DownloadManager
import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.util.Base64
import android.util.Log
import android.webkit.CookieManager
import android.webkit.DownloadListener
import android.webkit.JavascriptInterface
import android.webkit.URLUtil
import android.webkit.WebView
import android.widget.Toast
import java.io.File
import java.io.FileOutputStream
import java.io.OutputStream

/**
 * Download bridge for Transify Android WebView.
 *
 * Handles:
 * 1. Standard authenticated HTTP/HTTPS file downloads via DownloadManager.
 * 2. Blob URL / Base64 exports (e.g. Braille text translation files created via URL.createObjectURL).
 * 3. Filename sanitization, preventing directory traversal.
 * 4. Payload size limits preventing memory exhaustion.
 * 5. MediaStore storage (scoped storage on Android 10+ and public Downloads on older Android).
 */
class TransifyDownloadBridge(
    private val activity: MainActivity,
    private val webView: WebView
) : DownloadListener {

    companion object {
        private const val TAG = "TransifyDownloadBridge"
        const val INTERFACE_NAME = "TransifyDownloadBridge"
    }

    private val mainHandler = Handler(Looper.getMainLooper())

    private fun isOriginSecure(): Boolean {
        val currentUrl = webView.url ?: return false
        val uri = try {
            Uri.parse(currentUrl)
        } catch (e: Exception) {
            return false
        }
        return activity.isTrustedOrigin(uri)
    }

    override fun onDownloadStart(
        url: String?,
        userAgent: String?,
        contentDisposition: String?,
        mimetype: String?,
        contentLength: Long
    ) {
        if (url == null) return

        if (!isOriginSecure()) {
            Log.w(TAG, "Blocked download request from untrusted URL: ${webView.url}")
            return
        }

        Log.d(TAG, "Download requested for URL: $url (mimetype=$mimetype)")

        val guessedName = URLUtil.guessFileName(url, contentDisposition, mimetype).let {
            if (it.isNullOrBlank() || it == "downloadfile") {
                "Transify_Braille_Translation_${System.currentTimeMillis()}.txt"
            } else it
        }
        val safeName = OriginValidator.sanitizeFilename(guessedName)

        when {
            url.startsWith("data:") -> {
                saveDataUri(url, mimetype ?: "text/plain", safeName)
            }
            url.startsWith("http://") || url.startsWith("https://") -> {
                handleHttpDownload(url, userAgent, contentDisposition, mimetype, safeName)
            }
            else -> {
                Log.w(TAG, "Unsupported download scheme for URL: $url")
            }
        }
    }

    /**
     * Saves base64 encoded data URI directly to device storage.
     */
    @JavascriptInterface
    fun saveDataUri(dataUri: String, mimeType: String, filename: String) {
        mainHandler.post {
            if (!isOriginSecure()) {
                Log.w(TAG, "Blocked saveDataUri from untrusted page: ${webView.url}")
                return@post
            }

            if (dataUri.length > OriginValidator.MAX_PAYLOAD_SIZE_BYTES) {
                Log.e(TAG, "Download payload exceeds 10MB limit")
                showToast("Download rejected: file size exceeds 10MB limit")
                return@post
            }

            try {
                val base64Data = if (dataUri.contains(",")) {
                    dataUri.substringAfter(",")
                } else {
                    dataUri
                }
                val decodedBytes = Base64.decode(base64Data, Base64.DEFAULT)
                val safeFilename = OriginValidator.sanitizeFilename(
                    if (filename.isBlank()) "Transify_Braille_Translation_${System.currentTimeMillis()}.txt" else filename
                )
                val actualMime = if (OriginValidator.isValidMimeType(mimeType)) mimeType else "text/plain"

                saveBytesToDownloads(decodedBytes, safeFilename, actualMime)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to save data URI download", e)
                showToast("Failed to save download: ${e.localizedMessage}")
            }
        }
    }

    private fun saveBytesToDownloads(bytes: ByteArray, filename: String, mimeType: String) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
                    put(MediaStore.MediaColumns.MIME_TYPE, mimeType)
                    put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)
                }
                val resolver = activity.contentResolver
                val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                if (uri != null) {
                    resolver.openOutputStream(uri)?.use { os: OutputStream ->
                        os.write(bytes)
                    }
                    showToast("Downloaded: $filename to Downloads")
                    Log.i(TAG, "File saved successfully via MediaStore: $uri")
                } else {
                    throw IllegalStateException("Failed to create MediaStore entry for $filename")
                }
            } else {
                val downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                downloadsDir.mkdirs()
                val targetFile = File(downloadsDir, filename)
                FileOutputStream(targetFile).use { it.write(bytes) }
                showToast("Downloaded: $filename")
                Log.i(TAG, "File saved to external storage: ${targetFile.absolutePath}")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error writing downloaded file", e)
            showToast("Download error: ${e.message}")
        }
    }

    private fun handleHttpDownload(
        url: String,
        userAgent: String?,
        contentDisposition: String?,
        mimetype: String?,
        filename: String
    ) {
        try {
            val request = DownloadManager.Request(Uri.parse(url)).apply {
                val cookie = CookieManager.getInstance().getCookie(url)
                if (!cookie.isNullOrBlank()) {
                    addRequestHeader("Cookie", cookie)
                }
                if (!userAgent.isNullOrBlank()) {
                    addRequestHeader("User-Agent", userAgent)
                }
                setDescription("Transify Download: $filename")
                setTitle(filename)
                setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename)
                if (!mimetype.isNullOrBlank() && OriginValidator.isValidMimeType(mimetype)) {
                    setMimeType(mimetype)
                }
            }

            val dm = activity.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            dm.enqueue(request)
            showToast("Downloading $filename…")
        } catch (e: Exception) {
            Log.e(TAG, "DownloadManager failed", e)
            showToast("Unable to start download: ${e.localizedMessage}")
        }
    }

    private fun showToast(msg: String) {
        mainHandler.post {
            Toast.makeText(activity, msg, Toast.LENGTH_SHORT).show()
        }
    }
}
