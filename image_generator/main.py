import os
import json
import logging
import sys
from google import genai
from google.genai import types
from PIL import Image
import io
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
        client = genai.Client(vertexai=True, project=project, location=location)
    except Exception as e:
        logger.error(f"✗ Vertex AI Setup gescheitert. Bitte prüfe deine GOOGLE_APPLICATION_CREDENTIALS: {e}")
        sys.exit(1)

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

                    logger.info(f"🎨 Generiere Bild für Szene {sn} ({suffix}) (16:9) via Vertex AI...")

                    current_prompt = prompt
                    max_retries = 2
                    for attempt in range(max_retries + 1):
                        try:
                            result = client.models.generate_images(
                                model='imagen-4.0-fast-generate-001',
                                prompt=current_prompt,
                                config=types.GenerateImagesConfig(
                                    number_of_images=1,
                                    output_mime_type="image/jpeg",
                                    aspect_ratio="16:9"
                                )
                            )
                            if result.generated_images:
                                image = Image.open(io.BytesIO(result.generated_images[0].image.image_bytes))
                                image.save(out_path)
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
                            else:
                                logger.error(f"✗ Kein Bild {suffix} für Szene {sn} erhalten.")
                                has_error = True
                                break
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
                logger.info("🎨 Generiere Cover-Bild (16:9) via Vertex AI...")
                try:
                    result = client.models.generate_images(
                        model='imagen-4.0-fast-generate-001',
                        prompt=prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            output_mime_type="image/jpeg",
                            aspect_ratio="16:9"
                        )
                    )
                    if result.generated_images:
                        image = Image.open(io.BytesIO(result.generated_images[0].image.image_bytes))
                        image.save(out_path)
                        logger.info(f"✓ Cover gespeichert: {out_path}")
                    else:
                        logger.error("✗ Kein Bild erhalten.")
                        sys.exit(1)
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
            
        logger.info(f"🎨 Generiere Bild für Szene {sn} (9:16) via Vertex AI...")
        
        current_prompt = prompt
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                result = client.models.generate_images(
                    model='imagen-4.0-fast-generate-001',
                    prompt=current_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/jpeg",
                        aspect_ratio="9:16"
                    )
                )
                if result.generated_images:
                    image = Image.open(io.BytesIO(result.generated_images[0].image.image_bytes))
                    image.save(out_path)
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
                    # --------------------------
                else:
                    logger.error(f"✗ Kein Bild für Szene {sn} erhalten.")
                    has_error = True
                    break
            except Exception as e:
                logger.error(f"✗ Fehler bei Szene {sn} (Versuch {attempt + 1}): {e}")
                if attempt == max_retries:
                    has_error = True

    if has_error:
        sys.exit(1)

if __name__ == "__main__":
    main()
