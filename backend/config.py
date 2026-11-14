import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Gnani Voice AI Config (Prisma STT + Timbre TTS)
GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
GNANI_STT_URL = os.getenv("GNANI_STT_URL", "https://api.vachana.ai/stt/v3")
GNANI_TTS_URL = os.getenv("GNANI_TTS_URL", "https://api.vachana.ai/api/v1/tts/inference")
GNANI_STT_MODEL = os.getenv("GNANI_STT_MODEL", "prisma-v3.0")
GNANI_TTS_MODEL = os.getenv("GNANI_TTS_MODEL", "timbre-v3.0")
GNANI_DEFAULT_VOICE = os.getenv("GNANI_DEFAULT_VOICE", "Nalini")

# Reasoning LLM Config (NVIDIA NIM Nemotron / Evon 30B)
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY", "")
NVIDIA_NIM_URL = os.getenv("NVIDIA_NIM_URL", "https://integrate.api.nvidia.com/v1/chat/completions")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-4-340b-instruct")

# Storage & Cache Directories
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
AUDIO_DIR = DATA_DIR / "audio"
QDRANT_DIR = DATA_DIR / "qdrant_db"

for d in [DATA_DIR, UPLOAD_DIR, AUDIO_DIR, QDRANT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Legal vocabulary biasing for Gnani Prisma STT
LEGAL_KEYTERMS = (
    "lease,rent,deposit,lock-in period,penalty,maintenance charges,termination,"
    "lessor,lessee,landlord,tenant,indemnity,subletting,stamp duty,registration,"
    "possession,escalation clause,force majeure,arbitration,default,notice period"
)
