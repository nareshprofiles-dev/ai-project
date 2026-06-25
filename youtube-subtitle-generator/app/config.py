"""
config.py
---------
Single source of truth for all model and inference configuration.
Values are loaded from the .env file at the project root.

To change a model or parameter, edit .env — do not touch service code.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── Whisper ASR model ─────────────────────────────────────────────────────────
WHISPER_DEFAULT_MODEL: str = os.getenv("WHISPER_DEFAULT_MODEL", "large-v3")
WHISPER_FALLBACK_MODEL: str = os.getenv("WHISPER_FALLBACK_MODEL", "large-v3")
WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "te")

# ── Whisper inference parameters ──────────────────────────────────────────────
WHISPER_FP16: bool = os.getenv("WHISPER_FP16", "false").lower() == "true"
WHISPER_TEMPERATURE: float = float(os.getenv("WHISPER_TEMPERATURE", "0.0"))

_beam = os.getenv("WHISPER_BEAM_SIZE", "").strip()
WHISPER_BEAM_SIZE: int | None = int(_beam) if _beam else None

_best = os.getenv("WHISPER_BEST_OF", "").strip()
WHISPER_BEST_OF: int | None = int(_best) if _best else None

WHISPER_COMPRESSION_RATIO_THRESHOLD: float = float(
    os.getenv("WHISPER_COMPRESSION_RATIO_THRESHOLD", "1.8")
)
WHISPER_LOGPROB_THRESHOLD: float = float(os.getenv("WHISPER_LOGPROB_THRESHOLD", "-1.0"))
WHISPER_NO_SPEECH_THRESHOLD: float = float(os.getenv("WHISPER_NO_SPEECH_THRESHOLD", "0.3"))

# ── Translation backend ───────────────────────────────────────────────────────
TRANSLATION_BACKEND: str = os.getenv("TRANSLATION_BACKEND", "whisper")

# ── Paths ─────────────────────────────────────────────────────────────────────
DEFAULT_OUTPUT_DIR: str = os.getenv("DEFAULT_OUTPUT_DIR", "output")
CACHE_DIRNAME: str = os.getenv("CACHE_DIRNAME", "cache")
