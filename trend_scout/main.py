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


# ---------------------------------------------------------------------------
# Animal Pool for Natur category — with family-based dedup
# ---------------------------------------------------------------------------
ANIMAL_POOL = [
    {"name": "gấu trúc đáng yêu", "family": "bär", "label": "Gấu trúc"},
    {"name": "chim đại bàng", "family": "adler", "label": "Đại bàng"},
    {"name": "cá heo thông minh", "family": "delphin", "label": "Cá heo"},
    {"name": "hươu cao cổ", "family": "giraffe", "label": "Hươu cao cổ"},
    {"name": "voi châu Phi", "family": "elefant", "label": "Voi"},
    {"name": "hổ dũng mãnh", "family": "tiger", "label": "Hổ"},
    {"name": "cú mèo tinh anh", "family": "eule", "label": "Cú mèo"},
    {"name": "sư tử kiêu hãnh", "family": "löwe", "label": "Sư tử"},
    {"name": "ong mật chăm chỉ", "family": "biene", "label": "Ong mật"},
    {"name": "bướm xinh đẹp", "family": "schmetterling", "label": "Bướm"},
    {"name": "rùa biển", "family": "schildkröte", "label": "Rùa biển"},
    {"name": "chim cánh cụt", "family": "pinguin", "label": "Chim cánh cụt"},
    {"name": "cá voi lưng gù", "family": "wal", "label": "Cá voi"},
    {"name": "sói xám", "family": "wolf", "label": "Sói"},
    {"name": "báo đốm", "family": "leopard", "label": "Báo đốm"},
    {"name": "gấu Bắc Cực", "family": "eisbär", "label": "Gấu Bắc Cực"},
    {"name": "chim hồng hạc", "family": "flamingo", "label": "Hồng hạc"},
    {"name": "cá ngựa", "family": "seepferdchen", "label": "Cá ngựa"},
    {"name": "tắc kè hoa", "family": "chamäleon", "label": "Tắc kè hoa"},
    {"name": "đại bàng đầu trắng", "family": "adler", "label": "Đại bàng đầu trắng"},
    {"name": "koala", "family": "koala", "label": "Koala"},
    {"name": "kanguru", "family": "känguru", "label": "Kanguru"},
    {"name": "chim ruồi", "family": "kolibri", "label": "Chim ruồi"},
    {"name": "bạch tuộc", "family": "oktopus", "label": "Bạch tuộc"},
    {"name": "tuần lộc", "family": "rentier", "label": "Tuần lộc"},
    {"name": "cáo đỏ", "family": "fuchs", "label": "Cáo đỏ"},
    {"name": "gấu nâu", "family": "bär", "label": "Gấu nâu"},
    {"name": "cá mập trắng", "family": "hai", "label": "Cá mập"},
    {"name": "vẹt đuôi dài", "family": "papagei", "label": "Vẹt"},
    {"name": "chim bồ câu", "family": "taube", "label": "Bồ câu"},
]


def _pick_animal_from_pool(history: list[dict]) -> dict:
    """Pick an animal from ANIMAL_POOL, avoiding families already used in history."""
    import random

    used_families = set()
    for entry in history:
        family = entry.get("animal_family", "")
        if family:
            used_families.add(family)

    available = [a for a in ANIMAL_POOL if a["family"] not in used_families]

    if not available:
        logger.warning("⚠ Alle Tier-Familien wurden bereits verwendet. Pool wird zurückgesetzt.")
        available = ANIMAL_POOL

    chosen = random.choice(available)
    logger.info(f"🐾 Tier gewählt: {chosen['label']} (Familie: {chosen['family']})")
    logger.info(f"   Verfügbar: {len(available)}/{len(ANIMAL_POOL)} Tiere | Bereits verwendet: {len(used_families)} Familien")
    return chosen


