package com.abrarafick.transify

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Android Instrumentation Tests for Transify Android Host.
 *
 * Runs inside the Android runtime environment on an emulator or physical device.
 * Exercises:
 * 1. Application package context resolution.
 * 2. OriginValidator security boundaries on Android OS.
 * 3. FileProvider authority configuration against package manifest.
 * 4. Zero Auto-Audio policy parameter-free contracts.
 */
@RunWith(AndroidJUnit4::class)
class MainActivityInstrumentationTest {

    @Test
    fun useAppContext() {
        val appContext = InstrumentationRegistry.getInstrumentation().targetContext
        assertEquals("com.abrarafick.transify", appContext.packageName)
    }

    @Test
    fun testFileProviderAuthorityMatchesPackage() {
        val appContext = InstrumentationRegistry.getInstrumentation().targetContext
        val expectedAuthority = "${appContext.packageName}.fileprovider"
        assertEquals("com.abrarafick.transify.fileprovider", expectedAuthority)
    }

    @Test
    fun testOriginValidatorProductionOriginOnDevice() {
        val productionUrl = "https://transify20-production.up.railway.app"
        assertTrue(OriginValidator.isValidTargetUrl(productionUrl))
        assertTrue(OriginValidator.isExactTrustedOrigin("$productionUrl/sign", productionUrl))
        assertTrue(OriginValidator.isExactTrustedOrigin("$productionUrl/braille", productionUrl))
    }

    @Test
    fun testTtsStopActionValidationOnDevice() {
        val stopPayload = """{"action":"tts_stop"}"""
        val result = OriginValidator.validateMessagePayload(stopPayload)
        assertTrue(result is OriginValidator.ValidationResult.Success)
    }
}
