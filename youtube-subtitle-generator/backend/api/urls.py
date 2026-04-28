from django.urls import path

from .views import generate_subtitles, health, transcribe_audio_only, translate_segments_only


urlpatterns = [
    path("health/", health, name="health"),
    path("transcribe/", transcribe_audio_only, name="transcribe_audio_only"),
    path("translate/", translate_segments_only, name="translate_segments_only"),
    path("subtitles/", generate_subtitles, name="generate_subtitles"),
]
