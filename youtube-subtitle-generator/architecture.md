# Hybrid Subtitle Review Architecture

## Goal

Improve the human-in-the-loop review flow by keeping the current project structure, but changing the review experience to rely more heavily on translation quality than raw transcription quality.

The main product goal is:

- run Telugu transcription first, then English translation after transcription finishes
- show both results together on the review page
- let the user edit either side
- if Telugu text is modified, regenerate English only for that sentence
- keep timestamps stable per sentence-level review row


## Current Implementation Summary

Today the project already has these major pieces:

- audio download and WAV conversion in `app/services/youtube_downloader.py`
- Telugu transcription in `app/services/transcription_service.py`
- English translation in `app/services/translation_service.py`
- SRT generation in `app/services/subtitle_generator.py`
- Django API endpoints in `backend/api/views.py`
- Angular review flow in `frontend/src/app/components/*`

Current frontend flow:

1. Generate page sends a request to `/api/transcribe/`
2. Edit page shows Telugu-only segments
3. Continue sends reviewed Telugu segments to `/api/translate/`
4. Result page shows final SRT

Current limitation:

- English translation is often more useful than Telugu transcription
- Telugu review alone is not strong enough for human validation
- translation currently happens after the Telugu-only review step


## Target Architecture

The proposed architecture keeps the existing backend services, but changes the orchestration and the review data model.

### Core Principles

- translation quality is treated as the stronger signal
- transcription is still valuable as draft Telugu text for review
- review should happen on a single sentence-aligned table
- transcribe and translate should run one after the other to keep memory usage predictable
- long-running jobs should emit clear progress and error logs at each stage
- edits should be local to a sentence, not force a full rerun


## End-to-End Flow

### 1. Download audio once

The backend still downloads audio once and caches:

- `audio.wav`
- request metadata

This behavior already exists and should remain.

### 2. Run transcribe and translate sequentially

After audio is prepared, run each expensive job one after the other:

1. run Telugu transcription with `transcribe_audio(wav_path, model_name)`
2. write transcription segments to cache
3. release any transcription model resources if the runtime supports it
4. run English translation on the same `wav_path`
5. write translation segments to cache

The translation pass should start only after the transcription pass completes.

This is the key orchestration change from the earlier parallel design. The goal is to reduce peak memory usage and make failures easier to isolate.

Each stage should log:

- request/job id
- stage name
- input audio path
- selected model
- start time and finish time
- segment count produced
- cache file written
- full exception details on failure

### 3. Build a unified review model

When both jobs finish sequentially, merge them into one review list.

Each review row should contain:

- `id`
- `start`
- `end`
- `telugu_original`
- `telugu_current`
- `english_original`
- `english_current`
- `source_timeline`
- `edited`
- `needs_retranslate`

Suggested shape:

```json
{
  "id": 12,
  "start": 65.2,
  "end": 69.8,
  "telugu_original": "తెలుగు ముసాయిదా",
  "telugu_current": "తెలుగు ముసాయిదా",
  "english_original": "English draft",
  "english_current": "English draft",
  "source_timeline": "translate",
  "edited": false,
  "needs_retranslate": false
}
```

### 4. Show side-by-side review on page 2

The second page becomes the main human-in-the-loop workspace.

For each sentence row, show:

- timestamp range
- Telugu text area on the left
- English text area on the right
- per-row status
- per-row `Regenerate` button

This replaces the current Telugu-only review layout.

### 5. Local sentence retranslation

If the user edits Telugu for a row:

- mark that row as dirty
- enable `Regenerate`
- send only that sentence for translation
- update only that row’s English text

This avoids rerunning translation for the full video.

### 6. Final output generation

When the user clicks continue/finalize:

- build final subtitle rows from the reviewed list
- use `english_current` for subtitle content
- use stored `start` and `end` timestamps
- generate the final SRT


## Alignment Strategy

### Canonical timeline

Because translation is currently producing better sentence-level output, the canonical timeline should come from the translation pass by default.

That means:

- translated segments define the primary sentence boundaries
- transcribed Telugu text is aligned into those boundaries

### Telugu alignment onto translation timeline

Because transcription and translation may produce different segment counts, alignment should be a separate step. The jobs run sequentially, but their outputs are still aligned after both stages finish.

Recommended merge strategy:

1. align by timestamp overlap first
2. if multiple Telugu segments overlap one English segment, concatenate Telugu text
3. if one Telugu segment spans multiple English segments, split Telugu text approximately across the matching windows
4. preserve original source text separately from edited text

This design allows the review UI to stay stable even when raw segment counts differ.


## Backend Architecture

### Existing services to keep

- `app/services/transcription_service.py`
- `app/services/translation_service.py`
- `app/services/subtitle_generator.py`

### New orchestration responsibilities

