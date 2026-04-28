"""
Service 0: Der Trend-Scout – Main Orchestrator
Coordinates the full pipeline: Scrape → Pick Topic → Fetch Article → Generate Content → Save
Also supports manual article input via run_from_file().
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone

from trend_scout.config import (
    OUTPUT_DIR, OUTPUT_FILENAME,
    HISTORY_SHORTS_FILENAME, HISTORY_LONG_FILENAME, HISTORY_FILENAME
)
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


def _load_history(mode: str = "shorts") -> list[dict]:
    """Load existing topic history (shorts or long mode)."""
    filename = HISTORY_LONG_FILENAME if mode == "long" else HISTORY_SHORTS_FILENAME
    history_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(history_path):
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"[Historie/{mode}] {len(data)} bisherige Einträge geladen")
            return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"[Historie/{mode}] Fehler beim Laden: {e} – starte leer")
    return []


def _save_to_history(entry: dict, mode: str = "shorts") -> None:
    """Append a topic entry to the appropriate history file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filename = HISTORY_LONG_FILENAME if mode == "long" else HISTORY_SHORTS_FILENAME
    history_path = os.path.join(OUTPUT_DIR, filename)
    history = _load_history(mode)
    history.append(entry)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    logger.info(f"[Historie/{mode}] Neues Thema gespeichert → {len(history)} Einträge total")


