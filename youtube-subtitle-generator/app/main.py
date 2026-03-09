"""
main.py
-------
CLI entry point for the YouTube Telugu → English subtitle generator.

Usage:
    python app/main.py "https://youtube.com/watch?v=VIDEO_ID"

Optional flags:
    --model   Whisper model size (default: medium)
                choices: tiny | base | small | medium | large | large-v3
    --output  Output directory (default: output)

Full example:
    python app/main.py "https://youtu.be/abcXYZ123" --model small --output my_subs
"""

import argparse
import sys
import os

# ---------------------------------------------------------------------------
# Make sure `app` package is importable regardless of CWD
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.youtube_downloader import download_audio
from app.services.transcription_service import transcribe_audio
from app.services.translation_service import translate_segments
from app.services.subtitle_generator import generate_srt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate English SRT subtitles from a Telugu YouTube video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "url",
        help="YouTube video URL (Telugu audio).",
    )
    parser.add_argument(
        "--model",
        default="medium",
        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
        help="Whisper model size to use for transcription (default: medium).",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Directory where output files are saved (default: output).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    youtube_url = args.url
    model_name = args.model
    output_dir = args.output

    print("=" * 60)
    print("  Telugu YouTube -> English Subtitle Generator")
    print("=" * 60)
    print(f"  URL    : {youtube_url}")
    print(f"  Model  : {model_name}")
    print(f"  Output : {output_dir}")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1 — Download audio from YouTube
    # ------------------------------------------------------------------
    try:
        wav_path = download_audio(youtube_url, output_dir=output_dir)
    except RuntimeError as exc:
        print(f"\n[ERROR] Audio download failed:\n  {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 2 — Transcribe Telugu audio → Telugu text segments
    # ------------------------------------------------------------------
    try:
        segments = transcribe_audio(wav_path, model_name=model_name)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"\n[ERROR] Transcription failed:\n  {exc}")
        sys.exit(1)

    if not segments:
        print("\n[WARNING] Whisper produced no segments. The audio may be silent or too short.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 3 — Translate Telugu segments → English
    # ------------------------------------------------------------------
    try:
        segments = translate_segments(segments, wav_path=wav_path, model_name=model_name)
    except RuntimeError as exc:
        print(f"\n[ERROR] Translation failed:\n  {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 4 — Generate SRT subtitle file
    # ------------------------------------------------------------------
    try:
        srt_path = generate_srt(segments, output_dir=output_dir)
    except (ValueError, IOError) as exc:
        print(f"\n[ERROR] SRT generation failed:\n  {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    print()
    print("=" * 60)
    print(f"  Subtitles saved to: {srt_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
