"""
youtube_downloader.py
---------------------
Handles downloading audio from a YouTube URL using yt-dlp,
then converts it to a 16kHz mono WAV file using ffmpeg-python.
16kHz mono WAV is the format expected by OpenAI Whisper.
"""

import os
import yt_dlp
import ffmpeg


def download_audio(youtube_url: str, output_dir: str = "output") -> str:
    """
    Download audio from a YouTube URL and save it as a WAV file.

    Steps:
      1. Use yt-dlp to download the best available audio stream.
      2. Convert the downloaded file to 16kHz mono WAV with ffmpeg.

    Args:
        youtube_url: Full YouTube video URL.
        output_dir:  Directory where the WAV file will be saved.

    Returns:
        Absolute path to the converted WAV file.

    Raises:
        RuntimeError: If the download or conversion fails.
    """
    os.makedirs(output_dir, exist_ok=True)

    raw_audio_path = os.path.join(output_dir, "raw_audio")  # yt-dlp adds extension
    wav_path = os.path.join(output_dir, "audio.wav")

    # --- Step 1: Download audio with yt-dlp ---
    ydl_opts = {
        # Download only audio; prefer opus/webm/m4a for smaller files
        "format": "bestaudio/best",
        "outtmpl": raw_audio_path,
        # Post-process to extract audio; yt-dlp keeps original codec here
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        # Suppress verbose output
        "quiet": True,
        "no_warnings": True,
    }

    print(f"[Downloader] Downloading audio from: {youtube_url}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    except yt_dlp.utils.DownloadError as exc:
        raise RuntimeError(f"yt-dlp failed to download the video: {exc}") from exc

    # yt-dlp names the output file as raw_audio.wav after post-processing
    downloaded_wav = raw_audio_path + ".wav"
    if not os.path.exists(downloaded_wav):
        raise RuntimeError(
            f"Expected downloaded WAV not found at: {downloaded_wav}"
        )

    # --- Step 2: Resample to 16kHz mono WAV for Whisper ---
    print("[Downloader] Converting audio to 16kHz mono WAV for Whisper...")
    try:
        (
            ffmpeg
            .input(downloaded_wav)
            .output(
                wav_path,
                ar=16000,   # sample rate: 16 kHz
                ac=1,        # channels: mono
                acodec="pcm_s16le",  # 16-bit PCM
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as exc:
        raise RuntimeError(f"ffmpeg conversion failed: {exc.stderr.decode()}") from exc

    # Remove the intermediate raw WAV to save space
    if os.path.exists(downloaded_wav):
        os.remove(downloaded_wav)

    print(f"[Downloader] Audio saved to: {wav_path}")
    return wav_path
