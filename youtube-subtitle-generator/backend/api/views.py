import json
import os
import sys
import hashlib
import re
import wave
from pathlib import Path
from typing import Any

from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.youtube_downloader import download_audio
from app.services.segment_utils import normalize_segment_text, split_segments_by_sentence
from app.services.transcription_service import transcribe_audio
from app.services.translation_service import translate_segments
from app.services.subtitle_generator import generate_srt


REQUEST_CACHE_FILENAME = "request_cache.json"
TRANSCRIPTION_CACHE_FILENAME = "transcription_segments.json"
CACHE_DIRNAME = "cache"
TRANSCRIPTION_CACHE_VERSION = 3
TELUGU_CHAR_PATTERN = re.compile(r"[\u0C00-\u0C7F]")


def _parse_json(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def _normalize_output_dir(output_dir: str) -> str:
    cleaned = output_dir.strip() or "output"
    if not os.path.isabs(cleaned):
        cleaned = str(PROJECT_ROOT / cleaned)
    return cleaned


def _coerce_segments(raw_segments: list[Any]) -> list[dict[str, Any]]:
    cleaned_segments: list[dict[str, Any]] = []
    for index, seg in enumerate(raw_segments):
        if not isinstance(seg, dict):
            continue

        text = normalize_segment_text(seg.get("text", ""))
        if not text:
            continue

        try:
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", 0.0))
        except (TypeError, ValueError):
            continue

        if end <= start:
            end = start + 0.5

        try:
            seg_id = int(seg.get("id", index))
        except (TypeError, ValueError):
            seg_id = index

        cleaned_segments.append(
            {
                "id": seg_id,
                "start": start,
                "end": end,
                "text": text,
            }
        )

    return split_segments_by_sentence(cleaned_segments)


def _request_cache_path(output_dir: str) -> str:
    return os.path.join(output_dir, REQUEST_CACHE_FILENAME)


def _transcription_cache_path(output_dir: str) -> str:
    return os.path.join(output_dir, TRANSCRIPTION_CACHE_FILENAME)


def _request_signature(youtube_url: str, model_name: str) -> dict[str, str]:
    return {
        "url": youtube_url,
        "model": model_name,
    }


def _cache_root_dir() -> str:
    return str(PROJECT_ROOT / CACHE_DIRNAME)


def _cache_key(youtube_url: str, model_name: str) -> str:
    raw = f"{youtube_url.strip()}::{model_name.strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _cache_dir(youtube_url: str, model_name: str) -> str:
    return os.path.join(_cache_root_dir(), _cache_key(youtube_url, model_name))


def _read_json_file(path: str) -> dict[str, Any] | list[Any] | None:
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _get_wav_duration_seconds(wav_path: str) -> float:
    try:
        with wave.open(wav_path, "rb") as wav_file:
            frame_count = wav_file.getnframes()
            frame_rate = wav_file.getframerate()
            if frame_rate <= 0:
                return 0.0
            return frame_count / float(frame_rate)
    except (OSError, wave.Error):
        return 0.0


def _write_json_file(path: str, payload: dict[str, Any] | list[Any]) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _load_cached_wav_path(
    youtube_url: str,
    model_name: str,
    cache_dir: str,
) -> str | None:
    cache_data = _read_json_file(_request_cache_path(cache_dir))
    if not isinstance(cache_data, dict):
        return None

    if cache_data.get("request") != _request_signature(youtube_url, model_name):
        return None

    wav_path = cache_data.get("wav_path", "")
    if isinstance(wav_path, str) and wav_path and os.path.exists(wav_path):
        print(f"[Cache] Reusing downloaded audio: {wav_path}")
        return wav_path

    return None


def _load_request_cache(
    youtube_url: str,
    model_name: str,
    cache_dir: str,
) -> dict[str, Any] | None:
    cache_data = _read_json_file(_request_cache_path(cache_dir))
    if not isinstance(cache_data, dict):
        return None

    if cache_data.get("request") != _request_signature(youtube_url, model_name):
        return None

    return cache_data


def _load_cached_segments(
    youtube_url: str,
    model_name: str,
    cache_dir: str,
) -> list[dict[str, Any]] | None:
    cache_data = _read_json_file(_request_cache_path(cache_dir))
    if not isinstance(cache_data, dict):
        return None

    if cache_data.get("request") != _request_signature(youtube_url, model_name):
        return None

    if cache_data.get("transcription_cache_version") != TRANSCRIPTION_CACHE_VERSION:
        return None

    segments_data = _read_json_file(_transcription_cache_path(cache_dir))
    if not isinstance(segments_data, list):
        return None

    cleaned_segments = []
    for seg in segments_data:
        if not isinstance(seg, dict):
            continue
        try:
            text = normalize_segment_text(seg["text"])
            if not text:
                continue
            cleaned_segments.append(
                {
                    "id": int(seg["id"]),
                    "start": float(seg["start"]),
                    "end": float(seg["end"]),
                    "text": text,
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    cleaned_segments = split_segments_by_sentence(cleaned_segments)

    if cleaned_segments:
        print(f"[Cache] Reusing cached transcription with {len(cleaned_segments)} segment(s).")
        return cleaned_segments

    return None


def _segments_cover_audio(segments: list[dict[str, Any]], wav_path: str) -> bool:
    if not segments:
        return False

    duration_seconds = _get_wav_duration_seconds(wav_path)
    if duration_seconds <= 0:
        return True

    last_end = max(float(seg.get("end", 0.0)) for seg in segments)
    minimum_expected_end = max(duration_seconds - 3.0, duration_seconds * 0.9)
    return last_end >= minimum_expected_end


def _segments_look_corrupted(segments: list[dict[str, Any]]) -> bool:
    if not segments:
        return True

    suspicious_count = 0
    for seg in segments:
        text = normalize_segment_text(seg.get("text", ""))
        if not text:
            suspicious_count += 1
            continue

        has_telugu = bool(TELUGU_CHAR_PATTERN.search(text))
        has_replacement = "\ufffd" in text or "ï¿½" in text
        if has_replacement or not has_telugu:
            suspicious_count += 1

    return suspicious_count >= max(1, len(segments) // 3)


def _save_request_cache(
    youtube_url: str,
    model_name: str,
    cache_dir: str,
    wav_path: str,
    segments: list[dict[str, Any]] | None = None,
) -> None:
    payload = {
        "request": _request_signature(youtube_url, model_name),
        "wav_path": wav_path,
        "transcription_cache_version": TRANSCRIPTION_CACHE_VERSION,
    }

    _write_json_file(
        _request_cache_path(cache_dir),
        payload,
    )

    if segments is not None:
        _write_json_file(_transcription_cache_path(cache_dir), segments)
        print(f"[Cache] Saved transcription cache with {len(segments)} segment(s).")

    print(f"[Cache] Saved request cache for: {youtube_url}")


def _get_or_create_transcription(
    youtube_url: str,
    model_name: str,
    cache_dir: str,
) -> tuple[str, list[dict[str, Any]]]:
    wav_path = _load_cached_wav_path(youtube_url, model_name, cache_dir)
    if wav_path is None:
        wav_path = download_audio(youtube_url, output_dir=cache_dir)
        _save_request_cache(
            youtube_url=youtube_url,
            model_name=model_name,
            cache_dir=cache_dir,
            wav_path=wav_path,
        )

    segments = _load_cached_segments(youtube_url, model_name, cache_dir)
    if segments is not None and not _segments_cover_audio(segments, wav_path):
        print("[Cache] Cached transcription looks incomplete for this audio. Re-transcribing...")
        segments = None
    if segments is not None and _segments_look_corrupted(segments):
        print("[Cache] Cached transcription looks corrupted. Re-transcribing...")
        segments = None

    if segments is None:
        segments = transcribe_audio(wav_path, model_name=model_name)
        if segments and not _segments_cover_audio(segments, wav_path):
            print("[Transcription] Initial transcription looks incomplete. Retrying once...")
            segments = transcribe_audio(wav_path, model_name=model_name)
        if segments and _segments_look_corrupted(segments):
            print("[Transcription] Initial transcription looks corrupted. Retrying once...")
            segments = transcribe_audio(wav_path, model_name=model_name)
        if segments:
            _save_request_cache(
                youtube_url=youtube_url,
                model_name=model_name,
                cache_dir=cache_dir,
                wav_path=wav_path,
                segments=segments,
            )

    return wav_path, segments


@require_http_methods(["GET"])
def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_http_methods(["POST"])
def transcribe_audio_only(request: HttpRequest) -> JsonResponse:
    payload = _parse_json(request)

    youtube_url = payload.get("url", "").strip()
    model_name = payload.get("model", "medium").strip()
    output_dir = _normalize_output_dir(payload.get("output_dir", "output"))

    if not youtube_url:
        return JsonResponse({"error": "Missing 'url'."}, status=400)

    cache_dir = _cache_dir(youtube_url, model_name)

    try:
        wav_path, transcription_segments = _get_or_create_transcription(
            youtube_url=youtube_url,
            model_name=model_name,
            cache_dir=cache_dir,
        )
        if not transcription_segments:
            return JsonResponse({"error": "No transcription segments produced."}, status=400)
        _save_request_cache(
            youtube_url=youtube_url,
            model_name=model_name,
            cache_dir=cache_dir,
            wav_path=wav_path,
            segments=transcription_segments,
        )
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)

    return JsonResponse({"segments": transcription_segments})


@csrf_exempt
@require_http_methods(["POST"])
def translate_segments_only(request: HttpRequest) -> JsonResponse:
    payload = _parse_json(request)

    youtube_url = payload.get("url", "").strip()
    model_name = payload.get("model", "medium").strip()
    output_dir = _normalize_output_dir(payload.get("output_dir", "output"))
    segments = _coerce_segments(payload.get("segments", []))

    if not segments:
        return JsonResponse({"error": "No Telugu transcription segments provided."}, status=400)

    cache_dir = _cache_dir(youtube_url, model_name) if youtube_url else ""
    wav_path = _load_cached_wav_path(youtube_url, model_name, cache_dir) if youtube_url else None

    try:
        translated_segments = translate_segments(
            segments,
            wav_path=wav_path or "",
            model_name=model_name,
        )
        srt_path = generate_srt(translated_segments, output_dir=output_dir)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)

    try:
        with open(srt_path, "r", encoding="utf-8") as fh:
            srt_content = fh.read()
    except OSError:
        srt_content = ""

    return JsonResponse(
        {
            "srt_path": srt_path,
            "srt_content": srt_content,
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def generate_subtitles(request: HttpRequest) -> JsonResponse:
    payload = _parse_json(request)

    youtube_url = payload.get("url", "").strip()
    model_name = payload.get("model", "medium").strip()
    output_dir = _normalize_output_dir(payload.get("output_dir", "output"))

    if not youtube_url:
        return JsonResponse({"error": "Missing 'url'."}, status=400)

    cache_dir = _cache_dir(youtube_url, model_name)

    try:
        wav_path, transcription_segments = _get_or_create_transcription(
            youtube_url=youtube_url,
            model_name=model_name,
            cache_dir=cache_dir,
        )
        if not transcription_segments:
            return JsonResponse({"error": "No transcription segments produced."}, status=400)
        translated_segments = translate_segments(
            transcription_segments,
            wav_path=wav_path,
            model_name=model_name,
        )
        srt_path = generate_srt(translated_segments, output_dir=output_dir)
        _save_request_cache(
            youtube_url=youtube_url,
            model_name=model_name,
            cache_dir=cache_dir,
            wav_path=wav_path,
            segments=transcription_segments,
        )
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)

    try:
        with open(srt_path, "r", encoding="utf-8") as fh:
            srt_content = fh.read()
    except OSError:
        srt_content = ""

    return JsonResponse(
        {
            "srt_path": srt_path,
            "srt_content": srt_content,
        }
    )
