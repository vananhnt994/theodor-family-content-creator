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

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
BOOKS_DIR_SHORTS = os.path.join(BASE_DIR, "input", "shorts", "books")
BOOKS_DIR_LONG   = os.path.join(BASE_DIR, "input", "long", "books")


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


def pick_unread_chapter(filepath: str, used_chapters: set, sequential: bool = False) -> tuple:
    """
    Picks an unread chapter from a PDF.

    Args:
        filepath: Path to the PDF file.
        used_chapters: Set of chapter IDs already used.
        sequential: If True, pick the first available chapter in order.
                    If False, pick a random available chapter.

    Returns:
        (chapter_title, chapter_text) or (None, None) if all chapters used.
    """
    filename = os.path.basename(filepath)
    doc = fitz.open(filepath)
    chapters = _build_chapters(doc)

    available = []
    for chap in chapters:
        chapter_id = f"{filename}::{chap['title']}"
        if chapter_id not in used_chapters:
            available.append(chap)

    if not available:
        doc.close()
        return None, None

    selected = available[0] if sequential else random.choice(available)
    text = extract_text_from_pages(doc, selected["start"], selected["end"])
    doc.close()

    if not text or len(text.strip()) < 100:
        return selected["title"], f"(Leeres oder nicht lesbares Kapitel) {text}"

    return selected["title"], text


def run_book_reader(history_entries: list[dict], books_dir: str = None, sequential: bool = False) -> dict:
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
            chapter_title, chapter_text = pick_unread_chapter(book_path, used_chapters, sequential=sequential)
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
