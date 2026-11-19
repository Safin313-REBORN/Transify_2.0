package com.abrarafick.transify

import android.net.Uri
import org.json.JSONObject
import java.net.URI

/**
 * OriginValidator — Centralized Security & Origin Matching Engine.
 *
 * Implements strict, production-grade security boundaries:
 * 1. Exact HTTPS origin validation (no automatic subdomain trust, no scheme downgrade).
 * 2. Strict placeholder URL detection preventing release APKs from building or running against mocks.
 * 3. File name sanitization preventing directory traversal attacks.
 * 4. WebMessageListener action allowlisting, parameter validation, and payload size bounds.
 */
object OriginValidator {

    const val MAX_PAYLOAD_SIZE_BYTES = 10 * 1024 * 1024 // 10 MB payload limit
    const val MAX_TTS_TEXT_LENGTH = 5000 // 5000 characters limit for TTS requests

    val ALLOWED_BRIDGE_ACTIONS = setOf(
        "stt_start",
        "stt_stop",
        "stt_abort",
        "download_blob",
        "tts_speak",
        "tts_stop",
        "get_network_status"
    )

    private val PLACEHOLDER_KEYWORDS = listOf(
        "your-deployed",
        "actual-deployed",
        "your-domain",
        "example.com",
        "change-me",
        "placeholder",
        "your-transify-domain"
    )

    /**
     * Identifies whether a given URL string is an unconfigured placeholder.
     */
    fun isPlaceholderUrl(url: String): Boolean {
        val lower = url.lowercase().trim()
        if (lower.isEmpty() || lower == "https://" || lower == "http://") return true
        return PLACEHOLDER_KEYWORDS.any { lower.contains(it) }
    }

    /**
     * Validates that a string is a well-formed HTTPS target URL (or local HTTP in debug builds).
     */
    fun isValidTargetUrl(url: String, allowHttpLocal: Boolean = false): Boolean {
        if (url.isBlank() || isPlaceholderUrl(url)) return false
        val uri = try {
            URI(url.trim())
        } catch (e: Exception) {
            return false
        }

        val scheme = uri.scheme?.lowercase() ?: return false
        val host = uri.host?.lowercase() ?: return false

        if (host.isBlank()) return false

        val isHttps = scheme == "https"
        val isLocalLoopback = allowHttpLocal && scheme == "http" && (
                host == "localhost" ||
                host == "127.0.0.1" ||
                host == "10.0.2.2" ||
                host.startsWith("192.168.")
        )

        return isHttps || isLocalLoopback
    }

    /**
     * Compares a candidate URL against the trusted base URL.
     * Enforces exact scheme, exact host, and exact port.
     * Rejects subdomains, lookalikes, scheme downgrades, and port mismatches.
     */
    fun isExactTrustedOrigin(candidateUrl: String, trustedBaseUrl: String): Boolean {
        if (candidateUrl.isBlank() || trustedBaseUrl.isBlank()) return false
        return try {
            val candUri = URI(candidateUrl.trim())
            val baseUri = URI(trustedBaseUrl.trim())

            val candScheme = candUri.scheme?.lowercase() ?: return false
            val baseScheme = baseUri.scheme?.lowercase() ?: return false
            if (candScheme != baseScheme) return false

            val candHost = candUri.host?.lowercase() ?: return false
            val baseHost = baseUri.host?.lowercase() ?: return false
            if (candHost != baseHost) return false

            val candPort = if (candUri.port != -1) candUri.port else (if (candScheme == "https") 443 else 80)
            val basePort = if (baseUri.port != -1) baseUri.port else (if (baseScheme == "https") 443 else 80)

            candPort == basePort
        } catch (e: Exception) {
            false
        }
    }

    /**
     * Android Uri overload for exact trusted origin check.
     */
    fun isExactTrustedOrigin(
        candidateUri: Uri,
        trustedScheme: String,
        trustedHost: String,
        trustedPort: Int
    ): Boolean {
        val reqScheme = candidateUri.scheme?.lowercase() ?: return false
        val reqHost = candidateUri.host?.lowercase() ?: return false

        if (reqScheme != trustedScheme.lowercase()) return false
        if (reqHost != trustedHost.lowercase()) return false

        val reqPort = if (candidateUri.port != -1) candidateUri.port else (if (reqScheme == "https") 443 else 80)
        val expPort = if (trustedPort != -1) trustedPort else (if (trustedScheme == "https") 443 else 80)

        return reqPort == expPort
    }

