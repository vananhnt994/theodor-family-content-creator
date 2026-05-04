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
    """Librarian mode: Generates a completely new bedtime story using Gemini instead of reading from a PDF."""
    logger.info("=" * 60)
    logger.info("📚 SERVICE 0: STORYTELLER-MODUS (Long-Form KI-Generierung)")
    logger.info("=" * 60)

    from google import genai
    from google.genai import types
    from trend_scout.config import GEMINI_MODEL

    if not check_connection():
        logger.error("❌ Pipeline abgebrochen: API Fehler")
        sys.exit(1)

    logger.info("")
    logger.info("📖 Lasse KI eine neue Gute-Nacht-Geschichte erfinden (10-25 Min)...")
    logger.info("-" * 40)

    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
        
        import random
        animal_pool = random.sample([
            "con sư tử", "con voi", "con cáo", "con gấu", "con thỏ", "con rùa",
            "con chim đại bàng", "con cá heo", "con hươu cao cổ", "con ngựa vằn",
            "con bướm", "con ếch", "con hạc", "con chim công", "con mèo rừng",
            "con lợn rừng", "con gấu trúc", "con hổ", "con chim hải âu",
            "con rồng nhỏ", "con nhện", "con ong mật", "con rắn hiền lành",
            "con cừu", "con ngựa", "con bò rừng", "con cú mèo", "con chim sẻ",
            "con cá vàng", "con hải ly", "con tắc kè hoa", "con chim vẹt",
            "con sóc đất", "con gà trống", "con vịt trời", "con gấu bắc cực",
            "con khỉ", "con chim sếu", "con nhím", "con sói"
        ], k=3)
        animal_choice = animal_pool[0]

        prompt = f"""Bạn là một nhà văn thiếu nhi xuất sắc. Hãy sáng tác một câu chuyện cổ tích / chuyện kể trước khi đi ngủ hoàn toàn mới bằng tiếng Việt.
YÊU CẦU QUAN TRỌNG:
1. Câu chuyện phải RẤT DÀI và CHI TIẾT (khoảng 2000 đến 3500 từ), đủ để đọc to trong khoảng 10 đến 25 phút. Đừng tóm tắt, hãy kể thật chi tiết từng hành động, lời thoại.
2. Mỗi câu chuyện PHẢI TRUYỀN TẢI RÕ RÀNG 1 BÀI HỌC VỀ PHẨM CHẤT TỐT ĐẸP (ví dụ: lòng dũng cảm, sự trung thực, lòng nhân ái, sự kiên nhẫn, lòng biết ơn, v.v.) một cách rất rõ ràng và dễ hiểu cho trẻ em.
3. Nội dung ấm áp, giàu trí tưởng tượng, phù hợp cho trẻ em nghe trước khi ngủ.
4. NHÂN VẬT CHÍNH phải là: **{animal_choice}** — hãy xây dựng tính cách và ngoại hình thật sinh động, khác biệt.
5. TUYỆT ĐỐI KHÔNG dùng con sóc (sóc) làm nhân vật trong câu chuyện này.
6. KHÔNG copy truyện có sẵn, hãy sáng tạo nhân vật và cốt truyện mới hoàn toàn.
7. LÀM GIÀU SÁNG TẠO (BẮT BUỘC): Trong câu chuyện, hãy đan xen ít nhất 2-3 yếu tố thực tế sau đây một cách tự nhiên để tăng tính giáo dục và hấp dẫn:
   - 🧚 Nhân vật nổi tiếng (Peter Pan, Hoàng tử bé...) hoặc các nhân vật lịch sử (Mozart, Beethoven, Leonardo da Vinci...)
   - 🗼 Địa danh nổi tiếng (Tháp Eiffel, Vạn Lý Trường Thành, Núi Phú Sĩ, Kim tự tháp...)
   - 🌍 Các quốc gia và nền văn hóa xinh đẹp trên thế giới.
   - 🌌 Kiến thức về vũ trụ, các vì sao, hành tinh.
   - 📜 Các sự kiện lịch sử quan trọng được giải thích một cách dễ hiểu cho trẻ em.
8. Trả lời bằng JSON với định dạng sau (không thêm bất kỳ văn bản nào bên ngoài JSON):
{{
  "title": "Tên câu chuyện",
  "story": "Nội dung chi tiết của câu chuyện..."
}}"""
        config = types.GenerateContentConfig(temperature=0.9)  # High temp for creative variety
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config
        )
        
        text_resp = response.text.strip()
        if text_resp.startswith("```json"):
            text_resp = text_resp[7:]
        if text_resp.endswith("```"):
            text_resp = text_resp[:-3]
            
        story_data = json.loads(text_resp.strip())
        chapter_title = story_data.get("title", "Gute Nacht Geschichte")
        chapter_text = story_data.get("story", "")
        
        if not chapter_text or len(chapter_text) < 500:
            logger.error("❌ KI hat keine ausreichend lange Geschichte generiert.")
            sys.exit(1)
            
        logger.info(f"✅ Geschichte generiert: '{chapter_title}' ({len(chapter_text)} Zeichen)")

    except Exception as e:
        logger.error(f"❌ Fehler bei der KI-Generierung: {e}")
        sys.exit(1)

    logger.info("")
    logger.info("💾 Ergebnis speichern...")
    logger.info("-" * 40)

    output = {
        "title": chapter_title,
        "description": "",
        "solution": "",
        "source": "KI-Generiert",
        "source_url": f"ai_story_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "full_text": chapter_text,
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
    logger.info(f"   Titel:       {output['title']}")
    logger.info(f"   Textlänge:   {len(output['full_text'])} Zeichen")
    logger.info(f"   Timestamp:   {output['timestamp']}")
    logger.info("=" * 60)
    logger.info("🎉 KI Long-Form Geschichte erfolgreich generiert!")
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
