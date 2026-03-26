from django.urls import path

from .views import health, generate_subtitles


urlpatterns = [
    path("health/", health, name="health"),
    path("subtitles/", generate_subtitles, name="generate_subtitles"),
]
