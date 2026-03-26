import json
import os
import sys
from pathlib import Path

from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.youtube_downloader import download_audio
from app.services.transcription_service import transcribe_audio
from app.services.translation_service import translate_segments
from app.services.subtitle_generator import generate_srt


def _parse_json(request: HttpRequest) -> dict:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


@require_http_methods(["GET"])
def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_http_methods(["POST"])
def generate_subtitles(request: HttpRequest) -> JsonResponse:
    payload = _parse_json(request)

    youtube_url = payload.get("url", "").strip()
    model_name = payload.get("model", "medium").strip()
    output_dir = payload.get("output_dir", "output").strip() or "output"

    if not youtube_url:
        return JsonResponse({"error": "Missing 'url'."}, status=400)

    if not os.path.isabs(output_dir):
        output_dir = str(PROJECT_ROOT / output_dir)

    try:
        wav_path = download_audio(youtube_url, output_dir=output_dir)
        segments = transcribe_audio(wav_path, model_name=model_name)
        if not segments:
            return JsonResponse({"error": "No transcription segments produced."}, status=400)
        segments = translate_segments(segments, wav_path=wav_path, model_name=model_name)
        srt_path = generate_srt(segments, output_dir=output_dir)
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
