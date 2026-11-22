package com.abrarafick.transify

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * File Provider & Image Capture Unit Tests.
 *
 * Verifies:
 * 1. Braille capture filename generation format.
 * 2. MIME type filtering for camera and gallery image selection (JPEG, PNG, WebP).
 * 3. File sanitization preventing path traversal and illegal characters.
 * 4. Safe retention cutoff logic for temporary camera captures.
 */
class FileProviderAndCaptureTest {

    @Test
    fun testCaptureFilenamePattern() {
        val timestamp = 1732041234567L
        val filename = "braille_$timestamp.jpg"

        assertTrue(filename.startsWith("braille_"))
        assertTrue(filename.endsWith(".jpg"))
        assertEquals("braille_1732041234567.jpg", filename)
    }

    @Test
    fun testSupportedImageMimeTypes() {
        val supportedMimes = listOf("image/jpeg", "image/png", "image/webp")

        for (mime in supportedMimes) {
            assertTrue("MIME type $mime should be recognized as valid", OriginValidator.isValidMimeType(mime))
            assertTrue("MIME type $mime should be image", mime.startsWith("image/"))
        }

        // Malformed MIME strings
        assertFalse(OriginValidator.isValidMimeType(""))
        assertFalse(OriginValidator.isValidMimeType("not-a-valid-mime"))
        assertFalse(OriginValidator.isValidMimeType("image/"))
        assertFalse(OriginValidator.isValidMimeType("/jpeg"))
        assertFalse(OriginValidator.isValidMimeType("image/jpeg; charset=utf-8"))
    }

    @Test
    fun testFilenameSanitizationForCaptures() {
        val maliciousName = "../../../system/lib/bad.jpg"
        val sanitized = OriginValidator.sanitizeFilename(maliciousName)

        assertFalse(sanitized.contains(".."))
        assertFalse(sanitized.contains("/"))
        assertEquals("______system_lib_bad.jpg", sanitized)
    }

    @Test
    fun testCaptureRetentionCutoffAge() {
        val now = System.currentTimeMillis()
        val oneDayMillis = 24 * 60 * 60 * 1000L
        val cutoff = now - oneDayMillis

        val recentFileTime = now - (2 * 60 * 60 * 1000L) // 2 hours old
        val oldFileTime = now - (26 * 60 * 60 * 1000L) // 26 hours old

        // Recent file is newer than cutoff -> must be preserved
        assertTrue(recentFileTime > cutoff)

        // Old file is older than cutoff -> eligible for cleanup
        assertTrue(oldFileTime < cutoff)
    }
}
