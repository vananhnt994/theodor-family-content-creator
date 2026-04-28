import json
import logging
import os
import sys
from datetime import datetime

from art_director.config import INPUT_DIR, INPUT_FILENAME, OUTPUT_DIR, OUTPUT_FILENAME
from art_director.prompt_refiner import refine_prompts
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ArtDirectorMain")


def _rotate_voice(channel_cfg: dict) -> str:
    """
    For Long-Form mode: rotate through available voices based on how many
    times each has been used in historie_long.json.
    Returns the voice key (e.g. 'Mann', 'Frau', 'Kind') that has been used least.
    """
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from channel_config import load_channel_config

    available = list(channel_cfg.get("voices", {}).keys())
    if not available:
        return "Frau"
    if len(available) == 1:
        return available[0]

    # Count usage per voice from long history
    history_path = os.path.join("output", "historie_long.json")
    counts = {v: 0 for v in available}
    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
            for entry in history:
                v = entry.get("selected_voice")
                if v in counts:
                    counts[v] += 1
        except Exception:
            pass

    # Pick the least-used voice
    return min(counts, key=counts.get)


def _run_long_form(data: dict, env_path: str):
    """Handle the Long-Form Story-Critic pipeline."""
    import google.generativeai as genai
    from art_director.config import LONG_FORM_STORY_CRITIC_PROMPT, GEMINI_MODEL

    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from channel_config import load_channel_config
    channel_cfg = load_channel_config()

    genai.configure(api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", ""))

    cleaned_text = data.get("cleaned_text", "")
    video_title = data.get("video_title", "Unbekannt")

    logger.info(f"📖 Starte Story-Kritiker für: '{video_title}'")
    logger.info(f"   Textlänge: {len(cleaned_text)} Zeichen")

    # Step 1: Optimize text for read-aloud via Gemini
    logger.info("✍️  Gemini optimiert den Text für Kinder & Eltern...")
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=LONG_FORM_STORY_CRITIC_PROMPT,
            generation_config=genai.GenerationConfig(temperature=0.4),
        )
        # Truncate if very long (Gemini context limit safety)
        text_for_llm = cleaned_text[:20000] if len(cleaned_text) > 20000 else cleaned_text
        response = model.generate_content(
            f"Optimize this Vietnamese book chapter for read-aloud:\n\n{text_for_llm}"
        )
        if response.candidates:
            optimized_text = response.text.strip()
            logger.info(f"✓ Text optimiert ({len(optimized_text)} Zeichen).")
        else:
            logger.warning("⚠ Gemini hat nichts zurückgegeben – verwende bereinigten Originaltext.")
            optimized_text = cleaned_text
    except Exception as e:
        logger.warning(f"⚠ Fehler beim Story-Kritiker: {e}. Nutze Originaltext.")
        optimized_text = cleaned_text

    # Step 2: Generate single cover image prompt
    logger.info("🎨 Generiere Cover-Bild-Prompt...")
    try:
        cover_model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config=genai.GenerationConfig(temperature=0.5),
        )
        cover_response = cover_model.generate_content(
            f"""Create a single English image prompt for a children's book cover illustration.
Book chapter title: "{video_title}"
Style: flat 2D Japanese anime, Studio Ghibli, warm pastel colors, soft watercolor, cozy and dreamy atmosphere, suitable for a bedtime story cover.
Rules: No text in the image. Under 60 words. Return ONLY the prompt text, nothing else."""
        )
        if cover_response.candidates:
            bild_prompt = cover_response.text.strip()
            logger.info(f"✓ Cover-Prompt: {bild_prompt[:80]}...")
        else:
            bild_prompt = f"A cozy dreamy anime illustration of a child reading a book under warm lamplight, Studio Ghibli style, soft pastel colors."
    except Exception as e:
        logger.warning(f"⚠ Cover-Prompt Fehler: {e}. Nutze Fallback.")
        bild_prompt = "A cozy dreamy anime illustration of a child reading a book under warm lamplight, Studio Ghibli style, soft pastel colors."

    # Step 3: Rotate voice selection
    selected_voice = _rotate_voice(channel_cfg)
    logger.info(f"🎙️  Gewählte Stimme (rotiert): {selected_voice}")

    return optimized_text, bild_prompt, selected_voice


def main():
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
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f" Lese Skript: '{data.get('video_title', 'Unbekannt')}'")

    # ----------------------------------------------------------------
    # Long-Form mode: Story Critic + 1 cover image + voice rotation
    # ----------------------------------------------------------------
    if data.get("mode") == "long":
        logger.info("📖 Long-Form Modus: Story-Kritiker aktiv...")

        optimized_text, bild_prompt, selected_voice = _run_long_form(data, env_path)

        data["optimized_text"] = optimized_text
        data["cover_image"] = {"bild_prompt": bild_prompt}
        data["selected_voice"] = selected_voice
        data["art_director_checked_at"] = datetime.now().isoformat()

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ Long-Form Ausgabe gespeichert: {out_path}")
        return

    # ----------------------------------------------------------------
    # Shorts mode: existing prompt refinement
    # ----------------------------------------------------------------
    scenes = data.get("scenes", [])
    if not scenes:
        logger.error("✗ Keine Szenen im JSON gefunden.")
        sys.exit(1)

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
        sys.exit(1)


if __name__ == "__main__":
    main()
