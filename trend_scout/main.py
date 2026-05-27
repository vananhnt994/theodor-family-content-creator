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
    HISTORY_SHORTS_FILENAME, HISTORY_LONG_FILENAME,
    HISTORY_LONG_NATUR_FILENAME, HISTORY_FILENAME
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
    """Load existing topic history (shorts, long, or long_natur mode)."""
    if mode == "long_natur":
        filename = HISTORY_LONG_NATUR_FILENAME
    elif mode == "long":
        filename = HISTORY_LONG_FILENAME
    else:
        filename = HISTORY_SHORTS_FILENAME
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
    if mode == "long_natur":
        filename = HISTORY_LONG_NATUR_FILENAME
    elif mode == "long":
        filename = HISTORY_LONG_FILENAME
    else:
        filename = HISTORY_SHORTS_FILENAME
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
    """Librarian mode: Picks a chapter from input/long/books/ (or books_natur/) and tells a story."""
    category = os.environ.get("THEODOR_LONG_CATEGORY", "schlaf")
    
    logger.info("=" * 60)
    if category == "natur":
        logger.info("🌿 SERVICE 0: LIBRARIAN (Long-Form Natur-Modus)")
    else:
        logger.info("📚 SERVICE 0: LIBRARIAN (Long-Form Buch-Modus)")
    logger.info("=" * 60)

    from trend_scout.book_reader import run_book_reader, BOOKS_DIR_LONG, BOOKS_DIR_LONG_NATUR

    if category == "natur":
        books_dir = BOOKS_DIR_LONG_NATUR
        history_mode = "long_natur"
    else:
        books_dir = BOOKS_DIR_LONG
        history_mode = "long"
    
    history = _load_history(mode=history_mode)
    book_data = run_book_reader(history, books_dir=books_dir, sequential=True, check_story=False)
    
    if not book_data:
        sys.exit(1)

    return run_long_storyteller(
        source_text=book_data["text"], 
        source_name=book_data["book_filename"], 
        source_url=book_data["chapter_id"],
        category=category
    )


def run_long_from_file(file_path: str):
    """Generates a long bedtime story based on a local text file (Article)."""
    logger.info("=" * 60)
    logger.info("📝 SERVICE 0: ARTIKEL-STORYTELLER (Long-Form)")
    logger.info("=" * 60)

    if not os.path.exists(file_path):
        logger.error(f"❌ Datei nicht gefunden: {file_path}")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    return run_long_storyteller(
        source_text=text, 
        source_name=os.path.basename(file_path), 
        source_url="local_file"
    )


def run_long_storyteller(source_text: str, source_name: str, source_url: str, category: str = "schlaf"):
    """
    Core logic for Service 0 (Long-Form):
    - schlaf: Extracts lesson, invents a long bedtime story (2000-3500 words).
    - natur: Extracts nature topic, creates a short educational story (~700 words, 6 blocks).
    """
    from google import genai
    from google.genai import types
    from trend_scout.config import GEMINI_MODEL

    if not check_connection():
        logger.error("❌ Pipeline abgebrochen: API Fehler")
        sys.exit(1)

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))

    # Step 1: Extract the core lesson / nature topic
    logger.info("🧠 Schritt 1: Extrahiere Kernthema...")
    if category == "natur":
        value_prompt = f"""Bạn là một chuyên gia về thiên nhiên và động vật. Hãy đọc văn bản sau và xác định CHỦ ĐỀ THIÊN NHIÊN CHÍNH (ví dụ: loài động vật, hiện tượng tự nhiên, hệ sinh thái).

Văn bản:
{source_text[:5000]}

Trả lời ngắn gọn (1-2 câu) bằng tiếng Việt — mô tả chủ đề thiên nhiên chính."""
    else:
        value_prompt = f"""Bạn là một chuyên gia giáo dục sớm. Hãy đọc văn bản sau và tóm tắt GIÁ TRỊ GIÁO DỤC CỐT LÕI (Erziehungsinhalt) dành cho cha mẹ.
Tập trung vào: Bài học chính là gì? Cha mẹ nên dạy con điều gì từ nội dung này?

Văn bản:
{source_text[:5000]}

Trả lời ngắn gọn (1-2 câu) bằng tiếng Việt."""
    
    try:
        value_resp = client.models.generate_content(model=GEMINI_MODEL, contents=value_prompt)
        core_lesson = value_resp.text.strip()
        logger.info(f"✅ Kernthema extrahiert: {core_lesson[:100]}...")
    except Exception as e:
        logger.warning(f"⚠ Fehler bei Themen-Extraktion: {e}. Nutze Standard-Thema.")
        core_lesson = "Khám phá thiên nhiên" if category == "natur" else "Lòng tốt và sự thấu hiểu"

    # Step 2: Generate the story
    logger.info("")

    if category == "natur":
        return _generate_natur_story(client, core_lesson, source_name, source_url)
    else:
        return _generate_schlaf_story(client, core_lesson, source_name, source_url)


