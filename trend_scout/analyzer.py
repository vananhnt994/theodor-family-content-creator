"""
Qwen 3.5:9B via Ollama – Local LLM for topic curation and content generation.
Step 1: Pick the best headline from scraped data.
Step 2: Generate description (problem) + solution from article content.
"""

import json
import logging
import re

import ollama

from trend_scout.config import (
    OLLAMA_MODEL,
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
    """Verify that Ollama is running and the model is available."""
    try:
        models = ollama.list()
        available = [m.model for m in models.models]
        logger.info(f"[Analyzer] Ollama verbunden. Verfügbare Modelle: {available}")

        # Check if our model is available (with or without tag)
        model_base = OLLAMA_MODEL.split(":")[0]
        found = any(model_base in m for m in available)

        if not found:
            logger.error(
                f"[Analyzer] ✗ Modell '{OLLAMA_MODEL}' nicht gefunden! "
                f"Bitte 'ollama pull {OLLAMA_MODEL}' ausführen."
            )
            return False

        logger.info(f"[Analyzer] ✓ Modell '{OLLAMA_MODEL}' ist bereit")
        return True

    except Exception as e:
        logger.error(f"[Analyzer] ✗ Kann Ollama nicht erreichen: {e}")
        logger.error(
            "[Analyzer] Bitte sicherstellen, dass Ollama läuft: 'ollama serve'"
        )
        return False


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
        f"[Analyzer] Schritt 1: Sende {len(headlines)} Headlines an {OLLAMA_MODEL}..."
    )

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3},  # low temp for consistent selection
        )

        response_text = response.message.content
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

    logger.info(f"[Analyzer] Schritt 2: Generiere Content mit {OLLAMA_MODEL}...")

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.7},  # higher temp for creative content
        )

        response_text = response.message.content
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
        logger.error(f"[Analyzer] ✗ Fehler bei Content-Generierung: {e}")
        return None
