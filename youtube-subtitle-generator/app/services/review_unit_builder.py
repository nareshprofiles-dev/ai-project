"""
review_unit_builder.py
----------------------
Merges Telugu transcription segments and English translation segments
into a unified list of review rows.

The translation timeline is canonical: each translation segment defines
one review row, and Telugu text is aligned into it by timestamp overlap.
If no translation segments exist, falls back to transcription-only rows.
"""

from typing import Any


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def build_review_rows(
    transcription_segments: list[dict[str, Any]],
    translation_segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Align Telugu transcription onto the English translation timeline.

    For each translation segment:
      - Find all transcription segments that overlap its time window
      - Concatenate their Telugu text as the Telugu draft for the row
      - If no transcription segments overlap, leave Telugu text empty

    Fallback: if translation produced no segments, each transcription
    segment becomes its own row with an empty English side.

    Returns a list of review row dicts ready to be sent to the frontend
    or written to the review-rows cache.
    """
    rows: list[dict[str, Any]] = []

    if translation_segments:
        for idx, trans_seg in enumerate(translation_segments):
            t_start = float(trans_seg.get("start", 0.0))
            t_end = float(trans_seg.get("end", t_start + 0.5))
            english_text = trans_seg.get("english_text", trans_seg.get("text", "")).strip()

            matching_telugu: list[str] = []
            for te_seg in transcription_segments:
                te_start = float(te_seg.get("start", 0.0))
                te_end = float(te_seg.get("end", te_start + 0.5))
                if _overlap(t_start, t_end, te_start, te_end) > 0.0:
                    text = te_seg.get("text", "").strip()
                    if text:
                        matching_telugu.append(text)

            telugu_text = " ".join(matching_telugu)

            rows.append({
                "id": idx + 1,
                "start": t_start,
                "end": t_end,
                "telugu_original": telugu_text,
                "telugu_current": telugu_text,
                "english_original": english_text,
                "english_current": english_text,
                "source_timeline": "translate",
                "edited": False,
                "needs_retranslate": False,
            })

    else:
        # Translation pass produced nothing — use transcription segments as-is
        for idx, te_seg in enumerate(transcription_segments):
            telugu_text = te_seg.get("text", "").strip()
            rows.append({
                "id": idx + 1,
                "start": float(te_seg.get("start", 0.0)),
                "end": float(te_seg.get("end", 0.0)),
                "telugu_original": telugu_text,
                "telugu_current": telugu_text,
                "english_original": "",
                "english_current": "",
                "source_timeline": "transcribe",
                "edited": False,
                "needs_retranslate": False,
            })

    return rows