The main changes belong in `backend/api/views.py` or a new orchestration service.

Suggested responsibilities:

- prepare/reuse cached audio
- run transcription and translation sequentially
- log progress, cache writes, segment counts, and failures for each stage
- align both outputs into review rows
- cache review rows
- support sentence-level retranslation

### Suggested backend service split

Keep current services and add light orchestration helpers:

- `app/services/review_unit_builder.py`
  Purpose: merge transcription + translation into sentence review rows

- `app/services/sentence_translation_service.py`
  Purpose: translate a single Telugu sentence when edited

- optional `app/services/alignment_service.py`
  Purpose: timestamp-based alignment between transcription and translation outputs


## API Design

### 1. Review generation endpoint

Suggested new endpoint:

`POST /api/review-units/`

Input:

```json
{
  "url": "https://youtube.com/watch?v=...",
  "model": "large-v3",
  "output_dir": "output"
}
```

Behavior:

- prepare audio
- run Telugu transcription
- cache transcription segments
- run English translation
- cache translation segments
- align results
- return unified review rows

Output:

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

### 2. Sentence retranslation endpoint

Suggested new endpoint:

`POST /api/retranslate-sentence/`

Input:

```json
{
  "id": 1,
  "start": 5.0,
  "end": 11.0,
  "telugu_text": "మనిషి సరిచేసిన తెలుగు వాక్యం"
}
```

Behavior:

- translate only the supplied Telugu sentence
- return updated English text for that row

Output:

```json
{
  "id": 1,
  "english_text": "Updated English sentence"
}
```

### 3. Final subtitle generation endpoint

The current `/api/translate/` endpoint can evolve into a finalization endpoint, or a new endpoint can be introduced:

`POST /api/finalize-subtitles/`

Input:

- full reviewed rows
- output directory

Behavior:

- use reviewed English text and preserved timestamps
- generate SRT


## Frontend Architecture

### Current components

- generate page
- edit page
- result page

### Proposed UI flow

#### Page 1: Generate

The generate page remains simple:

- URL input
- model input
- output folder input
- button to start processing

The difference is that it should request review units instead of transcription only.

#### Page 2: Review Workspace

This becomes the main hybrid review page.

Each row should contain:

- timestamp
- Telugu editor
- English editor
- regenerate button
- visual marker for modified rows

Recommended table/card layout:

- left column: Telugu
- right column: English
- row toolbar: timestamp + regenerate action

#### Page 3: Result

The result page remains mostly the same:

- output path
- generated SRT preview


## Frontend State Model

The current `SubtitleStoreService` can evolve from simple `segments` to richer `reviewRows`.

Suggested state:

```ts
type ReviewRow = {
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
```

Store fields:

- `url`
- `model`
- `outputDir`
- `reviewRows`
- `srtPath`
- `srtContent`
- `statusMessage`


## Caching Strategy

The current cache already stores:

- request metadata
- audio path
- transcription segments

This can be extended to store:

- translation segments
- merged review rows
- cache version metadata

Suggested cache files:

- `audio.wav`
- `request_cache.json`
- `transcription_segments.json`
- `translation_segments.json`
- `review_rows.json`

This avoids rerunning expensive steps unless:

- the URL changes
- the model changes
- the cache version changes


## Why This Architecture Fits The Current Project

This design is aligned with the current implementation because:

- it keeps the existing Django + Angular structure
- it reuses the current transcription and translation services
- it preserves the current idea of a review page before final SRT generation
- it adds better review modeling without requiring a full rewrite
- it avoids peak memory pressure from running transcription and translation at the same time

It also solves the core product concern:

- Telugu transcription alone is not reliable enough for human review
- English translation is stronger and should anchor the workflow
- sentence-level retranslation keeps human edits useful and efficient


## Recommended Implementation Order

1. Add backend orchestration endpoint that returns merged review rows
2. Run transcription and translation sequentially
3. Add detailed stage logging for transcription, translation, caching, and alignment
4. Add translation result caching
5. Change frontend store from `segments` to `reviewRows`
6. Redesign page 2 to show Telugu and English side by side
7. Add per-row regenerate action
8. Finalize SRT from reviewed rows


## Non-Goals For The First Iteration

To keep the first version practical, avoid these initially:

- word-level manual alignment UI
- full subtitle timeline editor
- automatic confidence scoring from multiple models
- batch retranslation of only changed rows

These can come later if needed.


## Final Recommendation

Use a hybrid review architecture where:

- transcription and translation run sequentially to control memory usage
- translation defines the canonical review timeline
- the review page shows Telugu and English side by side
- Telugu edits trigger sentence-level retranslation only for that row
- final SRT is generated from reviewed English text with preserved timestamps

This is the best fit for the current codebase and the best product fit for a human-in-the-loop Telugu to English subtitle workflow.