    /**
     * Formats an origin rule string for WebViewCompat.addWebMessageListener.
     * Allowed origin rules must follow standard origin format: e.g. "https://example.com" or "https://example.com:8443".
     */
    fun getOriginRule(baseUrl: String): String {
        val uri = try {
            URI(baseUrl.trim())
        } catch (e: Exception) {
            return ""
        }
        val scheme = uri.scheme?.lowercase() ?: return ""
        val host = uri.host?.lowercase() ?: return ""
        val port = uri.port

        return if (port != -1 && !((scheme == "https" && port == 443) || (scheme == "http" && port == 80))) {
            "$scheme://$host:$port"
        } else {
            "$scheme://$host"
        }
    }

    /**
     * Sanitizes a downloaded file name, stripping directory traversal attempts,
     * invalid filesystem characters, and enforcing reasonable length.
     */
    fun sanitizeFilename(rawName: String): String {
        var clean = rawName.trim()
        if (clean.isBlank()) {
            return "Transify_Export_${System.currentTimeMillis()}.txt"
        }

        // Strip path traversal sequences
        clean = clean.replace("..", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace("\u0000", "")

        // Replace illegal filesystem characters
        clean = clean.replace(Regex("[\\\\/:*?\"<>|]"), "_")

        // Cap length to 255 characters
        if (clean.length > 255) {
            val ext = clean.substringAfterLast(".", "")
            clean = if (ext.isNotEmpty()) {
                clean.take(240) + "." + ext
            } else {
                clean.take(255)
            }
        }

        return if (clean.isBlank()) "Transify_Export_${System.currentTimeMillis()}.txt" else clean
    }

    /**
     * Validates MIME type strings.
     */
    fun isValidMimeType(mime: String): Boolean {
        if (mime.isBlank()) return false
        return mime.matches(Regex("^[a-zA-Z0-9!#$&^_.+-]+/[a-zA-Z0-9!#$&^_.+-]+$"))
    }

    sealed class ValidationResult {
        data class Success(val action: String, val json: JSONObject) : ValidationResult()
        data class Error(val reason: String) : ValidationResult()
    }

    /**
     * Validates incoming WebMessage payloads against the action allowlist and size limits.
     */
    fun validateMessagePayload(rawPayload: String): ValidationResult {
        if (rawPayload.length > MAX_PAYLOAD_SIZE_BYTES) {
            return ValidationResult.Error("Payload exceeds maximum size limit of 10MB")
        }

        val json = try {
            JSONObject(rawPayload)
        } catch (e: Exception) {
            return ValidationResult.Error("Malformed JSON payload: ${e.message}")
        }

        val action = json.optString("action", "").trim()
        if (action.isEmpty() || !ALLOWED_BRIDGE_ACTIONS.contains(action)) {
            return ValidationResult.Error("Unauthorized or unknown bridge action: '$action'")
        }

        when (action) {
            "stt_start" -> {
                val lang = json.optString("lang", "en-US")
                if (!lang.matches(Regex("^[a-zA-Z0-9_-]{2,15}$"))) {
                    return ValidationResult.Error("Invalid language tag: '$lang'")
                }
            }
            "download_blob" -> {
                val data = json.optString("data", "")
                if (data.isBlank()) {
                    return ValidationResult.Error("Missing or empty data payload for download_blob")
                }
            }
            "tts_speak" -> {
                val text = json.optString("text", "").trim()
                if (text.isEmpty()) {
                    return ValidationResult.Error("Missing or empty text for tts_speak")
                }
                if (text.length > MAX_TTS_TEXT_LENGTH) {
                    return ValidationResult.Error("Text length exceeds $MAX_TTS_TEXT_LENGTH characters limit for tts_speak")
                }
                val lang = json.optString("lang", "en-US").trim()
                if (lang.isNotEmpty() && !lang.matches(Regex("^[a-zA-Z0-9_-]{2,15}$"))) {
                    return ValidationResult.Error("Invalid language tag for tts_speak: '$lang'")
                }
            }
            "tts_stop", "get_network_status", "stt_stop", "stt_abort" -> {
                // Parameter-free actions
            }
        }

        return ValidationResult.Success(action, json)
    }
}

