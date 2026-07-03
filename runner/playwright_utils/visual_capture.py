from __future__ import annotations

from pathlib import Path

from playwright.async_api import async_playwright


async def capture_page_screenshot(url: str, output_path: Path) -> str:
    """Capture a full-page screenshot of a URL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(output_path), full_page=True)
        await browser.close()
    return str(output_path)
