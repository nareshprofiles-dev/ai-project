# YouTube Telugu → English Subtitle Generator

A fully local, free, and open-source pipeline that converts Telugu YouTube videos into English SRT subtitle files.

1. Downloads audio from a Telugu YouTube video
2. Transcribes Telugu speech using **OpenAI Whisper**
3. Translates to English using **Whisper's built-in translate task** (no separate model)
4. Writes an **SRT subtitle file** to the `output/` folder
5. Caches audio and transcription under `cache/` for fast re-runs

No paid APIs. Everything runs on your machine. Three ways to use it: CLI, Django REST API, or Angular web UI.

---

## Project Structure

```
youtube-subtitle-generator/
│
├── app/                                 # Core Python services
│   ├── main.py                          # CLI entry point
│   └── services/
│       ├── youtube_downloader.py        # yt-dlp + ffmpeg audio extraction
│       ├── transcription_service.py     # Whisper Telugu STT
│       ├── translation_service.py       # Whisper translate task (Telugu → English)
│       ├── subtitle_generator.py        # SRT file builder
│       └── segment_utils.py             # Text normalization & sentence segmentation
│
├── backend/                             # Django REST API
│   ├── api/
│   │   ├── views.py                     # API endpoints & caching logic
│   │   └── urls.py
│   └── subtitle_api/
│       └── settings.py                  # Django config (CORS enabled)
│
├── frontend/                            # Angular 21 web UI
│   └── src/app/
│       ├── components/
│       │   ├── generate.component.*     # URL input page
│       │   ├── edit.component.*         # Telugu review/edit page
│       │   └── result.component.*       # SRT output page
│       └── subtitle-store.service.ts    # In-memory state
│
├── cache/                               # Runtime cache (auto-created)
│   └── <url-hash>/
│       ├── audio.wav
│       ├── request_cache.json
│       └── transcription_segments.json
│
├── output/                              # Generated subtitles
├── requirements.txt
├── README.md
├── CLAUDE.md
└── architecture.md                      # Planned hybrid review architecture
```

---

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| **Python 3.9+** | Runtime | [python.org](https://python.org) |
| **ffmpeg** | Audio conversion | See below |
| **Node.js 18+** | Frontend (optional) | [nodejs.org](https://nodejs.org) |

### Install ffmpeg

**Windows (via Chocolatey):**
```bash
choco install ffmpeg
```
**Windows (via Scoop):**
```bash
scoop install ffmpeg
```
**macOS:**
```bash
brew install ffmpeg
```
**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

Verify: `ffmpeg -version`

---

## Installation

```bash
# 1. Enter the project directory
cd youtube-subtitle-generator

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# CPU-only PyTorch (smaller download, no GPU needed):
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

> **Note:** On first run, the Whisper model downloads automatically (~1.5 GB for `large-v3`).
> It is cached locally and reused on subsequent runs. No separate translation model is needed —
> Whisper handles both transcription and English translation.

---

## Usage

### CLI

```bash
python app/main.py "https://youtube.com/watch?v=VIDEO_ID"
```

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | `medium` | Whisper model size (`tiny` / `base` / `small` / `medium` / `large` / `large-v3`) |
| `--output` | `output` | Directory to save the SRT file |

```bash
# Use a smaller (faster) model
python app/main.py "https://youtu.be/abcXYZ123" --model small

# Use the most accurate model
python app/main.py "https://youtu.be/abcXYZ123" --model large-v3

# Custom output directory
python app/main.py "https://youtu.be/abcXYZ123" --output my_subtitles
```

### Backend API (Django)

```bash
cd backend
python manage.py runserver 0.0.0.0:8000
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health/` | GET | Health check |
| `/api/transcribe/` | POST | Transcribe only (returns Telugu segments) |
| `/api/translate/` | POST | Translate provided segments → SRT |
| `/api/subtitles/` | POST | Full pipeline (transcribe + translate → SRT) |

**Example request body** for `/api/transcribe/`:
```json
{ "url": "https://youtu.be/abcXYZ123", "model": "large-v3", "output_dir": "output" }
```

### Web UI (Angular)

```bash
cd frontend
npm install
npm start   # Serves on http://localhost:4200, proxies API calls to :8000
```

The UI guides you through three steps:
1. **Generate** — Paste a YouTube URL and pick a Whisper model
2. **Edit** — Review and correct the Telugu transcription before translation
3. **Result** — Download the finished SRT file

---

## Cache Behavior

- Generated SRT files land in `output/`.
- Downloaded audio and transcription results are cached under `cache/<url-hash>/`.
- Cache is validated per request (URL + model must match, Telugu content checked).
- If the cache looks corrupt or incomplete, the pipeline retries automatically.
- Delete `cache/` to force a full re-download and re-transcription from scratch.

---

## Model Selection Guide

| Model | RAM | Speed | Accuracy |
|-------|-----|-------|----------|
| `tiny` | ~1 GB | Fastest | Low |
| `base` | ~1 GB | Fast | Low–Medium |
| `small` | ~2 GB | Medium | Medium |
| `medium` | ~5 GB | Moderate | Good |
| `large-v3` | ~10 GB | Slow | **Best (recommended)** |

`large-v3` gives the best Telugu transcription and translation quality. Use `small` or `medium` for faster iteration during development.

---

## Troubleshooting

**`ffmpeg not found`** — Make sure ffmpeg is installed and on your PATH.

**Whisper produces garbled text** — Try a larger model (`--model large-v3`). The transcription service will auto-retry with `large-v3` if it detects low Telugu character density.

**Translation quality is poor** — Both transcription and translation use Whisper; improving transcription quality (larger model, cleaner audio) also improves translation.

**`yt-dlp` download fails** — Update yt-dlp: `pip install -U yt-dlp`

**Frontend won't connect to backend** — Make sure Django is running on port 8000 before starting the Angular dev server.

---

## Tech Stack

| Component | Library / Tool |
|-----------|----------------|
| Audio download | `yt-dlp` |
| Audio conversion | `ffmpeg-python` + ffmpeg binary |
| Telugu STT + translation | `openai-whisper` (transcribe + translate tasks) |
| SRT generation | `srt` |
| REST API | Django + `django-cors-headers` |
| Web UI | Angular 21 |
