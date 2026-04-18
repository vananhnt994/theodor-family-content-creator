import subprocess
import sys
import logging
import time
import os
import argparse

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("UploaderPipeline")

def run_service(name: str, module_path: str):
    logger.info(f"\n{'='*50}")
    logger.info(f"🚀 Starte {name}...")
    logger.info(f"{'='*50}")
    
    start_time = time.time()
    
    try:
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
    parser = argparse.ArgumentParser(description="Starte den Theodorbot Uploader.")
    parser.add_argument("--channel", type=str, default="betheo", help="Name des zu startenden Channels (ohne .json).")
    args = parser.parse_args()

    channel_file = f"channels/{args.channel}.json"
    os.environ["THEODOR_CHANNEL_CONFIG"] = channel_file

    logger.info("==================================================")
    logger.info(f"   ⏱ Theodorbot - Uploader Schedule Start [{args.channel}]")
    logger.info("==================================================")
    
    run_service("Service 5: The Uploader", "uploader.main")
        
    logger.info("🎉 Upload-Durchlauf beendet!")

if __name__ == "__main__":
    main()
