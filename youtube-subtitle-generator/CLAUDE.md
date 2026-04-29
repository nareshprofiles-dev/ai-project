# CLAUDE.md — Project Notes for Claude Code

## Project Overview

Telugu YouTube video → English SRT subtitle generator.

Three interfaces share the same core pipeline:
- **CLI**: `python app/main.py`
- **Django REST API**: `backend/` — transcribe/translate/full-pipeline endpoints
- **Angular 21 UI**: `frontend/` — 3-step flow: Generate → Edit → Result

Core pipeline: `yt-dlp → ffmpeg → Whisper (transcribe) → Whisper (translate) → srt`

---

## Key Design Decisions

- **Whisper language hint**: Pass `language="te"` explicitly to prevent misdetection on short or noisy clips.
- **fp16=False**: Forces CPU-safe float32 inference. Remove for GPU speedup.
- **16kHz mono WAV**: Whisper's required input format. The downloader always resamples to this via ffmpeg regardless of source quality.
- **Translation via Whisper translate task**: Both transcription and translation use the same Whisper model. The translation pass re-runs `model.transcribe()` with `task="translate"` on the same audio — no separate MarianMT model. `requirements.txt` still lists `transformers`/`sentencepiece` but they are not used by the current code.
- **Segment fallback**: If the translate pass returns fewer segments than the transcription pass, English text is aligned by index. If alignment fails for a segment, the original Telugu text is kept.
- **Auto-retry with large-v3**: `transcription_service.py` checks the Telugu character ratio in the output. If it looks weak (< 45% Telugu chars), it automatically retries with `large-v3`.

---

## Entry Points

```bash
# CLI
python app/main.py "<YouTube URL>" [--model <size>] [--output <dir>]

# Django backend (runs on :8000)
cd backend && python manage.py runserver 0.0.0.0:8000

# Angular frontend (runs on :4200, proxies API to :8000)
cd frontend && npm start
```

---

## Service Responsibilities

| File | Role |
|------|------|
| `app/services/youtube_downloader.py` | yt-dlp download + ffmpeg resample to 16kHz WAV |
| `app/services/transcription_service.py` | Whisper Telugu STT → sentence-level segment list; auto-retry with large-v3 if quality is low |
| `app/services/translation_service.py` | Whisper translate task → English segments; aligns to transcription segments by index |
| `app/services/subtitle_generator.py` | Build `srt.Subtitle` objects → write UTF-8 .srt file |
| `app/services/segment_utils.py` | Text normalization (mojibake repair, ANSI strip), sentence segmentation heuristics (max 6.5s / 56 chars / 14 words per cue) |

---

## Backend API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health/` | GET | Health check |
| `/api/transcribe/` | POST | Download + transcribe; returns Telugu segments. Caches result. |
| `/api/translate/` | POST | Accepts segments (possibly edited by user) + audio path → generates SRT |
| `/api/subtitles/` | POST | Full pipeline in one call |

### Caching Strategy

- Cache key: first 16 chars of `SHA256(url::model)`
- Cache dir: `cache/<hash>/`
- Cached files: `audio.wav`, `request_cache.json`, `transcription_segments.json`
- Validation checks: URL + model match, cache version (currently v3), audio duration coverage, Telugu content present
- Auto-retries once on validation failure

---

## Frontend Flow

1. **GenerateComponent** (`/`) — user enters URL + picks model → calls `/api/transcribe/`
2. **EditComponent** (`/edit`) — user reviews/edits Telugu segments in a table → calls `/api/translate/`
3. **ResultComponent** (`/result`) — shows SRT path + content preview, download button

State is shared via `SubtitleStoreService` (singleton). Default model in the UI is `large-v3`.

---

## Dependencies Requiring System Install

- **ffmpeg binary** must be on PATH (not just the `ffmpeg-python` pip wrapper).

---

## Output & Cache Layout

```
cache/<hash>/
  audio.wav                    # Downloaded + resampled audio
  request_cache.json           # Request metadata + cache version
  transcription_segments.json  # Telugu segments (reused on re-runs)

output/
  subtitles.srt                # Final English subtitle file
```

---

## Testing a New Change

1. Run with a short Telugu video to keep iteration fast.
2. Use `--model tiny` or `--model base` during development.
3. Check `output/subtitles.srt` for correct timestamps and readable English text.
4. For backend changes, verify caching by running the same URL twice — the second run should skip download and transcription.
5. For frontend changes, run both the Django server and `npm start`, then walk through all three pages.
