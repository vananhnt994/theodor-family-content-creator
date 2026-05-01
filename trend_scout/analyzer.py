"""
Gemini – Cloud LLM for topic curation and content generation.
Step 1: Pick the best headline from scraped data.
Step 2: Generate description (problem) + solution from article content.
"""

import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from shared.gemini_utils import SAFETY_SETTINGS_NONE, create_client, extract_json
from google.genai import types
from dotenv import load_dotenv

from trend_scout.config import (
    GEMINI_MODEL,
    TOPIC_SELECTION_PROMPT,
    CONTENT_GENERATION_PROMPT,
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


def check_connection() -> bool:
    """Verify that Gemini API key is set."""
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("[Analyzer] ✗ GEMINI_API_KEY in .env fehlt!")
        return False

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

    for attempt in range(3):
        try:
            client = _get_client()
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
                safety_settings=SAFETY_SETTINGS_NONE,
            )
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config
            )
            if not response.candidates:
                logger.warning(f"[Analyzer] ⚠ Gemini Content Filter blockiert (Auswahl): {getattr(response, 'prompt_feedback', 'Kein Feedback')}")
                return None
            response_text = response.text
            logger.debug(f"[Analyzer] LLM Antwort: {response_text}")

            result = extract_json(response_text)
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

    # Truncate long articles to save tokens (OP-3: 2000 chars is enough for a 60s Short)
    if len(article_text) > 2000:
        article_text = article_text[:2000] + "\n\n[... nội dung đã được rút gọn ...]"

    prompt = CONTENT_GENERATION_PROMPT.format(
        title=topic["title"],
        article_text=article_text,
    )

    logger.info(f"[Analyzer] Schritt 2: Generiere Content mit {GEMINI_MODEL}...")

    for attempt in range(3):
        try:
            client = _get_client()
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
                safety_settings=SAFETY_SETTINGS_NONE,
            )
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config
            )
            if not response.candidates:
                logger.warning(f"[Analyzer] ⚠ Gemini Content Filter blockiert (Content): {getattr(response, 'prompt_feedback', 'Kein Feedback')}")
                return None
            response_text = response.text
            logger.debug(f"[Analyzer] LLM Antwort: {response_text}")

            result = extract_json(response_text)
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
