package com.abrarafick.transify

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Production Security & Origin Validation Unit Tests.
 *
 * Validates the actual production component [OriginValidator] without relying on duplicate local test helpers.
 * Covers:
 * 1. Target URL validation (HTTPS required, local loopback allowed only in debug).
 * 2. Exact origin matching (protocol, domain, port).
 * 3. Subdomain rejection (no automatic subdomain trust).
 * 4. Lookalike domain rejection (phishing/suffix attacks).
 * 5. Scheme mismatch rejection (HTTP vs HTTPS).
 * 6. Port mismatch rejection (:8443 vs default 443).
 * 7. Origin rule generation for WebMessageListener.
 * 8. Download filename sanitization (directory traversal prevention, illegal character stripping).
 * 9. MIME type validation.
 * 10. WebMessage payload validation (action allowlisting, parameter type safety).
 * 11. WebMessage payload size limit enforcement (10MB limit).
 */
class UrlValidationTest {

    @Test
    fun testPlaceholderDetection() {
        // Placeholders must return true
        assertTrue(OriginValidator.isPlaceholderUrl("https://YOUR-DEPLOYED-TRANSIFY-DOMAIN"))
        assertTrue(OriginValidator.isPlaceholderUrl("https://ACTUAL-DEPLOYED-DOMAIN"))
        assertTrue(OriginValidator.isPlaceholderUrl("https://your-domain.com"))
        assertTrue(OriginValidator.isPlaceholderUrl("https://example.com"))
        assertTrue(OriginValidator.isPlaceholderUrl("https://change-me.com"))
        assertTrue(OriginValidator.isPlaceholderUrl("https://your-transify-domain.com"))
        assertTrue(OriginValidator.isPlaceholderUrl("https://placeholder-site.org"))
        assertTrue(OriginValidator.isPlaceholderUrl("https://"))
        assertTrue(OriginValidator.isPlaceholderUrl("http://"))
        assertTrue(OriginValidator.isPlaceholderUrl(""))

        // Real domains must return false
        assertFalse(OriginValidator.isPlaceholderUrl("https://transify.ai"))
        assertFalse(OriginValidator.isPlaceholderUrl("https://transify-platform.org"))
        assertFalse(OriginValidator.isPlaceholderUrl("https://transify.app.internal"))
    }

    @Test
    fun testValidTargetUrl() {
        // Valid HTTPS production endpoints
        assertTrue(OriginValidator.isValidTargetUrl("https://transify.ai"))
        assertTrue(OriginValidator.isValidTargetUrl("https://app.transify-platform.org"))
        assertTrue(OriginValidator.isValidTargetUrl("https://transify-assistive.up.railway.app"))

        // Placeholders must be rejected
        assertFalse(OriginValidator.isValidTargetUrl("https://YOUR-DEPLOYED-TRANSIFY-DOMAIN"))
        assertFalse(OriginValidator.isValidTargetUrl("https://ACTUAL-DEPLOYED-DOMAIN"))
        assertFalse(OriginValidator.isValidTargetUrl("https://example.com"))
        assertFalse(OriginValidator.isValidTargetUrl(""))

        // Insecure or dangerous protocols must be rejected
        assertFalse(OriginValidator.isValidTargetUrl("ftp://transify.ai"))
        assertFalse(OriginValidator.isValidTargetUrl("javascript:alert(1)"))
        assertFalse(OriginValidator.isValidTargetUrl("file:///android_asset/index.html"))
        assertFalse(OriginValidator.isValidTargetUrl("content://media/external/images"))

        // HTTP allowed only in debug mode for loopback
        assertFalse(OriginValidator.isValidTargetUrl("http://transify.ai", allowHttpLocal = false))
        assertFalse(OriginValidator.isValidTargetUrl("http://localhost:8000", allowHttpLocal = false))
        assertTrue(OriginValidator.isValidTargetUrl("http://localhost:8000", allowHttpLocal = true))
        assertTrue(OriginValidator.isValidTargetUrl("http://10.0.2.2:8000", allowHttpLocal = true))
        assertTrue(OriginValidator.isValidTargetUrl("http://192.168.1.100:8000", allowHttpLocal = true))
    }

    @Test
    fun testExactTrustedOriginMatching() {
        val trustedBase = "https://transify.ai"

        // 1. Same origin with varying internal routes & queries -> MUST BE TRUSTED
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify.ai", trustedBase))
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify.ai/sign", trustedBase))
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify.ai/dashboard", trustedBase))
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify.ai/api/sign/predict", trustedBase))
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify.ai/braille?lang=en", trustedBase))
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify.ai/#sign", trustedBase))

        // 2. Subdomains must NOT be automatically trusted (Strict origin boundary)
        assertFalse(OriginValidator.isExactTrustedOrigin("https://attacker.transify.ai", trustedBase))
        assertFalse(OriginValidator.isExactTrustedOrigin("https://sub.transify.ai/sign", trustedBase))
        assertFalse(OriginValidator.isExactTrustedOrigin("https://api.transify.ai", trustedBase))

        // 3. Suffix / lookalike domain attacks must be REJECTED
        assertFalse(OriginValidator.isExactTrustedOrigin("https://transify.ai.attacker.com", trustedBase))
        assertFalse(OriginValidator.isExactTrustedOrigin("https://transify.ai.phishingsite.org", trustedBase))
        assertFalse(OriginValidator.isExactTrustedOrigin("https://nottransify.ai", trustedBase))

        // 4. Protocol downgrade (HTTP vs HTTPS) must be REJECTED
        assertFalse(OriginValidator.isExactTrustedOrigin("http://transify.ai", trustedBase))

        // 5. Port mismatch must be REJECTED
        assertFalse(OriginValidator.isExactTrustedOrigin("https://transify.ai:8443", trustedBase))
        assertFalse(OriginValidator.isExactTrustedOrigin("https://transify.ai:8080", trustedBase))

        // 6. External domains must be REJECTED
        assertFalse(OriginValidator.isExactTrustedOrigin("https://google.com", trustedBase))
        assertFalse(OriginValidator.isExactTrustedOrigin("https://github.com/Abrarafick/transify", trustedBase))
    }

