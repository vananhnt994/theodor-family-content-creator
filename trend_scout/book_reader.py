"""
Module for reading and extracting chapters from PDF books in input/books.
Uses PyMuPDF (fitz) to read TOC or chunk the book if no TOC is found.
"""

import os
import glob
import random
import logging
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

BOOKS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input", "books")

def get_available_books() -> list[str]:
    """Returns a list of PDF file paths in the books directory."""
    if not os.path.exists(BOOKS_DIR):
        return []
    return glob.glob(os.path.join(BOOKS_DIR, "*.pdf"))

def extract_text_from_pages(doc: fitz.Document, start_page: int, end_page: int) -> str:
    """Extracts text from a range of pages (1-indexed based on TOC)."""
    text = ""
    # fitz uses 0-indexed pages, TOC pages are typically 1-indexed (or refer to physical pages).
    # get_toc() returns physical page numbers (1-indexed relative to doc).
    start_idx = max(0, start_page - 1)
    end_idx = min(len(doc) - 1, end_page - 1)
    
    for i in range(start_idx, end_idx + 1):
        page = doc.load_page(i)
        text += page.get_text("text") + "\n"
    return text.strip()

def pick_unread_chapter(filepath: str, used_chapters: set[str]) -> tuple[str, str]:
    """
    Attempts to read TOC and pick an unread chapter.
    If no TOC, splits the document into 5-page chunks and picks an unread chunk.
    Returns (chapter_title, chapter_text).
    """
    filename = os.path.basename(filepath)
    doc = fitz.open(filepath)
    
    toc = doc.get_toc()
    chapters = []
    
    if toc:
        # Filter top-level or second-level items that look like chapters
        # TOC format: [level, title, page_number]
        # We assume each entry goes until the next entry's page_number
        for i, item in enumerate(toc):
            level, title, page = item[:3]
            # Find the next page
            next_page = len(doc)
            for next_item in toc[i+1:]:
                if next_item[2] > page:
                    next_page = next_item[2]
                    break
            
            # Avoid very short sections (like just 1 page or 0 pages if it's just a heading)
            # Actually, let's just collect all top level (level 1 or 2)
            if level <= 2:
                chapters.append({
                    "title": title.strip(),
                    "start": page,
                    "end": next_page
                })
    else:
        # No TOC, chunk by 5 pages
        chunk_size = 5
        total_pages = len(doc)
        for i in range(0, total_pages, chunk_size):
            start = i + 1
            end = min(i + chunk_size, total_pages)
            chapters.append({
                "title": f"Kapitel/Chunk {start}-{end}",
                "start": start,
                "end": end
            })
            
    # Filter out used chapters
    available_chapters = []
    for chap in chapters:
        chapter_id = f"{filename}::{chap['title']}"
        if chapter_id not in used_chapters:
            available_chapters.append(chap)
            
    if not available_chapters:
        doc.close()
        return None, None
        
    # Pick a random chapter
    selected = random.choice(available_chapters)
    text = extract_text_from_pages(doc, selected["start"], selected["end"])
    doc.close()
    
    if not text or len(text.strip()) < 100:
        # Fallback if the extracted text is too short or empty
        return selected["title"], f"(Leeres oder nicht lesbares Kapitel) {text}"
        
    return selected["title"], text

def run_book_reader(history_entries: list[dict]) -> dict:
    """
    Picks a random book and an unread chapter from it.
    Returns a dict with title, text, source (filename), url (chapter_id).
    """
    books = get_available_books()
    if not books:
        logger.error("❌ Keine Bücher im Ordner input/books/ gefunden!")
        return None
        
    # Build set of used chapter IDs
    used_chapters = set()
    for entry in history_entries:
        # We store book filename in source, and chapter ID in source_url
        if entry.get("source_url") and entry.get("source", "").endswith(".pdf"):
            used_chapters.add(entry.get("source_url"))
            
    # Randomize books to pick one with available chapters
    random.shuffle(books)
    
    for book_path in books:
        filename = os.path.basename(book_path)
        logger.info(f"📖 Untersuche Buch: {filename}")
        try:
            chapter_title, chapter_text = pick_unread_chapter(book_path, used_chapters)
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
