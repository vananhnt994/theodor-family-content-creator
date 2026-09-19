import os
import json
import logging
import sys
import io
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from shared.gemini_utils import create_client

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ImageGenerator")

INPUT_FILE = "output/finale_prompts.json"
OUTPUT_DIR = "output"

def generate_image(prompt: str, aspect_ratio: str = "9:16") -> Image.Image:
    """
    Generates an image using available providers/models:
    1. Vertex AI Imagen models (if GOOGLE_PROJECT_ID set & access available)
    2. Gemini API Key Client with native image models (gemini-3.1-flash-image, gemini-2.5-flash-image)
    """
    project = os.environ.get("GOOGLE_PROJECT_ID")
    location = os.environ.get("GOOGLE_LOCATION", "us-central1")

    # 1. Try Vertex AI Imagen if configured
    if project:
        for model_name in ["imagen-3.0-generate-002", "imagen-3.0-fast-generate-001"]:
            try:
                vclient = genai.Client(vertexai=True, project=project, location=location)
                result = vclient.models.generate_images(
                    model=model_name,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/jpeg",
                        aspect_ratio=aspect_ratio
                    )
                )
                if result.generated_images:
                    return Image.open(io.BytesIO(result.generated_images[0].image.image_bytes))
            except Exception as e:
                logger.debug(f"Vertex AI Imagen ({model_name}) nicht verfügbar: {e}")

    # 2. Fallback: Gemini API Key Client
    gclient = create_client()
    ratio_str = "9:16 vertical ratio" if aspect_ratio == "9:16" else "16:9 horizontal ratio"
    full_prompt = f"{prompt} Format: {ratio_str}."

    for model_name in ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]:
        try:
            res = gclient.models.generate_content(
                model=model_name,
                contents=full_prompt,
            )
            if res.candidates:
                for part in res.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        return Image.open(io.BytesIO(part.inline_data.data))
        except Exception as e:
            logger.debug(f"Gemini API Modell ({model_name}) fehlgeschlagen: {e}")

    raise RuntimeError("Kein Bildgenerator verfügbar oder alle Versuche fehlgeschlagen.")


