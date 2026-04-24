import subprocess
import sys
import logging
import time
import os
import argparse

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Pipeline")

OUTPUT_FILES = {
    "Service 0: Trend-Scout": "output/thema.json",
    "Service 1: The Creator": "output/roh_skript.json",
    "Service 2: The Art Director": "output/finale_prompts.json"
}

def run_service(name: str, module_path: str):
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
        # Ausführen als eigener Prozess, um RAM auf dem Edge Device (Nvidia Jetson) wieder freizugeben!
        result = subprocess.run(
            [sys.executable, "-m", module_path],
            check=True
        )
        duration = time.time() - start_time
        logger.info(f"✅ {name} erfolgreich beendet in {duration:.1f} Sekunden.\n")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {name} ist fehlgeschlagen (Exit Code {e.returncode}). Pipeline wird abgebrochen.")
        sys.exit(1)

def _run_artikel_mode(channel_file: str):
    """Run pipeline in manual article mode: read input/artikel.txt → generate thema.json via Gemini."""
    artikel_path = os.path.join(os.path.dirname(__file__), "input", "artikel.txt")
    
    if not os.path.exists(artikel_path):
        logger.error(f"❌ Artikel-Datei nicht gefunden: {artikel_path}")
        logger.error("   Erstelle die Datei 'input/artikel.txt' mit deinem Text.")
        sys.exit(1)
    
    # Check if thema.json already exists (skip like normal mode)
    if os.path.exists("output/thema.json"):
        logger.info(f"\n{'='*50}")
        logger.info(f"⏭  Überspringe Artikel-Verarbeitung: 'output/thema.json' existiert bereits.")
        logger.info(f"{'='*50}")
        return
    
    logger.info(f"\n{'='*50}")
    logger.info(f"📝 Artikel-Modus: Lese '{artikel_path}'...")
    logger.info(f"{'='*50}")
    
    start_time = time.time()
    
    # Import and run the file-based trend scout
    os.environ["THEODOR_CHANNEL_CONFIG"] = channel_file
    from trend_scout.main import run_from_file
    run_from_file(artikel_path)
    
    duration = time.time() - start_time
    logger.info(f"✅ Artikel verarbeitet in {duration:.1f} Sekunden.\n")

def _run_book_mode(channel_file: str):
    """Run pipeline in book mode: read a chapter from input/books/ → generate thema.json."""
    if os.path.exists("output/thema.json"):
        logger.info(f"\n{'='*50}")
        logger.info(f"⏭  Überspringe Buch-Verarbeitung: 'output/thema.json' existiert bereits.")
        logger.info(f"{'='*50}")
        return
    
    logger.info(f"\n{'='*50}")
    logger.info(f"📚 Buch-Modus: Wähle ein Kapitel aus input/books/...")
    logger.info(f"{'='*50}")
    
    start_time = time.time()
    
    os.environ["THEODOR_CHANNEL_CONFIG"] = channel_file
    from trend_scout.main import run_from_books
    run_from_books()
    
    duration = time.time() - start_time
    logger.info(f"✅ Buchkapitel verarbeitet in {duration:.1f} Sekunden.\n")


def main():
    parser = argparse.ArgumentParser(description="Starte die Theodorbot Pipeline.")
    parser.add_argument("--channel", type=str, default="betheo", help="Name des zu startenden Channels (ohne .json).")
    parser.add_argument("--artikel", action="store_true", help="Eigener Artikel-Modus: Liest input/artikel.txt statt Trend-Scout.")
    parser.add_argument("--book", action="store_true", help="Buch-Modus: Wählt ein ungelesenes Kapitel aus input/books/.")
    args = parser.parse_args()

    channel_file = f"channels/{args.channel}.json"
    os.environ["THEODOR_CHANNEL_CONFIG"] = channel_file

    logger.info("==================================================")
    if args.artikel:
        logger.info(f"   🎬 Theodorbot - Pipeline Start [{args.channel}] (Artikel-Modus)")
    elif args.book:
        logger.info(f"   🎬 Theodorbot - Pipeline Start [{args.channel}] (Buch-Modus)")
    else:
        logger.info(f"   🎬 Theodorbot - Gesamte Pipeline Start [{args.channel}]")
    logger.info("==================================================")
    
    if args.artikel:
        # Artikel-Modus: Überspringe Trend-Scout, nutze eigenen Text
        _run_artikel_mode(channel_file)
        
        # Rest der Pipeline normal ausführen (ab Service 1)
        services = [
            ("Service 1: The Creator", "creator.main"),
            ("Service 2: The Art Director", "art_director.main"),
            ("Service 3A: Bild-Beschaffer", "image_generator.main"),
            ("Service 3B: Ton-Meister", "audio_generator.main"),
            ("Service 4: Archiver", "archiver.main")
        ]
    elif args.book:
        # Buch-Modus: Nutze Buch-Kapitel statt Trend-Scout
        _run_book_mode(channel_file)
        
        # Rest der Pipeline normal ausführen (ab Service 1)
        services = [
            ("Service 1: The Creator", "creator.main"),
            ("Service 2: The Art Director", "art_director.main"),
            ("Service 3A: Bild-Beschaffer", "image_generator.main"),
            ("Service 3B: Ton-Meister", "audio_generator.main"),
            ("Service 4: Archiver", "archiver.main")
        ]
    else:
        # Normaler Modus: Alle Services
        services = [
            ("Service 0: Trend-Scout", "trend_scout.main"),
            ("Service 1: The Creator", "creator.main"),
            ("Service 2: The Art Director", "art_director.main"),
            ("Service 3A: Bild-Beschaffer", "image_generator.main"),
            ("Service 3B: Ton-Meister", "audio_generator.main"),
            ("Service 4: Archiver", "archiver.main")
        ]
    
    for name, module in services:
        run_service(name, module)
        
    logger.info("🎉 Alle Services wurden erfolgreich nacheinander ausgeführt!")
    logger.info("Dein Archiv sollte jetzt bereit oder bereits auf Google Drive sein.")

if __name__ == "__main__":
    main()