def _generate_natur_story(client, core_lesson: str, source_name: str, source_url: str):
    """Generate a ~700-word nature exploration story with 6 content blocks."""
    from google.genai import types
    from trend_scout.config import GEMINI_MODEL

    logger.info("🌿 Lasse KI eine Natur-Entdeckungsgeschichte erfinden (~6 Min)...")
    logger.info("-" * 40)

    try:
        import random
        animal_choice = random.choice([
            "con sóc", "con nai", "con cáo", "con gấu", "con thỏ", "con rùa",
            "con chim đại bàng", "con cá heo", "con hươu cao cổ", "con voi",
            "con gấu trúc", "con hổ", "con cú mèo", "con sư tử",
            "con ong mật", "con bướm", "con chuồn chuồn", "con chim cánh cụt"
        ])

        prompt = f"""Bạn là một nhà văn thiếu nhi và chuyên gia thiên nhiên. Hãy sáng tác một câu chuyện khám phá thiên nhiên hoàn toàn mới bằng tiếng Việt.

CHỦ ĐỀ THIÊN NHIÊN:
"{core_lesson}"

NHÂN VẬT CHÍNH: **{animal_choice}**

YÊU CẦU QUAN TRỌNG:
1. Câu chuyện phải NGẮN GỌN, khoảng 600 đến 700 từ, đủ để đọc to trong khoảng 5-6 phút.
2. CẤU TRÚC BẮT BUỘC — chia thành ĐÚNG 6 đoạn nội dung, mỗi đoạn ~100 từ:
   - Đoạn 1: Chào mừng và bước vào thế giới thiên nhiên
   - Đoạn 2: Phát hiện con vật ({animal_choice}) — mô tả ngoại hình sinh động
   - Đoạn 3: Giải thích thói quen và đặc điểm của {animal_choice} (ăn gì, sống ở đâu)
   - Đoạn 4: Một sự kiện thú vị hoặc hành vi đặc biệt của {animal_choice}
   - Đoạn 5: Bài học thiên nhiên — tại sao {animal_choice} quan trọng cho hệ sinh thái
   - Đoạn 6: Tạm biệt và lời nhắn nhủ yêu thiên nhiên
3. Phong cách: VUI VẺ, tò mò, kích thích khám phá — KHÔNG buồn ngủ.
4. Lồng ghép ít nhất 2 sự thật khoa học thú vị (fun facts) về {animal_choice}.
5. TUYỆT ĐỐI KHÔNG dùng tên riêng. Dùng "nhà thám hiểm nhí", "bạn nhỏ".

Trả lời bằng JSON với định dạng sau (không thêm bất kỳ văn bản nào bên ngoài JSON):
{{
  "title": "Tên câu chuyện",
  "animal": "{animal_choice}",
  "story": "Nội dung đầy đủ của câu chuyện..."
}}"""
        
        config = types.GenerateContentConfig(temperature=0.8)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config
        )
        
        from shared.gemini_utils import extract_json
        story_data = extract_json(response.text)
        if not story_data:
             raise ValueError("Ungültiges JSON von Gemini")

        chapter_title = story_data.get("title", "Khám Phá Thiên Nhiên")
        chapter_text = story_data.get("story", "")
        animal = story_data.get("animal", animal_choice)
        
        if not chapter_text or len(chapter_text) < 200:
            logger.error("❌ KI hat keine ausreichend lange Geschichte generiert.")
            sys.exit(1)

        word_count = len(chapter_text.split())
        logger.info(f"✅ Natur-Geschichte generiert: '{chapter_title}' ({word_count} Wörter, {len(chapter_text)} Zeichen)")

        logger.info("")
        logger.info("💾 Ergebnis speichern...")
        logger.info("-" * 40)

        output = {
            "title": chapter_title,
            "description": core_lesson,
            "solution": "",
            "source": source_name,
            "source_url": source_url,
            "full_text": chapter_text,
            "animal": animal,
            "mode": "long",
            "category": "natur",
            "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        }

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Gespeichert: {output_path}")

        _save_to_history(output, mode="long_natur")
        logger.info("")
        logger.info("=" * 60)
        logger.info("📋 ERGEBNIS (Natur)")
        logger.info("=" * 60)
        logger.info(f"   Titel:       {output['title']}")
        logger.info(f"   Tier:        {output['animal']}")
        logger.info(f"   Wörter:      {word_count}")
        logger.info(f"   Textlänge:   {len(output['full_text'])} Zeichen")
        logger.info("=" * 60)
        return output

    except Exception as e:
        logger.error(f"❌ Fehler bei der KI-Generierung: {e}")
        sys.exit(1)


def _generate_schlaf_story(client, core_lesson: str, source_name: str, source_url: str):
    """Generate a long bedtime story (2000-3500 words) — original schlaf logic."""
    from google.genai import types
    from trend_scout.config import GEMINI_MODEL

    logger.info("📖 Lasse KI eine neue Gute-Nacht-Geschichte erfinden (10-25 Min)...")
    logger.info("-" * 40)

    try:
        import random
        animal_choice = random.choice([
            "con sư tử", "con voi", "con cáo", "con gấu", "con thỏ", "con rùa",
            "con chim đại bàng", "con cá heo", "con hươu cao cổ", "con mèo rừng",
            "con gấu trúc", "con hổ", "con rồng nhỏ", "con cú mèo", "con sóc đất"
        ])

        prompt = f"""Bạn là một nhà văn thiếu nhi xuất sắc. Hãy sáng tác một câu chuyện cổ tích / chuyện kể trước khi đi ngủ hoàn toàn mới bằng tiếng Việt.

CHỦ ĐỀ GIÁO DỤC BẮT BUỘC (Trái tim của câu chuyện):
"{core_lesson}"

YÊU CẦU QUAN TRỌNG:
1. Câu chuyện phải RẤT DÀI và CHI TIẾT (khoảng 2000 đến 3500 từ), đủ để đọc to trong khoảng 10 đến 25 phút. Đừng tóm tắt, hãy kể thật chi tiết từng hành động, lời thoại.
2. Bài học "{core_lesson}" phải được lồng ghép một cách TỰ NHIÊN nhưng RÕ RÀNG xuyên suốt câu chuyện. Trẻ em phải học được điều này sau khi nghe xong.
3. Nội dung ấm áp, giàu trí tưởng tượng, phù hợp cho trẻ em nghe trước khi ngủ.
4. NHÂN VẬT CHÍNH phải là: **{animal_choice}** — hãy xây dựng tính cách và ngoại hình thật sinh động.
5. TUYỆT ĐỐI KHÔNG dùng con sóc (sóc) làm nhân vật chính.
6. LÀM GIÀU SÁNG TẠO (MANDATORY): Lồng ghép ít nhất 2 yếu tố thực tế (Địa danh, Nhân vật lịch sử, Kiến thức vũ trụ...) như một phần của câu chuyện.

Trả lời bằng JSON với định dạng sau (không thêm bất kỳ văn bản nào bên ngoài JSON):
{{
  "title": "Tên câu chuyện",
  "story": "Nội dung chi tiết của câu chuyện..."
}}"""
        
        config = types.GenerateContentConfig(temperature=0.8)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=config
        )
        
        from shared.gemini_utils import extract_json
        story_data = extract_json(response.text)
        if not story_data:
             raise ValueError("Ungültiges JSON von Gemini")

        chapter_title = story_data.get("title", "Gute Nacht Geschichte")
        chapter_text = story_data.get("story", "")
        
        if not chapter_text or len(chapter_text) < 500:
            logger.error("❌ KI hat keine ausreichend lange Geschichte generiert.")
            sys.exit(1)
            
        logger.info(f"✅ Geschichte generiert: '{chapter_title}' ({len(chapter_text)} Zeichen)")

        logger.info("")
        logger.info("💾 Ergebnis speichern...")
        logger.info("-" * 40)

        output = {
            "title": chapter_title,
            "description": core_lesson,
            "solution": "",
            "source": source_name,
            "source_url": source_url,
            "full_text": chapter_text,
            "mode": "long",
            "category": "schlaf",
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
        logger.info(f"   Lektion:     {output['description'][:100]}...")
        logger.info(f"   Textlänge:   {len(output['full_text'])} Zeichen")
        logger.info("=" * 60)
        return output

    except Exception as e:
        logger.error(f"❌ Fehler bei der KI-Generierung: {e}")
        sys.exit(1)



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
