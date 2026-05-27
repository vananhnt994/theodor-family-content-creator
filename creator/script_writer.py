"""
Script Writer – The creative engine of Service 1.
Step 1: Generate a warm, professional voiceover script based on the topic mood.
Step 2: Split into timed scenes with image prompts.
"""

import logging
import os
import sys

import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from shared.gemini_utils import SAFETY_SETTINGS_NONE, create_client, extract_json
from google.genai import types
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

# Module-level singleton — created once on first use
_client = None


def _get_client():
    """Return the module-level Gemini client, creating it if necessary."""
    global _client
    if _client is None:
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
        load_dotenv()
        _client = create_client()
    return _client


def _call_llm(prompt: str, temperature: float = 0.7, use_system_prompt: bool = True, model_override: str = None) -> str:
    """Call Gemini with the editorial system prompt baked in."""
    client = _get_client()

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=temperature,
        safety_settings=SAFETY_SETTINGS_NONE,
    )
    if use_system_prompt:
        config.system_instruction = SYSTEM_PROMPT

    response = client.models.generate_content(
        model=model_override or GEMINI_MODEL,
        contents=prompt,
        config=config
    )
    if not response.candidates:
        logger.warning(f"[Creator] ⚠ Gemini Content Filter blockiert: {getattr(response, 'prompt_feedback', 'Kein Feedback')}")
        raise ValueError("PROHIBITED_CONTENT block")
    return response.text.strip()

# Maximum retries when LLM doesn't produce valid JSON
MAX_RETRIES = 2


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

            response_text = _call_llm(prompt, temperature=0.75, use_system_prompt=True)
            logger.debug(f"[Creator] LLM Antwort: {response_text}")

            result = extract_json(response_text)
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
            use_sys = True
            mod_override = None
            if attempt > 1:
                logger.info(f"[Creator] 🔄 Versuch {attempt}/{MAX_RETRIES + 1} (Safe-Mode)...")
                # Fallback: Entschärfter Prompt für Gemini Filter
                current_prompt += "\n\nCRITICAL SAFETY INSTRUCTION: The generated image prompts MUST be extremely safe, positive, and non-violent. Do not describe children in distress, danger, or any negative situations. Use abstract, peaceful, or purely positive imagery (e.g. 'a peaceful garden', 'a warm glowing light', 'a calm family scene') even if the voiceover text discusses a serious or painful problem. Ignore the negative aspects of the voiceover when creating the image prompts. Focus ONLY on the positive resolution."
            if attempt == 3:
                # Remove system prompt to see if that was triggering the filter, and use a stronger model
                use_sys = False
                mod_override = "gemini-2.5-flash"

            response_text = _call_llm(current_prompt, temperature=0.5, use_system_prompt=use_sys, model_override=mod_override)
            logger.debug(f"[Creator] LLM Antwort: {response_text}")

            result = extract_json(response_text)
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


def clean_book_text(raw_text: str, category: str = "schlaf") -> dict | None:
    """
    Long-Form mode: Clean raw PDF text for use as a read-aloud voiceover.
    Removes PDF artifacts (page numbers, headers, broken line breaks) without
    using an LLM – pure rule-based cleaning.

    Args:
        raw_text: Raw text extracted from a PDF chapter.
        category: 'schlaf' (default, no word limit) or 'natur' (hard 700-word cap).

    Returns:
        Dict with 'cleaned_text', 'word_count', 'estimated_duration_minutes',
        or None if the text is too short.
    """
    import re

    if not raw_text or len(raw_text.strip()) < 50:
        logger.error("[Creator/Long] ✗ Rohtext ist zu kurz oder leer.")
        return None

    text = raw_text

    # 1. Remove isolated page numbers (a line containing only a number)
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text)

    # 2. Fix hyphenation at line breaks (word-\ncontinuation → wordcontinuation)
    text = re.sub(r"-\n([a-záàảãạăắặằẳẵâấậầẩẫêếệềểễôốộồổỗơớợờởỡưứựừửữđ])",
                  r"\1", text, flags=re.IGNORECASE)

    # 3. Join lines that were broken mid-sentence (no sentence-ending punctuation)
    text = re.sub(r"([^.!?»«\n])\n([a-záàảãạăắặằẳẵâấậầẩẫêếệềểễôốộồổỗơớợờởỡưứựừửữđ])",
                  r"\1 \2", text, flags=re.IGNORECASE)

    # 4. Collapse multiple blank lines into a single paragraph break
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 5. Strip trailing whitespace per line
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = text.strip()

    word_count = len(text.split())

    # Category-specific word limit & speed estimate
    if category == "natur":
        NATUR_WORD_LIMIT = 700
        if word_count > NATUR_WORD_LIMIT:
            logger.warning(f"[Creator/Long-Natur] ⚠ Text hat {word_count} Wörter — kürze auf {NATUR_WORD_LIMIT} Wörter.")
            words = text.split()
            text = " ".join(words[:NATUR_WORD_LIMIT])
            word_count = NATUR_WORD_LIMIT
        # Normal speaking speed ~120 words/min
        estimated_minutes = round(word_count / 120, 1)
    else:
        # Warm, slow narration ~130 words/min
        estimated_minutes = round(word_count / 130, 1)

    logger.info(f"[Creator/Long] ✓ Text bereinigt: {word_count} Wörter (~{estimated_minutes} Min.) [Kategorie: {category}]")
    logger.info(f"[Creator/Long]   Vorschau: {text[:120]}...")

    return {
        "cleaned_text": text,
        "word_count": word_count,
        "estimated_duration_minutes": estimated_minutes,
    }
