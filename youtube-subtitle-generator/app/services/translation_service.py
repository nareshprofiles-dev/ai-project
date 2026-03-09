"""
translation_service.py
----------------------
Translates Telugu transcription segments to English using Whisper's built-in
translation task — no separate model download required.

Whisper's `task="translate"` runs the already-downloaded model a second time
on the audio file and returns English text with matching segment timestamps.
We align the English segments with the original Telugu segments by index.
"""

from typing import List, Dict, Any

import whisper


def translate_segments(
    segments: List[Dict[str, Any]],
    wav_path: str = "",
    model_name: str = "small",
) -> List[Dict[str, Any]]:
    """
    Translate Telugu segments to English using Whisper's translate task.

    Whisper is re-run on the same audio file with task="translate", which
    produces English text for each segment. We match results to the original
    Telugu segments by index and add an "english_text" key to each.

    Args:
        segments:   List of segment dicts from transcription_service, each with
                    {"id", "start", "end", "text"}.
        wav_path:   Path to the original WAV file (needed for Whisper translate).
        model_name: Whisper model size to reuse (must match transcription model).

    Returns:
        The same list with "english_text" added to each segment.

    Raises:
        RuntimeError: If Whisper translation fails.
    """
    if not segments:
        return segments

    if not wav_path:
        # Fallback: keep Telugu text as-is if no audio path provided
        for seg in segments:
            seg["english_text"] = seg.get("text", "")
        return segments

    print(f"[Translation] Running Whisper translate pass (Telugu -> English) ...")
    print(f"  Model: '{model_name}' | Audio: {wav_path}")

    try:
        model = whisper.load_model(model_name)

        result = model.transcribe(
            wav_path,
            language="te",       # source language: Telugu
            task="translate",    # translate directly to English
            verbose=False,
            fp16=False,
        )
    except Exception as exc:
        raise RuntimeError(f"Whisper translation pass failed: {exc}") from exc

    # Build a list of English segments from Whisper's translate output
    english_segments = [
        seg["text"].strip()
        for seg in result.get("segments", [])
        if seg["text"].strip()
    ]

    print(f"[Translation] Received {len(english_segments)} English segment(s).")

    # Align English text to Telugu segments by index (best-effort)
    for i, seg in enumerate(segments):
        if i < len(english_segments):
            seg["english_text"] = english_segments[i]
        else:
            # Fallback: keep Telugu text if no matching English segment
            seg["english_text"] = seg.get("text", "")

    print("[Translation] Translation complete.")
    return segments
