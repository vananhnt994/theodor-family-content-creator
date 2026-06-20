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

    native_client = genai.Client(api_key=api_key)
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    return GeminiOrDeepSeekClient(native_client, deepseek_key)


class GeminiOrDeepSeekModels:
    def __init__(self, gemini_models_client, deepseek_api_key: str = None):
        self.gemini_models_client = gemini_models_client
        self.deepseek_api_key = deepseek_api_key

    def generate_content(self, model: str, contents, config=None):
        if model.startswith("deepseek"):
            return self._generate_deepseek_content(model, contents, config)
        else:
            return self.gemini_models_client.generate_content(model=model, contents=contents, config=config)

    def _generate_deepseek_content(self, model: str, contents, config=None):
        import urllib.request
        import json

        system_instruction = None
        temperature = 0.7
        response_mime_type = None

        if config:
            # config can be a types.GenerateContentConfig or dict
            system_instruction = getattr(config, "system_instruction", None)
            temperature = getattr(config, "temperature", 0.7)
            response_mime_type = getattr(config, "response_mime_type", None)

            # config might be a dict-like or have these attributes
            if hasattr(config, "get"):
                system_instruction = config.get("system_instruction") or system_instruction
                temperature = config.get("temperature") or temperature
                response_mime_type = config.get("response_mime_type") or response_mime_type

        # Build messages list
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": str(system_instruction)})

        # Turn contents into text
        content_str = ""
        if isinstance(contents, list):
            parts = []
            for item in contents:
                if hasattr(item, "text") and item.text:
                    parts.append(item.text)
                elif isinstance(item, str):
                    parts.append(item)
            content_str = "\n".join(parts)
        else:
            content_str = str(contents)

        messages.append({"role": "user", "content": content_str})

        if not self.deepseek_api_key:
            raise ValueError("Kein DEEPSEEK_API_KEY in der .env gefunden!")

        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }

        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }

        if response_mime_type == "application/json":
            data["response_format"] = {"type": "json_object"}

        req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text_response = res_data["choices"][0]["message"]["content"]

                # Mock response structure for genai library compatibility
                class MockCandidate:
                    pass

                class MockResponse:
                    def __init__(self, text):
                        self.text = text
                        self.candidates = [MockCandidate()]

                return MockResponse(text_response)
        except Exception as e:
            logger.error(f"Fehler bei DeepSeek API-Aufruf ({model}): {e}")
            raise


class GeminiOrDeepSeekClient:
    def __init__(self, gemini_client, deepseek_api_key: str = None):
        self.gemini_client = gemini_client
        self.models = GeminiOrDeepSeekModels(gemini_client.models, deepseek_api_key)


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
