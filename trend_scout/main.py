"""
Service 0: Der Trend-Scout – Main Orchestrator
Coordinates the full pipeline: Scrape → Pick Topic → Fetch Article → Generate Content → Save
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone

from trend_scout.config import OUTPUT_DIR, OUTPUT_FILENAME
from trend_scout.scraper import scrape_headlines, scrape_article
from trend_scout.analyzer import check_connection, pick_topic, generate_content

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run():
    """Execute the full Trend Scout pipeline."""
    logger.info("=" * 60)
    logger.info("🔍 SERVICE 0: DER TREND-SCOUT")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # Step 0: Check Ollama connection
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("📡 Prüfe Ollama-Verbindung...")
    if not check_connection():
        logger.error("❌ Pipeline abgebrochen: Ollama nicht erreichbar")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Phase 1: Scrape headlines from all sources
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("🌐 Phase 1: Headlines scrapen...")
    logger.info("-" * 40)
    headlines = scrape_headlines()

    if not headlines:
        logger.error("❌ Pipeline abgebrochen: Keine Headlines gefunden")
        sys.exit(1)

    logger.info(f"✅ {len(headlines)} Headlines gesammelt")

    # ------------------------------------------------------------------
    # Step 1: Let Qwen pick the best topic
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("🧠 Schritt 1: Qwen wählt das beste Thema...")
    logger.info("-" * 40)
    topic = pick_topic(headlines)

    if not topic:
        logger.error("❌ Pipeline abgebrochen: Kein Thema ausgewählt")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Phase 2: Fetch full article content
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("📄 Phase 2: Artikelinhalt laden...")
    logger.info("-" * 40)
    article_text = scrape_article(topic.get("url", ""), topic.get("source", ""))

    # ------------------------------------------------------------------
    # Step 2: Generate description + solution
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("✍️  Schritt 2: Content generieren (description + solution)...")
    logger.info("-" * 40)
    content = generate_content(topic, article_text)

    if not content:
        logger.error("❌ Pipeline abgebrochen: Content-Generierung fehlgeschlagen")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Save output
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("💾 Ergebnis speichern...")
    logger.info("-" * 40)

    output = {
        "title": content["title"],
        "description": content["description"],
        "solution": content["solution"],
        "source": topic.get("source", ""),
        "source_url": topic.get("url", ""),
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ Gespeichert: {output_path}")
    logger.info("")
    logger.info("=" * 60)
    logger.info("📋 ERGEBNIS")
    logger.info("=" * 60)
    logger.info(f"   Title:       {output['title']}")
    logger.info(f"   Description: {output['description'][:100]}...")
    logger.info(f"   Solution:    {output['solution'][:100]}...")
    logger.info(f"   Source:      {output['source']}")
    logger.info(f"   Timestamp:   {output['timestamp']}")
    logger.info("=" * 60)
    logger.info("🎉 Service 0 erfolgreich abgeschlossen!")

    return output


if __name__ == "__main__":
    run()