def run_natur_direct():
    """Direct KI-driven nature content generation — no PDF books needed.
    
    Picks an animal from the pool (avoiding recent families via history),
    then generates a ~7-minute nature exploration story.
    """
    logger.info("=" * 60)
    logger.info("🌿 SERVICE 0: NATUR-GENERATOR (Direkte KI-Generierung)")
    logger.info("=" * 60)

    if not check_connection():
        logger.error("❌ Pipeline abgebrochen: API Fehler")
        sys.exit(1)

    # Pick animal with family-based dedup
    history = _load_history(mode="long_natur")
    chosen = _pick_animal_from_pool(history)

    from google import genai
    from google.genai import types
    from trend_scout.config import GEMINI_MODEL

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))

    # Short topic extraction for the chosen animal
    core_lesson = f"Khám phá cuộc sống kỳ thú của {chosen['name']} trong thiên nhiên hoang dã."

    return _generate_natur_story(
        client, core_lesson,
        source_name="Direkte KI-Generierung",
        source_url="direct_ai",
        chosen_animal=chosen
    )


def run_from_long_books():
    """Librarian mode: Picks a chapter from input/long/books/ and tells a bedtime story."""
    logger.info("=" * 60)
    logger.info("📚 SERVICE 0: LIBRARIAN (Long-Form Buch-Modus)")
    logger.info("=" * 60)

    from trend_scout.book_reader import run_book_reader, BOOKS_DIR_LONG

    history = _load_history(mode="long")
    book_data = run_book_reader(history, books_dir=BOOKS_DIR_LONG, sequential=True, check_story=False)
    
    if not book_data:
        sys.exit(1)

    return run_long_storyteller(
        source_text=book_data["text"], 
        source_name=book_data["book_filename"], 
        source_url=book_data["chapter_id"],
        category="schlaf"
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


def _generate_natur_story(client, core_lesson: str, source_name: str, source_url: str, chosen_animal: dict = None):
    """Generate a ~800-word nature exploration story with 6 content blocks matching the 7-minute video structure.
    
    Args:
        chosen_animal: Dict with 'name', 'family', 'label' from ANIMAL_POOL.
                       If None, falls back to random selection (legacy).
    """
    from google.genai import types
    from trend_scout.config import GEMINI_MODEL

    logger.info("🌿 Lasse KI eine Natur-Entdeckungsgeschichte erfinden (~7 Min)...")
    logger.info("-" * 40)

    try:
        import random

        if chosen_animal:
            animal_choice = chosen_animal["name"]
            animal_family = chosen_animal["family"]
            animal_label = chosen_animal["label"]
        else:
            # Legacy fallback
            animal_choice = random.choice([a["name"] for a in ANIMAL_POOL])
            animal_family = next((a["family"] for a in ANIMAL_POOL if a["name"] == animal_choice), "unbekannt")
            animal_label = animal_choice

        prompt = f"""Bạn là một nhà văn thiếu nhi xuất sắc và một nhà sinh vật học truyền cảm hứng. Hãy sáng tác một câu chuyện/kịch bản khám phá thiên nhiên hoàn toàn mới bằng tiếng Việt, khơi gợi trí tò mò của trẻ em.

CHỦ ĐỀ THIÊN NHIÊN CHÍNH:
"{core_lesson}"

NHÂN VẬT CHÍNH: **{animal_choice}**

YÊU CẦU CẤU TRÚC KỊCH BẢN CHI TIẾT (BẮT BUỘC):
Kịch bản phải được chia thành ĐÚNG 6 đoạn nội dung tương ứng với 6 phần sau đây (tổng cộng khoảng 680 đến 780 từ, cho video 7 phút):

1. **Phần 1 — Khởi đầu đầy lôi cuốn (Starker Einstieg)** (Độ dài: ~60 từ, cho khoảng 40 giây nói):
   - Mục tiêu: Thu hút sự chú ý ngay lập tức.
   - Nội dung: Đặt một câu hỏi bất ngờ hoặc một sự thật thú vị về {animal_choice}, giải thích lý do loài động vật này thú vị, giới thiệu nhanh về nội dung câu chuyện hôm nay.

2. **Phần 2 — Nơi sinh sống của loài vật (Lebensraum der Tiere)** (Độ dài: ~100 từ, cho khoảng 60 giây nói):
   - Mục tiêu: Giới thiệu môi trường sống của {animal_choice}.
   - Nội dung: Rừng hoang dã, đại dương bao la, sa mạc hay rừng nhiệt đới; cách {animal_choice} thích nghi đặc biệt với môi trường đó; tầm quan trọng của môi trường sống này.

3. **Phần 3 — Khả năng đặc biệt thú vị (Interessante Fähigkeiten der Tiere)** (Độ dài: ~100 từ, cho khoảng 60 giây nói):
   - Mục tiêu: Khiến người xem ngạc nhiên và thán phục.
   - Nội dung: Tốc độ, ngụy trang, kỹ năng sinh tồn đặc biệt, hoặc cách giao tiếp độc đáo của {animal_choice}. Lồng ghép sự thật khoa học ấn tượng.

4. **Phần 4 — Cuộc sống thường ngày (Das tägliche Leben der Tiere)** (Độ dài: ~120 từ, cho khoảng 70 giây nói):
   - Mục tiêu: Giới thiệu cuộc sống đời thường, tạo cảm giác gần gũi, ấm áp.
   - Nội dung: Cách kiếm thức ăn, tập tính ngủ nghỉ, tình cảm bầy đàn gia đình, cách bảo vệ con non của {animal_choice}.

5. **Phần 5 — Mối đe dọa & Bảo tồn thiên nhiên (Gefahren & Naturschutz)** (Độ dài: ~140 từ, cho khoảng 90 giây nói):
   - Mục tiêu: Tạo sự kết nối cảm xúc và ý thức trách nhiệm.
   - Nội dung: Các nguy cơ thực tế (mất môi trường sống, biến đổi khí hậu...), tại sao {animal_choice} quan trọng cho sự cân bằng hệ sinh thái, cách chúng ta có thể bảo vệ chúng.

6. **Phần 6 — Lời kết & Thông điệp truyền cảm hứng (Abschluss & starke Botschaft)** (Độ dài: ~160 từ, cho khoảng 100 giây nói):
   - Mục tiêu: Kết thúc tươi đẹp và truyền động lực.
   - Nội dung: Tóm tắt ngắn gọn điều kỳ diệu nhất vừa khám phá, thông điệp bảo vệ thiên nhiên. Đặt câu hỏi tương tác thú vị cho người xem, kêu gọi Like và Đăng ký (Subscribe) kênh để đón chờ bài học sau.

PHONG CÁCH VIẾT:
- Giọng văn: Vui vẻ, hào hứng, giàu tò mò, đầy năng lượng (hoàn toàn KHÔNG phải truyện ru ngủ).
- Cách xưng hô: Dùng các từ thân thiện như "các nhà thám hiểm nhí", "chúng ta", "bạn nhỏ". Tuyệt đối không dùng tên riêng.
- Khoa học và chính xác: Lồng ghép ít nhất 2 sự thật khoa học thú vị và chính xác về {animal_choice}.

Trả lời bằng JSON với định dạng sau (không thêm bất kỳ văn bản nào bên ngoài JSON):
{{
  "title": "Tên kịch bản khám phá thiên nhiên cực kỳ hấp dẫn",
  "animal": "{animal_choice}",
  "story": "Nối liền cả 6 phần trên thành một văn bản hoàn chỉnh, mỗi phần phân tách bằng đúng một dòng trống và bắt đầu bằng thẻ Phần 1, Phần 2, v.v."
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
            "animal_family": animal_family,
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
        logger.info(f"   Tier:        {output['animal']} (Familie: {animal_family})")
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
