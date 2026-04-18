import asyncio
from playwright.async_api import async_playwright
import sys
import os

async def dump():
    if not os.path.exists('html_dumps'):
        os.makedirs('html_dumps')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        urls = {
            "dantri.html": "https://dantri.com.vn/giao-duc/cong-an-vao-cuoc-vu-sach-tin-hoc-lop-3-co-link-web-den-20260409171628501.htm",
            "lamchame.html": "https://www.lamchame.com/forum/threads/cutrite-v10.5296031/",
            "webtretho_home.html": "https://www.webtretho.vn/thinh-hanh/suc-khoe-doi-song",
            "spiegel_home.html": "https://www.spiegel.de/thema/erziehung/"
        }

        for name, url in urls.items():
            print(f"Dumping {name}...")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                html = await page.content()
                with open(os.path.join('html_dumps', name), 'w', encoding='utf-8') as f:
                    f.write(html)
            except Exception as e:
                print(f"Error {name}: {e}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(dump())
