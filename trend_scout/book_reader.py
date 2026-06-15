"""
Module for reading and extracting chapters from PDF books.
Supports two modes:
  - shorts: input/shorts/books/ — picks a random unread chapter
  - long:   input/long/books/   — picks sequentially the next unread chapter
Uses PyMuPDF (fitz) to read TOC or chunk the book if no TOC is found.
"""

import os
import glob
import random
import logging
import fitz  # PyMuPDF
from google import genai

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
BOOKS_DIR_SHORTS = os.path.join(BASE_DIR, "input", "shorts", "books")
BOOKS_DIR_LONG       = os.path.join(BASE_DIR, "input", "long", "books")





def _is_actual_story(text: str) -> bool:
    """Uses Gemini to determine if the text is a narrative story."""
    try:
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from trend_scout.config import GEMINI_MODEL
        from dotenv import load_dotenv
        
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
        load_dotenv()
        
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", ""))
        
        sample = text[:2000]
        prompt = f"""You are a content classifier. Analyze the following Vietnamese text and determine if it is an ACTUAL NARRATIVE STORY (e.g., a fairy tale with characters, dialogue, and a plot).

It is STRICTLY NOT a story if it is:
- An academic analysis or essay ABOUT literature, myths, or fairy tales.
- A preface, table of contents, or author's note.
- An explanation of concepts (like "what is a fairy tale").

First, briefly explain your reasoning. Then, on a new line at the very end, write EXACTLY "YES" (if it's a story) or "NO" (if it is not).

Text:
{sample}"""
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        if response.candidates:
            answer = response.text.strip().upper()
            last_line = answer.split('\n')[-1]
            return "YES" in last_line
        return True
    except Exception as e:
        logger.warning(f"AI Classification failed: {e}. Assuming it is a story.")
        return True


def _has_educational_value(text: str) -> bool:
    """Uses Gemini to determine if the text has high educational value for parenting."""
    try:
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from trend_scout.config import GEMINI_MODEL
        from dotenv import load_dotenv
        
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
        load_dotenv()
        
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", ""))
        
        sample = text[:3000]
        prompt = f"""Bạn là một chuyên gia đánh giá nội dung giáo dục sớm và tâm lý trẻ em. 
Hãy phân tích đoạn văn bản tiếng Việt sau đây và xác định xem nó có mang lại GIÁ TRỊ GIÁO DỤC THỰC TẾ (ví dụ: lời khuyên cụ thể, bài học ý nghĩa, phương pháp nuôi dạy con, kiến thức tâm lý bổ ích) hay không.

Nội dung bị coi là THIẾU GIÁ TRỊ nếu:
- Chỉ là lời mở đầu, mục lục, hoặc giới thiệu tác giả.
- Chỉ là những thảo luận chung chung, trừu tượng mà không có lời khuyên cụ thể.
- Chỉ là liệt kê các khái niệm mà không giải thích ứng dụng.
- Nội dung quá hàn lâm, khó hiểu cho cha mẹ thông thường.

Hãy giải thích ngắn gọn lý do. Sau đó, ở dòng cuối cùng, viết chính xác "YES" (nếu có giá trị thực tế) hoặc "NO" (nếu không).

Văn bản:
{sample}"""
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        if response.candidates:
            answer = response.text.strip().upper()
            last_line = answer.split('\n')[-1]
            return "YES" in last_line
        return True
    except Exception as e:
        logger.warning(f"Value classification failed: {e}. Assuming it has value.")
        return True


def get_available_books(books_dir: str) -> list[str]:
    """Returns a list of PDF file paths in the given directory."""
    if not os.path.exists(books_dir):
        return []
    return glob.glob(os.path.join(books_dir, "*.pdf"))


def extract_text_from_pages(doc: fitz.Document, start_page: int, end_page: int) -> str:
    """Extracts text from a range of pages (1-indexed based on TOC)."""
    text = ""
    start_idx = max(0, start_page - 1)
    end_idx = min(len(doc) - 1, end_page - 1)
    for i in range(start_idx, end_idx + 1):
        page = doc.load_page(i)
        text += page.get_text("text") + "\n"
    return text.strip()


def _build_chapters(doc: fitz.Document) -> list[dict]:
    """Build chapter list from TOC, or fall back to 5-page chunks."""
    toc = doc.get_toc()
    chapters = []
    if toc:
        for i, item in enumerate(toc):
            level, title, page = item[:3]
            next_page = len(doc)
            for next_item in toc[i + 1:]:
                if next_item[2] > page:
                    next_page = next_item[2]
                    break
            if level <= 2:
                chapters.append({"title": title.strip(), "start": page, "end": next_page})
    else:
        chunk_size = 5
        total_pages = len(doc)
        for i in range(0, total_pages, chunk_size):
            start = i + 1
            end = min(i + chunk_size, total_pages)
            chapters.append({"title": f"Kapitel/Chunk {start}-{end}", "start": start, "end": end})
    return chapters


