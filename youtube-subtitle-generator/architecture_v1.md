# Architecture v1 — Implemented Hybrid Review Architecture

This document describes the architecture as actually implemented. It records what was built,
how it works, and where key decisions were made. The original design proposal lives in
`architecture.md`.

---

## Overview

The system generates English SRT subtitles from Telugu YouTube videos through a three-step
human-in-the-loop workflow:

1. **Generate** — user provides a YouTube URL and model; backend runs transcription then
   translation sequentially and returns merged review rows
2. **Review** — user edits Telugu and/or English text side-by-side per sentence; edited rows
   can be individually retranslated without reprocessing the video
3. **Finalize** — user submits reviewed rows; backend generates the final SRT from
   `english_current` + stored timestamps

Three interfaces share the same Django backend:

- **CLI**: `python app/main.py <url> [--model <size>] [--output <dir>]`
- **Django REST API**: runs on `:8000`
- **Angular 21 web UI**: runs on `:4200`

---

## Directory Structure

```
youtube-subtitle-generator/
│
├── app/                                       # Core pipeline (CLI + shared services)
│   ├── main.py                                # CLI entry point
│   └── services/
│       ├── youtube_downloader.py              # yt-dlp download + ffmpeg → 16kHz mono WAV
│       ├── transcription_service.py           # Whisper Telugu STT; auto-retry on low quality
│       ├── translation_service.py             # Whisper translate task → English segments
│       ├── subtitle_generator.py              # SRT builder (srt library, UTF-8 output)
│       ├── segment_utils.py                   # Text normalisation, sentence segmentation
│       ├── review_unit_builder.py             # Merge transcription + translation → review rows
│       └── sentence_translation_service.py    # Per-sentence MarianMT translation (retranslate)
│
├── backend/                                   # Django 4 REST API
│   ├── manage.py
│   ├── api/
│   │   ├── views.py                           # All endpoints + caching + orchestration
│   │   └── urls.py                            # Route definitions
│   └── subtitle_api/
│       └── settings.py                        # CORS, installed apps, database
│
├── frontend/                                  # Angular 21 standalone components
│   └── src/app/
│       ├── subtitle-store.service.ts          # In-memory shared state (ReviewRow[])
│       ├── app.routes.ts                      # /, /edit, /result
│       └── components/
│           ├── generate.component.*           # Page 1 — URL + model input
│           ├── edit.component.*               # Page 2 — side-by-side review table
│           └── result.component.*             # Page 3 — SRT path + content preview
│
├── cache/                                     # Runtime cache (auto-created, git-ignored)
│   └── <16-char SHA256 hash>/
│       ├── audio.wav
│       ├── request_cache.json
│       ├── transcription_segments.json
│       ├── translation_segments.json
│       └── review_rows.json
│
└── output/                                    # Generated SRT files (auto-created)
```

---

## Core Pipeline

### Audio preparation

`youtube_downloader.py` — `download_audio(url, output_dir)`

- Downloads audio via yt-dlp, resamples to 16 kHz mono WAV via ffmpeg
- Output placed in the cache directory for that URL+model hash
- Cached: re-requests skip download entirely

### Transcription

`transcription_service.py` — `transcribe_audio(wav_path, model_name)`

- Runs `whisper.load_model(model_name).transcribe(wav_path, language="te", fp16=False)`
- Returns list of `{id, start, end, text}` dicts with Telugu text
- Auto-retries once if output is incomplete (last segment end < 90% of audio duration)
- Auto-retries once if output looks corrupted (< Telugu chars in ≥ 1/3 of segments)

### Translation

`translation_service.py` — `translate_segments(transcription_segments, wav_path, model_name)`

- Re-runs Whisper with `task="translate"` on the same WAV — no separate translation model
- Returns list of `{id, start, end, text, english_text}` dicts
- If the translate pass returns fewer segments than transcription, falls back to index alignment

### Review row building

