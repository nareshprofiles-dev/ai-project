# YouTube Telugu → English Subtitle Generator

A fully local, free, and open-source pipeline that:

1. Downloads audio from a Telugu YouTube video
2. Transcribes the Telugu speech to text with **OpenAI Whisper**
3. Translates the text to English using a **HuggingFace MarianMT** model
4. Writes an **SRT subtitle file** to the `output/` folder

No paid APIs. Everything runs on your machine.

---

## Project Structure

```
youtube-subtitle-generator/
│
├── app/
│   ├── main.py                      # CLI entry point
│   └── services/
│       ├── youtube_downloader.py    # yt-dlp + ffmpeg audio extraction
│       ├── transcription_service.py # Whisper Telugu speech-to-text
│       ├── translation_service.py   # HuggingFace Telugu → English
│       └── subtitle_generator.py   # SRT file builder
│
├── output/                          # Generated subtitles land here
├── requirements.txt
├── README.md
└── CLAUDE.md
```

---

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| **Python 3.9+** | Runtime | [python.org](https://python.org) |
| **ffmpeg** | Audio conversion | See below |

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
# 1. Clone or enter the project directory
cd youtube-subtitle-generator

# 2. Create and activate a virtual environment (recommended)
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

> **Note:** On first run, two model downloads happen automatically:
> - Whisper `medium` model (~1.5 GB)
> - `Helsinki-NLP/opus-mt-te-en` translation model (~300 MB)
>
> Both are cached locally and reused on subsequent runs.

---

## Usage

```bash
python app/main.py "https://youtube.com/watch?v=VIDEO_ID"
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | `medium` | Whisper model size (`tiny` / `base` / `small` / `medium` / `large` / `large-v3`) |
| `--output` | `output` | Directory to save the SRT file |

### Examples

```bash
# Basic usage
python app/main.py "https://youtu.be/abcXYZ123"

# Use a smaller (faster) model
python app/main.py "https://youtu.be/abcXYZ123" --model small

# Use the most accurate model
python app/main.py "https://youtu.be/abcXYZ123" --model large-v3

# Custom output directory
python app/main.py "https://youtu.be/abcXYZ123" --output my_subtitles
```

### Expected Output

```
============================================================
  Telugu YouTube → English Subtitle Generator
============================================================
  URL    : https://youtu.be/abcXYZ123
  Model  : medium
  Output : output
============================================================
[Downloader] Downloading audio from: https://youtu.be/abcXYZ123
[Downloader] Converting audio to 16kHz mono WAV for Whisper...
[Downloader] Audio saved to: output/audio.wav
[Transcription] Loading Whisper model: 'medium' ...
[Transcription] Transcribing: output/audio.wav
[Transcription] Produced 42 segment(s).
[Translation] Loading model: 'Helsinki-NLP/opus-mt-te-en' ...
[Translation] Translating 42 segment(s) from Telugu to English ...
[Translation] Translation complete.
[Subtitle] SRT file written: output/subtitles.srt  (42 cues)

============================================================
  Subtitles saved to: output/subtitles.srt
============================================================
```

The `output/subtitles.srt` file will look like:

```
1
00:00:01,240 --> 00:00:04,860
Welcome to this Telugu video about technology.

2
00:00:05,100 --> 00:00:09,320
Today we will discuss artificial intelligence.
```

---

## Model Selection Guide

| Model | VRAM / RAM | Speed | Accuracy |
|-------|-----------|-------|----------|
| `tiny` | ~1 GB | Fastest | Low |
| `base` | ~1 GB | Fast | Low–Medium |
| `small` | ~2 GB | Medium | Medium |
| `medium` | ~5 GB | Moderate | **Good (recommended)** |
| `large-v3` | ~10 GB | Slow | Best |

For most Telugu videos, `medium` is the sweet spot.

---

## Troubleshooting

**`ffmpeg not found`** — Make sure ffmpeg is installed and on your PATH.

**Whisper produces garbled text** — Try a larger model (`--model large-v3`).

**Translation quality is poor** — The MarianMT model works best on clean,
well-formed sentences. Noisy audio leads to noisy translations.

**`yt-dlp` download fails** — Update yt-dlp: `pip install -U yt-dlp`

---

## Tech Stack

| Component | Library |
|-----------|---------|
| Audio download | `yt-dlp` |
| Audio conversion | `ffmpeg-python` |
| Telugu STT | `openai-whisper` |
| Telugu→English MT | `transformers` (Helsinki-NLP/opus-mt-te-en) |
| SRT generation | `srt` |
