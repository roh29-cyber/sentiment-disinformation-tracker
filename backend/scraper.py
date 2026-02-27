import os
import requests
from bs4 import BeautifulSoup
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ─── Firecrawl (primary scraper when API key available) ──────────────────────

def scrape_with_firecrawl(url: str) -> str:
    """Scrape page content using Firecrawl API — returns clean markdown/text."""
    if not FIRECRAWL_API_KEY:
        return ""
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        result = app.scrape_url(url, params={
            "formats": ["markdown"],
            "onlyMainContent": True,
            "timeout": 30000,
        })
        # result is a dict with 'markdown' key
        text = ""
        if isinstance(result, dict):
            text = result.get("markdown", "") or result.get("content", "") or ""
        elif hasattr(result, "markdown"):
            text = result.markdown or ""
        if text:
            logger.info(f"Firecrawl scraped {url}: {len(text)} chars")
        return text
    except Exception as e:
        logger.warning(f"Firecrawl scrape failed for {url}: {e}")
        return ""


# ─── Fallback scrapers ───────────────────────────────────────────────────────

def scrape_with_requests(url: str, timeout: int = 10) -> str:
    """Scrape page content using requests + BeautifulSoup."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Remove script/style tags
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Extract meaningful text
        text = soup.get_text(separator=" ", strip=True)
        text = " ".join(text.split())
        return text
    except Exception as e:
        logger.warning(f"requests scrape failed for {url}: {e}")
        return ""


def scrape_with_playwright(url: str) -> str:
    """Fallback scraper using Playwright for JS-heavy sites."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)
            content = page.content()
            browser.close()

        soup = BeautifulSoup(content, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = " ".join(text.split())
        return text
    except Exception as e:
        logger.warning(f"Playwright scrape failed for {url}: {e}")
        return ""


# ─── Main entry point ────────────────────────────────────────────────────────

def scrape_url(url: str) -> str:
    """Scrape a URL using Firecrawl first, then BS4, then Playwright."""
    # 1. Firecrawl (best quality — clean markdown, handles JS)
    if FIRECRAWL_API_KEY:
        text = scrape_with_firecrawl(url)
        if text and len(text) > 100:
            return text[:15000]

    # 2. Requests + BeautifulSoup (fast, free)
    text = scrape_with_requests(url)
    if text and len(text) > 100:
        return text[:15000]

    # 3. Playwright (last resort for JS-heavy sites)
    logger.info(f"Falling back to Playwright for {url}")
    text = scrape_with_playwright(url)
    return text[:15000]
