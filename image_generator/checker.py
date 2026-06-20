"""
image_generator/checker.py
Provides quality assurance for generated images using Gemini Vision.
Checks for style consistency (Ghibli) and prompt adherence.
"""

import logging
import os
from PIL import Image
from shared.gemini_utils import create_client, SAFETY_SETTINGS_NONE
from google.genai import types

logger = logging.getLogger(__name__)

CHECKER_PROMPT = """
You are a strict Quality Assurance expert for an animation studio specializing in Studio Ghibli style.
Your task is to analyze the provided image and determine if it meets our high standards.

CHECKLIST:
1. STYLE: Is the image a "flat 2D Japanese anime illustration" in the "Studio Ghibli style"? 
   - CRITICAL: If it looks like a realistic photo, 3D CGI, or a generic stock photo, it is a FAIL.
   - It should have soft watercolor textures, warm pastel colors, and cel-shaded character design.
2. CONTENT: Does the image contain the key elements described in the prompt and voiceover?
   - Look for specific people (e.g., Vietnamese mother, child).
   - Look for specific objects (e.g., wooden spoon, drawing).
3. MOOD: Does the visual mood match the voiceover text?

OUTPUT:
Return ONLY a JSON object with the following structure:
{
  "is_passed": true/false,
  "score": 0-10,
  "reason": "Detailed explanation of why it passed or failed",
  "detected_style": "e.g. Anime, Photo, 3D",
  "missing_elements": ["list of missing things if any"]
}
"""

def check_image(image_path, bild_prompt, voiceover_text):
    """
    Analyzes an image using Gemini Vision to verify style and content.
    """
    if not os.path.exists(image_path):
        return {"is_passed": False, "reason": "Image file not found"}

    client = create_client()
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    prompt = f"""
PROMPT: {bild_prompt}
VOICEOVER: {voiceover_text}

Analyze this image based on the provided prompt and voiceover.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", # High performance vision model
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                types.Part.from_text(text=CHECKER_PROMPT + "\n\n" + prompt)
            ],
            config=types.GenerateContentConfig(
                safety_settings=SAFETY_SETTINGS_NONE,
                response_mime_type="application/json",
                temperature=0.2
            )
        )

        if not response.text:
            return {"is_passed": False, "reason": "Gemini returned no analysis"}

        from shared.gemini_utils import extract_json
        result = extract_json(response.text)
        return result or {"is_passed": False, "reason": "Failed to parse JSON response"}

    except Exception as e:
        logger.error(f"Error checking image {image_path}: {e}")
        return {"is_passed": False, "reason": f"API Error: {str(e)}"}

def refine_prompt_on_failure(old_prompt, reason, missing_elements):
    """
    Asks Gemini to rewrite the prompt to fix issues identified by the checker.
    """
    client = create_client()
    
    refine_instruction = f"""
The previous image generation failed our quality check.
OLD PROMPT: {old_prompt}
FAILURE REASON: {reason}
MISSING ELEMENTS: {', '.join(missing_elements) if missing_elements else 'None'}

TASK:
Rewrite the prompt to FIX these issues. 
- If it looked like a photo, emphasize "Studio Ghibli anime illustration" and "cel-shaded" even more.
- If elements were missing, make them the focal point of the description.
- Keep the Ghibli style keywords at the VERY BEGINNING.

Return ONLY the new refined prompt as plain text.
"""

    try:
        response = client.models.generate_content(
            model="deepseek-chat",
            contents=refine_instruction
        )
        return response.text.strip() if response.text else old_prompt
    except Exception as e:
        logger.error(f"Error refining prompt: {e}")
        return old_prompt
