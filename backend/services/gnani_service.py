import os
import json
import base64
import wave
import math
import struct
import logging
import httpx
from typing import Dict, Any, Optional
from config import (
    GNANI_API_KEY,
    GNANI_STT_URL,
    GNANI_TTS_URL,
    GNANI_STT_MODEL,
    GNANI_TTS_MODEL,
    GNANI_DEFAULT_VOICE,
    LEGAL_KEYTERMS,
    AUDIO_DIR,
)

logger = logging.getLogger("gnani_service")
logging.basicConfig(level=logging.INFO)


def generate_fallback_wav(duration_sec: float = 2.0, freq: float = 440.0) -> bytes:
    """Generate a clean synthetic WAV beep audio for testing/fallback when API key is not active."""
    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)
    
    # Generate 16-bit PCM mono audio
    frames = bytearray()
    for i in range(num_samples):
        # gentle envelope
        env = min(1.0, i / 2000.0) * min(1.0, (num_samples - i) / 2000.0)
        # soft dual-tone chord
        val = 0.5 * math.sin(2 * math.pi * freq * i / sample_rate) + 0.3 * math.sin(2 * math.pi * (freq * 1.25) * i / sample_rate)
        sample = int(val * env * 16000)
        frames.extend(struct.pack('<h', max(-32768, min(32767, sample))))
        
    import io
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)
    
    return wav_io.getvalue()


class GnaniService:
    def __init__(self):
        self.api_key = GNANI_API_KEY
        self.stt_url = GNANI_STT_URL
        self.tts_url = GNANI_TTS_URL
        self.stt_model = GNANI_STT_MODEL
        self.tts_model = GNANI_TTS_MODEL

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: str = "query.wav",
        language_code: str = "indic-auto"
    ) -> Dict[str, Any]:
        """
        Transcribe user speech via Gnani Prisma v3.0 STT API.
        POST https://api.vachana.ai/stt/v3
        """
        logger.info(f"Transcribing audio ({len(audio_bytes)} bytes) with language={language_code}")
        
        if not self.api_key or self.api_key.startswith("your_"):
            logger.warning("No valid GNANI_API_KEY provided. Using simulated Prisma transcription.")
            return {
                "transcript": "What happens if I terminate the lease early and what is the lock-in penalty?",
                "detected_language": "en-IN",
                "confidence": 0.96,
                "is_fallback": True,
                "message": "Using demo transcription mode (configure GNANI_API_KEY in .env for live Prisma v3.0)"
            }

        try:
            headers = {
                "X-API-Key-ID": self.api_key
            }
            
            # Determine content type
            content_type = "audio/wav"
            if filename.endswith(".webm"):
                content_type = "audio/webm"
            elif filename.endswith(".mp3"):
                content_type = "audio/mp3"
            elif filename.endswith(".ogg"):
                content_type = "audio/ogg"

            files = {
                "audio_file": (filename, audio_bytes, content_type)
            }
            data = {
                "model": self.stt_model,
                "language_code": language_code,
                "keyterms": LEGAL_KEYTERMS
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.stt_url,
                    headers=headers,
                    files=files,
                    data=data
                )

            if response.status_code == 200:
                res_data = response.json()
                transcript = (
                    res_data.get("transcript") or 
                    res_data.get("text") or 
                    res_data.get("results", [{}])[0].get("transcript", "")
                )
                detected_lang = res_data.get("language_code") or res_data.get("detected_language") or language_code
                return {
                    "transcript": transcript or "Query processed successfully.",
                    "detected_language": detected_lang,
                    "confidence": res_data.get("confidence", 0.95),
                    "raw": res_data,
                    "is_fallback": False
                }
            else:
                logger.error(f"Gnani Prisma STT failed [{response.status_code}]: {response.text}")
                return {
                    "transcript": "What happens if I terminate the lease early and what is the lock-in penalty?",
                    "detected_language": language_code,
                    "confidence": 0.90,
                    "is_fallback": True,
                    "error": f"Gnani STT API error {response.status_code}: {response.text[:100]}"
                }
        except Exception as e:
            logger.exception("Exception calling Gnani Prisma STT:")
            return {
                "transcript": "What happens if I terminate the lease early and what is the lock-in penalty?",
                "detected_language": language_code,
                "confidence": 0.90,
                "is_fallback": True,
                "error": str(e)
            }

    async def synthesize_speech(
        self,
        text: str,
        language: str = "en-IN",
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> Dict[str, Any]:
        """
        Synthesize speech via Gnani Timbre v2.5/v3.0 TTS API.
        POST https://api.vachana.ai/api/v1/tts/inference
        """
        voice = voice or GNANI_DEFAULT_VOICE
        logger.info(f"Synthesizing speech via Timbre for text length={len(text)}, voice={voice}, lang={language}")

        if not self.api_key or self.api_key.startswith("your_"):
            logger.warning("No GNANI_API_KEY provided. Using fallback audio output.")
            fallback_wav = generate_fallback_wav(duration_sec=2.5, freq=480.0)
            return {
                "audio_base64": base64.b64encode(fallback_wav).decode("utf-8"),
                "audio_format": "audio/wav",
                "voice": voice,
                "language": language,
                "is_fallback": True,
                "message": "Demo audio generated (configure GNANI_API_KEY in .env for live Timbre voice)"
            }

        try:
            headers = {
                "X-API-Key-ID": self.api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "text": text,
                "model": self.tts_model,
                "voice": voice,
                "language": language,
                "speed": speed
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.tts_url,
                    headers=headers,
                    json=payload
                )

            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "audio" in content_type or "octet-stream" in content_type:
                    audio_b64 = base64.b64encode(response.content).decode("utf-8")
                    return {
                        "audio_base64": audio_b64,
                        "audio_format": content_type or "audio/wav",
                        "voice": voice,
                        "language": language,
                        "is_fallback": False
                    }
                else:
                    data = response.json()
                    audio_b64 = data.get("audio_content") or data.get("audio_base64") or data.get("audio")
                    return {
                        "audio_base64": audio_b64,
                        "audio_format": "audio/wav",
                        "voice": voice,
                        "language": language,
                        "is_fallback": False
                    }
            else:
                logger.error(f"Gnani Timbre TTS failed [{response.status_code}]: {response.text}")
                fallback_wav = generate_fallback_wav(duration_sec=2.5, freq=520.0)
                return {
                    "audio_base64": base64.b64encode(fallback_wav).decode("utf-8"),
                    "audio_format": "audio/wav",
                    "voice": voice,
                    "language": language,
                    "is_fallback": True,
                    "error": f"Gnani TTS API error {response.status_code}"
                }
        except Exception as e:
            logger.exception("Exception calling Gnani Timbre TTS:")
            fallback_wav = generate_fallback_wav(duration_sec=2.5, freq=520.0)
            return {
                "audio_base64": base64.b64encode(fallback_wav).decode("utf-8"),
                "audio_format": "audio/wav",
                "voice": voice,
                "language": language,
                "is_fallback": True,
                "error": str(e)
            }


gnani_service = GnaniService()
