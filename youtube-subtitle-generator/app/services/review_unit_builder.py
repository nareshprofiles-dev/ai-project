"""
review_unit_builder.py
----------------------
Merges Telugu transcription segments and English translation segments
into unified review rows.

Transcription timestamps are canonical: each transcription segment
defines one review row (precise sentence-level, word-timestamp-driven).
English text is assigned by finding the translation segment with the
greatest time overlap.

When multiple transcription segments share the same best-matching
translation segment, the English words are distributed proportionally
by duration to avoid duplicate text across adjacent rows.
"""

from collections import defaultdict
from typing import Any


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _split_words_proportional(
    english_text: str,
    te_indices: list[int],
    transcription_segments: list[dict[str, Any]],
) -> list[str]:
    """
    Divide english_text word-proportionally across te_indices by duration.
    Returns one string per entry in te_indices, preserving order.
    """
    words = english_text.strip().split()
    n = len(te_indices)

    if not words:
        return [""] * n
    if n == 1:
        return [english_text.strip()]

    durations = []
    for idx in te_indices:
        seg = transcription_segments[idx]
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start + 0.5))
        durations.append(max(0.1, end - start))

    total_dur = sum(durations)
    total_words = len(words)

    word_counts = [max(1, round(d / total_dur * total_words)) for d in durations]

    # Correct rounding drift so word counts sum exactly to total_words
    diff = sum(word_counts) - total_words
    if diff > 0:
        for _ in range(diff):
            peak = max(range(n), key=lambda i: word_counts[i])
            word_counts[peak] -= 1
    elif diff < 0:
        for _ in range(-diff):
            trough = min(range(n), key=lambda i: word_counts[i])
            word_counts[trough] += 1

    parts = []
    cursor = 0
    for count in word_counts:
        parts.append(" ".join(words[cursor: cursor + count]))
        cursor += count
    return parts


def build_review_rows(
    transcription_segments: list[dict[str, Any]],
    translation_segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Align English translation onto the Telugu transcription timeline.

    Pass 1 — for each transcription segment find the translation segment
              with the greatest time overlap.
    Pass 2 — group transcription segments that share the same best-match
              translation segment.
    Pass 3 — build rows; if a group has >1 member, distribute the English
              words proportionally by duration to avoid duplicate text.

    This guarantees:
      - Row timestamps always match the transcription (no drift)
      - No duplicate English text across adjacent rows
      - Telugu text is never placed in the English column
    """

    # --- Pass 1: best-matching translation index per transcription segment ---
    assignments: list[tuple[int | None, float]] = []
    for te_seg in transcription_segments:
        te_start = float(te_seg.get("start", 0.0))
        te_end = float(te_seg.get("end", te_start + 0.5))

        best_ov = 0.0
        best_tr: int | None = None
        for tr_idx, tr_seg in enumerate(translation_segments):
            tr_start = float(tr_seg.get("start", 0.0))
            tr_end = float(tr_seg.get("end", tr_start + 0.5))
            ov = _overlap(te_start, te_end, tr_start, tr_end)
            if ov > best_ov:
                best_ov = ov
                best_tr = tr_idx

        assignments.append((best_tr, best_ov))

    # --- Pass 2: group transcription indices by their assigned translation ---
    tr_to_te_group: dict[int, list[int]] = defaultdict(list)
    for te_idx, (tr_idx, _) in enumerate(assignments):
        if tr_idx is not None:
            tr_to_te_group[tr_idx].append(te_idx)

    # Pre-compute proportional splits for every translation segment claimed by >1 row
    distributed: dict[int, list[str]] = {}
    for tr_idx, te_group in tr_to_te_group.items():
        if len(te_group) > 1:
            tr_text = translation_segments[tr_idx].get("english_text", "")
            distributed[tr_idx] = _split_words_proportional(
                tr_text, te_group, transcription_segments
            )

    # --- Pass 3: build the final row list ---
    rows: list[dict[str, Any]] = []
    for te_idx, te_seg in enumerate(transcription_segments):
        te_start = float(te_seg.get("start", 0.0))
        te_end = float(te_seg.get("end", te_start + 0.5))
        telugu_text = te_seg.get("text", "").strip()

        tr_idx, ov = assignments[te_idx]
        if tr_idx is None or ov == 0.0:
            english_text = ""
        elif tr_idx in distributed:
            pos = tr_to_te_group[tr_idx].index(te_idx)
            english_text = distributed[tr_idx][pos]
        else:
            english_text = translation_segments[tr_idx].get("english_text", "").strip()

        rows.append(
            {
                "id": te_idx + 1,
                "start": te_start,
                "end": te_end,
                "telugu_original": telugu_text,
                "telugu_current": telugu_text,
                "english_original": english_text,
                "english_current": english_text,
                "edited": False,
                "needs_retranslate": False,
            }
        )

    return rows
