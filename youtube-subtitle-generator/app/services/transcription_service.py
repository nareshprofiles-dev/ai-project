"""
transcription_service.py
------------------------
Transcribes Telugu audio (WAV) to Telugu text using OpenAI Whisper
running entirely on the local machine.

Whisper returns word-level or segment-level timestamps that we preserve
so the subtitle generator can build accurate SRT cues later.
"""

import os
from typing import Any, Dict, List

import whisper

from app.services.segment_utils import (
    normalize_segment_text,
    split_segments_by_sentence,
    split_word_timestamps_into_segments,
)


DEFAULT_MODEL = "large-v3"
TELUGU_INITIAL_PROMPT = (
    "ఇది తెలుగు ఆడియో. స్పష్టమైన తెలుగు పదాలు, వాక్యాలు, విరామ చిహ్నాలతో ఖచ్చితంగా లిప్యంతరీకరణ చేయండి."
)


def _run_transcription(model_name: str, wav_path: str) -> dict[str, Any]:
    print(f"[Transcription] Loading Whisper model: '{model_name}' ...")
    print("  (First run will download the model weights; this may take a moment.)")
    print(f"[Transcription] Transcribing: {wav_path}")
    print("  Language hint: Telugu (te)")

    try:
        model = whisper.load_model(model_name)
    except Exception as exc:
        raise RuntimeError(f"Failed to load Whisper model '{model_name}': {exc}") from exc

    try:
        return model.transcribe(
            wav_path,
            language="te",
            task="transcribe",
            verbose=False,
            word_timestamps=True,
            condition_on_previous_text=False,
            temperature=0.0,
            beam_size=None,
            best_of=None,
            compression_ratio_threshold=1.8,
            logprob_threshold=-1.0,
            no_speech_threshold=0.3,
            initial_prompt=TELUGU_INITIAL_PROMPT,
            fp16=False,
        )
    except Exception as exc:
        raise RuntimeError(f"Whisper transcription failed: {exc}") from exc


def _build_sentence_segments(result: dict[str, Any]) -> list[dict[str, Any]]:
    segments: List[Dict[str, Any]] = [
        {
            "id": int(seg.get("id", index)),
            "start": float(seg.get("start", 0.0)),
            "end": float(seg.get("end", 0.0)),
            "text": normalize_segment_text(seg.get("text", "")),
        }
        for index, seg in enumerate(result.get("segments", []))
        if normalize_segment_text(seg.get("text", ""))
    ]

    word_timestamps: List[Dict[str, Any]] = []
    for seg in result.get("segments", []):
        for word in seg.get("words", []):
            word_timestamps.append(
                {
                    "text": word.get("word", ""),
                    "start": word.get("start", seg.get("start", 0.0)),
                    "end": word.get("end", seg.get("end", 0.0)),
                }
            )

    sentence_segments = split_word_timestamps_into_segments(word_timestamps, segments)
    if not sentence_segments:
        sentence_segments = split_segments_by_sentence(segments)

    return sentence_segments


def _looks_like_low_quality_telugu(segments: list[dict[str, Any]]) -> bool:
    if not segments:
        return True

    total_chars = 0
    telugu_chars = 0
    short_segments = 0

    for segment in segments:
        text = normalize_segment_text(segment.get("text", ""))
        total_chars += len(text)
        telugu_chars += sum(1 for char in text if "\u0C00" <= char <= "\u0C7F")
        if len(text) < 8:
            short_segments += 1

    if total_chars == 0:
        return True

    telugu_ratio = telugu_chars / total_chars
    return telugu_ratio < 0.45 or short_segments >= max(2, len(segments) // 2)


def transcribe_audio(
    wav_path: str,
    model_name: str = DEFAULT_MODEL,
) -> List[Dict[str, Any]]:
    """
    Transcribe a WAV file containing Telugu speech using Whisper.
    """
    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"WAV file not found: {wav_path}")

    result = _run_transcription(model_name, wav_path)
    sentence_segments = _build_sentence_segments(result)

    if model_name != "large-v3" and _looks_like_low_quality_telugu(sentence_segments):
        print("[Transcription] Telugu output still looks weak. Retrying with 'large-v3'...")
        result = _run_transcription("large-v3", wav_path)
        sentence_segments = _build_sentence_segments(result)

    print(f"[Transcription] Produced {len(sentence_segments)} sentence-level segment(s).")
    return sentence_segments
