from django.urls import path

from .views import (
    finalize_subtitles,
    generate_subtitles,
    get_review_units,
    health,
    retranslate_sentence,
    transcribe_audio_only,
    translate_segments_only,
)


urlpatterns = [
    # Health
    path("health/", health, name="health"),

    # Legacy endpoints (kept for backward compatibility)
    path("transcribe/", transcribe_audio_only, name="transcribe_audio_only"),
    path("translate/", translate_segments_only, name="translate_segments_only"),
    path("subtitles/", generate_subtitles, name="generate_subtitles"),

    # Hybrid review architecture endpoints
    path("review-units/", get_review_units, name="get_review_units"),
    path("retranslate-sentence/", retranslate_sentence, name="retranslate_sentence"),
    path("finalize-subtitles/", finalize_subtitles, name="finalize_subtitles"),
]
