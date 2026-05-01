"""
shared/gemini_utils.py
Shared utilities for all Gemini API calls across Theodorbot services.
Centralizes: client creation, safety settings, JSON extraction.
"""

import json
import logging
import os
import re

from google import genai
from google.genai import types
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Safety Settings — BLOCK_NONE for all harm categories
# Used across: trend_scout, creator, art_director
# ---------------------------------------------------------------------------
SAFETY_SETTINGS_NONE = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT",        threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH",       threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
]


def create_client() -> genai.Client:
    """
    Create and return a Gemini client using the API key from environment variables.
    Loads .env files from both the project root and the caller's directory.
    Raises ValueError if no API key is found.
    """
    # Load from project root .env (called services may have their own, but root is authoritative)
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
    load_dotenv()  # also load current working directory .env

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Kein Gemini API-Key gefunden. Bitte GEMINI_API_KEY in .env setzen.")

    return genai.Client(api_key=api_key)


def extract_json(text: str) -> dict | None:
    """
    Robustly extract a JSON object from an LLM response.
    Handles: plain JSON, markdown ```json blocks, first {...} block.
    Returns parsed dict or None if all attempts fail.
    """
    text = text.strip()

    # 1. Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Markdown code block ```json ... ```
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. First balanced { ... } block (handles nested objects)
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    start = -1

    return None
