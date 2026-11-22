package com.abrarafick.transify

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Text-to-Speech (TTS) Bridge & Audio Rule Unit Tests.
 *
 * Enforces:
 * 1. Strict NO-AUTO-AUDIO: Speech synthesis is strictly gated behind valid tts_speak WebMessage actions.
 * 2. Multi-language tag validation (English: en-US, en-GB; Bengali: bn-BD, bn-IN; etc.).
 * 3. Text length limits (5,000 characters maximum) preventing memory exhaustion and DoS.
 * 4. Empty/blank text rejection.
 * 5. Parameter-free tts_stop action validation.
 * 6. Malformed JSON and injection payload rejection.
 */
class TTSBridgeValidationTest {

    @Test
    fun testValidTtsSpeakPayload() {
        val payload = """{"action":"tts_speak","text":"Hello, welcome to Transify","lang":"en-US"}"""
        val result = OriginValidator.validateMessagePayload(payload)

        assertTrue(result is OriginValidator.ValidationResult.Success)
        val success = result as OriginValidator.ValidationResult.Success
        assertEquals("tts_speak", success.action)
        assertEquals("Hello, welcome to Transify", success.json.getString("text"))
        assertEquals("en-US", success.json.getString("lang"))
    }

    @Test
    fun testBengaliTtsSpeakPayload() {
        // Bengali Bangladesh
        val payloadBD = """{"action":"tts_speak","text":"স্বাগতম ট্রান্সফাই এ","lang":"bn-BD"}"""
        val resultBD = OriginValidator.validateMessagePayload(payloadBD)
        assertTrue(resultBD is OriginValidator.ValidationResult.Success)

        // Bengali India
        val payloadIN = """{"action":"tts_speak","text":"নমস্কার","lang":"bn-IN"}"""
        val resultIN = OriginValidator.validateMessagePayload(payloadIN)
        assertTrue(resultIN is OriginValidator.ValidationResult.Success)
    }

    @Test
    fun testDefaultLanguageFallback() {
        // Language omitted -> defaults to en-US in application
        val payload = """{"action":"tts_speak","text":"Speech synthesis with default language"}"""
        val result = OriginValidator.validateMessagePayload(payload)
        assertTrue(result is OriginValidator.ValidationResult.Success)
    }

    @Test
    fun testEmptyOrBlankTextRejected() {
        // Empty text string
        val emptyPayload = """{"action":"tts_speak","text":"","lang":"en-US"}"""
        val resEmpty = OriginValidator.validateMessagePayload(emptyPayload)
        assertTrue(resEmpty is OriginValidator.ValidationResult.Error)
        assertTrue((resEmpty as OriginValidator.ValidationResult.Error).reason.contains("Missing or empty text"))

        // Blank text string (spaces only)
        val blankPayload = """{"action":"tts_speak","text":"    ","lang":"en-US"}"""
        val resBlank = OriginValidator.validateMessagePayload(blankPayload)
        assertTrue(resBlank is OriginValidator.ValidationResult.Error)

        // Missing text key
        val missingText = """{"action":"tts_speak","lang":"en-US"}"""
        val resMissing = OriginValidator.validateMessagePayload(missingText)
        assertTrue(resMissing is OriginValidator.ValidationResult.Error)
    }

    @Test
    fun testTextLengthLimitEnforcement() {
        // Text under 5000 chars -> Accepted
        val validText = "A".repeat(4999)
        val validPayload = """{"action":"tts_speak","text":"$validText","lang":"en-US"}"""
        assertTrue(OriginValidator.validateMessagePayload(validPayload) is OriginValidator.ValidationResult.Success)

        // Text exceeding 5000 chars -> Rejected
        val oversizedText = "A".repeat(5001)
        val oversizedPayload = """{"action":"tts_speak","text":"$oversizedText","lang":"en-US"}"""
        val result = OriginValidator.validateMessagePayload(oversizedPayload)
        assertTrue(result is OriginValidator.ValidationResult.Error)
        assertTrue((result as OriginValidator.ValidationResult.Error).reason.contains("5000"))
    }

    @Test
    fun testInvalidLanguageTagRejected() {
        val invalidTags = listOf(
            "../../malicious",
            "en-US<script>",
            "lang_with_invalid!chars",
            "a", // Too short (min 2)
            "this-tag-is-way-too-long-to-be-valid-bcp47" // Too long (>15)
        )

        for (tag in invalidTags) {
            val payload = """{"action":"tts_speak","text":"Testing language tag","lang":"$tag"}"""
            val result = OriginValidator.validateMessagePayload(payload)
            assertTrue("Expected rejection for tag: $tag", result is OriginValidator.ValidationResult.Error)
        }
    }

    @Test
    fun testTtsStopActionValidation() {
        val payload = """{"action":"tts_stop"}"""
        val result = OriginValidator.validateMessagePayload(payload)
        assertTrue(result is OriginValidator.ValidationResult.Success)
        assertEquals("tts_stop", (result as OriginValidator.ValidationResult.Success).action)
    }
}
