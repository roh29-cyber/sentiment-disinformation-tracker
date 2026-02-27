import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


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


def scrape_url(url: str) -> str:
    """Try BeautifulSoup first, fall back to Playwright if content is empty."""
    text = scrape_with_requests(url)
    if not text or len(text) < 100:
        logger.info(f"Falling back to Playwright for {url}")
        text = scrape_with_playwright(url)
    return text[:15000]  # Cap at 15k chars to avoid overload