def pick_unread_chapter(filepath: str, used_chapters: set, sequential: bool = False, check_story: bool = False) -> tuple:
    """
    Picks an unread chapter from a PDF, skipping prefaces and short intros.
    If check_story is True, uses AI to strictly ensure it is a narrative story.
    """
    filename = os.path.basename(filepath)
    doc = fitz.open(filepath)
    chapters = _build_chapters(doc)

    if check_story:
        # Strict filtering for fairy tales / stories
        skip_keywords = [
            "lời nói đầu", "giới thiệu", "mục lục", "tựa", "lời tựa", "lời mở đầu", 
            "preface", "introduction", "khác với", "là gì", "tại sao", "như thế nào", 
            "tổng quan", "phân loại", "đặc điểm", "nghiên cứu", "lịch sử", "khái niệm", 
            "định nghĩa", "chú thích", "phần mở đầu", "lời kết", "kết luận"
        ]
    else:
        # Relaxed filtering for parenting articles / ratgeber
        skip_keywords = [
            "lời nói đầu", "giới thiệu", "mục lục", "tựa", "lời tựa", "lời mở đầu", 
            "preface", "introduction", "chú thích", "phần mở đầu", "lời kết", "kết luận"
        ]

    available = []
    
    for chap in chapters:
        chapter_id = f"{filename}::{chap['title']}"
        title_lower = chap['title'].lower()
        if chapter_id not in used_chapters:
            # Skip intro/academic chapters based on title keywords or question marks
            if any(k in title_lower for k in skip_keywords) or (check_story and "?" in title_lower):
                logger.info(f"⏭  Überspringe Intro-Kapitel: {chap['title']}")
                used_chapters.add(chapter_id)
                continue
            available.append(chap)

    if not available:
        doc.close()
        return None, None

    if not sequential:
        random.shuffle(available)

    # Find the first chapter that has enough content
    for selected in available:
        text = extract_text_from_pages(doc, selected["start"], selected["end"])
        if text and len(text.strip()) >= 500:
            if check_story:
                logger.info(f"🤖 Lasse KI prüfen, ob '{selected['title']}' eine echte Geschichte ist...")
                if _is_actual_story(text):
                    doc.close()
                    return selected["title"], text
                else:
                    logger.info(f"⏭  KI sagt: Kapitel '{selected['title']}' ist keine echte Geschichte. Überspringe.")
                    used_chapters.add(f"{filename}::{selected['title']}")
            else:
                # No story check required, but check for educational value (Shorts)
                logger.info(f"🤖 Prüfe pädagogischen Mehrwert für '{selected['title']}'...")
                if _has_educational_value(text):
                    doc.close()
                    return selected["title"], text
                else:
                    logger.info(f"⏭  KI sagt: Kapitel '{selected['title']}' hat keinen ausreichenden pädagogischen Mehrwert. Überspringe.")
                    used_chapters.add(f"{filename}::{selected['title']}")
        else:
            logger.info(f"⏭  Kapitel '{selected['title']}' ist zu kurz ({len(text) if text else 0} Zeichen). Überspringe.")
            used_chapters.add(f"{filename}::{selected['title']}")

    doc.close()
    return None, None


def run_book_reader(history_entries: list[dict], books_dir: str = None, sequential: bool = False, check_story: bool = False) -> dict:
    """
    Picks a book and an unread chapter from it.

    Args:
        history_entries: Entries from the appropriate history file.
        books_dir: Directory to scan for PDFs. Defaults to BOOKS_DIR_SHORTS.
        sequential: If True, picks the first available chapter in order (Long-Form mode).

    Returns:
        Dict with book_filename, chapter_title, chapter_id, text — or None.
    """
    if books_dir is None:
        books_dir = BOOKS_DIR_SHORTS

    books = get_available_books(books_dir)
    if not books:
        logger.error(f"❌ Keine Bücher in '{books_dir}' gefunden!")
        return None

    # Build set of used chapter IDs
    used_chapters = set()
    for entry in history_entries:
        if entry.get("source_url") and entry.get("source", "").endswith(".pdf"):
            used_chapters.add(entry.get("source_url"))

    if not sequential:
        random.shuffle(books)

    for book_path in books:
        filename = os.path.basename(book_path)
        logger.info(f"📖 Untersuche Buch: {filename}")
        try:
            chapter_title, chapter_text = pick_unread_chapter(book_path, used_chapters, sequential=sequential, check_story=check_story)
            if chapter_title and chapter_text:
                chapter_id = f"{filename}::{chapter_title}"
                logger.info(f"✅ Kapitel gefunden: {chapter_title} ({len(chapter_text)} Zeichen)")
                return {
                    "book_filename": filename,
                    "chapter_title": chapter_title,
                    "chapter_id": chapter_id,
                    "text": chapter_text
                }
        except Exception as e:
            logger.warning(f"⚠️ Fehler beim Lesen von {filename}: {e}")
            continue

    logger.error("❌ Alle Kapitel aus allen Büchern wurden bereits verwendet oder können nicht gelesen werden.")
    return None
