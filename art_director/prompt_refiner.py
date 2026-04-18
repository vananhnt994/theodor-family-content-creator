import json
import logging
import os
import sys
import google.generativeai as genai
import re

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from channel_config import load_channel_config
from art_director.config import GEMINI_MODEL, SYSTEM_PROMPT

channel_cfg = load_channel_config()

logger = logging.getLogger(__name__)

def _extract_json(text: str) -> dict | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0: start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start:i+1])
                except json.JSONDecodeError:
                    start = -1
    return None

def refine_prompts(scenes: list[dict]) -> list[dict] | None:
    """Takes the scenes from Service 1 and refines the draft_prompts using Gemini API."""
    
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", ""))
    
    available_voices = list(channel_cfg.get("voices", {"Mann": "", "Frau": ""}).keys())
    voices_str = ", ".join([f"'{v}'" for v in available_voices])
    default_voice = available_voices[0] if available_voices else "Unbekannt"
    
    scenes_json = json.dumps([{"scene_number": s["scene_number"], "voiceover_text": s.get("voiceover_text", ""), "draft_prompt": s.get("draft_prompt", "")} for s in scenes], indent=2)

    prompt = f"""Hier sind die Bild-Entwürfe für die einzelnen Szenen und der Voiceover-Text:

```json
{scenes_json}
```

AUFGABE: 
1. Überarbeite jeden `draft_prompt` in einen neuen `final_prompt`, unter strikter Einhaltung deiner System-Prompt-Regeln (Sanitization, hyper-expressive faces, close-up shot, style-consistency).
2. Analysiere das gesamte Skript (Tonfall, Text und Geschwindigkeit) und bestimme aus welcher Perspektive die Geschichte erzählt wird. Entscheide, welche Stimme für das Voiceover geeignet ist. Du DARFST NUR EINE DIESER STIMMEN WÄHLEN: {voices_str}.

Gib nur gültiges JSON im folgenden Format zurück:

{{
  "selected_voice": "{default_voice}", 
  "refined_scenes": [
    {{
      "scene_number": 1,
      "final_prompt": "<DEIN ÜBERARBEITETER PROMPT IN ENGLISCH>"
    }}
  ]
}}
"""

    logger.info(f"[Art Director] 🎨 Verfeinere {len(scenes)} Prompts mit {GEMINI_MODEL}...")
    
    try:
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.4
            )
        )
        
        response = model.generate_content(prompt)
        text = response.text
        logger.debug(f"[Art Director] API Antwort: {text}")
        
        result = _extract_json(text)
        if not result or "refined_scenes" not in result:
            logger.warning("[Art Director] ⚠ JSON konnte nicht geparst werden.")
            return None, None
            
        refined_list = result["refined_scenes"]
        selected_voice = result.get("selected_voice", "Mann")
        
        scene_map = {s["scene_number"]: s["final_prompt"] for s in refined_list}
        
        for scene in scenes:
            sn = scene["scene_number"]
            if sn in scene_map:
                scene["bild_prompt"] = scene_map[sn]
                if "draft_prompt" in scene:
                    del scene["draft_prompt"]
                
        logger.info(f"[Art Director] ✓ Prompts verfeinert! Gewählte Stimme: {selected_voice}")
        return scenes, selected_voice

    except Exception as e:
        logger.error(f"[Art Director] ✗ Fehler bei Gemini API: {e}")
        return None, None
