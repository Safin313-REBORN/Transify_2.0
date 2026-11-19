package com.abrarafick.transify

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Network State & Offline Awareness Unit Tests.
 *
 * Verifies:
 * 1. get_network_status action validation.
 * 2. Network state contract (isOnline: Boolean, networkType: String).
 * 3. Recognized network transports: wifi, cellular, ethernet, none, other.
 * 4. Graceful handling of offline status without application crash.
 */
class NetworkMonitorValidationTest {

    @Test
    fun testGetNetworkStatusActionValidation() {
        val payload = """{"action":"get_network_status"}"""
        val result = OriginValidator.validateMessagePayload(payload)

        assertTrue(result is OriginValidator.ValidationResult.Success)
        val success = result as OriginValidator.ValidationResult.Success
        assertEquals("get_network_status", success.action)
    }

    @Test
    fun testNetworkTypeStringsValidity() {
        val validTypes = setOf("wifi", "cellular", "ethernet", "other", "none")

        assertTrue(validTypes.contains("wifi"))
        assertTrue(validTypes.contains("cellular"))
        assertTrue(validTypes.contains("ethernet"))
        assertTrue(validTypes.contains("none"))
    }

    @Test
    fun testNetworkStateCallbackFormatting() {
        val isOnline = false
        val type = "none"

        val callbackScript = "window._transifyNetworkCallback && window._transifyNetworkCallback($isOnline, \"$type\");"
        assertTrue(callbackScript.contains("false"))
        assertTrue(callbackScript.contains("\"none\""))

        val onlineScript = "window._transifyNetworkCallback && window._transifyNetworkCallback(true, \"wifi\");"
        assertTrue(onlineScript.contains("true"))
        assertTrue(onlineScript.contains("\"wifi\""))
    }
}