`review_unit_builder.py` — `build_review_rows(transcription_segments, translation_segments)`

- Translation timeline is canonical: each translation segment becomes one review row
- Telugu text is aligned into each row by timestamp overlap — multiple transcription segments
  overlapping one translation window are concatenated
- Fallback: if translation produced nothing, transcription segments become rows with empty
  English (`source_timeline: "transcribe"`)

### Per-sentence retranslation

`sentence_translation_service.py` — `translate_sentence(telugu_text: str) -> str`

- Model: `Helsinki-NLP/opus-mt-mul-en` (publicly accessible multilingual → English)
- Input is prefixed with `>>te<<` to steer the model toward Telugu source
- Model loaded once per process and cached in module-level globals
- **Note**: `Helsinki-NLP/opus-mt-te-en` (Telugu-only) was made private on HuggingFace in 2024
  and returns 401. `opus-mt-mul-en` with the `>>te<<` prefix is the working replacement.

### SRT generation

`subtitle_generator.py` — `generate_srt(segments, output_dir)`

- Reads `english_text` from each segment for subtitle content
- Writes UTF-8 `.srt` file to `output_dir/subtitles.srt`

---

## Backend API

All endpoints live under `/api/` prefix, defined in `backend/api/urls.py`.

### Active endpoints (hybrid review flow)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/health/` | GET | Health check — returns `{"status": "ok"}` |
| `POST /api/review-units/` | POST | Main entry point: download + transcribe + translate + align. Returns merged review rows. Caches all stages. |
| `POST /api/retranslate-sentence/` | POST | Retranslates one edited Telugu sentence via MarianMT. No audio reprocessing. |
| `POST /api/finalize-subtitles/` | POST | Generates final SRT from reviewed rows (uses `english_current` + timestamps). |

### Legacy endpoints (kept for backward compatibility)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/transcribe/` | POST | Transcription-only; returns Telugu segments |
| `POST /api/translate/` | POST | Translation + SRT generation from supplied segments |
| `POST /api/subtitles/` | POST | Full CLI-equivalent pipeline in one call |

---

## API Contract

### `POST /api/review-units/`

Request:
```json
{
  "url": "https://youtube.com/watch?v=...",
  "model": "large-v3",
  "output_dir": "output"
}
```

Response:
```json
{
  "rows": [
    {
      "id": 1,
      "start": 5.0,
      "end": 11.0,
      "telugu_original": "...",
      "telugu_current": "...",
      "english_original": "...",
      "english_current": "...",
      "source_timeline": "translate",
      "edited": false,
      "needs_retranslate": false
    }
  ]
}
```

### `POST /api/retranslate-sentence/`

Request:
```json
{
  "id": 3,
  "start": 18.4,
  "end": 22.1,
  "telugu_text": "మనిషి సరిచేసిన తెలుగు వాక్యం"
}
```

Response:
```json
{
  "id": 3,
  "english_text": "Human-corrected Telugu sentence"
}
```

### `POST /api/finalize-subtitles/`

Request:
```json
{
  "rows": [
    {
      "id": 1,
      "start": 5.0,
      "end": 11.0,
      "telugu_current": "...",
      "english_current": "..."
    }
  ],
  "output_dir": "output"
}
```

Response:
```json
{
  "srt_path": "/absolute/path/to/subtitles.srt",
  "srt_content": "1\n00:00:05,000 --> 00:00:11,000\n..."
}
```

---

## Caching Strategy

Cache key: first 16 characters of `SHA256("<url>::<model>")`.
Cache root: `cache/<key>/` relative to project root.

| File | Invalidated when |
|------|-----------------|
| `audio.wav` | URL or model changes (new cache dir) |
| `request_cache.json` | URL or model changes |
| `transcription_segments.json` | Cache version bumped (`TRANSCRIPTION_CACHE_VERSION = 3`), or output looks corrupted/incomplete |
| `translation_segments.json` | URL or model changes, or cache version changes |
| `review_rows.json` | URL or model changes (fastest path — skips all model work on re-request) |

