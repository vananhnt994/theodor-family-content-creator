"""
run_long_pipeline.py – Separate orchestrator for the Long-Form pipeline.

Supports two categories:
  - schlaf (default): Gute Nacht Geschichten (audio only, ~12 min)
  - natur: Natur erkunden (video with 6 scenes, ~6 min)

Service chain:
  0. Librarian     → trend_scout  (PDF scan, sequential chapter pick)
  1. Text-Cleaner  → creator      (PDF artifact removal)
  2. Story-Critic  → art_director (LLM text optimization + cover prompt + voice rotation)
  3A. Cover Image  → image_generator (1 image via Vertex AI) [natur: 6 images]
  3B. Ton-Meister  → audio_generator (chunked ElevenLabs TTS, calm speed)
  6. Video-Editor  → video_editor (FFmpeg Ken Burns zoom: image + audio → MP4) [natur only]
  4. Archiver      → archiver     (ZIP + Drive upload + cleanup)

Usage:
    python run_long_pipeline.py --channel betheo                       # Schlafgeschichten (default)
    python run_long_pipeline.py --channel betheo --category schlaf     # Explicit schlaf
    python run_long_pipeline.py --channel betheo --category natur      # Natur erkunden
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


def _run_long_source(channel_file: str, mode: str = "book"):
    """Run Service 0 for Long-Form (Librarian, Article, or Natur-Direct mode)."""
    if os.path.exists("output/thema.json"):
        logger.info(f"\n{'='*50}")
        logger.info("⏭  Überspringe Service 0: 'output/thema.json' existiert bereits.")
        logger.info(f"{'='*50}")
        return

    start_time = time.time()
    os.environ["THEODOR_CHANNEL_CONFIG"] = channel_file
    os.environ["THEODOR_PIPELINE_MODE"] = "long"

    category = os.environ.get("THEODOR_LONG_CATEGORY", "schlaf")

    if category == "natur":
        # Natur: Direct KI generation — no book reader
        logger.info(f"\n{'='*50}")
        logger.info("🌿 Natur-Modus: KI generiert direkt eine neue Tiergeschichte...")
        logger.info(f"{'='*50}")
        from trend_scout.main import run_natur_direct
        run_natur_direct()
    elif mode == "artikel":
        from trend_scout.main import run_from_long_books, run_long_from_file
        artikel_path = os.path.join("input", "shorts", "artikel.txt")
        logger.info(f"\n{'='*50}")
        logger.info(f"📝 Artikel-Storyteller: Lese '{artikel_path}'...")
        logger.info(f"{'='*50}")
        run_long_from_file(artikel_path)
    else:
        from trend_scout.main import run_from_long_books
        logger.info(f"\n{'='*50}")
        logger.info("📚 Librarian-Modus: Wähle nächstes Kapitel aus input/long/books/...")
        logger.info(f"{'='*50}")
        run_from_long_books()

    duration = time.time() - start_time
    logger.info(f"✅ Service 0 erfolgreich in {duration:.1f} Sekunden.\n")



def main():
    parser = argparse.ArgumentParser(description="Starte die Long-Form Theodorbot Pipeline.")
    parser.add_argument(
        "--channel", type=str, default="betheo",
        help="Name des zu startenden Channels (ohne .json)."
    )
    parser.add_argument(
        "--category", type=str, default="schlaf",
        choices=["schlaf", "natur"],
        help="Long-Form Kategorie: 'schlaf' (Gute Nacht Geschichten) oder 'natur' (Natur erkunden)."
    )
    parser.add_argument("--artikel", action="store_true", help="Liest input/shorts/artikel.txt als Basis für die Geschichte.")
    parser.add_argument("--book", action="store_true", help="Wählt ein Kapitel aus input/long/books/ als Basis (Standard).")
    args = parser.parse_args()

    channel_file = f"channels/{args.channel}.json"
    os.environ["THEODOR_CHANNEL_CONFIG"] = channel_file
    os.environ["THEODOR_PIPELINE_MODE"] = "long"
    os.environ["THEODOR_LONG_CATEGORY"] = args.category

    logger.info("==================================================")
    logger.info(f"   📚 Theodorbot - Long-Form Pipeline [{args.channel}]")
    if args.category == "natur":
        logger.info("   🌿 Natur erkunden — ~7 Minuten (Video mit 6 Szenen)")
    else:
        logger.info("   😴 Gute Nacht Geschichten — bis 12 Minuten")
    logger.info("==================================================")

    # Service 0: Get the source and generate the base story
    mode = "artikel" if args.artikel else "book"
    _run_long_source(channel_file, mode=mode)

    # Build service chain based on category
    if args.category == "natur":
        # Natur: Hybrid pipeline with scenes and images (video editor removed by user request)
        services = [
            ("Service 1: Text-Cleaner",   "creator"),
            ("Service 2: Story-Kritiker", "art_director"),
            ("Service 3A: Cover-Bild",    "image_generator"),
            ("Service 3B: Ton-Meister",   "audio_generator"),
            ("Service 4: Archiver",       "archiver"),
        ]
    else:
        # Schlaf: Text-only pipeline (audio generation disabled)
        services = [
            ("Service 1: Text-Cleaner",   "creator"),
            ("Service 2: Story-Kritiker", "art_director"),
            ("Service 4: Archiver",       "archiver"),
        ]

    for name, module in services:
        run_service(name, module)

    logger.info("🎉 Long-Form Pipeline erfolgreich abgeschlossen!")
    logger.info("Die Dateien sollten jetzt auf Google Drive verfügbar sein.")


if __name__ == "__main__":
    main()
