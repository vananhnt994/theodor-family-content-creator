"""
Service 6: Der Video-Editor
Combines a single cover image and a long audio file into a video
using FFmpeg, applying a subtle Ken Burns zoom effect over the full duration.
"""

import json
import logging
import os
import subprocess
import sys
import winreg

# Ensure newly installed programs (like FFmpeg via winget) are immediately available
# without requiring the user to restart VS Code or the terminal.
try:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ) as key:
        user_path = winreg.QueryValueEx(key, "PATH")[0]
    os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + user_path
except Exception:
    pass

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("VideoEditor")

INPUT_FILE = "output/finale_prompts.json"
OUTPUT_DIR = "output"
COVER_IMAGE = "output/Cover.jpg"
AUDIO_FILE = "output/Voiceover_Finale.mp3"
OUTPUT_VIDEO = "output/Final_Video.mp4"

# Output video resolution (16:9 landscape for Long-Form Youtube)
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30


def _check_ffmpeg():
    """Verify that ffmpeg and ffprobe are available on PATH."""
    for tool in ("ffmpeg", "ffprobe"):
        result = subprocess.run(
            [tool, "-version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(
                f"✗ '{tool}' nicht gefunden! Bitte installieren:\n"
                "   Windows: choco install ffmpeg\n"
                "   oder manuell von https://ffmpeg.org/download.html"
            )
            sys.exit(1)
    logger.info("✓ FFmpeg verfügbar.")


def _get_audio_duration(audio_path: str) -> float:
    """Use ffprobe to get audio duration in seconds."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error(f"✗ ffprobe Fehler: {result.stderr}")
        sys.exit(1)
    try:
        return float(result.stdout.strip())
    except ValueError:
        logger.error(f"✗ Konnte Audio-Dauer nicht lesen: {result.stdout!r}")
        sys.exit(1)


def create_video_with_zoom(
    image_path: str,
    audio_path: str,
    output_path: str,
    duration_seconds: float,
    fps: int = VIDEO_FPS,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
):
    """
    Create a video from a still image + audio using FFmpeg's zoompan filter.
    The image slowly zooms from 100% to 105% over the full audio duration
    (Ken Burns effect), keeping things visually gentle for children.

    Args:
        image_path: Path to the cover JPG image.
        audio_path: Path to the MP3 audio file.
        output_path: Path for the output MP4 video.
        duration_seconds: Total audio duration in seconds.
        fps: Frames per second (default 30).
        width: Output video width in pixels (default 1080).
        height: Output video height in pixels (default 1920).
    """
    total_frames = int(duration_seconds * fps)

    # zoompan filter:
    #   z: zoom level — starts at 1.0, increments by tiny amount per frame → ends at ~1.05
    #   x/y: keep image centered while zooming
    #   d: total number of frames
    #   s: output size
    #   fps: input fps for the zoompan filter
    zoom_increment = 0.05 / max(total_frames, 1)  # spread 5% zoom over all frames
    zoom_expr = f"'min(zoom+{zoom_increment:.8f},1.05)'"
    x_expr = f"'iw/2-(iw/zoom/2)'"
    y_expr = f"'ih/2-(ih/zoom/2)'"

    zoompan_filter = (
        f"zoompan="
        f"z={zoom_expr}:"
        f"x={x_expr}:"
        f"y={y_expr}:"
        f"d={total_frames}:"
        f"s={width}x{height}:"
        f"fps={fps}"
    )

    cmd = [
        "ffmpeg",
        "-y",                        # overwrite output
        "-loop", "1",                # loop the still image
        "-i", image_path,            # input image
        "-i", audio_path,            # input audio
        "-filter_complex", zoompan_filter,
        "-c:v", "libx264",
        "-preset", "slow",           # better compression quality
        "-crf", "18",                # visually lossless quality
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",                 # stop when audio ends
        "-pix_fmt", "yuv420p",       # required for broad compatibility
        output_path,
    ]

    logger.info(f"🎬 Starte FFmpeg... Dauer: {duration_seconds:.1f}s | Frames: {total_frames}")
    logger.info(f"   Zoom: 100% → 105% über {duration_seconds:.0f} Sekunden")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"✗ FFmpeg Fehler:\n{result.stderr[-2000:]}")
        sys.exit(1)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    logger.info(f"✓ Video erstellt: {output_path} ({size_mb:.1f} MB)")


def main():
    logger.info("==================================================")
    logger.info("   🎬 Theodorbot - Service 6: Der Video-Editor   ")
    logger.info("==================================================")

    # 1. Check FFmpeg
    _check_ffmpeg()

    # 2. Validate inputs
    if not os.path.exists(INPUT_FILE):
        logger.error(f"✗ Input-Datei nicht gefunden: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("mode") != "long":
        logger.error("✗ Video-Editor wird nur im Long-Form Modus (mode='long') ausgeführt.")
        sys.exit(1)

    if not os.path.exists(COVER_IMAGE):
        logger.error(f"✗ Cover-Bild nicht gefunden: {COVER_IMAGE}")
        sys.exit(1)

    if not os.path.exists(AUDIO_FILE):
        logger.error(f"✗ Audio-Datei nicht gefunden: {AUDIO_FILE}")
        sys.exit(1)

    # 3. Skip if video already exists
    if os.path.exists(OUTPUT_VIDEO):
        logger.info(f"Video existiert bereits ({OUTPUT_VIDEO}). Überspringe Generierung...")
        return

    # 4. Get audio duration
    logger.info(f"🎵 Lese Audio-Dauer aus: {AUDIO_FILE}")
    duration = _get_audio_duration(AUDIO_FILE)
    logger.info(f"   Dauer: {duration:.1f}s (~{duration/60:.1f} Min.)")

    max_duration_minutes = 12
    if duration > max_duration_minutes * 60:
        logger.warning(
            f"⚠ Audio ist länger als {max_duration_minutes} Minuten ({duration/60:.1f} Min.). "
            f"Bitte prüfe das Kapitel."
        )

    # 5. Create video
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    create_video_with_zoom(
        image_path=COVER_IMAGE,
        audio_path=AUDIO_FILE,
        output_path=OUTPUT_VIDEO,
        duration_seconds=duration,
    )

    logger.info("")
    logger.info("=" * 50)
    logger.info("🎉 Service 6 erfolgreich abgeschlossen!")
    logger.info(f"   Video: {OUTPUT_VIDEO}")
    logger.info(f"   Dauer: {duration:.1f}s (~{duration/60:.1f} Min.)")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
