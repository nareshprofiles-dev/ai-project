import re
from typing import Any


TELUGU_MOJIBAKE_MARKERS = ("à°", "à±", "ï¿½", "\ufffd")
SENTENCE_BREAK_PATTERN = re.compile(r"(?<=[.!?।॥])\s+")
MAX_SEGMENT_SECONDS = 6.5
MAX_SEGMENT_CHARS = 56
MAX_SEGMENT_WORDS = 14


def normalize_segment_text(text: Any) -> str:
    cleaned = str(text or "").replace("\u001b", "").strip()
    if not cleaned:
        return ""

    if any(marker in cleaned for marker in TELUGU_MOJIBAKE_MARKERS):
        try:
            repaired = cleaned.encode("latin-1").decode("utf-8")
            repaired = repaired.replace("\u001b", "").strip()
            if repaired:
                cleaned = repaired
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return cleaned.replace("\r\n", "\n").replace("\r", "\n").strip()


def split_segments_by_sentence(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sentence_segments: list[dict[str, Any]] = []

    for segment in segments:
        text = normalize_segment_text(segment.get("text", ""))
        if not text:
            continue

        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        if end <= start:
            end = start + 0.5

        parts = [part.strip() for part in SENTENCE_BREAK_PATTERN.split(text) if part.strip()]
        if len(parts) <= 1:
            sentence_segments.append(
                {
                    "id": len(sentence_segments),
                    "start": start,
                    "end": end,
                    "text": text,
                }
            )
            continue

        total_chars = sum(len(part) for part in parts) or len(parts)
        cursor = start
        duration = end - start

        for index, part in enumerate(parts):
            share = len(part) / total_chars if total_chars else 1 / len(parts)
            next_end = end if index == len(parts) - 1 else cursor + (duration * share)
            sentence_segments.append(
                {
                    "id": len(sentence_segments),
                    "start": round(cursor, 2),
                    "end": round(max(next_end, cursor + 0.2), 2),
                    "text": part,
                }
            )
            cursor = next_end

    return sentence_segments


def split_word_timestamps_into_segments(
    words: list[dict[str, Any]],
    fallback_segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized_words: list[dict[str, Any]] = []

    for word in words:
        text = normalize_segment_text(word.get("text", ""))
        if not text:
            continue

        try:
            start = float(word.get("start", 0.0))
            end = float(word.get("end", start))
        except (TypeError, ValueError):
            continue

        if end <= start:
            end = start + 0.1

        normalized_words.append(
            {
                "text": text,
                "start": start,
                "end": end,
            }
        )

    if not normalized_words:
        return split_segments_by_sentence(fallback_segments)

    grouped_segments: list[dict[str, Any]] = []
    current_words: list[dict[str, Any]] = []
    current_start = 0.0

    def flush() -> None:
        nonlocal current_words, current_start
        if not current_words:
            return

        text = " ".join(word["text"] for word in current_words).strip()
        if text:
            grouped_segments.append(
                {
                    "id": len(grouped_segments),
                    "start": round(current_start, 2),
                    "end": round(current_words[-1]["end"], 2),
                    "text": text,
                }
            )

        current_words = []
        current_start = 0.0

    for word in normalized_words:
        if not current_words:
            current_words = [word]
            current_start = word["start"]
            continue

        preview_words = current_words + [word]
        preview_text = " ".join(item["text"] for item in preview_words).strip()
        preview_duration = word["end"] - current_start
        previous_word = current_words[-1]
        gap = max(0.0, word["start"] - previous_word["end"])
        ends_sentence = previous_word["text"].endswith((".", "!", "?", "।", "॥"))

        should_flush = (
            ends_sentence
            or preview_duration >= MAX_SEGMENT_SECONDS
            or len(preview_text) >= MAX_SEGMENT_CHARS
            or len(preview_words) >= MAX_SEGMENT_WORDS
            or gap >= 0.55
        )

        if should_flush:
            flush()
            current_words = [word]
            current_start = word["start"]
            continue

        current_words.append(word)

    flush()
    return grouped_segments
