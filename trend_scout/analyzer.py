"""
Qwen 3.5:9B via Ollama – Local LLM for topic curation and content generation.
Step 1: Pick the best headline from scraped data.
Step 2: Generate description (problem) + solution from article content.
"""

import json
import logging
import re

import os
import google.generativeai as genai
from dotenv import load_dotenv

from trend_scout.config import (
    GEMINI_MODEL,
    TOPIC_SELECTION_PROMPT,
    CONTENT_GENERATION_PROMPT,
)

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from LLM response, handling markdown code blocks."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block ```json ... ```
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def check_connection() -> bool:
    """Verify that Gemini API key is set."""
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    load_dotenv()
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("[Analyzer] ✗ GEMINI_API_KEY in .env fehlt!")
        return False
        
    genai.configure(api_key=api_key)
    logger.info(f"[Analyzer] ✓ Gemini API verbunden (Modell: {GEMINI_MODEL})")
    return True


def pick_topic(headlines: list[dict]) -> dict | None:
    """
    Step 1: Send all headlines to Qwen and let it pick the best one.

    Args:
        headlines: List of dicts with 'title', 'url', 'source' keys.

    Returns:
        The selected headline dict with added 'reason', or None on failure.
    """
    if not headlines:
        logger.error("[Analyzer] Keine Headlines vorhanden – Abbruch")
        return None

    # Format headlines for the prompt
    headline_text = "\n".join(
        f"{i+1}. [{h['source']}] {h['title']}"
        for i, h in enumerate(headlines)
    )

    prompt = TOPIC_SELECTION_PROMPT.format(headlines=headline_text)

    logger.info(
        f"[Analyzer] Schritt 1: Sende {len(headlines)} Headlines an {GEMINI_MODEL}..."
    )

    import time
    for attempt in range(3):
        try:
            model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )
            response = model.generate_content(prompt)
            response_text = response.text
            logger.debug(f"[Analyzer] LLM Antwort: {response_text}")

            result = _extract_json(response_text)
            if not result or "index" not in result:
                logger.error(
                    f"[Analyzer] ✗ Konnte JSON nicht parsen: {response_text[:200]}"
                )
                return None

            idx = int(result["index"]) - 1  # convert 1-based to 0-based
            if idx < 0 or idx >= len(headlines):
                logger.error(f"[Analyzer] ✗ Ungültiger Index: {result['index']}")
                return None

            selected = headlines[idx].copy()
            selected["reason"] = result.get("reason", "")

            logger.info(f"[Analyzer] ✓ Gewählt: '{selected['title']}'")
            logger.info(f"[Analyzer]   Grund: {selected['reason']}")
            logger.info(f"[Analyzer]   Quelle: {selected['source']}")
            return selected

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str:
                if attempt < 2:
                    logger.warning(f"[Analyzer] ⏳ Gemini Rate Limit erreicht. Warte 25 Sekunden... (Versuch {attempt+1}/3)")
                    time.sleep(25)
                    continue
            
            logger.error(f"[Analyzer] ✗ Fehler bei Themen-Auswahl: {e}")
            return None


def generate_content(topic: dict, article_text: str) -> dict | None:
    """
    Step 2: Generate description (problem) + solution from the article content.

    Args:
        topic: The selected headline dict (with 'title', 'url', 'source').
        article_text: Full article text from Phase 2 scraping.

    Returns:
        Dict with 'title', 'description', 'solution' keys, or None on failure.
    """
    # If article text is too short, tell the LLM to use its own knowledge
    if len(article_text) < 100:
        article_text = (
            "(Nội dung bài viết gốc quá ngắn hoặc không tải được. "
            "Hãy sử dụng kiến thức chuyên môn của bạn để tạo nội dung.)"
        )

    # Truncate very long articles to save tokens
    if len(article_text) > 3000:
        article_text = article_text[:3000] + "\n\n[... nội dung đã được rút gọn ...]"

    prompt = CONTENT_GENERATION_PROMPT.format(
        title=topic["title"],
        article_text=article_text,
    )

    logger.info(f"[Analyzer] Schritt 2: Generiere Content mit {GEMINI_MODEL}...")

    import time
    for attempt in range(3):
        try:
            model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.7
                )
            )
            response = model.generate_content(prompt)
            response_text = response.text
            logger.debug(f"[Analyzer] LLM Antwort: {response_text}")

            result = _extract_json(response_text)
            if not result:
                logger.error(
                    f"[Analyzer] ✗ Konnte JSON nicht parsen: {response_text[:200]}"
                )
                return None

            # Validate required fields
            required = ["title", "description", "solution"]
            missing = [f for f in required if f not in result]
            if missing:
                logger.error(f"[Analyzer] ✗ Fehlende Felder: {missing}")
                return None

            logger.info(f"[Analyzer] ✓ Content generiert:")
            logger.info(f"[Analyzer]   Title: {result['title']}")
            logger.info(f"[Analyzer]   Description: {result['description'][:80]}...")
            logger.info(f"[Analyzer]   Solution: {result['solution'][:80]}...")
            return result

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str:
                if attempt < 2:
                    logger.warning(f"[Analyzer] ⏳ Gemini Rate Limit erreicht. Warte 25 Sekunden... (Versuch {attempt+1}/3)")
                    time.sleep(25)
                    continue

            logger.error(f"[Analyzer] ✗ Fehler bei Content-Generierung: {e}")
            return None
