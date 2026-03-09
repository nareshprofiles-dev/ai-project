# CLAUDE.md — Project Notes for Claude Code

## Project Overview
Telugu YouTube video → English SRT subtitle generator.
Fully local pipeline: yt-dlp → ffmpeg → Whisper → MarianMT → srt

## Key Design Decisions

- **Whisper language hint**: We pass `language="te"` explicitly to avoid
  misdetection on short or noisy audio clips.
- **fp16=False**: Forced CPU-safe float32 inference. Remove this flag if a
  GPU is available to speed up transcription significantly.
- **16kHz mono WAV**: Whisper's expected input format. The downloader always
  resamples to this format via ffmpeg regardless of source quality.
- **MarianMT model**: `Helsinki-NLP/opus-mt-te-en` — best freely available
  offline Telugu→English model. ~300 MB, CPU-compatible.
- **Segment fallback**: If translation fails for a segment, the original
  Telugu text is kept rather than crashing the whole pipeline.

## Entry Point
```
python app/main.py "<YouTube URL>" [--model <size>] [--output <dir>]
```

## Service Responsibilities
| File | Role |
|------|------|
| `youtube_downloader.py` | yt-dlp download + ffmpeg resample to 16kHz WAV |
| `transcription_service.py` | Whisper Telugu STT → segment list |
| `translation_service.py` | MarianMT Telugu→English per segment |
| `subtitle_generator.py` | Build `srt.Subtitle` objects → write .srt file |

## Dependencies Requiring System Install
- **ffmpeg binary** must be on PATH (not just `ffmpeg-python` pip package).

## Output
All output files land in `output/` (or the directory given by `--output`):
- `audio.wav` — intermediate audio (can be deleted after use)
- `subtitles.srt` — final English subtitle file

## Testing a New Change
1. Run with a short Telugu video to keep iteration fast.
2. Check `output/subtitles.srt` for correct timestamps and readable English.
3. Use `--model tiny` or `--model base` during development for faster runs.
