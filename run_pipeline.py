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

def main():
    parser = argparse.ArgumentParser(description="Starte die Theodorbot Pipeline.")
    parser.add_argument("--channel", type=str, default="betheo", help="Name des zu startenden Channels (ohne .json).")
    args = parser.parse_args()

    channel_file = f"channels/{args.channel}.json"
    os.environ["THEODOR_CHANNEL_CONFIG"] = channel_file

    logger.info("==================================================")
    logger.info(f"   🎬 Theodorbot - Gesamte Pipeline Start [{args.channel}]")
    logger.info("==================================================")
    
    # Ausführungsreihenfolge entsprechend der Architektur
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
