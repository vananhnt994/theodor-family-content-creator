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
        
        prompt = f"""Optimize this Vietnamese bedtime story. 
CRITICAL REQUIREMENTS:
1. MANDATORY CREATIVE ENRICHMENT: You MUST weave in at least 2-3 educational or cultural elements (Famous Landmarks, Historical Figures like Mozart/Da Vinci, Universe/Science facts, or World Cultures). These must feel natural within the story.
2. FLOW & WARMTH: Make it sound natural, warm, and engaging for parents to read to children.
3. LENGTH: The final story MUST be between 2000 and 3000 words (~15-25 minutes read time). If the input is too long, condense it skillfully.
4. SATISFYING ENDING: Ensure the story has a proper, warm conclusion.

Input Text:
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

    # Step 3: Always use 'Frau' for bedtime stories (user request)
    selected_voice = "Frau"
    logger.info(f"🎙️  Gewählte Stimme (Fixiert): {selected_voice}")

    return optimized_text, selected_voice


def _run_long_form_natur(data: dict, env_path: str):
    """Handle the Long-Form Natur pipeline: text optimization + 6-scene split with image/video prompts."""
    from google.genai import types
    from art_director.config import (
        LONG_FORM_NATUR_CRITIC_PROMPT,
        LONG_FORM_NATUR_SCENE_SPLIT_PROMPT,
        GEMINI_MODEL
    )

    client = create_client()

    cleaned_text = data.get("cleaned_text", "")
    video_title = data.get("video_title", "Unbekannt")
    animal = data.get("animal", "")

    logger.info(f"🌿 Starte Natur-Kritiker für: '{video_title}'")
    logger.info(f"   Tier: {animal}")
    logger.info(f"   Textlänge: {len(cleaned_text)} Zeichen")

    # Step 1: Optimize text for nature narration
    logger.info("✍️  Gemini optimiert den Text für Natur-Entdeckung...")
    try:
        config = types.GenerateContentConfig(
            system_instruction=LONG_FORM_NATUR_CRITIC_PROMPT,
            temperature=0.5,
            max_output_tokens=4096,
        )

        prompt = f"""Optimize this Vietnamese nature exploration text.
CRITICAL REQUIREMENTS:
1. Make it sound exciting, curious, and playful — like a nature documentary for kids.
2. Organize into exactly 6 content blocks with variable lengths (60, 100, 100, 120, 140, 160 words).
3. Keep all factual content about the animal: {animal}
4. Final length: 700-800 words (~7 minutes).

