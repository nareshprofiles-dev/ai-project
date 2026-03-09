"""
subtitle_generator.py
---------------------
Converts translated segments into an SRT subtitle file using the `srt` library.

SRT (SubRip Text) format:
  <index>
  <HH:MM:SS,mmm> --> <HH:MM:SS,mmm>
  <subtitle text>
  <blank line>

Each Whisper segment becomes one SRT cue with its start/end timestamp
and the English translation as the display text.
"""

import os
import datetime
from typing import List, Dict, Any

import srt


def generate_srt(
    segments: List[Dict[str, Any]],
    output_dir: str = "output",
    filename: str = "subtitles.srt",
) -> str:
    """
    Build an SRT file from translated segments and write it to disk.

    Args:
        segments:   List of segment dicts, each expected to contain:
                      - "start":        float  (seconds)
                      - "end":          float  (seconds)
                      - "english_text": str    (translated text)
        output_dir: Directory where the SRT file will be written.
        filename:   Output file name (default: subtitles.srt).

    Returns:
        Absolute path to the written SRT file.

    Raises:
        ValueError:  If segments list is empty.
        IOError:     If the file cannot be written.
    """
    if not segments:
        raise ValueError("No segments provided — cannot generate an empty SRT file.")

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    subtitles: List[srt.Subtitle] = []

    for index, seg in enumerate(segments, start=1):
        english_text = seg.get("english_text", "").strip()

        # Skip segments where translation is empty
        if not english_text:
            continue

        start_td = _seconds_to_timedelta(seg["start"])
        end_td = _seconds_to_timedelta(seg["end"])

        # Ensure end is always after start (guard against Whisper quirks)
        if end_td <= start_td:
            end_td = start_td + datetime.timedelta(milliseconds=500)

        subtitle = srt.Subtitle(
            index=index,
            start=start_td,
            end=end_td,
            content=english_text,
        )
        subtitles.append(subtitle)

    if not subtitles:
        raise ValueError(
            "All translated segments were empty — no SRT cues to write."
        )

    # Compose the full SRT file content
    srt_content = srt.compose(subtitles)

    try:
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(srt_content)
    except IOError as exc:
        raise IOError(f"Failed to write SRT file to '{output_path}': {exc}") from exc

    print(f"[Subtitle] SRT file written: {output_path}  ({len(subtitles)} cues)")
    return output_path


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _seconds_to_timedelta(seconds: float) -> datetime.timedelta:
    """Convert a float number of seconds to a datetime.timedelta."""
    total_ms = int(round(seconds * 1000))
    return datetime.timedelta(milliseconds=total_ms)
