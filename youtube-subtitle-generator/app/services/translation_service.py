"""
translation_service.py
----------------------
Translates Telugu audio to English using Whisper's built-in translate task.

Returns raw Whisper translate segments (timestamps + english_text).
Alignment with transcription segments is handled downstream by
review_unit_builder, which uses transcription timestamps as canonical.
"""

from typing import List, Dict, Any

import whisper

from app.config import (
    WHISPER_BEAM_SIZE,
    WHISPER_BEST_OF,
    WHISPER_COMPRESSION_RATIO_THRESHOLD,
    WHISPER_DEFAULT_MODEL,
    WHISPER_FP16,
    WHISPER_LANGUAGE,
    WHISPER_LOGPROB_THRESHOLD,
    WHISPER_NO_SPEECH_THRESHOLD,
    WHISPER_TEMPERATURE,
)


def translate_segments(
    segments: List[Dict[str, Any]],
    wav_path: str = "",
    model_name: str = WHISPER_DEFAULT_MODEL,
) -> List[Dict[str, Any]]:
    """
    Run Whisper's translate task and return English segments.

    Args:
        segments:   Transcription segments (used only to check for empty input).
        wav_path:   Path to the original WAV file.
        model_name: Whisper model size (must match the transcription model).

    Returns:
        List of dicts with {"id", "start", "end", "english_text"} from the
        translate pass.  Empty list if wav_path is missing or Whisper returns
        nothing.  Never contains Telugu text — alignment is left to the caller.

    Raises:
        RuntimeError: If Whisper translation fails.
    """
    if not segments:
        return []

    if not wav_path:
        return []

    print(f"[Translation] Running Whisper translate pass (Telugu -> English) ...")
    print(f"  Model: '{model_name}' | Audio: {wav_path}")

    try:
        model = whisper.load_model(model_name)

        result = model.transcribe(
            wav_path,
            language=WHISPER_LANGUAGE,
            task="translate",
            verbose=False,
            condition_on_previous_text=False,
            temperature=WHISPER_TEMPERATURE,
            beam_size=WHISPER_BEAM_SIZE,
            best_of=WHISPER_BEST_OF,
            compression_ratio_threshold=WHISPER_COMPRESSION_RATIO_THRESHOLD,
            logprob_threshold=WHISPER_LOGPROB_THRESHOLD,
            no_speech_threshold=WHISPER_NO_SPEECH_THRESHOLD,
            fp16=WHISPER_FP16,
        )
    except Exception as exc:
        raise RuntimeError(f"Whisper translation pass failed: {exc}") from exc

    translated_segments = []
    for index, seg in enumerate(result.get("segments", [])):
        english_text = seg.get("text", "").strip()
        if not english_text:
            continue

        translated_segments.append(
            {
                "id": int(seg.get("id", index)),
                "start": float(seg["start"]),
                "end": float(seg["end"]),
                "english_text": english_text,
            }
        )

    print(f"[Translation] Received {len(translated_segments)} English segment(s).")
    return translated_segments
