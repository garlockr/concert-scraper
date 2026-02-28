from __future__ import annotations

import logging
from urllib.parse import urlparse, urlunparse

import html2text
import httpx

logger = logging.getLogger(__name__)

# Common paths where venues host their event listings
COMMON_EVENT_PATHS = [
    "/calendar",
    "/events",
    "/shows",
    "/schedule",
    "/concerts",
    "/upcoming-events",
    "/event",
    "/live-music",
]


def clean_html(raw_html: str) -> str:
    """Convert raw HTML to markdown text, truncated to 50k characters."""
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    converter.body_width = 0
    result = converter.handle(raw_html)
    return result[:50_000]


def _looks_like_spa_shell(html: str) -> bool:
    """Heuristic check for single-page app shells with no real content."""
    import re

    body_match = re.search(r"<body[^>]*>(.*)</body>", html, re.DOTALL | re.IGNORECASE)
    if body_match:
        body_text = re.sub(r"<[^>]+>", "", body_match.group(1)).strip()
        if len(body_text) < 500:
            return True

    spa_indicators = [
        '<div id="root"></div>',
        '<div id="app"></div>',
        '<div id="root">',
        '<div id="app">',
    ]
    lower_html = html.lower()
    for indicator in spa_indicators:
        if indicator.lower() in lower_html:
            # Check if the div is essentially empty
            if '<noscript>' in lower_html:
                return True

    return False


def _build_fallback_urls(url: str) -> list[str]:
    """Given a URL that 404'd, generate fallback URLs using common event paths."""
    parsed = urlparse(url)
    base = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    seen = {parsed.path.rstrip("/")}
    fallbacks = []
    for path in COMMON_EVENT_PATHS:
        if path.rstrip("/") not in seen:
            fallbacks.append(base + path)
            seen.add(path.rstrip("/"))
    return fallbacks


async def scrape_fast(url: str) -> str | None:
    """Fetch a URL via plain HTTP. Returns cleaned markdown or None if it
    looks like an SPA shell or request fails.
    If the URL returns 404, tries common event page paths on the same domain."""
    async with httpx.AsyncClient(
        timeout=15,
        follow_redirects=True,
        headers={"User-Agent": "ConcertScraper/0.1 (personal calendar tool)"},
    ) as client:
        response = await client.get(url)
        if response.status_code == 200 and not _looks_like_spa_shell(response.text):
            return clean_html(response.text)

        if response.status_code in (404, 410):
            logger.info("Got %d for %s, trying common event paths...", response.status_code, url)
            for fallback_url in _build_fallback_urls(url):
                try:
                    resp = await client.get(fallback_url, timeout=10)
                    if resp.status_code == 200 and not _looks_like_spa_shell(resp.text):
                        logger.info("Found working URL: %s", fallback_url)
                        return clean_html(resp.text)
                except (httpx.HTTPError, httpx.TimeoutException):
                    continue

        return None


async def scrape_browser(url: str) -> str:
    """Fetch a URL using a headless browser for JS-rendered content."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise ImportError(
            "Playwright not installed. Run: pip install concert-scraper[browser] && playwright install chromium"
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30_000)
        content = await page.content()
        await browser.close()
    return clean_html(content)


async def scrape(url: str, requires_browser: bool = False) -> str:
    """Scrape a venue URL. Uses fast HTTP by default, falling back to browser.

    Args:
        url: The URL to scrape.
        requires_browser: If True, skip HTTP and go straight to browser.

    Returns:
        Cleaned markdown text of the page content.

    Raises:
        RuntimeError: If both methods fail.
    """
    if requires_browser:
        return await scrape_browser(url)

    result = await scrape_fast(url)
    if result is not None:
        return result

    try:
        return await scrape_browser(url)
    except ImportError:
        raise RuntimeError(
            f"Fast HTTP returned an SPA shell for {url} and Playwright is not installed.\n"
            "Run: pip install concert-scraper[browser] && playwright install chromium"
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to scrape {url}: {exc}") from exc
