import json
import logging
import os
import sys
from google.genai import types
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from shared.gemini_utils import SAFETY_SETTINGS_NONE, create_client, extract_json as _shared_extract_json
from channel_config import load_channel_config
from art_director.config import GEMINI_MODEL, SYSTEM_PROMPT

channel_cfg = load_channel_config()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Ghibli Style Fallback Config
# ---------------------------------------------------------------------------
GHIBLI_SUFFIX = "flat 2D Japanese anime illustration, Studio Ghibli style, Hayao Miyazaki, soft watercolor textures, warm pastel colors, cel-shaded anime character design."

VIDEO_FALLBACK_MAP = {
    "sadness": "Slow gentle zoom in, soft particles drift downward like quiet snowflakes",
    "longing": "Camera slowly pans across the scene, warm light shifts gently",
    "loneliness": "Gentle camera drift to the right, dust motes float in soft light",
    "doubt": "Slow zoom into character's face, soft bokeh lights pulse gently",
    "comfort": "Camera gently pulls back revealing warmth, soft golden particles rise",
    "reassurance": "Slow upward tilt, warm light grows brighter and softer",
    "bittersweet": "Gentle pan left, a single leaf drifts slowly through warm air",
    "strength": "Slow zoom out revealing full scene, warm sunset light glows",
    "self-love": "Gentle pulsing warm glow, camera slowly pulls back peacefully",
    "hopeful": "Slow zoom out to wide shot, golden sunlight fills the frame",
    "peaceful": "Gentle camera sway, soft breeze moves grass and hair slowly",
    "warm": "Slow pan across scene, warm golden light filters through softly",
    "gentle": "Camera drifts slowly upward, soft clouds pass in background",
}
VIDEO_FALLBACK_DEFAULT = "Gentle slow camera pan, soft warm light, peaceful atmosphere"

PHOTO_WORDS = ["35mm", "film grain", "photo", "realistic", "camera", "lens",
               "cinematic", "8k", "photorealistic", "3D", "CGI", "documentary"]


def _extract_json(text: str) -> dict | None:
    """Delegate to shared extract_json."""
    return _shared_extract_json(text)


def _local_fallback(scenes: list[dict]) -> tuple[list[dict], str]:
    """Apply Ghibli style keywords locally when Gemini content filter blocks the request."""
    for scene in scenes:
        draft = scene.get("draft_prompt", "")

        # Remove photography words
        for word in PHOTO_WORDS:
            draft = draft.replace(word, "").replace(word.lower(), "")

        # Add Ghibli suffix if not already present
        if "ghibli" not in draft.lower():
            draft = GHIBLI_SUFFIX + ". " + draft.strip(". ")

        scene["bild_prompt"] = draft.strip()

        # Generate video prompt based on emotion
        emotion = scene.get("emotion", "").lower()
        scene["video_prompt"] = VIDEO_FALLBACK_MAP.get(emotion, VIDEO_FALLBACK_DEFAULT)

        if "draft_prompt" in scene:
            del scene["draft_prompt"]

    selected_voice = "Frau"
    logger.info(f"[Art Director] ✓ Lokaler Fallback angewendet! {len(scenes)} Szenen verarbeitet. Stimme: {selected_voice}")
    return scenes, selected_voice


def refine_prompts(scenes: list[dict]) -> tuple[list[dict], str] | tuple[None, None]:
    """Takes the scenes from Service 1 and refines the draft_prompts using Gemini API.
    Generates both image prompts (bild_prompt) and video prompts (video_prompt).
    Falls back to local processing if Gemini content filter blocks the request.
    """
    client = create_client()

    available_voices = list(channel_cfg.get("voices", {"Mann": "", "Frau": ""}).keys())
    voices_str = ", ".join([f"'{v}'" for v in available_voices])
    default_voice = available_voices[0] if available_voices else "Unbekannt"

    # Only send draft_prompt and emotion to Gemini – voiceover_text can trigger content filters
    scenes_json = json.dumps(
        [{"scene_number": s["scene_number"], "emotion": s.get("emotion", ""), "draft_prompt": s.get("draft_prompt", "")}
         for s in scenes],
        indent=2
    )

    # OP-6: Shortened prompt — Ghibli/character rules already live in SYSTEM_PROMPT
    prompt = f"""Szenen-Entwürfe:

```json
{scenes_json}
```

AUFGABE:
1. Überarbeite jeden `draft_prompt` zu einem `final_prompt` (Bildgenerierung) gemäß deinen System-Prompt-Regeln.
2. Erstelle für jede Szene einen `video_prompt` — sanfte Kamerabewegung, max. 20 Wörter, entspannt und friedlich.
3. Wähle die passende Stimme. Erlaubte Werte: {voices_str}.

Nur gültiges JSON zurückgeben:

{{
  "selected_voice": "{default_voice}",
  "refined_scenes": [
    {{
      "scene_number": 1,
      "final_prompt": "<BILD-PROMPT IN ENGLISCH>",
      "video_prompt": "<ANIMATION/KAMERA IN ENGLISCH, max 20 Wörter>"
    }}
  ]
}}
"""

    logger.info(f"[Art Director] 🎨 Verfeinere {len(scenes)} Prompts mit {GEMINI_MODEL}...")
    
    try:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            safety_settings=SAFETY_SETTINGS_NONE,
            response_mime_type="application/json",
            temperature=0.4
        )
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config
        )
        
        # Check if response was blocked by content filter
        if not response.candidates:
            logger.warning("[Art Director] ⚠ Gemini hat den Inhalt blockiert (Content Filter). Verwende lokalen Fallback...")
            return _local_fallback(scenes)
        
        text = response.text
        logger.debug(f"[Art Director] API Antwort: {text}")
        
        result = _extract_json(text)
        if not result or "refined_scenes" not in result:
            logger.warning("[Art Director] ⚠ JSON konnte nicht geparst werden. Verwende lokalen Fallback...")
            return _local_fallback(scenes)
            
        refined_list = result["refined_scenes"]
        selected_voice = result.get("selected_voice", "Frau")
        
        scene_map = {s["scene_number"]: s for s in refined_list}
        
        for scene in scenes:
            sn = scene["scene_number"]
            if sn in scene_map:
                refined = scene_map[sn]
                scene["bild_prompt"] = refined.get("final_prompt", "")
                scene["video_prompt"] = refined.get("video_prompt", "")
                if "draft_prompt" in scene:
                    del scene["draft_prompt"]
                
        logger.info(f"[Art Director] ✓ Bild- & Video-Prompts verfeinert! Gewählte Stimme: {selected_voice}")
        return scenes, selected_voice

    except Exception as e:
        error_msg = str(e)
        if "PROHIBITED_CONTENT" in error_msg or "blocked" in error_msg.lower() or "empty" in error_msg.lower():
            logger.warning(f"[Art Director] ⚠ Content Filter aktiv: {e}")
            logger.info("[Art Director] 🔄 Verwende lokalen Fallback...")
            return _local_fallback(scenes)
        logger.error(f"[Art Director] ✗ Fehler bei Gemini API: {e}")
        return None, None
