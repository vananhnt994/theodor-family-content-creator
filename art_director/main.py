import json
import logging
import os
from datetime import datetime

from art_director.config import INPUT_DIR, INPUT_FILENAME, OUTPUT_DIR, OUTPUT_FILENAME
from art_director.prompt_refiner import refine_prompts
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ArtDirectorMain")

def main():
    # Lade zuerst eine eventuelle .env aus dem art_director Ordner, dann als Fallback aus dem Stammverzeichnis:
    import os
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)
    load_dotenv()
    
    logger.info("==================================================")
    logger.info("   🎬 Theodorbot - Service 2: The Art Director    ")
    logger.info("==================================================")
    
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
         logger.warning("⚠ ACHTUNG: GEMINI_API_KEY nicht gesetzt. API Aufrufe werden möglicherweise fehlschlagen.")

    input_path = os.path.join(INPUT_DIR, INPUT_FILENAME)
    if not os.path.exists(input_path):
        logger.error(f"✗ Input-Datei nicht gefunden: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f" Lese Skript: '{data.get('video_title', 'Unbekannt')}'")
    scenes = data.get("scenes", [])
    
    if not scenes:
        logger.error("✗ Keine Szenen im JSON gefunden.")
        return

    refined_scenes, selected_voice = refine_prompts(scenes)
    
    if refined_scenes:
        data["scenes"] = refined_scenes
        data["selected_voice"] = selected_voice
        data["art_director_checked_at"] = datetime.now().isoformat()
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"✓ Finale Prompts gespeichert in: {out_path}")
    else:
        logger.error("✗ Verfeinerung fehlgeschlagen.")

if __name__ == "__main__":
    main()
