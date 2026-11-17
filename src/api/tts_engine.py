"""
Text-to-Speech (TTS) Service for Transify.
Provides audio synthesis support for browser playback and screen reader integration.
"""

import io
import wave
import math
import struct
import base64
from typing import Dict, Any, Optional


class TTSService:
    """
    Synthesizes speech notifications and accessible audio tokens.
    """

    def generate_tone_wav(self, duration: float = 0.3, freq: float = 520.0) -> bytes:
        """Generates standard uncompressed 16-bit PCM WAV notification chime."""
        sample_rate = 16000
        n_samples = int(sample_rate * duration)
        buf = io.BytesIO()

        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)

            for i in range(n_samples):
                # Smooth envelope to avoid clicking
                env = math.sin(math.pi * i / n_samples)
                val = int(math.sin(2.0 * math.pi * freq * (i / sample_rate)) * env * 14000)
                wf.writeframes(struct.pack('<h', val))

        return buf.getvalue()

    def synthesize(self, text: str, voice: Optional[str] = None, speed: float = 1.0) -> Dict[str, Any]:
        """
        Processes TTS request for text.
        Returns synthesized audio data URI and client-side speech directives.
        """
        if not text or not text.strip():
            return {"success": False, "error": "Empty text provided"}

        clean_text = text.replace("\n", " ").strip()
        chime_bytes = self.generate_tone_wav()
        b64_audio = base64.b64encode(chime_bytes).decode("ascii")

        return {
            "success": True,
            "text": clean_text,
            "voice": voice or "en-US",
            "speed": speed,
            "format": "audio/wav",
            "audio_data_uri": f"data:audio/wav;base64,{b64_audio}",
            "audio_uri": f"data:audio/wav;base64,{b64_audio}",
            "client_speech_supported": True,
            "client_utterance": {
                "text": clean_text,
                "lang": "en-US",
                "rate": speed,
                "pitch": 1.0
            }
        }


tts_service = TTSService()
