# Changelog

All notable changes to this project are recorded here, grouped by date.

---

## 2026-06-25

### Fixed
- **Frontend retry on broken pipe** (`frontend/src/app/components/generate.component.ts`)
  - Extracted `fetchReviewUnits()` helper with auto-retry logic.
  - If the HTTP connection drops mid-request (TCP timeout / broken pipe) the frontend retries once after 2 s; the backend cache is already written by then so the retry returns instantly.

- **Duplicate and misaligned English subtitles** (`app/services/review_unit_builder.py`)
  - Root cause: Whisper's translate task produces coarser segments than the transcription pass. Multiple Telugu rows were all best-matching the same English segment, causing identical text to repeat.
  - Fix: added `_split_words_proportional()` — when N transcription segments share one translation segment, English words are distributed across them proportionally by duration.
  - Added `REVIEW_ROWS_CACHE_VERSION = 2` in `backend/api/views.py` to invalidate stale cached rows on next request.

### Added
- **Environment-based configuration** (`.env`, `app/config.py`)
  - All model names, inference parameters, and path defaults moved out of service code into `.env`.
  - `app/config.py` is the single loader — services import typed constants from it.
  - `.env.example` committed as a template; `.env` added to `.gitignore`.
  - `python-dotenv>=1.0.0` added to `requirements.txt`.

### Changed
- `app/services/transcription_service.py` — replaced all hardcoded Whisper params with `app.config` imports.
- `app/services/translation_service.py` — same; default model now reads from `WHISPER_DEFAULT_MODEL`.
- `backend/api/views.py` — `CACHE_DIRNAME` and endpoint model/output defaults now sourced from `app.config`.

---

## Template for future entries

```
## YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Removed
- ...
```
