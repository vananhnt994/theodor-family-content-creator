import json
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from shared.gemini_utils import SAFETY_SETTINGS_NONE, create_client
from google.genai import types
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
    from google.genai import types
    from art_director.config import LONG_FORM_STORY_CRITIC_PROMPT, GEMINI_MODEL

    client = create_client()

    cleaned_text = data.get("cleaned_text", "")
    video_title = data.get("video_title", "Unbekannt")

    logger.info(f"📖 Starte Story-Kritiker für: '{video_title}'")
    logger.info(f"   Textlänge: {len(cleaned_text)} Zeichen")

    # Step 1: Optimize text for read-aloud via Gemini
    logger.info("✍️  Gemini optimiert den Text für Kinder & Eltern...")
    try:
        config = types.GenerateContentConfig(
            system_instruction=LONG_FORM_STORY_CRITIC_PROMPT,
            temperature=0.4,
            max_output_tokens=8192,  # OP-4: cap output to ~15k chars (25 min audio)
        )
        # OP-4: Reduced from 30000 to 20000 chars — prompt already asks to condense if too long
        text_for_llm = cleaned_text[:20000] if len(cleaned_text) > 20000 else cleaned_text
        
        prompt = f"""Optimize this Vietnamese book chapter for a bedtime read-aloud.
CRITICAL INSTRUCTION: The final audio MUST NOT exceed 25 minutes (which is roughly 3000 words or 15000 characters). 
If the provided text is too long, you MUST skillfully condense or summarize parts of the story. 
However, you MUST ensure the story remains engaging and has a PROPER, SATISFYING ENDING. Do not let the story cut off abruptly!

Text:
{text_for_llm}"""
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config
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

    # Step 3: Always use 'Frau' for long form (user request)
    selected_voice = "Frau"
    logger.info(f"🎙️  Gewählte Stimme (Fixiert): {selected_voice}")

    return optimized_text, selected_voice


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

        optimized_text, selected_voice = _run_long_form(data, env_path)

        data["optimized_text"] = optimized_text
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
