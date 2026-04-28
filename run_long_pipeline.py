"""
run_long_pipeline.py – Separate orchestrator for the Long-Form "Gute Nacht Geschichten" pipeline.

Service chain:
  0. Librarian     → trend_scout  (PDF scan, sequential chapter pick)
  1. Text-Cleaner  → creator      (PDF artifact removal)
  2. Story-Critic  → art_director (LLM text optimization + cover prompt + voice rotation)
  3A. Cover Image  → image_generator (1 image via Vertex AI)
  3B. Ton-Meister  → audio_generator (chunked ElevenLabs TTS, calm speed)
  6. Video-Editor  → video_editor (FFmpeg Ken Burns zoom: image + audio → MP4)
  4. Archiver      → archiver     (ZIP + Drive upload + cleanup)

Usage:
    python run_long_pipeline.py --channel betheo
"""

import subprocess
import sys
import logging
import time
import os
import argparse

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("LongPipeline")

# Output files that mark a completed service — used to skip re-runs
OUTPUT_FILES = {
    "Service 0: Librarian":      "output/thema.json",
    "Service 1: Text-Cleaner":   "output/roh_skript.json",
    "Service 2: Story-Kritiker": "output/finale_prompts.json",
    "Service 3A: Cover-Bild":    "output/Cover.jpg",
    "Service 3B: Ton-Meister":   "output/Voiceover_Finale.mp3",
    "Service 6: Video-Editor":   "output/Final_Video.mp4",
}


def run_service(name: str, module_path: str):
    """Run a single service as a subprocess, with skip-logic for existing outputs."""
    if name in OUTPUT_FILES and os.path.exists(OUTPUT_FILES[name]):
        logger.info(f"\n{'='*50}")
        logger.info(f"⏭  Überspringe {name}: Ergebnis '{OUTPUT_FILES[name]}' existiert bereits.")
        logger.info(f"{'='*50}")
        return

    logger.info(f"\n{'='*50}")
    logger.info(f"🚀 Starte {name}...")
    logger.info(f"{'='*50}")

    start_time = time.time()

    try:
        subprocess.run(
            [sys.executable, "-m", module_path],
            check=True,
        )
        duration = time.time() - start_time
        logger.info(f"✅ {name} erfolgreich beendet in {duration:.1f} Sekunden.\n")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {name} ist fehlgeschlagen (Exit Code {e.returncode}). Pipeline wird abgebrochen.")
        sys.exit(1)


def _run_librarian(channel_file: str):
    """Run Service 0 in Librarian mode (long-form PDF chapter selection)."""
    if os.path.exists("output/thema.json"):
        logger.info(f"\n{'='*50}")
        logger.info("⏭  Überspringe Librarian: 'output/thema.json' existiert bereits.")
        logger.info(f"{'='*50}")
        return

    logger.info(f"\n{'='*50}")
    logger.info("📚 Librarian-Modus: Wähle nächstes Kapitel aus input/long/books/...")
    logger.info(f"{'='*50}")

    start_time = time.time()

    os.environ["THEODOR_CHANNEL_CONFIG"] = channel_file
    os.environ["THEODOR_PIPELINE_MODE"] = "long"
    from trend_scout.main import run_from_long_books
    run_from_long_books()

    duration = time.time() - start_time
    logger.info(f"✅ Librarian erfolgreich in {duration:.1f} Sekunden.\n")


def main():
    parser = argparse.ArgumentParser(description="Starte die Long-Form Theodorbot Pipeline.")
    parser.add_argument(
        "--channel", type=str, default="betheo",
        help="Name des zu startenden Channels (ohne .json)."
    )
    args = parser.parse_args()

    channel_file = f"channels/{args.channel}.json"
    os.environ["THEODOR_CHANNEL_CONFIG"] = channel_file
    os.environ["THEODOR_PIPELINE_MODE"] = "long"

    logger.info("==================================================")
    logger.info(f"   📚 Theodorbot - Long-Form Pipeline [{args.channel}]")
    logger.info("   Gute Nacht Geschichten — bis 12 Minuten")
    logger.info("==================================================")

    # Service 0: Librarian (runs in-process, not subprocess, so env vars are inherited)
    _run_librarian(channel_file)

    # Services 1–6 and Archiver
    services = [
        ("Service 1: Text-Cleaner",   "creator"),
        ("Service 2: Story-Kritiker", "art_director"),
        ("Service 3A: Cover-Bild",    "image_generator"),
        ("Service 3B: Ton-Meister",   "audio_generator"),
        ("Service 6: Video-Editor",   "video_editor"),
        ("Service 4: Archiver",       "archiver"),
    ]

    for name, module in services:
        run_service(name, module)

    logger.info("🎉 Long-Form Pipeline erfolgreich abgeschlossen!")
    logger.info("Das Video sollte jetzt auf Google Drive verfügbar sein.")


if __name__ == "__main__":
    main()