Input Text:
{cleaned_text}"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config
        )
        if response.candidates:
            optimized_text = response.text.strip()
            logger.info(f"✓ Text optimiert ({len(optimized_text)} Zeichen).")
        else:
            logger.warning("⚠ Gemini hat nichts zurückgegeben – verwende Originaltext.")
            optimized_text = cleaned_text
    except Exception as e:
        logger.warning(f"⚠ Fehler beim Natur-Kritiker: {e}. Nutze Originaltext.")
        optimized_text = cleaned_text

    # Step 2: Scene-Split with image + video prompts
    logger.info("")
    logger.info("🎬 Schritt 2: Szenen-Split mit Bild+Video-Prompts (6 Szenen)...")
    logger.info("-" * 40)

    try:
        scene_prompt = f"""{LONG_FORM_NATUR_SCENE_SPLIT_PROMPT}

TIER IM FOKUS: {animal}
Verwende KONSISTENTE Beschreibung für {animal} in JEDEM bild_prompt und video_prompt.

NATUR-SKRIPT:
{optimized_text}"""

        scene_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.4,
            safety_settings=SAFETY_SETTINGS_NONE,
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=scene_prompt,
            config=scene_config,
        )

        if not response.candidates:
            logger.error("⚠ Gemini hat den Scene-Split blockiert.")
            raise ValueError("Scene split blocked by content filter")

        from shared.gemini_utils import extract_json
        result = extract_json(response.text)
        if not result or "scenes" not in result:
            raise ValueError(f"JSON-Parse fehlgeschlagen: {response.text[:200]}")

        scenes = result["scenes"]

        # Validate and clean scenes
        valid_scenes = []
        for i, scene in enumerate(scenes):
            scene["scene_number"] = i + 1
            scene["duration_seconds"] = scene.get("duration_seconds", 60)
            
            # Support both backward compatibility (if Gemini still outputs bild_prompt sometimes) and two image prompts
            bp_fallback = scene.get("bild_prompt") or f"flat 2D Japanese anime illustration, cute Studio Ghibli style, bright daylight, {animal} in a lush green forest, 16:9 landscape format."
            
            if "bild_prompt_a" not in scene:
                scene["bild_prompt_a"] = scene.get("bild_prompt") or bp_fallback
            if "bild_prompt_b" not in scene:
                # Add a slight variation to the second prompt if it was missing
                scene["bild_prompt_b"] = scene.get("bild_prompt_a") + " Alternative view, slightly different angle, cute close-up."
                
            if "video_prompt" not in scene:
                scene["video_prompt"] = f"Gentle {animal} moving through sunlit forest, soft breeze, peaceful nature atmosphere."
            valid_scenes.append(scene)

        logger.info(f"✓ {len(valid_scenes)} Szenen mit Bild+Video-Prompts (jeweils 2 Bilder) generiert.")
        for s in valid_scenes:
            logger.info(f"  🎞 Szene {s['scene_number']}: {s.get('emotion', '?')} | {s['voiceover_text'][:50]}...")

    except Exception as e:
        logger.error(f"⚠ Fehler beim Scene-Split: {e}. Erstelle Fallback-Szenen.")
        # Fallback: split text into 6 parts with variable durations
        words = optimized_text.split()
        # Variable chunk sizes matching 7-min structure (proportional)
        chunk_ratios = [60, 100, 100, 120, 140, 160]  # word targets per section
        total_ratio = sum(chunk_ratios)
        durations = [40, 60, 60, 70, 90, 100]  # seconds per section
        valid_scenes = []
        word_pos = 0
        for i in range(6):
            chunk_words = max(1, int(len(words) * chunk_ratios[i] / total_ratio))
            end_pos = word_pos + chunk_words if i < 5 else len(words)
            scene_text = " ".join(words[word_pos:end_pos])
            word_pos = end_pos
            valid_scenes.append({
                "scene_number": i + 1,
                "voiceover_text": scene_text,
                "duration_seconds": durations[i],
                "emotion": "curious",
                "bild_prompt_a": f"flat 2D Japanese anime illustration, cute Studio Ghibli style, bright daylight, {animal} in a lush green forest, 16:9 landscape format.",
                "bild_prompt_b": f"flat 2D Japanese anime illustration, cute Studio Ghibli style, bright daylight, cute close-up of {animal} in a lush green forest, 16:9 landscape format.",
                "video_prompt": f"Gentle {animal} exploring nature, soft breeze, peaceful forest atmosphere.",
            })

    selected_voice = "Frau"
    logger.info(f"🎙️  Gewählte Stimme: {selected_voice}")

    return optimized_text, selected_voice, valid_scenes


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
        category = data.get("category", "schlaf")
        logger.info(f"📖 Long-Form Modus (Kategorie: {category})...")

        if category == "natur":
            optimized_text, selected_voice, scenes = _run_long_form_natur(data, env_path)
            data["optimized_text"] = optimized_text
            data["selected_voice"] = selected_voice
            data["scenes"] = scenes
            data["scene_count"] = len(scenes)
        else:
            optimized_text, selected_voice = _run_long_form(data, env_path)
            data["optimized_text"] = optimized_text
            data["selected_voice"] = selected_voice

        data["art_director_checked_at"] = datetime.now().isoformat()

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"✓ Long-Form Ausgabe gespeichert: {out_path}")
        if category == "natur":
            logger.info(f"  📸 {len(scenes)} Szenen mit Bild+Video-Prompts generiert.")
        return

    # ----------------------------------------------------------------
    # Shorts mode: existing prompt refinement
    # ----------------------------------------------------------------
    scenes = data.get("scenes", [])
    if not scenes:
        logger.error("✗ Keine Szenen im JSON gefunden.")
        sys.exit(1)

    full_script = " ".join([s.get("voiceover_text", "") for s in scenes])
    refined_scenes, selected_voice = refine_prompts(scenes, full_script=full_script)

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
