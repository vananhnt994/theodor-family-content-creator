import os
import json
import logging
import sys
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ImageGenerator")

INPUT_FILE = "output/finale_prompts.json"
OUTPUT_DIR = "output"

def main():
    # .env laden für Umgebungsvariablen wie GOOGLE_APPLICATION_CREDENTIALS
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)
    load_dotenv()
    
    logger.info("==================================================")
    logger.info("   🖼️ Theodorbot - Service 3A: Bild-Beschaffer    ")
    logger.info("==================================================")
    
    project = os.environ.get("GOOGLE_PROJECT_ID")
    location = os.environ.get("GOOGLE_LOCATION", "us-central1")
    
    try:
        vertexai.init(project=project, location=location)
        model = ImageGenerationModel.from_pretrained("imagen-4.0-fast-generate-001") # Vertex Imagen 3/Fast API Modell
    except Exception as e:
        logger.error(f"✗ Vertex AI Setup gescheitert. Bitte prüfe deine GOOGLE_APPLICATION_CREDENTIALS: {e}")
        sys.exit(1)

    if not os.path.exists(INPUT_FILE):
        logger.error(f"✗ Input Datei {INPUT_FILE} fehlt.")
        sys.exit(1)
        
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    scenes = data.get("scenes", [])
    
    has_error = False
    for scene in scenes:
        sn = scene.get("scene_number")
        prompt = scene.get("bild_prompt")
        
        if not prompt: continue
        
        out_path = os.path.join(OUTPUT_DIR, f"Szene_{sn:02d}.jpg")
        if os.path.exists(out_path):
            logger.info(f"Szene {sn} Bild existiert bereits. Überspringe...")
            continue
            
        logger.info(f"🎨 Generiere Bild für Szene {sn} (9:16) via Vertex AI...")
        try:
            images = model.generate_images(
                prompt=prompt,
                number_of_images=1,
                language="en",
                aspect_ratio="9:16",
            )
            if images:
                images[0].save(location=out_path)
                logger.info(f"✓ Bild gespeichert: {out_path}")
            else:
                logger.error(f"✗ Kein Bild für Szene {sn} erhalten.")
                has_error = True
        except Exception as e:
            logger.error(f"✗ Fehler bei Szene {sn}: {e}")
            has_error = True

    if has_error:
        sys.exit(1)

if __name__ == "__main__":
    main()