def _parse_artikel_file(filepath: str) -> tuple[str, str]:
    """Parse an artikel.txt file into (title, article_text).
    
    Expected format:
        TITEL: Dein Titel hier
        ---
        Dein Artikeltext hier...
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
    
    # Split on the first '---' separator
    if "---" in content:
        header, body = content.split("---", 1)
        # Extract title from header
        title = header.strip()
        if title.upper().startswith("TITEL:"):
            title = title[6:].strip()
        article_text = body.strip()
    else:
        # No separator – first line is title, rest is body
        lines = content.split("\n", 1)
        title = lines[0].strip()
        if title.upper().startswith("TITEL:"):
            title = title[6:].strip()
        article_text = lines[1].strip() if len(lines) > 1 else title
    
    return title, article_text


def run_from_file(filepath: str):
    """Execute the Trend Scout pipeline using a manually written article file.
    
    Skips scraping and topic selection. Uses Gemini to generate
    title/description/solution from the provided text.
    
    Args:
        filepath: Path to the artikel.txt file.
    
    Returns:
        The generated output dict, or None on failure.
    """
    logger.info("=" * 60)
    logger.info("📝 SERVICE 0: EIGENER ARTIKEL-MODUS")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # Step 0: Check Gemini connection
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("📡 Prüfe Gemini-Verbindung...")
    if not check_connection():
        logger.error("❌ Pipeline abgebrochen: API Fehler")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 1: Read and parse the article file
    # ------------------------------------------------------------------
    logger.info("")
    logger.info(f"📄 Lese Artikel aus: {filepath}")
    logger.info("-" * 40)

    if not os.path.exists(filepath):
        logger.error(f"❌ Datei nicht gefunden: {filepath}")
        sys.exit(1)

    title, article_text = _parse_artikel_file(filepath)
    
    if not article_text or len(article_text.strip()) < 20:
        logger.error("❌ Artikeltext ist zu kurz oder leer. Bitte schreibe mehr Text in die Datei.")
        sys.exit(1)

    logger.info(f"✅ Titel: {title}")
    logger.info(f"   Textlänge: {len(article_text)} Zeichen")

    # ------------------------------------------------------------------
    # Step 2: Generate content via Gemini (title/description/solution)
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("✍️  Schritt 2: Content generieren (description + solution)...")
    logger.info("-" * 40)
    
    topic = {"title": title, "source": "Eigener Artikel", "url": ""}
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
        "source": "Eigener Artikel",
        "source_url": "",
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ Gespeichert: {output_path}")

    # Append to history
    _save_to_history(output)
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
    logger.info("🎉 Eigener Artikel erfolgreich verarbeitet!")

    return output


def run_from_books():
    """Execute the Trend Scout pipeline using a chapter from input/shorts/books/."""
    logger.info("=" * 60)
    logger.info("📚 SERVICE 0: BUCH-MODUS (Shorts)")
    logger.info("=" * 60)

    logger.info("")
    logger.info("📡 Prüfe Gemini-Verbindung...")
    if not check_connection():
        logger.error("❌ Pipeline abgebrochen: API Fehler")
        sys.exit(1)

    from trend_scout.book_reader import run_book_reader, BOOKS_DIR_SHORTS
    logger.info("")
    logger.info("📖 Wähle ungelesenes Kapitel aus Büchern (Shorts)...")
    logger.info("-" * 40)

    history = _load_history(mode="shorts")
    book_data = run_book_reader(history, books_dir=BOOKS_DIR_SHORTS, sequential=False)

    if not book_data:
        sys.exit(1)

    topic = {
        "title": book_data["chapter_title"],
        "source": book_data["book_filename"],
        "url": book_data["chapter_id"]
    }

    logger.info("")
    logger.info("✍️  Schritt 2: Content generieren (description + solution)...")
    logger.info("-" * 40)

    content = generate_content(topic, book_data["text"])
    if not content:
        logger.error("❌ Pipeline abgebrochen: Content-Generierung fehlgeschlagen")
        sys.exit(1)

    logger.info("")
    logger.info("💾 Ergebnis speichern...")
    logger.info("-" * 40)

    output = {
        "title": content["title"],
        "description": content["description"],
        "solution": content["solution"],
        "source": book_data["book_filename"],
        "source_url": book_data["chapter_id"],
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ Gespeichert: {output_path}")

    _save_to_history(output, mode="shorts")
    logger.info("")
    logger.info("=" * 60)
    logger.info("📋 ERGEBNIS")
    logger.info("=" * 60)
    logger.info(f"   Title:       {output['title']}")
    logger.info(f"   Description: {output['description'][:100]}...")
    logger.info(f"   Solution:    {output['solution'][:100]}...")
    logger.info(f"   Source:      {output['source']}")
    logger.info(f"   Chapter ID:  {output['source_url']}")
    logger.info(f"   Timestamp:   {output['timestamp']}")
    logger.info("=" * 60)
    logger.info("🎉 Buchkapitel erfolgreich verarbeitet!")
    return output


def run_from_long_books():
    """Librarian mode: pick the next unread chapter from input/long/books/ and
    save the full raw text to thema.json (no Gemini call needed)."""
    logger.info("=" * 60)
    logger.info("📚 SERVICE 0: LIBRARIAN-MODUS (Long-Form)")
    logger.info("=" * 60)

    from trend_scout.book_reader import run_book_reader, BOOKS_DIR_LONG
    logger.info("")
    logger.info("📖 Wähle nächstes ungelesenes Kapitel (Long-Form, sequenziell)...")
    logger.info("-" * 40)

    history = _load_history(mode="long")
    book_data = run_book_reader(history, books_dir=BOOKS_DIR_LONG, sequential=True)

    if not book_data:
        logger.error("❌ Kein ungelesenes Kapitel in input/long/books/ gefunden.")
        sys.exit(1)

    logger.info("")
    logger.info("💾 Ergebnis speichern (kein LLM-Aufruf – Rohtext direkt aus PDF)...")
    logger.info("-" * 40)

    output = {
        "title": book_data["chapter_title"],
        "description": "",
        "solution": "",
        "source": book_data["book_filename"],
        "source_url": book_data["chapter_id"],
        "full_text": book_data["text"],
        "mode": "long",
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"✅ Gespeichert: {output_path}")

    _save_to_history(output, mode="long")
    logger.info("")
    logger.info("=" * 60)
    logger.info("📋 ERGEBNIS")
    logger.info("=" * 60)
    logger.info(f"   Buch:        {output['source']}")
    logger.info(f"   Kapitel:     {output['title']}")
    logger.info(f"   Textlänge:   {len(output['full_text'])} Zeichen")
    logger.info(f"   Timestamp:   {output['timestamp']}")
    logger.info("=" * 60)
    logger.info("🎉 Long-Form Kapitel erfolgreich ausgewählt!")
    return output


def main():
    """Execute the full Trend Scout pipeline."""
    logger.info("=" * 60)
    logger.info("🔍 SERVICE 0: DER TREND-SCOUT")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # Step 0: Check Ollama connection
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("📡 Prüfe Gemini-Verbindung...")
    if not check_connection():
        logger.error("❌ Pipeline abgebrochen: API Fehler")
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
    # Filter: Remove already-used topics (by URL)
    # ------------------------------------------------------------------
    history = _load_history(mode="shorts")
    used_urls = {entry.get("source_url", "") for entry in history}
    original_count = len(headlines)
    headlines = [h for h in headlines if h.get("url", "") not in used_urls or not h.get("url")]
    filtered_count = original_count - len(headlines)
    if filtered_count > 0:
        logger.info(f"🔄 {filtered_count} bereits verwendete Themen herausgefiltert")
    if not headlines:
        logger.error("❌ Pipeline abgebrochen: Alle Headlines bereits verwendet")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 1: Let Qwen pick the best topic
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("🧠 Schritt 1: Gemini wählt das beste Thema...")
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

    # Append to history
    _save_to_history(output, mode="shorts")
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
    main()
