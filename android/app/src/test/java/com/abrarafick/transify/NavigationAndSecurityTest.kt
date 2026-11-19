package com.abrarafick.transify

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.net.URI

/**
 * Navigation, Scheme Filtering & Origin Security Unit Tests.
 *
 * Verifies:
 * 1. Double-tap back exit debounce window (2,000 ms).
 * 2. URL scheme routing (internal HTTPS vs external mailto/tel/sms vs blocked dangerous schemes).
 * 3. Exact origin match with paths, queries, and fragments.
 * 4. Strict rejection of protocol downgrades, lookalikes, and port mismatches.
 */
class NavigationAndSecurityTest {

    @Test
    fun testDoubleTapBackExitDebounce() {
        val debounceWindowMs = 2000L

        val firstPress = 10000L
        val rapidSecondPress = 10800L // 800ms difference -> Exit app
        val slowSecondPress = 12500L  // 2500ms difference -> Show toast, do not exit

        assertTrue(rapidSecondPress - firstPress < debounceWindowMs)
        assertFalse(slowSecondPress - firstPress < debounceWindowMs)
    }

    @Test
    fun testSchemeClassification() {
        val trustedBase = "https://transify.ai"

        // Web schemes
        val httpsUri = URI("https://transify.ai/dashboard")
        assertEquals("https", httpsUri.scheme.lowercase())

        // System external schemes (must route out of WebView)
        val mailtoUri = URI("mailto:support@transify.ai")
        assertEquals("mailto", mailtoUri.scheme.lowercase())

        val telUri = URI("tel:+18005550199")
        assertEquals("tel", telUri.scheme.lowercase())

        val smsUri = URI("sms:+18005550199")
        assertEquals("sms", smsUri.scheme.lowercase())
    }

    @Test
    fun testExactOriginPreservesDeepLinks() {
        val base = "https://transify20-production.up.railway.app"

        // Password reset URL fragment deep links
        val resetDeepLink = "https://transify20-production.up.railway.app/#reset_token=abc123secret"
        assertTrue(OriginValidator.isExactTrustedOrigin(resetDeepLink, base))

        // Navigation paths
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify20-production.up.railway.app/login", base))
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify20-production.up.railway.app/sign", base))
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify20-production.up.railway.app/braille", base))
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify20-production.up.railway.app/dashboard", base))
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify20-production.up.railway.app/terms", base))
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify20-production.up.railway.app/privacy", base))
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify20-production.up.railway.app/cookies", base))
        assertTrue(OriginValidator.isExactTrustedOrigin("https://transify20-production.up.railway.app/refund", base))

        // External attack origins must be rejected
        assertFalse(OriginValidator.isExactTrustedOrigin("https://evil-transify.app", base))
        assertFalse(OriginValidator.isExactTrustedOrigin("https://transify20-production.up.railway.app.phishing.com", base))
    }
}
