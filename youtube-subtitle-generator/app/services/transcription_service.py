"""
transcription_service.py
------------------------
Transcribes Telugu audio (WAV) to Telugu text using OpenAI Whisper
running entirely on the local machine — no API keys required.

Whisper returns word-level or segment-level timestamps that we preserve
so the subtitle generator can build accurate SRT cues later.
"""

import os
from typing import List, Dict, Any

import whisper


# Default Whisper model size. "medium" gives a good balance between
# accuracy and speed for Telugu. Use "large-v3" for best accuracy.
DEFAULT_MODEL = "medium"


def transcribe_audio(
    wav_path: str,
    model_name: str = DEFAULT_MODEL,
) -> List[Dict[str, Any]]:
    """
    Transcribe a WAV file containing Telugu speech using Whisper.

    Whisper auto-detects the language, but we explicitly hint "te" (Telugu)
    to improve accuracy and avoid misdetection for short clips.

    Args:
        wav_path:   Path to the 16kHz mono WAV file.
        model_name: Whisper model to use ("tiny", "base", "small",
                    "medium", "large", "large-v2", "large-v3").

    Returns:
        A list of segment dicts, each containing:
          {
            "id":    int,         # segment index (0-based)
            "start": float,       # start time in seconds
            "end":   float,       # end time in seconds
            "text":  str,         # transcribed Telugu text for this segment
          }

    Raises:
        FileNotFoundError: If wav_path does not exist.
        RuntimeError:      If Whisper transcription fails.
    """
    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"WAV file not found: {wav_path}")

    print(f"[Transcription] Loading Whisper model: '{model_name}' ...")
    print("  (First run will download the model weights — this may take a moment.)")

    try:
        model = whisper.load_model(model_name)
    except Exception as exc:
        raise RuntimeError(f"Failed to load Whisper model '{model_name}': {exc}") from exc

    print(f"[Transcription] Transcribing: {wav_path}")
    print("  Language hint: Telugu (te)")

    try:
        result = model.transcribe(
            wav_path,
            language="te",          # Telugu ISO-639-1 code
            task="transcribe",      # 'transcribe' keeps source language; 'translate' → English
            verbose=False,
            # fp16=False forces CPU-safe float32 inference; remove if you have a GPU
            fp16=False,
        )
    except Exception as exc:
        raise RuntimeError(f"Whisper transcription failed: {exc}") from exc

    # Extract segment-level data (each segment ≈ one subtitle cue)
    segments: List[Dict[str, Any]] = [
        {
            "id": seg["id"],
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
        }
        for seg in result.get("segments", [])
        if seg["text"].strip()  # skip empty segments
    ]

    print(f"[Transcription] Produced {len(segments)} segment(s).")
    return segments
