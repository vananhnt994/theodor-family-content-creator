"""
Playwright-based headless web scraper for Vietnamese family/parenting websites.
Phase 1: Collect headlines + URLs from multiple sources.
Phase 2: Fetch full article content for a selected URL.
"""

import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from trend_scout.config import (
    SCRAPE_TARGETS,
    BLOCKED_RESOURCE_TYPES,
    PAGE_TIMEOUT_MS,
    MAX_HEADLINES_PER_SOURCE,
)

logger = logging.getLogger(__name__)


def _block_resources(route):
    """Abort requests for images, CSS, fonts to save bandwidth and RAM."""
    if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
        route.abort()
    else:
        route.continue_()


def scrape_headlines() -> list[dict]:
    """
    Phase 1: Scrape headlines from all configured targets.

    Returns:
        List of dicts with keys: title, url, source
    """
    all_headlines = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="vi-VN",
        )

        for target in SCRAPE_TARGETS:
            name = target["name"]
            url = target["url"]
            selector = target["headline_selector"]

            logger.info(f"[Scraper] Đang truy cập: {name} ({url})")

            page = context.new_page()
            page.route("**/*", _block_resources)

            try:
                page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)  # extra wait for any lazy-loaded text

                # Extract all matching headline elements
                elements = page.query_selector_all(selector)
                count = 0

                for el in elements:
                    if count >= MAX_HEADLINES_PER_SOURCE:
                        break

                    title = (el.inner_text() or "").strip()
                    href = el.get_attribute("href") or ""

                    # Skip empty or too-short headlines
                    if not title or len(title) < 10:
                        continue

                    # Resolve relative URLs
                    if href and not href.startswith("http"):
                        # Build absolute URL from base
                        from urllib.parse import urljoin
                        href = urljoin(url, href)

                    all_headlines.append({
                        "title": title,
                        "url": href,
                        "source": name,
                    })
                    count += 1

                logger.info(f"[Scraper] ✓ {name}: {count} tiêu đề thu thập được")

            except PlaywrightTimeout:
                logger.warning(f"[Scraper] ✗ Timeout khi truy cập {name} – bỏ qua")
            except Exception as e:
                logger.warning(f"[Scraper] ✗ Lỗi khi scrape {name}: {e} – bỏ qua")
            finally:
                page.close()

        browser.close()

    logger.info(f"[Scraper] Tổng cộng: {len(all_headlines)} tiêu đề từ tất cả nguồn")
    return all_headlines


def scrape_article(article_url: str, source_name: str = "") -> str:
    """
    Phase 2: Fetch full article text from a specific URL.

    Args:
        article_url: The URL of the article to scrape.
        source_name: Name of the source (to find correct selector).

    Returns:
        The full article text as a single string.
    """
    if not article_url:
        logger.warning("[Scraper] Keine Artikel-URL vorhanden, überspringe Phase 2")
        return ""

    # Find the matching article body selector
    article_selector = "article p, div.content p, div.entry-content p"  # fallback
    for target in SCRAPE_TARGETS:
        if target["name"] == source_name:
            article_selector = target["article_body_selector"]
            break

    logger.info(f"[Scraper] Đang tải nội dung bài viết: {article_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="vi-VN",
        )

        page = context.new_page()
        page.route("**/*", _block_resources)

        try:
            page.goto(article_url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # Extract all paragraphs from the article body
            paragraphs = page.query_selector_all(article_selector)
            texts = []

            for p_el in paragraphs:
                text = (p_el.inner_text() or "").strip()
                if text and len(text) > 20:  # skip tiny fragments
                    texts.append(text)

            article_text = "\n\n".join(texts)
            logger.info(
                f"[Scraper] ✓ Nội dung bài viết: {len(texts)} đoạn, "
                f"{len(article_text)} ký tự"
            )
            return article_text

        except PlaywrightTimeout:
            logger.warning(f"[Scraper] ✗ Timeout khi tải bài viết – bỏ qua")
            return ""
        except Exception as e:
            logger.warning(f"[Scraper] ✗ Lỗi khi tải bài viết: {e}")
            return ""
        finally:
            page.close()
            browser.close()