def main():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)
    load_dotenv()
    
    logger.info("==================================================")
    logger.info("   🖼️ Theodorbot - Service 3A: Bild-Beschaffer    ")
    logger.info("==================================================")

    if not os.path.exists(INPUT_FILE):
        logger.error(f"✗ Input Datei {INPUT_FILE} fehlt.")
        sys.exit(1)
        
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    scenes = data.get("scenes", [])

    # ------------------------------------------------------------------
    # Long-Form mode
    # ------------------------------------------------------------------
    if data.get("mode") == "long":
        category = data.get("category", "schlaf")

        if category == "natur":
            # Natur: Generate 12 scene images (2 per scene) in 16:9 landscape
            scenes = data.get("scenes", [])
            if not scenes:
                logger.error("✗ Keine Szenen in finale_prompts.json gefunden für Natur-Modus.")
                sys.exit(1)

            logger.info(f"🌿 Natur-Modus: Generiere {len(scenes) * 2} Szenen-Bilder (16:9 - 2 pro Szene)...")
            has_error = False
            for scene in scenes:
                sn = scene.get("scene_number")
                prompts_to_gen = [
                    ("A", scene.get("bild_prompt_a") or scene.get("bild_prompt")),
                    ("B", scene.get("bild_prompt_b") or scene.get("bild_prompt"))
                ]

                for suffix, prompt in prompts_to_gen:
                    if not prompt:
                        continue

                    out_path = os.path.join(OUTPUT_DIR, f"Szene_{sn:02d}_{suffix}.jpg")
                    if os.path.exists(out_path):
                        logger.info(f"Szene {sn} Bild {suffix} existiert bereits. Überspringe...")
                        continue

                    logger.info(f"🎨 Generiere Bild für Szene {sn} ({suffix}) (16:9)...")

                    current_prompt = prompt
                    max_retries = 2
                    for attempt in range(max_retries + 1):
                        try:
                            image = generate_image(current_prompt, aspect_ratio="16:9")
                            image.convert("RGB").save(out_path, "JPEG")
                            logger.info(f"✓ Bild {suffix} gespeichert: {out_path} (Versuch {attempt + 1})")

                            # --- Quality Check Step ---
                            from image_generator.checker import check_image, refine_prompt_on_failure
                            logger.info(f"🔍 Prüfe Bildqualität für Szene {sn} ({suffix})...")
                            check_result = check_image(out_path, current_prompt, scene.get("voiceover_text", ""))

                            if check_result.get("is_passed"):
                                logger.info(f"✅ Qualitätssicherung bestanden (Score: {check_result.get('score')}/10)")
                                break
                            else:
                                logger.warning(f"⚠️ QUALITÄTS-WARNUNG Szene {sn} ({suffix}): {check_result.get('reason')}")
                                if attempt < max_retries:
                                    logger.info(f"🔄 Verfeinere Prompt und versuche es erneut...")
                                    current_prompt = refine_prompt_on_failure(
                                        current_prompt,
                                        check_result.get("reason", ""),
                                        check_result.get("missing_elements", [])
                                    )
                                else:
                                    logger.error(f"❌ Max. Versuche erreicht für Szene {sn} ({suffix}). Behalte letztes Bild.")
                        except Exception as e:
                            logger.error(f"✗ Fehler bei Szene {sn} ({suffix}) (Versuch {attempt + 1}): {e}")
                            if attempt == max_retries:
                                has_error = True

            if has_error:
                sys.exit(1)
            return

        else:
            # Schlaf: Generate a single cover image (16:9)
            cover = data.get("cover_image", {})
            prompt = cover.get("bild_prompt")
            if not prompt:
                logger.error("✗ Kein 'bild_prompt' in cover_image gefunden.")
                sys.exit(1)

            out_path = os.path.join(OUTPUT_DIR, "Cover.jpg")
            if os.path.exists(out_path):
                logger.info(f"Cover existiert bereits ({out_path}). Überspringe Generierung...")
            else:
                logger.info("🎨 Generiere Cover-Bild (16:9)...")
                try:
                    image = generate_image(prompt, aspect_ratio="16:9")
                    image.convert("RGB").save(out_path, "JPEG")
                    logger.info(f"✓ Cover gespeichert: {out_path}")
                except Exception as e:
                    logger.error(f"✗ Fehler bei Cover-Generierung: {e}")
                    sys.exit(1)
            return

    # ------------------------------------------------------------------
    # Shorts mode: generate per-scene images
    # ------------------------------------------------------------------
    has_error = False
    for scene in scenes:
        sn = scene.get("scene_number")
        prompt = scene.get("bild_prompt")
        
        if not prompt: continue
        
        out_path = os.path.join(OUTPUT_DIR, f"Szene_{sn:02d}.jpg")
        if os.path.exists(out_path):
            logger.info(f"Szene {sn} Bild existiert bereits. Überspringe...")
            continue
            
        logger.info(f"🎨 Generiere Bild für Szene {sn} (9:16)...")
        
        current_prompt = prompt
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                image = generate_image(current_prompt, aspect_ratio="9:16")
                image.convert("RGB").save(out_path, "JPEG")
                logger.info(f"✓ Bild gespeichert: {out_path} (Versuch {attempt + 1})")

                # --- Quality Check Step ---
                from image_generator.checker import check_image, refine_prompt_on_failure
                logger.info(f"🔍 Prüfe Bildqualität für Szene {sn}...")
                check_result = check_image(out_path, current_prompt, scene.get("voiceover_text", ""))
                
                if check_result.get("is_passed"):
                    logger.info(f"✅ Qualitätssicherung bestanden (Score: {check_result.get('score')}/10)")
                    break # Success!
                else:
                    logger.warning(f"⚠️ QUALITÄTS-WARNUNG Szene {sn}: {check_result.get('reason')}")
                    if attempt < max_retries:
                        logger.info(f"🔄 Verfeinere Prompt und versuche es erneut...")
                        current_prompt = refine_prompt_on_failure(
                            current_prompt, 
                            check_result.get("reason", ""), 
                            check_result.get("missing_elements", [])
                        )
                        logger.debug(f"Neuer Prompt: {current_prompt}")
                    else:
                        logger.error(f"❌ Max. Versuche erreicht für Szene {sn}. Behalte letztes Bild.")
            except Exception as e:
                logger.error(f"✗ Fehler bei Szene {sn} (Versuch {attempt + 1}): {e}")
                if attempt == max_retries:
                    has_error = True

    if has_error:
        sys.exit(1)

if __name__ == "__main__":
    main()