    @Test
    fun testOriginRuleGeneration() {
        assertEquals("https://transify.ai", OriginValidator.getOriginRule("https://transify.ai/dashboard"))
        assertEquals("https://transify.ai", OriginValidator.getOriginRule("https://transify.ai:443/"))
        assertEquals("https://transify.ai:8443", OriginValidator.getOriginRule("https://transify.ai:8443/sign"))
        assertEquals("http://localhost:8000", OriginValidator.getOriginRule("http://localhost:8000/"))
    }

    @Test
    fun testFilenameSanitization() {
        // Path traversal attempts must be neutralized
        val traversalName = "../../etc/passwd"
        val cleanTraversal = OriginValidator.sanitizeFilename(traversalName)
        assertFalse(cleanTraversal.contains(".."))
        assertFalse(cleanTraversal.contains("/"))
        assertEquals("____etc_passwd", cleanTraversal)

        // Illegal characters must be replaced with underscores
        val dirtyName = "Braille:Export?*\"<>.txt"
        val cleanDirty = OriginValidator.sanitizeFilename(dirtyName)
        assertFalse(cleanDirty.contains(":"))
        assertFalse(cleanDirty.contains("?"))
        assertFalse(cleanDirty.contains("*"))
        assertFalse(cleanDirty.contains("\""))
        assertFalse(cleanDirty.contains("<"))
        assertFalse(cleanDirty.contains(">"))

        // Blank filename should provide a safe default
        val blankName = "   "
        val cleanBlank = OriginValidator.sanitizeFilename(blankName)
        assertTrue(cleanBlank.startsWith("Transify_Export_"))
        assertTrue(cleanBlank.endsWith(".txt"))
    }

    @Test
    fun testMimeTypeValidation() {
        assertTrue(OriginValidator.isValidMimeType("text/plain"))
        assertTrue(OriginValidator.isValidMimeType("image/jpeg"))
        assertTrue(OriginValidator.isValidMimeType("image/png"))
        assertTrue(OriginValidator.isValidMimeType("image/webp"))
        assertTrue(OriginValidator.isValidMimeType("application/json"))

        assertFalse(OriginValidator.isValidMimeType(""))
        assertFalse(OriginValidator.isValidMimeType("invalid-mime"))
        assertFalse(OriginValidator.isValidMimeType("text/"))
        assertFalse(OriginValidator.isValidMimeType("/plain"))
        assertFalse(OriginValidator.isValidMimeType("text/plain; charset=utf-8"))
    }

    @Test
    fun testWebMessagePayloadValidation() {
        // 1. Valid stt_start
        val validSttStart = """{"action":"stt_start","lang":"en-US","interim":true,"continuous":true}"""
        val res1 = OriginValidator.validateMessagePayload(validSttStart)
        assertTrue(res1 is OriginValidator.ValidationResult.Success)
        assertEquals("stt_start", (res1 as OriginValidator.ValidationResult.Success).action)

        // 2. Valid Bengali stt_start
        val validBengaliStt = """{"action":"stt_start","lang":"bn-BD","interim":true,"continuous":true}"""
        val resBengali = OriginValidator.validateMessagePayload(validBengaliStt)
        assertTrue(resBengali is OriginValidator.ValidationResult.Success)

        // 3. Valid stt_stop & stt_abort
        assertTrue(OriginValidator.validateMessagePayload("""{"action":"stt_stop"}""") is OriginValidator.ValidationResult.Success)
        assertTrue(OriginValidator.validateMessagePayload("""{"action":"stt_abort"}""") is OriginValidator.ValidationResult.Success)

        // 4. Valid download_blob
        val validDownload = """{"action":"download_blob","filename":"Braille.txt","mimeType":"text/plain","data":"SGVsbG8gV29ybGQ="}"""
        assertTrue(OriginValidator.validateMessagePayload(validDownload) is OriginValidator.ValidationResult.Success)

        // 5. Unauthorized action
        val unauthorized = """{"action":"delete_all_files"}"""
        val resUnauth = OriginValidator.validateMessagePayload(unauthorized)
        assertTrue(resUnauth is OriginValidator.ValidationResult.Error)

        // 6. Malformed JSON
        val malformed = "{not a json"
        assertTrue(OriginValidator.validateMessagePayload(malformed) is OriginValidator.ValidationResult.Error)

        // 7. Invalid language tag in stt_start
        val badLang = """{"action":"stt_start","lang":"../../malicious"}"""
        assertTrue(OriginValidator.validateMessagePayload(badLang) is OriginValidator.ValidationResult.Error)

        // 8. Missing data in download_blob
        val emptyDownload = """{"action":"download_blob","filename":"Braille.txt","mimeType":"text/plain","data":""}"""
        assertTrue(OriginValidator.validateMessagePayload(emptyDownload) is OriginValidator.ValidationResult.Error)

        // 9. Oversized payload (> 10MB)
        val oversizedString = "A".repeat(11 * 1024 * 1024)
        val resOversized = OriginValidator.validateMessagePayload(oversizedString)
        assertTrue(resOversized is OriginValidator.ValidationResult.Error)
    }
}
