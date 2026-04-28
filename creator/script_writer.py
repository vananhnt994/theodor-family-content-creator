"""
Script Writer – The creative engine of Service 1.
Step 1: Generate a warm, professional voiceover script based on the topic mood.
Step 2: Split into timed scenes with image prompts.
"""

import json
import logging
import re

import os
import google.generativeai as genai
from dotenv import load_dotenv

from creator.config import (
    GEMINI_MODEL,
    SYSTEM_PROMPT,
    VOICEOVER_PROMPT,
    SCENE_SPLIT_PROMPT,
    TARGET_DURATION_SECONDS,
    TARGET_SCENE_COUNT,
    SCENE_DURATION_MIN,
    SCENE_DURATION_MAX,
)

logger = logging.getLogger(__name__)

# Maximum retries when LLM doesn't produce valid JSON
MAX_RETRIES = 2


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from LLM response, handling markdown code blocks."""
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try markdown code block ```json ... ```
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block (including nested)
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start:i+1])
                except json.JSONDecodeError:
                    start = -1

    return None


def _call_llm(prompt: str, temperature: float = 0.7) -> str:
    """Call Gemini with the editorial system prompt baked in."""
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    load_dotenv()
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("[Creator] ✗ GEMINI_API_KEY in .env fehlt!")
        raise ValueError("GEMINI_API_KEY fehlt")
        
    genai.configure(api_key=api_key)
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
        safety_settings=safety_settings,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=temperature
        )
    )
    response = model.generate_content(prompt)
    if not response.candidates:
        logger.warning(f"[Creator] ⚠ Gemini Content Filter blockiert: {getattr(response, 'prompt_feedback', 'Kein Feedback')}")
        raise ValueError("PROHIBITED_CONTENT block")
    return response.text.strip()


def generate_voiceover(thema: dict) -> dict | None:
    """
    Step 1: Generate a full voiceover script from the topic.

    Args:
        thema: Dict with 'title', 'description', 'solution' keys from thema.json.

    Returns:
        Dict with 'mood' and 'voiceover_full', or None on failure.
    """
    prompt = VOICEOVER_PROMPT.format(
        title=thema.get("title", ""),
        description=thema.get("description", ""),
        solution=thema.get("solution", ""),
        duration=TARGET_DURATION_SECONDS,
    )

    logger.info(f"[Creator] 📝 Generiere Voiceover-Skript mit {GEMINI_MODEL}...")

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            if attempt > 1:
                logger.info(f"[Creator] 🔄 Versuch {attempt}/{MAX_RETRIES + 1}...")

            response_text = _call_llm(prompt, temperature=0.75)
            logger.debug(f"[Creator] LLM Antwort: {response_text}")

            result = _extract_json(response_text)
            if not result:
                logger.warning(
                    f"[Creator] ⚠ JSON-Parse fehlgeschlagen (Versuch {attempt}): "
                    f"{response_text[:200]}"
                )
                if attempt <= MAX_RETRIES:
                    continue
                return None

            if "voiceover_full" not in result:
                logger.warning(f"[Creator] ⚠ 'voiceover_full' fehlt (Versuch {attempt})")
                if attempt <= MAX_RETRIES:
                    continue
                return None

            word_count = len(result["voiceover_full"].split())
            logger.info(f"[Creator] ✓ Voiceover generiert: {word_count} Wörter")
            logger.info(f"[Creator]   Stimmung: {result.get('mood', 'unbekannt')}")
            logger.info(f"[Creator]   Vorschau: {result['voiceover_full'][:120]}...")
            return result

        except Exception as e:
            logger.error(f"[Creator] ✗ Fehler bei Voiceover-Generierung: {e}")
            if attempt <= MAX_RETRIES:
                continue
            return None

    return None


def split_into_scenes(voiceover_text: str, mood: str) -> list[dict] | None:
    """
    Step 2: Split the voiceover into timed scenes with image prompts.

    Args:
        voiceover_text: The full voiceover text from Step 1.
        mood: The mood/emotion of the video.

    Returns:
        List of scene dicts, or None on failure.
    """
    prompt = SCENE_SPLIT_PROMPT.format(
        voiceover=voiceover_text,
        scene_count=TARGET_SCENE_COUNT,
        min_sec=SCENE_DURATION_MIN,
        max_sec=SCENE_DURATION_MAX,
        mood=mood,
    )

    logger.info(f"[Creator] 🎬 Szenen-Splitting ({TARGET_SCENE_COUNT} Szenen)...")

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            current_prompt = prompt
            if attempt > 1:
                logger.info(f"[Creator] 🔄 Versuch {attempt}/{MAX_RETRIES + 1} (Safe-Mode)...")
                # Fallback: Entschärfter Prompt für Gemini Filter
                current_prompt += "\n\nCRITICAL SAFETY INSTRUCTION: The generated image prompts MUST be extremely safe, positive, and non-violent. Do not describe children in distress, danger, or any negative situations. Use abstract, peaceful, or purely positive imagery (e.g. 'a peaceful garden', 'a warm glowing light', 'a calm family scene') even if the voiceover text discusses a serious or painful problem. Ignore the negative aspects of the voiceover when creating the image prompts."

            response_text = _call_llm(current_prompt, temperature=0.5)
            logger.debug(f"[Creator] LLM Antwort: {response_text}")

            result = _extract_json(response_text)
            if not result or "scenes" not in result:
                logger.warning(
                    f"[Creator] ⚠ JSON-Parse fehlgeschlagen (Versuch {attempt}): "
                    f"{response_text[:200]}"
                )
                if attempt <= MAX_RETRIES:
                    continue
                return None

            scenes = result["scenes"]

            # Validate scenes
            valid_scenes = []
            for i, scene in enumerate(scenes):
                if "voiceover_text" not in scene or "draft_prompt" not in scene:
                    logger.warning(f"[Creator] ⚠ Szene {i+1} unvollständig – überspringe")
                    continue

                # Ensure scene_number is set
                scene["scene_number"] = i + 1

                # Clamp duration
                dur = scene.get("duration_seconds", SCENE_DURATION_MIN)
                scene["duration_seconds"] = max(SCENE_DURATION_MIN, min(SCENE_DURATION_MAX, dur))

                valid_scenes.append(scene)

            if not valid_scenes:
                logger.warning(f"[Creator] ⚠ Keine gültigen Szenen (Versuch {attempt})")
                if attempt <= MAX_RETRIES:
                    continue
                return None

            total_dur = sum(s["duration_seconds"] for s in valid_scenes)
            logger.info(f"[Creator] ✓ {len(valid_scenes)} Szenen erstellt, ~{total_dur}s Gesamtdauer")

            for s in valid_scenes:
                logger.info(
                    f"[Creator]   Szene {s['scene_number']}: "
                    f"{s['duration_seconds']}s | {s.get('emotion', '?')} | "
                    f"{s['voiceover_text'][:50]}..."
                )

            return valid_scenes

        except Exception as e:
            logger.error(f"[Creator] ✗ Fehler beim Szenen-Splitting: {e}")
            if attempt <= MAX_RETRIES:
                continue
            return None

    return None
