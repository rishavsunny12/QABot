from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.async_api import Page, async_playwright

from playwright_utils.selector_builder import build_selector_from_element_info


DESTRUCTIVE_KEYWORDS = {"delete", "remove", "destroy", "logout", "sign out", "signout"}


class PlaywrightCrawler:
    """Domain-restricted BFS crawler using Playwright."""

    def __init__(
        self,
        base_url: str,
        allowed_domains: list[str],
        output_dir: Path,
        max_pages: int = 50,
        max_depth: int = 3,
        seed_urls: list[str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.allowed_domains = allowed_domains or [urlparse(base_url).netloc]
        self.output_dir = output_dir
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.seed_urls = seed_urls or [base_url]
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def crawl(
        self,
        login_fn=None,
    ) -> dict[str, Any]:
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(url, 0) for url in self.seed_urls]
        pages_data: list[dict[str, Any]] = []
        transitions: list[dict[str, Any]] = []
        logs: list[str] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            if login_fn:
                await login_fn(page)
                logs.append("Login completed")

            while queue and len(pages_data) < self.max_pages:
                url, depth = queue.pop(0)
                normalized = self._normalize_url(url)
                if normalized in visited or depth > self.max_depth:
                    continue
                if not self._is_allowed(normalized):
                    logs.append(f"Skipped disallowed URL: {normalized}")
                    continue

                visited.add(normalized)
                try:
                    await page.goto(normalized, wait_until="domcontentloaded", timeout=30000)
                    page_data = await self._extract_page(page, normalized, depth)
                    pages_data.append(page_data)
                    logs.append(f"Captured page: {normalized}")

                    for link in page_data.get("links", []):
                        if link not in visited:
                            queue.append((link, depth + 1))
                except Exception as exc:
                    logs.append(f"Error on {normalized}: {exc}")

            await browser.close()

        return {
            "pages": pages_data,
            "transitions": transitions,
            "logs": logs,
            "pages_count": len(pages_data),
            "elements_count": sum(len(p.get("elements", [])) for p in pages_data),
        }

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/') or '/'}"

    def _is_allowed(self, url: str) -> bool:
        host = urlparse(url).netloc
        return any(host == d or host.endswith(f".{d}") for d in self.allowed_domains)

    async def _extract_page(self, page: Page, url: str, depth: int) -> dict[str, Any]:
        title = await page.title()
        dom_hash = hashlib.sha256((await page.content()).encode()).hexdigest()[:16]
        screenshot_name = f"{dom_hash}.png"
        screenshot_path = self.output_dir / screenshot_name
        await page.screenshot(path=str(screenshot_path), full_page=True)

        elements = await page.evaluate(
            """() => {
            const results = [];
            const selectors = 'a, button, input, textarea, select, [role=button], h1, h2, h3, nav a';
            document.querySelectorAll(selectors).forEach((el, idx) => {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 && rect.height === 0) return;
                const text = (el.innerText || el.textContent || '').trim().slice(0, 200);
                const tag = el.tagName.toLowerCase();
                let role = el.getAttribute('role') || tag;
                if (tag === 'a') role = 'link';
                if (tag === 'button') role = 'button';
                const cssPath = el.id ? `#${el.id}` : `${tag}:nth-of-type(${idx + 1})`;
                results.push({
                    element_type: tag,
                    text: text,
                    aria_label: el.getAttribute('aria-label'),
                    testId: el.getAttribute('data-testid'),
                    role: role,
                    accessibleName: el.getAttribute('aria-label') || text,
                    label: el.labels?.[0]?.innerText || null,
                    cssPath: cssPath,
                    href: el.getAttribute('href'),
                });
            });
            return results;
        }"""
        )

        parsed_elements = []
        links: set[str] = set()
        for raw in elements:
            if self._is_destructive(raw.get("text", "")):
                continue
            candidate = build_selector_from_element_info(raw)
            parsed_elements.append(
                {
                    "element_type": raw.get("element_type", "unknown"),
                    "text_content": raw.get("text"),
                    "aria_label": raw.get("aria_label"),
                    "selector_primary": candidate.primary,
                    "selector_fallbacks": candidate.fallbacks,
                    "dom_signature_json": {
                        "role": candidate.role,
                        "name": candidate.name,
                        "tag": raw.get("element_type"),
                    },
                }
            )
            href = raw.get("href")
            if href and not href.startswith(("#", "javascript:")):
                links.add(urljoin(url, href))

        return {
            "url": url,
            "title": title,
            "dom_hash": dom_hash,
            "screenshot_path": str(screenshot_path),
            "elements": parsed_elements,
            "links": list(links),
            "depth": depth,
        }

    def _is_destructive(self, text: str) -> bool:
        lower = (text or "").lower()
        return any(kw in lower for kw in DESTRUCTIVE_KEYWORDS)


async def perform_form_login(page: Page, login_url: str, username: str, password: str) -> None:
    await page.goto(login_url, wait_until="domcontentloaded")
    user_selectors = [
        'input[type="email"]',
        'input[name="username"]',
        'input[name="email"]',
        'input[type="text"]',
    ]
    password_selectors = ['input[type="password"]', 'input[name="password"]']

    filled_user = False
    for sel in user_selectors:
        if await page.locator(sel).count() > 0:
            await page.locator(sel).first.fill(username)
            filled_user = True
            break
    if not filled_user:
        raise ValueError("Could not find username field")

    filled_pass = False
    for sel in password_selectors:
        if await page.locator(sel).count() > 0:
            await page.locator(sel).first.fill(password)
            filled_pass = True
            break
    if not filled_pass:
        raise ValueError("Could not find password field")

    submit = page.get_by_role("button", name="Log in").or_(page.get_by_role("button", name="Sign in"))
    if await submit.count() == 0:
        submit = page.locator('button[type="submit"], input[type="submit"]')
    await submit.first.click()
    await page.wait_for_load_state("domcontentloaded")
