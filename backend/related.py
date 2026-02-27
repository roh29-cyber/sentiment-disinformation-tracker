import os
import re
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

SERPER_URL = "https://google.serper.dev/search"
NEWS_API_URL = "https://newsapi.org/v2/everything"

FACT_CHECK_SITES = ["snopes.com", "factcheck.org", "politifact.com", "fullfact.org", "reuters.com/fact-check"]


# âââ Mock data helpers ââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def _mock_articles(query: str) -> list[dict]:
    return [
        {
            "title": f"Analysis: {query[:60]}",
            "url": "https://reuters.com/world/analysis",
            "source": "Reuters",
        },
        {
            "title": f"Report on {query[:50]} â What experts say",
            "url": "https://bbc.com/news/world",
            "source": "BBC News",
        },
        {
            "title": f"Breaking: {query[:55]} developments",
            "url": "https://apnews.com/article/sample",
            "source": "AP News",
        },
    ]


def _mock_fact_checks(query: str) -> list[dict]:
    return [
        {
            "title": f"Fact Check: Claims about {query[:50]}",
            "url": "https://snopes.com/fact-check/sample",
            "source": "Snopes",
        },
        {
            "title": f"PolitiFact: Is it true that {query[:45]}?",
            "url": "https://politifact.com/factchecks/sample",
            "source": "PolitiFact",
        },
    ]


# âââ Serper.dev integration âââââââââââââââââââââââââââââââââââââââââââââââââââ

def search_serper(query: str, num: int = 5) -> list[dict]:
    """Search Google via Serper.dev API."""
    if not SERPER_API_KEY or SERPER_API_KEY.startswith("mock"):
        logger.info("Using mock Serper data")
        return _mock_articles(query)

    try:
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {"q": query, "num": num}
        resp = requests.post(SERPER_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("organic", [])[:num]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "source": item.get("displayLink", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"Serper search failed: {e}")
        return _mock_articles(query)


def search_fact_checks(query: str) -> list[dict]:
    """Search for fact-check pages via Serper.dev."""
    if not SERPER_API_KEY or SERPER_API_KEY.startswith("mock"):
        return _mock_fact_checks(query)

    try:
        fc_query = f"fact check {query} site:snopes.com OR site:factcheck.org OR site:politifact.com OR site:fullfact.org"
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {"q": fc_query, "num": 5}
        resp = requests.post(SERPER_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("organic", [])[:5]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "source": item.get("displayLink", ""),
            })
        return results if results else _mock_fact_checks(query)
    except Exception as e:
        logger.warning(f"Fact-check search failed: {e}")
        return _mock_fact_checks(query)


# âââ NewsAPI integration ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def search_news(query: str, num: int = 5) -> list[dict]:
    """Fetch news articles from NewsAPI."""
    if not NEWS_API_KEY or NEWS_API_KEY.startswith("mock"):
        logger.info("Using mock NewsAPI data")
        return _mock_articles(query)

    try:
        params = {
            "q": query,
            "apiKey": NEWS_API_KEY,
            "pageSize": num,
            "language": "en",
            "sortBy": "relevancy",
        }
        resp = requests.get(NEWS_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for article in data.get("articles", [])[:num]:
            results.append({
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "source": article.get("source", {}).get("name", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"NewsAPI search failed: {e}")
        return _mock_articles(query)


# âââ Named Entity Recognition âââââââââââââââââââââââââââââââââââââââââââââââââ

def extract_entities_spacy(text: str) -> list[dict]:
    """Extract named entities using spaCy."""
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text[:5000])  # Limit for performance
        seen = set()
        entities = []
        type_map = {
            "PERSON": "PERSON",
            "ORG": "ORG",
            "GPE": "LOCATION",
            "LOC": "LOCATION",
            "FAC": "LOCATION",
        }
        for ent in doc.ents:
            if ent.label_ in type_map and ent.text not in seen:
                seen.add(ent.text)
                entities.append({
                    "name": ent.text,
                    "type": type_map[ent.label_],
                })
        return entities[:20]
    except Exception as e:
        logger.warning(f"spaCy NER failed: {e}")
        return extract_entities_regex(text)


def extract_entities_regex(text: str) -> list[dict]:
    """Fallback regex-based entity extraction."""
    # Match capitalized multi-word phrases (simple heuristic)
    pattern = r'\b([A-Z][a-z]+ (?:[A-Z][a-z]+ )*[A-Z][a-z]+|[A-Z]{2,})\b'
    matches = re.findall(pattern, text[:5000])
    seen = set()
    entities = []
    for match in matches:
        if match not in seen and len(match) > 2:
            seen.add(match)
            entities.append({"name": match, "type": "ORG"})
    return entities[:15]


def extract_entities(text: str) -> list[dict]:
    """Extract named entities, preferring spaCy with regex fallback."""
    return extract_entities_spacy(text)


# âââ Top-level related info fetcher ââââââââââââââââââââââââââââââââââââââââââ

def fetch_related_info(query: str, content: str) -> dict:
    """
    Fetch related articles, fact-checks, and entities.
    """
    # Combine Serper + NewsAPI results, deduplicate
    serper_articles = search_serper(query, num=5)
    news_articles = search_news(query, num=5)

    seen_urls = set()
    combined_articles = []
    for article in serper_articles + news_articles:
        url = article.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            combined_articles.append(article)

    articles = combined_articles[:5]
    fact_checks = search_fact_checks(query)[:5]
    entities = extract_entities(content)

    return {
        "articles": articles,
        "fact_checks": fact_checks,
        "entities": entities,
    }


def get_topic_urls(query: str, num: int = 5) -> list[str]:
    """Get top URLs for a text/topic query to scrape."""
    results = search_serper(query, num=num)
    return [r["url"] for r in results if r.get("url")]
