import asyncio
from playwright.async_api import async_playwright
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from trend_scout.config import SCRAPE_TARGETS, BLOCKED_RESOURCE_TYPES

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        for target in SCRAPE_TARGETS:
            name = target["name"]
            url = target["url"]
            headline_sel = target["headline_selector"]
            body_sel = target["article_body_selector"]
            consent_sel = target.get("consent_selector")
            print(f"\n--- Checking {name} ---")

            page = await context.new_page()
            
            # block resources
            async def route_intercept(route):
                if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
                    await route.abort()
                else:
                    await route.continue_()
            await page.route("**/*", route_intercept)

            try:
                print(f"Visiting URL: {url}")
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                
                # check consent
                if consent_sel:
                    consent_elements = await page.locator(consent_sel).count()
                    print(f"  [Consent] Selector '{consent_sel}': Found {consent_elements} element(s)")
                else:
                    print(f"  [Consent] No selector configured")

                # find a headline to click on
                headlines = await page.locator(headline_sel).all()
                link = None
                for hl in headlines:
                    # try to get href
                    tag_name = await hl.evaluate("el => el.tagName.toLowerCase()")
                    if tag_name == "a":
                        link = await hl.get_attribute("href")
                        if link: break
                    else:
                        a_tag = hl.locator("a").first
                        if await a_tag.count() > 0:
                            link = await a_tag.get_attribute("href")
                            if link: break
                
                if link:
                    if not link.startswith("http"):
                        from urllib.parse import urljoin
                        link = urljoin(url, link)
                    print(f"  Found article link: {link}")
                    
                    # navigate to article
                    try:
                        await page.goto(link, timeout=30000, wait_until="domcontentloaded")
                        body_elements = await page.locator(body_sel).count()
                        print(f"  [Article Body] Selector '{body_sel}': Found {body_elements} element(s)")
                        if body_elements > 0:
                            # fetch some text
                            text = await page.locator(body_sel).first.inner_text()
                            print(f"  [Article Body] Sample text: {repr(text[:50])}...")
                    except Exception as e:
                        print(f"  [Article Body] Error loading article link: {e}")
                else:
                    print(f"  [Headline] No link found using selector '{headline_sel}'")

            except Exception as e:
                print(f"Error checking {name}: {e}")
            finally:
                await page.close()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check())
