"""
translation_service.py
----------------------
Translates Telugu transcription segments to English using Whisper's built-in
translation task — no separate model download required.

Whisper's `task="translate"` runs the already-downloaded model a second time
on the audio file and returns English text with segment timestamps.
When the translate pass produces richer segmentation than the transcription
pass, we prefer the translated segments directly so the final SRT keeps all
available subtitle cues.
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
    produces English text for each segment. If that translate pass yields
    enough segments, those translated segments become the subtitle source.
    Otherwise we fall back to aligning translated text onto the original
    transcription segments by index.

    Args:
        segments:   List of segment dicts from transcription_service, each with
                    {"id", "start", "end", "text"}.
        wav_path:   Path to the original WAV file (needed for Whisper translate).
        model_name: Whisper model size to reuse (must match transcription model).

    Returns:
        A segment list ready for SRT generation, each containing timestamps and
        an "english_text" field.

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
                "text": segments[index]["text"] if index < len(segments) else "",
                "english_text": english_text,
            }
        )

    print(f"[Translation] Received {len(translated_segments)} English segment(s).")

    if len(translated_segments) >= len(segments):
        print("[Translation] Using translated segment timestamps directly.")
        return translated_segments

    # Align English text to Telugu segments by index (best-effort)
    for i, seg in enumerate(segments):
        if i < len(translated_segments):
            seg["english_text"] = translated_segments[i]["english_text"]
        else:
            # Fallback: keep Telugu text if no matching English segment
            seg["english_text"] = seg.get("text", "")

    print("[Translation] Translation complete.")
    return segments
