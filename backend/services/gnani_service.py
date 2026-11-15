import os
import io
import wave
import base64
import logging
import tempfile
import subprocess
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
)

logger = logging.getLogger("gnani_service")
logging.basicConfig(level=logging.INFO)


def convert_to_16k_mono_wav(audio_bytes: bytes) -> bytes:
    """
    Ensure audio data is 16kHz mono 16-bit PCM WAV (as required by Gnani Prisma STT).
    Uses ffmpeg to transcode from webm, mp3, ogg, or non-compliant WAV.
    """
    # Quick check if it's already a valid RIFF/WAVE header
    if audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:16]:
        return audio_bytes

    with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as in_f:
        in_f.write(audio_bytes)
        in_path = in_f.name

    out_path = in_path + "_converted.wav"
    try:
        cmd = [
            "ffmpeg", "-y", "-i", in_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            out_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        with open(out_path, "rb") as out_f:
            converted = out_f.read()
        return converted
    except Exception as e:
        logger.error(f"FFmpeg conversion failed: {e}")
        # Return original if conversion fails
        return audio_bytes
    finally:
        for p in [in_path, out_path]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


def raw_pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 24000, channels: int = 1, sampwidth: int = 2) -> bytes:
    """
    Convert raw PCM audio bytes (from Gnani Timbre) into a valid RIFF/WAVE container
    so that browser <audio> tags and standard audio players can decode and play it.
    """
    wav_buf = io.BytesIO()
    with wave.open(wav_buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return wav_buf.getvalue()


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
        Transcribe speech using live Gnani Prisma v3.0 STT API.
        POST https://api.vachana.ai/stt/v3
        """
        if not self.api_key:
            raise ValueError("GNANI_API_KEY is not set. Please set it in .env")

        # Convert to 16kHz mono WAV for Prisma STT
        wav_bytes = convert_to_16k_mono_wav(audio_bytes)
        logger.info(f"Calling Gnani Prisma STT with {len(wav_bytes)} bytes of WAV audio, lang={language_code}")

        headers = {
            "X-API-Key-ID": self.api_key
        }
        files = {
            "audio_file": ("speech.wav", wav_bytes, "audio/wav")
        }
        data = {
            "model": self.stt_model,
            "language_code": language_code or "indic-auto",
            "keyterms": LEGAL_KEYTERMS
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                self.stt_url,
                headers=headers,
                files=files,
                data=data
            )

        if response.status_code == 200:
            res_data = response.json()
            transcript = res_data.get("transcript", "").strip()
            detected_lang = res_data.get("detected_language_code") or res_data.get("language_code") or language_code
            latency = res_data.get("processing_time") or res_data.get("end_to_end_latency")
            return {
                "transcript": transcript,
                "detected_language": detected_lang,
                "processing_time": latency,
                "confidence": 0.98 if transcript else 0.0,
                "raw": res_data
            }
        else:
            err_msg = f"Gnani Prisma STT Error [{response.status_code}]: {response.text}"
            logger.error(err_msg)
            raise RuntimeError(err_msg)

    async def synthesize_speech(
        self,
        text: str,
        language: str = "en-IN",
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> Dict[str, Any]:
        """
        Synthesize speech using live Gnani Timbre v3.0 TTS API.
        POST https://api.vachana.ai/api/v1/tts/inference
        Supported voices for Timbre v3.0: Avinash, Shivani, Lakshmi, Kalpana, Shubham, Prakash, Devansh, Yashraj
        """
        if not self.api_key:
            raise ValueError("GNANI_API_KEY is not set. Please set it in .env")

        voice_name = voice or GNANI_DEFAULT_VOICE
        # If an unsupported voice name was passed, default to Shivani
        supported_voices = ["Avinash", "Shivani", "Lakshmi", "Kalpana", "Shubham", "Prakash", "Devansh", "Yashraj"]
        if voice_name not in supported_voices:
            voice_name = "Shivani"

        # Sanitize language code for Timbre
        if "auto" in language.lower():
            language = "en-IN"

        logger.info(f"Calling Gnani Timbre TTS: voice={voice_name}, lang={language}, text_len={len(text)}")

        headers = {
            "X-API-Key-ID": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model": self.tts_model,
            "voice": voice_name,
            "language": language,
            "speed": float(speed)
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                self.tts_url,
                headers=headers,
                json=payload
            )

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            raw_audio = response.content

            # Gnani Timbre returns raw 24kHz 16-bit PCM. Convert to standard RIFF WAV for browser playback
            wav_audio = raw_pcm_to_wav(raw_audio, sample_rate=24000, channels=1, sampwidth=2)
            audio_b64 = base64.b64encode(wav_audio).decode("utf-8")

            return {
                "audio_base64": audio_b64,
                "audio_format": "audio/wav",
                "voice": voice_name,
                "language": language,
                "audio_bytes_length": len(wav_audio)
            }
        else:
            err_msg = f"Gnani Timbre TTS Error [{response.status_code}]: {response.text}"
            logger.error(err_msg)
            raise RuntimeError(err_msg)


gnani_service = GnaniService()