Cache hit priority in `get_review_units`:
1. `review_rows.json` exists → return immediately (no model loaded)
2. `translation_segments.json` exists → skip translation, run alignment only
3. `transcription_segments.json` exists → skip transcription, run translation + alignment
4. Nothing cached → full pipeline

---

## Orchestration Details (`views.py`)

### Sequential execution

Transcription completes fully before translation starts. This prevents both Whisper models
from being loaded into memory simultaneously.

### Stage logging

Each `get_review_units` call generates a short `job_id` (8-char UUID prefix). Every log line
includes `[job_id] [stage]` prefix with timing and segment counts:

```
[a3f2b1c0] [review-units] Request | url=... | model=large-v3
[a3f2b1c0] [transcription] Starting | model=large-v3 | audio=cache/.../audio.wav
[a3f2b1c0] [transcription] Done | segments=47 | time=214.3s
[a3f2b1c0] [translation] Starting | model=large-v3 | audio=cache/.../audio.wav
[a3f2b1c0] [translation] Done | segments=43 | time=198.1s
[a3f2b1c0] [alignment] Building review rows from 47 transcription + 43 translation segment(s)...
[a3f2b1c0] [alignment] Done | rows=43 | time=0.00s
```

---

## Frontend Architecture

### State model (`subtitle-store.service.ts`)

Single injectable service, no persistence — state lives only for the current browser session.

```typescript
export type ReviewRow = {
  id: number;
  start: number;
  end: number;
  teluguOriginal: string;
  teluguCurrent: string;
  englishOriginal: string;
  englishCurrent: string;
  edited: boolean;
  needsRetranslate: boolean;
};

// Store fields:
// url, model, outputDir, reviewRows, srtPath, srtContent, statusMessage
```

### Component flow

**GenerateComponent** (`/`)
- URL + model + output-dir form
- Calls `POST /api/review-units/`
- Maps snake_case response to camelCase `ReviewRow[]`, stores via `store.setReviewRows()`
- Navigates to `/edit` on success

**EditComponent** (`/edit`)
- 4-column grid table: `[140px meta] [1fr Telugu] [1fr English] [72px action]`
- `[(ngModel)]` on both `row.teluguCurrent` and `row.englishCurrent`
- Telugu edit → `onTeluguEdit(row)` sets `row.edited = true`, `row.needsRetranslate = true`
- Regen button calls `retranslate(row)` → `POST /api/retranslate-sentence/` → updates only
  `row.englishCurrent`, clears `row.needsRetranslate`
- English textarea gets `class="retranslating"` (dimmed, pointer-events disabled) while
  per-row retranslation is in flight
- Edited rows get yellow left border via `[class.row-edited]="row.edited"`
- "Finalize subtitles" calls `finalize()` → `POST /api/finalize-subtitles/` → navigates to `/result`

**ResultComponent** (`/result`)
- Displays `srtPath` and `srtContent` from store
- Copy / download buttons for the SRT file

---

## Known Issues and Resolutions

### `Helsinki-NLP/opus-mt-te-en` returns HTTP 401

The Telugu-only MarianMT model was made private/gated on HuggingFace at some point in 2024.
Any `from_pretrained("Helsinki-NLP/opus-mt-te-en")` call fails with 401 Unauthorized even
without a token.

**Resolution**: `sentence_translation_service.py` uses `Helsinki-NLP/opus-mt-mul-en` (publicly
accessible, ~300 MB) with a `>>te<<` language prefix to steer it toward Telugu input. The model
is downloaded once and cached by the HuggingFace hub in `~/.cache/huggingface/`.

---

## Non-Goals (explicitly out of scope for v1)

- Word-level manual alignment UI
- Full subtitle timeline scrubber / editor
- Confidence scoring or automatic quality metrics
- Batch retranslation of multiple changed rows in one request
- Persistent session storage (refreshing the browser clears state)
