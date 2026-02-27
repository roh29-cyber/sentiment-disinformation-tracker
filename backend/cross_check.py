"""
Cross-platform fact verification module.

Extracts key claims from content, searches multiple platforms,
and identifies corrections when claims appear to be false or misleading.
"""

import os
import re
import html
import logging
import requests
from dotenv import load_dotenv

try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
except Exception:
    _nlp = None

load_dotenv()
logger = logging.getLogger(__name__)

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
SERPER_URL = "https://google.serper.dev/search"
NEWSAPI_URL = "https://newsapi.org/v2/everything"

# Platforms we cross-check against
PLATFORMS = {
    "google_search": "Google Search",
    "google_news": "Google News",
    "fact_check_sites": "Fact-Check Sites",
    "wikipedia": "Wikipedia",
}

FACT_CHECK_DOMAINS = [
    "snopes.com",
    "factcheck.org",
    "politifact.com",
    "fullfact.org",
    "reuters.com/fact-check",
    "apnews.com/hub/ap-fact-check",
]

# ─── Trusted source hierarchy (higher tier = more trust weight) ──────────────
# Tier 3 (highest): Government / official regulatory bodies
_TIER3_GOVT_DOMAINS = {
    "gov.in", "nic.in", "pib.gov.in",        # India govt
    ".gov", ".gov.uk", ".gov.au",             # US/UK/AU govt
    "who.int", "un.org", "worldbank.org",     # International orgs
    "sec.gov", "fda.gov", "cdc.gov",          # US agencies
    "sebi.gov.in", "rbi.org.in",              # Indian regulators
    "europa.eu",                               # EU
}

# Tier 2: Major wire services, fact-checkers, encyclopedias
_TIER2_TRUSTED_DOMAINS = {
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "snopes.com", "factcheck.org", "politifact.com", "fullfact.org",
    "wikipedia.org", "britannica.com",
    "nytimes.com", "theguardian.com", "washingtonpost.com",
    "thehindu.com", "ndtv.com", "indianexpress.com",
    "nature.com", "sciencedirect.com", "pubmed.ncbi.nlm.nih.gov",
}

# Tier 1: Other known news outlets
_TIER1_NEWS_DOMAINS = {
    "cnn.com", "aljazeera.com", "dw.com", "france24.com",
    "timesofindia.indiatimes.com", "hindustantimes.com",
    "livemint.com", "moneycontrol.com", "economictimes.indiatimes.com",
    "cnbc.com", "bloomberg.com", "forbes.com",
}


def _get_source_tier(url: str) -> int:
    """Return trust tier for a URL: 3=govt/official, 2=trusted, 1=news, 0=other."""
    url_lower = url.lower()
    for domain in _TIER3_GOVT_DOMAINS:
        if domain in url_lower:
            return 3
    for domain in _TIER2_TRUSTED_DOMAINS:
        if domain in url_lower:
            return 2
    for domain in _TIER1_NEWS_DOMAINS:
        if domain in url_lower:
            return 1
    return 0


def _get_trust_weight(tier: int) -> float:
    """Return score multiplier for a source tier."""
    return {3: 3.0, 2: 2.0, 1: 1.5, 0: 1.0}.get(tier, 1.0)


def _tier_label(tier: int) -> str:
    return {3: "Official/Govt", 2: "Trusted", 1: "News", 0: "Other"}.get(tier, "Other")


# ─── Organization detection & official site lookup ───────────────────────────

def _extract_org_names(text: str) -> list[str]:
    """Extract organization names from text using spaCy NER or keyword fallback."""
    orgs: list[str] = []
    if _nlp:
        doc = _nlp(text)
        orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
        if not orgs:
            doc2 = _nlp(text.title())
            orgs = [ent.text for ent in doc2.ents if ent.label_ == "ORG"]
    return list(dict.fromkeys(orgs))  # dedupe, preserve order


def _find_official_website(entity_name: str) -> str | None:
    """Use Wikipedia to find the official website of a company/org."""
    try:
        # Search Wikipedia for the entity
        params = {
            "action": "query", "list": "search",
            "srsearch": entity_name, "format": "json",
            "srlimit": 1,
        }
        headers = {"User-Agent": "NarrativeRiskDetector/1.0 (educational project)"}
        resp = requests.get("https://en.wikipedia.org/w/api.php",
                            params=params, headers=headers, timeout=8)
        resp.raise_for_status()
        results = resp.json().get("query", {}).get("search", [])
        if not results:
            return None

        title = results[0]["title"]

        # Get the Wikidata ID to look for official website (P856)
        params2 = {
            "action": "query", "titles": title,
            "prop": "pageprops", "ppprop": "wikibase_item", "format": "json",
        }
        resp2 = requests.get("https://en.wikipedia.org/w/api.php",
                             params=params2, headers=headers, timeout=8)
        resp2.raise_for_status()
        pages = resp2.json().get("query", {}).get("pages", {})
        qid = None
        for page in pages.values():
            qid = page.get("pageprops", {}).get("wikibase_item")
        if not qid:
            return None

        wd_resp = requests.get(
            f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json",
            headers=headers, timeout=8,
        )
        wd_resp.raise_for_status()
        entity = wd_resp.json().get("entities", {}).get(qid, {})
        claims = entity.get("claims", {})

        # P856 = official website
        for claim in claims.get("P856", []):
            url = claim.get("mainsnak", {}).get("datavalue", {}).get("value", "")
            if url:
                logger.info(f"Official website for '{entity_name}': {url}")
                return url
    except Exception as e:
        logger.warning(f"Official site lookup failed for '{entity_name}': {e}")
    return None


def _search_newsapi(query: str, page_size: int = 5) -> list[dict]:
    """Search NewsAPI /everything endpoint for recent news articles.
    This is the PRIMARY search source — NewsAPI aggregates data from 150k+
    news sources worldwide, giving us pre-crawled, structured content."""
    if not NEWS_API_KEY or NEWS_API_KEY.startswith("mock"):
        return []
    try:
        params = {
            "q": query,
            "pageSize": page_size,
            "sortBy": "relevancy",
            "language": "en",
            "apiKey": NEWS_API_KEY,
        }
        resp = requests.get(NEWSAPI_URL, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for article in data.get("articles", [])[:page_size]:
            source_name = article.get("source", {}).get("name", "")
            title = article.get("title", "") or ""
            description = article.get("description", "") or ""
            content = article.get("content", "") or ""
            snippet = description if description else content[:300]
            url = article.get("url", "")

            # Determine trust tier based on source
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lstrip("www.").lower() if url else ""
            tier = _get_source_tier(domain)
            trust_label = {3: "Official/Govt", 2: "Trusted Media", 1: "News"}.get(tier, "News")

            results.append({
                "platform": f"NewsAPI ({trust_label})",
                "title": title,
                "snippet": snippet,
                "url": url,
                "source": source_name,
                "trust_tier": tier,
            })
        logger.info(f"NewsAPI returned {len(results)} results for '{query}'")
        return results
    except Exception as e:
        logger.warning(f"NewsAPI search failed: {e}")
        return []


def _search_official_site(query: str, official_url: str) -> list[dict]:
    """Search within an official website using Serper site: filter."""
    if not SERPER_API_KEY or SERPER_API_KEY.startswith("mock"):
        return []
    try:
        from urllib.parse import urlparse
        domain = urlparse(official_url).netloc.lstrip("www.")
        site_query = f"site:{domain} {query}"
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        resp = requests.post(SERPER_URL, json={"q": site_query, "num": 3},
                             headers=headers, timeout=10)
        resp.raise_for_status()
        results = []
        for item in resp.json().get("organic", [])[:3]:
            results.append({
                "platform": f"Official Site ({domain})",
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", ""),
                "source": domain,
                "trust_tier": 3,  # Official = highest tier
            })
        return results
    except Exception as e:
        logger.warning(f"Official site search failed for {official_url}: {e}")
        return []


def _search_govt_sites(query: str) -> list[dict]:
    """Search specifically on government and regulatory websites."""
    if not SERPER_API_KEY or SERPER_API_KEY.startswith("mock"):
        return []
    govt_domains = ["site:gov.in", "site:pib.gov.in", "site:.gov",
                    "site:who.int", "site:un.org"]
    site_filter = " OR ".join(govt_domains)
    try:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        resp = requests.post(SERPER_URL,
                             json={"q": f"{query} {site_filter}", "num": 5},
                             headers=headers, timeout=10)
        resp.raise_for_status()
        results = []
        for item in resp.json().get("organic", [])[:5]:
            results.append({
                "platform": "Government/Official",
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", ""),
                "source": item.get("displayLink", ""),
                "trust_tier": 3,
            })
        return results
    except Exception as e:
        logger.warning(f"Govt site search failed: {e}")
        return []

# Relationship / event keywords we look for in short queries
_RELATIONSHIP_WORDS = {
    "marriage", "married", "wedding", "engaged", "engagement",
    "husband", "wife", "spouse", "partner", "boyfriend", "girlfriend",
    "dating", "divorce", "divorced", "couple", "relationship",
    "affair", "breakup", "split", "marrage",
}

_EVENT_WORDS = {
    "died", "death", "dead", "killed", "arrested", "pregnant",
    "born", "accident", "resigned", "elected", "won", "lost",
    "award", "oscar", "grammy", "murdered", "assassination", "assassinated",
    "suicide", "passed", "rip",
}

_DEATH_WORDS = {
    "dead", "died", "death", "killed", "murdered", "assassination",
    "assassinated", "suicide", "passed", "rip",
}

# Role/position keywords — "X is CEO of Y" type claims
_ROLE_WORDS = {
    "ceo", "cto", "cfo", "coo", "founder", "cofounder", "co-founder",
    "president", "chairman", "chairperson", "director", "head",
    "manager", "owner", "chief", "lead", "leader",
    "minister", "secretary", "governor", "mayor", "commissioner",
    "captain", "coach", "principal", "dean",
}

# ─── Helper: extract person names ────────────────────────────────────────────

def _extract_person_names(text: str) -> list[str]:
    """Return a list of person names found in *text* using spaCy NER or regex fallback."""
    names: list[str] = []
    if _nlp:
        # Try with original text first
        doc = _nlp(text)
        names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
        # If nothing found, try title-cased version (handles lowercase input)
        if not names:
            doc2 = _nlp(text.title())
            names = [ent.text for ent in doc2.ents if ent.label_ == "PERSON"]
    if not names:
        # Regex fallback: capitalised multi-word tokens
        names = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text)
    if not names:
        # Last resort: try title case and look for capitalised single words
        # that are NOT common English words (likely proper nouns)
        _STOP = {
            "the", "a", "an", "is", "was", "are", "were", "with", "and", "or",
            "of", "in", "on", "at", "to", "for", "by", "from", "about", "that",
            "this", "it", "not", "but", "if", "has", "had", "have", "be", "been",
            "will", "would", "should", "could", "may", "might", "do", "does",
            "did", "who", "whom", "whose", "which", "what", "where", "when",
            "how", "why", "his", "her", "him", "she", "he", "they", "them",
            "we", "us", "you", "your", "my", "its", "our", "their",
            "marriage", "married", "wedding", "engaged", "engagement", "husband",
            "wife", "spouse", "partner", "boyfriend", "girlfriend", "dating",
            "divorce", "divorced", "couple", "relationship", "affair", "breakup",
            "died", "death", "dead", "killed", "arrested", "pregnant", "born",
            "accident", "resigned", "elected", "won", "lost", "award", "split",
            "marrage", "news", "real", "fake", "true", "false", "rumor", "rumour",
            "latest", "breaking", "update", "updates", "today", "yesterday",
            "report", "reports", "story", "stories", "video", "photo", "photos",
            "live", "watch", "new", "old", "big", "viral", "trending", "top",
            "best", "worst", "first", "last", "just", "now", "also", "very",
            "murder", "murdered", "suicide", "assassination", "assassinated",
            "passed", "rip", "ceo", "founder", "president", "chairman",
            "captain", "coach", "minister", "secretary", "governor",
        }
        words = text.split()
        for w in words:
            clean = re.sub(r"[^a-zA-Z']", "", w)
            if clean and clean.lower() not in _STOP and len(clean) >= 3:
                names.append(clean.title())
    # Deduplicate
    seen = set()
    unique = []
    for n in names:
        key = n.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(n.strip())
    return unique


def _is_relationship_or_event_claim(text: str) -> bool:
    """Return True if *text* mentions a relationship, notable event, or role/position."""
    words = set(re.findall(r'[a-z]+', text.lower()))
    return bool(words & (_RELATIONSHIP_WORDS | _EVENT_WORDS | _ROLE_WORDS))


# ─── Claim extraction ───────────────────────────────────────────────────────

def extract_claims(text: str, max_claims: int = 5) -> list[str]:
    """
    Extract key factual claims from text using heuristics.
    For short inputs that mention people + relationships/events,
    the whole input is treated as a claim.
    """
    text = text.strip()

    # --- Short input fast-path (typical user queries) ---
    if len(text) < 300:
        names = _extract_person_names(text)
        if names and _is_relationship_or_event_claim(text):
            return [text]
        # Even without event words, if there are 2+ person names assume a
        # relationship-type claim
        if len(names) >= 2:
            return [text]

    # --- Long text: sentence-level extraction ---
    sentences = re.split(r'(?<=[.!?])\s+', text)
    claims = []

    claim_indicators = [
        r'\d+',
        r'\b(according to|study|report|research|data|survey|found|showed|revealed)\b',
        r'\b(percent|million|billion|thousand|hundred)\b',
        r'\b(is|was|are|were|will be|has been|have been)\b.*\b(the|a)\b',
        r'\b(confirmed|denied|announced|stated|claimed|said)\b',
        r'\b(true|false|fake|real|hoax|myth|misleading|debunked)\b',
        r'\b(caused|causes|linked to|associated with|leads to|results in)\b',
        r'\b(first|largest|smallest|most|least|highest|lowest|best|worst)\b',
    ]

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 15 or len(sentence) > 300:
            continue

        score = 0
        for pattern in claim_indicators:
            if re.search(pattern, sentence, re.IGNORECASE):
                score += 1

        # Also count sentences with person names + event/relationship words
        if _extract_person_names(sentence) and _is_relationship_or_event_claim(sentence):
            score += 3  # strong boost

        if score >= 2:
            claims.append(sentence)

    # Deduplicate similar claims
    unique_claims = []
    for claim in claims:
        is_dup = False
        for existing in unique_claims:
            words_a = set(claim.lower().split())
            words_b = set(existing.lower().split())
            overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
            if overlap > 0.7:
                is_dup = True
                break
        if not is_dup:
            unique_claims.append(claim)

    # If nothing extracted, fall back to the whole text
    if not unique_claims:
        unique_claims = [text[:300]]

    return unique_claims[:max_claims]


# ─── Platform search functions ───────────────────────────────────────────────

def _search_serper_general(query: str, num: int = 5) -> list[dict]:
    """Search Google via Serper.dev and return results with snippets."""
    if not SERPER_API_KEY or SERPER_API_KEY.startswith("mock"):
        return []

    try:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        resp = requests.post(SERPER_URL, json={"q": query, "num": num}, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []

        # Knowledge graph (high authority)
        kg = data.get("knowledgeGraph", {})
        if kg.get("description"):
            results.append({
                "platform": "Google Knowledge Graph",
                "title": kg.get("title", ""),
                "snippet": kg["description"],
                "url": kg.get("descriptionLink", kg.get("website", "")),
                "source": kg.get("descriptionSource", "Google"),
            })

        # Organic results
        for item in data.get("organic", [])[:num]:
            results.append({
                "platform": "Google Search",
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", ""),
                "source": item.get("displayLink", ""),
            })

        # Answer box
        ab = data.get("answerBox", {})
        if ab.get("answer") or ab.get("snippet"):
            results.insert(0, {
                "platform": "Google Answer Box",
                "title": ab.get("title", "Direct Answer"),
                "snippet": ab.get("answer") or ab.get("snippet", ""),
                "url": ab.get("link", ""),
                "source": ab.get("displayLink", "Google"),
            })

        return results
    except Exception as e:
        logger.warning(f"Serper general search failed: {e}")
        return []


def _search_serper_news(query: str, num: int = 3) -> list[dict]:
    """Search Google News via Serper.dev."""
    if not SERPER_API_KEY or SERPER_API_KEY.startswith("mock"):
        return []

    try:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        resp = requests.post(
            "https://google.serper.dev/news",
            json={"q": query, "num": num},
            headers=headers, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("news", [])[:num]:
            results.append({
                "platform": "Google News",
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", ""),
                "source": item.get("source", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"Serper news search failed: {e}")
        return []


def _search_fact_check_sites(query: str) -> list[dict]:
    """Search specifically on fact-check websites."""
    if not SERPER_API_KEY or SERPER_API_KEY.startswith("mock"):
        return []

    site_filter = " OR ".join(f"site:{d}" for d in FACT_CHECK_DOMAINS)
    fc_query = f"{query} {site_filter}"

    try:
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        resp = requests.post(SERPER_URL, json={"q": fc_query, "num": 5}, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("organic", [])[:5]:
            results.append({
                "platform": "Fact-Check Site",
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", ""),
                "source": item.get("displayLink", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"Fact-check site search failed: {e}")
        return []


def _search_wikipedia(query: str) -> list[dict]:
    """Search Wikipedia API for relevant information."""
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 3,
            "srprop": "snippet",
        }
        headers = {
            "User-Agent": "NarrativeRiskDetector/1.0 (educational project)"
        }
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params=params, headers=headers, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("query", {}).get("search", []):
            snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
            snippet = html.unescape(snippet)
            results.append({
                "platform": "Wikipedia",
                "title": item.get("title", ""),
                "snippet": snippet,
                "url": f"https://en.wikipedia.org/wiki/{item['title'].replace(' ', '_')}",
                "source": "Wikipedia",
            })
        return results
    except Exception as e:
        logger.warning(f"Wikipedia search failed: {e}")
        return []


def _search_person_wikipedia(person_names: list[str]) -> list[dict]:
    """Search Wikipedia directly for each person's page.
    Unlike _search_wikipedia (which searches the full claim text and may match
    unrelated pages like movies), this searches for each person name individually
    and fetches the first few paragraphs of their article.
    Returns enriched source dicts with full extract snippets.
    """
    results = []
    seen_titles: set[str] = set()
    for name in person_names:
        wiki_hits = _search_wikipedia(name)
        if not wiki_hits:
            continue
        best = wiki_hits[0]
        title = best["title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)
        # Fetch the article extract to get real content about the person
        extract = _get_wikipedia_extract(title, 4000)
        results.append({
            "platform": "Wikipedia",
            "title": title,
            "url": best["url"],
            "source": "Wikipedia",
            "snippet": extract[:500] if extract else best["snippet"],
            "stance": "neutral",
        })
        logger.info(f"Person-Wikipedia: '{name}' -> article '{title}'")
    return results


def _get_wikipedia_extract(title: str, chars: int = 3000) -> str:
    """Fetch the plain-text extract of a Wikipedia article (first ~chars characters)."""
    try:
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "exintro": False,
            "explaintext": True,
            "exchars": chars,
            "format": "json",
        }
        headers = {"User-Agent": "NarrativeRiskDetector/1.0 (educational project)"}
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params=params, headers=headers, timeout=10,
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            return page.get("extract", "")
    except Exception as e:
        logger.warning(f"Wikipedia extract fetch failed for '{title}': {e}")
    return ""


def _get_wikidata_spouse(title: str) -> list[str]:
    """Try to get spouse/partner names from Wikidata for a Wikipedia article title."""
    try:
        # First resolve title -> wikidata id
        params = {
            "action": "query",
            "titles": title,
            "prop": "pageprops",
            "ppprop": "wikibase_item",
            "format": "json",
        }
        headers = {"User-Agent": "NarrativeRiskDetector/1.0 (educational project)"}
        resp = requests.get("https://en.wikipedia.org/w/api.php",
                            params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        qid = None
        for page in pages.values():
            qid = page.get("pageprops", {}).get("wikibase_item")
        if not qid:
            return []

        # Fetch Wikidata entity
        wd_resp = requests.get(
            f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json",
            headers=headers, timeout=10,
        )
        wd_resp.raise_for_status()
        entity = wd_resp.json().get("entities", {}).get(qid, {})
        claims = entity.get("claims", {})

        # P26 = spouse, P451 = partner
        spouse_ids = []
        for prop in ("P26", "P451"):
            for claim in claims.get(prop, []):
                ms = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
                sid = ms.get("id")
                if sid:
                    spouse_ids.append(sid)

        # Resolve QIDs to labels
        names = []
        for sid in spouse_ids:
            try:
                lr = requests.get(
                    f"https://www.wikidata.org/wiki/Special:EntityData/{sid}.json",
                    headers=headers, timeout=8,
                )
                lr.raise_for_status()
                label = (lr.json().get("entities", {}).get(sid, {})
                         .get("labels", {}).get("en", {}).get("value", ""))
                if label:
                    names.append(label)
            except Exception:
                pass
        return names
    except Exception as e:
        logger.warning(f"Wikidata spouse lookup failed for '{title}': {e}")
        return []


def _get_wikidata_death_date(title: str) -> str | None:
    """Check Wikidata for date of death (P570). Returns date string or None if alive."""
    try:
        params = {
            "action": "query", "titles": title,
            "prop": "pageprops", "ppprop": "wikibase_item", "format": "json",
        }
        headers = {"User-Agent": "NarrativeRiskDetector/1.0 (educational project)"}
        resp = requests.get("https://en.wikipedia.org/w/api.php",
                            params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        qid = None
        for page in pages.values():
            qid = page.get("pageprops", {}).get("wikibase_item")
        if not qid:
            return None

        wd_resp = requests.get(
            f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json",
            headers=headers, timeout=10,
        )
        wd_resp.raise_for_status()
        entity = wd_resp.json().get("entities", {}).get(qid, {})
        claims = entity.get("claims", {})

        # P570 = date of death
        for claim in claims.get("P570", []):
            time_val = (claim.get("mainsnak", {})
                        .get("datavalue", {})
                        .get("value", {})
                        .get("time", ""))
            if time_val:
                # Format: "+1945-04-30T00:00:00Z" -> "1945-04-30"
                cleaned = time_val.lstrip("+").split("T")[0]
                return cleaned
        return None  # No death date -> person is alive
    except Exception as e:
        logger.warning(f"Wikidata death-date lookup failed for '{title}': {e}")
        return None


# ─── Entity-aware fact checking ──────────────────────────────────────────────

def _verify_person_claim(claim: str, person_names: list[str]) -> dict | None:
    """
    For claims involving people (marriage, death, etc.), look up each person
    on Wikipedia / Wikidata and compare the real facts with the claim.
    Returns a fully-formed claim result dict or None if we can't determine.
    """
    if not person_names:
        return None

    claim_lower = claim.lower()
    claim_words = set(re.findall(r'[a-z]+', claim_lower))
    is_relationship = bool(claim_words & _RELATIONSHIP_WORDS)
    is_death_claim = bool(claim_words & _DEATH_WORDS)

    all_sources: list[dict] = []
    real_facts: list[str] = []          # facts gathered from Wikipedia/Wikidata
    contradicts_claim = False
    corrected_info_parts: list[str] = []

    for name in person_names:
        # Search Wikipedia for the person
        wiki_results = _search_wikipedia(name)
        if not wiki_results:
            continue

        best_title = wiki_results[0]["title"]
        extract = _get_wikipedia_extract(best_title, 4000)
        url = wiki_results[0]["url"]

        all_sources.append({
            "platform": "Wikipedia",
            "title": best_title,
            "url": url,
            "source": "Wikipedia",
            "snippet": extract[:400] if extract else wiki_results[0]["snippet"],
            "stance": "neutral",
        })

        if is_death_claim:
            # Check Wikidata for death date (P570)
            death_date = _get_wikidata_death_date(best_title)
            logger.info(f"Wikidata death date for {best_title}: {death_date}")

            if death_date:
                # Person IS dead — claim is true
                real_facts.append(f"According to Wikidata, {best_title} died on {death_date}.")
                # Don't set contradicts_claim — this supports it
            else:
                # No death date — person is ALIVE — claim is false
                contradicts_claim = True
                corrected_info_parts.append(
                    f"{best_title} is NOT dead. According to Wikidata, there is no date of death recorded. "
                    f"{best_title} is alive as of the latest available data."
                )

        elif is_relationship:
            # Check Wikidata for actual spouse
            spouses = _get_wikidata_spouse(best_title)
            logger.info(f"Wikidata spouses for {best_title}: {spouses}")

            if spouses:
                real_facts.append(f"According to Wikipedia/Wikidata, {best_title}'s spouse(s): {', '.join(spouses)}.")

                # Check whether the OTHER person name(s) in the claim appear among real spouses
                other_names = [n for n in person_names if n.lower() != name.lower()]
                for other in other_names:
                    matched = any(
                        other.lower() in s.lower() or s.lower() in other.lower()
                        for s in spouses
                    )
                    if not matched:
                        contradicts_claim = True
                        corrected_info_parts.append(
                            f"{best_title} is NOT married to / in a relationship with {other}. "
                            f"According to Wikidata, {best_title}'s known spouse(s): {', '.join(spouses)}."
                        )
            else:
                # No spouse listed; check the extract for relationship keywords
                extract_lower = extract.lower() if extract else ""
                other_names = [n for n in person_names if n.lower() != name.lower()]
                for other in other_names:
                    if other.lower() not in extract_lower:
                        # The other person isn't even mentioned
                        contradicts_claim = True
                        corrected_info_parts.append(
                            f"There is no verified information linking {best_title} to {other} "
                            f"in a romantic relationship or marriage. "
                            f"This claim could not be confirmed via Wikipedia or Wikidata."
                        )
        else:
            # Non-relationship claim – check extract for contradiction keywords
            extract_lower = (extract or "").lower()
            for kw in ("not true", "false", "hoax", "debunked", "no evidence", "fake"):
                if kw in extract_lower:
                    contradicts_claim = True
                    corrected_info_parts.append(f"Wikipedia article on {best_title} mentions: '{kw}'.")
                    break

    if not all_sources:
        return None  # couldn't find anything

    # Determine verdict
    if contradicts_claim:
        verdict = "likely_false"
        confidence = 0.85
        for s in all_sources:
            s["stance"] = "contradicts"
    elif real_facts:
        verdict = "likely_true"
        confidence = 0.7
        for s in all_sources:
            s["stance"] = "supports"
    else:
        verdict = "unverified"
        confidence = 0.3

    corrected_info = " ".join(corrected_info_parts)[:600] if corrected_info_parts else None
    if real_facts and not corrected_info:
        corrected_info = " ".join(real_facts)[:600]

    return {
        "claim": claim,
        "verdict": verdict,
        "confidence": round(confidence, 2),
        "corrected_info": corrected_info,
        "sources": all_sources[:8],
    }


# ─── Organization-role claim verification ────────────────────────────────────

def _get_wikidata_leaders(title: str) -> list[dict]:
    """Get CEO/chairman/head of an org from Wikidata.
    Returns list of {role, name} dicts."""
    try:
        params = {
            "action": "query", "titles": title,
            "prop": "pageprops", "ppprop": "wikibase_item", "format": "json",
        }
        headers = {"User-Agent": "NarrativeRiskDetector/1.0 (educational project)"}
        resp = requests.get("https://en.wikipedia.org/w/api.php",
                            params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
        qid = None
        for page in pages.values():
            qid = page.get("pageprops", {}).get("wikibase_item")
        if not qid:
            return []

        wd_resp = requests.get(
            f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json",
            headers=headers, timeout=10,
        )
        wd_resp.raise_for_status()
        entity = wd_resp.json().get("entities", {}).get(qid, {})
        claims_data = entity.get("claims", {})

        # Wikidata properties for leadership:
        # P169 = CEO, P488 = chairperson, P35 = head of state,
        # P6 = head of government, P112 = founder
        role_props = {
            "P169": "CEO",
            "P488": "Chairperson",
            "P35": "Head of State",
            "P6": "Head of Government",
            "P112": "Founder",
        }

        leaders = []
        for prop, role_name in role_props.items():
            for claim_item in claims_data.get(prop, []):
                ms = claim_item.get("mainsnak", {}).get("datavalue", {}).get("value", {})
                person_qid = ms.get("id")
                if not person_qid:
                    continue
                try:
                    lr = requests.get(
                        f"https://www.wikidata.org/wiki/Special:EntityData/{person_qid}.json",
                        headers=headers, timeout=8,
                    )
                    lr.raise_for_status()
                    label = (lr.json().get("entities", {}).get(person_qid, {})
                             .get("labels", {}).get("en", {}).get("value", ""))
                    if label:
                        leaders.append({"role": role_name, "name": label})
                except Exception:
                    pass
        return leaders
    except Exception as e:
        logger.warning(f"Wikidata leader lookup failed for '{title}': {e}")
        return []


def _verify_org_role_claim(claim: str, person_names: list[str], org_names: list[str]) -> dict | None:
    """
    Verify claims like 'X is CEO of Y' by checking Wikidata for org leadership.
    Returns a fully-formed claim result dict or None.
    """
    if not person_names or not org_names:
        return None

    claim_lower = claim.lower()
    has_role_word = bool(set(re.findall(r'[a-z]+', claim_lower)) & _ROLE_WORDS)
    if not has_role_word:
        return None

    all_sources: list[dict] = []
    real_facts: list[str] = []
    contradicts_claim = False
    corrected_info_parts: list[str] = []

    for org in org_names:
        # Search with "company" / "organization" suffix to disambiguate
        # (e.g., "Tesla" -> "Tesla company" to avoid "Nikola Tesla")
        wiki_results = _search_wikipedia(f"{org} company")
        if not wiki_results:
            wiki_results = _search_wikipedia(f"{org} organization")
        if not wiki_results:
            wiki_results = _search_wikipedia(org)
        if not wiki_results:
            continue

        best_title = wiki_results[0]["title"]
        extract = _get_wikipedia_extract(best_title, 4000)
        url = wiki_results[0]["url"]

        all_sources.append({
            "platform": "Wikipedia",
            "title": best_title,
            "url": url,
            "source": "Wikipedia",
            "snippet": extract[:400] if extract else wiki_results[0]["snippet"],
            "stance": "neutral",
        })

        # Get actual leaders from Wikidata
        leaders = _get_wikidata_leaders(best_title)
        logger.info(f"Wikidata leaders for {best_title}: {leaders}")

        if leaders:
            leader_strs = [f"{l['role']}: {l['name']}" for l in leaders]
            real_facts.append(
                f"According to Wikidata, {best_title} leadership: {', '.join(leader_strs)}."
            )

            # Check if claimed person actually holds a role
            leader_names_lower = [l["name"].lower() for l in leaders]
            for person in person_names:
                matched = any(
                    person.lower() in ln or ln in person.lower()
                    for ln in leader_names_lower
                )
                if not matched:
                    contradicts_claim = True
                    corrected_info_parts.append(
                        f"{person} is NOT a known leader of {best_title}. "
                        f"According to Wikidata: {', '.join(leader_strs)}."
                    )
        else:
            extract_lower = (extract or "").lower()
            for person in person_names:
                if person.lower() not in extract_lower:
                    contradicts_claim = True
                    corrected_info_parts.append(
                        f"No verified information linking {person} to a leadership "
                        f"role at {best_title}."
                    )

    if not all_sources:
        return None

    if contradicts_claim:
        verdict = "likely_false"
        confidence = 0.85
        for s in all_sources:
            s["stance"] = "contradicts"
    elif real_facts:
        verdict = "likely_true"
        confidence = 0.7
        for s in all_sources:
            s["stance"] = "supports"
    else:
        verdict = "unverified"
        confidence = 0.3

    corrected_info = " ".join(corrected_info_parts)[:600] if corrected_info_parts else None
    if real_facts and not corrected_info:
        corrected_info = " ".join(real_facts)[:600]

    return {
        "claim": claim,
        "verdict": verdict,
        "confidence": round(confidence, 2),
        "corrected_info": corrected_info,
        "sources": all_sources[:8],
    }


# ─── Verdict analysis ────────────────────────────────────────────────────────

def _analyze_claim_against_sources(claim: str, sources: list[dict]) -> dict:
    """
    Analyze whether sources support, contradict, or are inconclusive about a claim.
    Returns a verdict with corrected info if applicable.
    """
    if not sources:
        return {
            "claim": claim,
            "verdict": "unverified",
            "confidence": 0.0,
            "corrected_info": None,
            "sources": [],
        }

    contradiction_keywords = [
        "false", "fake", "hoax", "myth", "debunked", "misleading",
        "incorrect", "inaccurate", "not true", "no evidence",
        "disproven", "baseless", "unfounded", "fabricated",
        "pants on fire", "mostly false", "partly false",
        "misinformation", "disinformation", "conspiracy",
    ]

    support_keywords = [
        "true", "confirmed", "verified", "accurate", "correct",
        "evidence supports", "mostly true", "fact", "proven",
    ]

    contradiction_score = 0.0
    support_score = 0.0
    correction_snippets = []
    relevant_sources = []

    # Sort sources so highest-tier (govt/official) are evaluated first
    sources_sorted = sorted(sources, key=lambda s: s.get("trust_tier", _get_source_tier(s.get("url", ""))), reverse=True)

    for src in sources_sorted:
        snippet_lower = (src.get("snippet", "") + " " + src.get("title", "")).lower()
        url = src.get("url", "")
        tier = src.get("trust_tier", _get_source_tier(url))
        weight = _get_trust_weight(tier)

        is_contradiction = False
        is_support = False

        for kw in contradiction_keywords:
            if kw in snippet_lower:
                contradiction_score += weight
                is_contradiction = True
                break

        for kw in support_keywords:
            if kw in snippet_lower:
                support_score += weight
                is_support = True
                break

        tier_tag = _tier_label(tier)
        base_entry = {
            "platform": src["platform"],
            "title": src.get("title", ""),
            "url": url,
            "source": src.get("source", ""),
            "snippet": src.get("snippet", ""),
            "trust_tier": tier_tag,
        }

        if is_contradiction:
            correction_snippets.append((tier, src.get("snippet", "")))
            relevant_sources.append({**base_entry, "stance": "contradicts"})
        elif is_support:
            relevant_sources.append({**base_entry, "stance": "supports"})
        else:
            relevant_sources.append({**base_entry, "stance": "neutral"})

    total = contradiction_score + support_score
    if total == 0:
        verdict = "unverified"
        confidence = 0.3
    elif contradiction_score > support_score:
        verdict = "likely_false"
        confidence = min(contradiction_score / max(total, 1), 1.0)
    elif support_score > contradiction_score:
        verdict = "likely_true"
        confidence = min(support_score / max(total, 1), 1.0)
    else:
        verdict = "disputed"
        confidence = 0.5

    # Build corrected info — prioritize snippets from higher-tier sources
    corrected_info = None
    if verdict in ("likely_false", "disputed") and correction_snippets:
        correction_snippets.sort(key=lambda x: x[0], reverse=True)  # highest tier first
        corrected_info = " ".join(s for _, s in correction_snippets[:2])[:500]

    return {
        "claim": claim,
        "verdict": verdict,
        "confidence": round(confidence, 2),
        "corrected_info": corrected_info,
        "sources": relevant_sources[:8],
    }


# ─── Mock data for when no API key is available ──────────────────────────────

def _mock_cross_check(claims: list[str]) -> list[dict]:
    """Generate mock cross-check results for demo purposes."""
    results = []
    for claim in claims:
        results.append({
            "claim": claim,
            "verdict": "unverified",
            "confidence": 0.4,
            "corrected_info": None,
            "sources": [
                {
                    "platform": "Google Search",
                    "title": f"Related: {claim[:50]}...",
                    "url": "https://www.google.com/search?q=" + claim[:30].replace(" ", "+"),
                    "source": "Google",
                    "snippet": "Multiple sources discuss this topic. Cross-reference with trusted sources for verification.",
                    "stance": "neutral",
                },
                {
                    "platform": "Wikipedia",
                    "title": f"Background on {claim[:40]}",
                    "url": "https://en.wikipedia.org",
                    "source": "Wikipedia",
                    "snippet": "This topic has been covered in various publications. Check primary sources for accuracy.",
                    "stance": "neutral",
                },
            ],
        })
    return results


# ─── Main cross-check function ──────────────────────────────────────────────

def cross_check_content(content: str, query: str) -> dict:
    """
    Cross-check content claims across multiple platforms.

    Returns:
        {
            "claims_checked": int,
            "claims": [
                {
                    "claim": str,
                    "verdict": "likely_true" | "likely_false" | "disputed" | "unverified",
                    "confidence": float,
                    "corrected_info": str | None,
                    "sources": [
                        {
                            "platform": str,
                            "title": str,
                            "url": str,
                            "source": str,
                            "snippet": str,
                            "stance": "supports" | "contradicts" | "neutral",
                        }
                    ],
                }
            ],
            "platforms_searched": [str],
            "overall_reliability": "reliable" | "questionable" | "unreliable" | "insufficient_data",
        }
    """
    # Step 1: Extract claims.
    # PRIORITY: if the user's *query* itself looks like a person+relationship/event
    # claim, always use it as the primary claim — the scraped content is just
    # background and should NOT replace the user's assertion.
    query_names = _extract_person_names(query)
    query_is_claim = bool(query_names) and _is_relationship_or_event_claim(query)

    if query_is_claim:
        claims = [query.strip()[:300]]
        logger.info(f"User query IS the claim (persons={query_names}): '{claims[0]}'")
    else:
        claims = extract_claims(content)
        if not claims:
            claims = [query[:200]]

    logger.info(f"Extracted {len(claims)} claims to cross-check")

    # Step 2: Check if we have API access
    has_api = SERPER_API_KEY and not SERPER_API_KEY.startswith("mock")
    platforms_searched = ["Wikipedia", "Wikidata"]

    # Detect organizations in the query for official-site lookups
    org_names = _extract_org_names(query)
    official_sites: dict[str, str] = {}  # org_name -> official_url
    for org in org_names:
        url = _find_official_website(org)
        if url:
            official_sites[org] = url
            if "Official Sites" not in platforms_searched:
                platforms_searched.append("Official Sites")
    logger.info(f"Orgs detected: {org_names}, official sites: {official_sites}")

    checked_claims = []
    for claim in claims:
        # --- Try entity-aware person verification FIRST ---
        person_names = _extract_person_names(claim)
        if not person_names and query_is_claim:
            person_names = query_names  # use names from the original query

        # Detect orgs in this specific claim too
        claim_orgs = _extract_org_names(claim)
        if not claim_orgs:
            claim_orgs = org_names  # fall back to orgs from the query

        if person_names and _is_relationship_or_event_claim(claim):
            logger.info(f"Person-claim detected: names={person_names}, claim='{claim}'")

            # Try org-role verification (e.g. "X is CEO of Y")
            if claim_orgs:
                role_words = set(re.findall(r'[a-z]+', claim.lower())) & _ROLE_WORDS
                if role_words:
                    logger.info(f"Org-role claim: persons={person_names}, orgs={claim_orgs}")
                    org_result = _verify_org_role_claim(claim, person_names, claim_orgs)
                    if org_result and org_result["verdict"] != "unverified":
                        checked_claims.append(org_result)
                        continue

            # Try person-relationship verification (e.g. "X married Y")
            person_result = _verify_person_claim(claim, person_names)
            if person_result and person_result["verdict"] != "unverified":
                checked_claims.append(person_result)
                continue  # skip generic check – we got a definitive answer

        # --- Cross-check with SOURCE PRIORITY ---
        all_sources = []

        # PRIORITY 0: Person's own Wikipedia page (if persons detected)
        # Search each person's Wikipedia article directly — avoids matching
        # movies/songs/other unrelated pages that a generic search might return.
        effective_person_names = person_names or query_names
        if effective_person_names:
            person_wiki = _search_person_wikipedia(effective_person_names)
            all_sources.extend(person_wiki)
            logger.info(f"Person-Wikipedia results: {len(person_wiki)} for {effective_person_names}")

        # PRIORITY 1: NewsAPI (primary search — aggregates 150k+ sources)
        has_newsapi = NEWS_API_KEY and not NEWS_API_KEY.startswith("mock")
        if has_newsapi:
            newsapi_results = _search_newsapi(claim, page_size=5)
            all_sources.extend(newsapi_results)
            if newsapi_results and "NewsAPI" not in platforms_searched:
                platforms_searched.append("NewsAPI")

        # PRIORITY 2: Official company/org sites (if detected)
        for org, site_url in official_sites.items():
            if has_api:
                official_results = _search_official_site(claim, site_url)
                all_sources.extend(official_results)
                logger.info(f"Official site results for {org}: {len(official_results)}")

        # PRIORITY 3: Government / regulatory sites
        if has_api:
            govt_results = _search_govt_sites(claim)
            all_sources.extend(govt_results)
            if govt_results and "Government Sites" not in platforms_searched:
                platforms_searched.append("Government Sites")
            logger.info(f"Govt site results: {len(govt_results)}")

        # PRIORITY 4: Fact-check sites
        if has_api:
            fc_results = _search_fact_check_sites(claim)
            all_sources.extend(fc_results)
            if "Fact-Check Sites" not in platforms_searched:
                platforms_searched.append("Fact-Check Sites")

        # PRIORITY 5: Wikipedia / Wikidata generic search (always available)
        wiki_results = _search_wikipedia(claim)
        # Avoid duplicating person pages already fetched in priority 0
        existing_titles = {s["title"] for s in all_sources}
        wiki_results = [r for r in wiki_results if r["title"] not in existing_titles]
        all_sources.extend(wiki_results)

        # PRIORITY 6: General search & news via Serper (fallback)
        if has_api:
            if "Google Search" not in platforms_searched:
                platforms_searched.extend(["Google Search", "Google News"])
            all_sources.extend(_search_serper_general(claim, num=3))
            all_sources.extend(_search_serper_news(claim, num=2))

        if all_sources:
            result = _analyze_claim_against_sources(claim, all_sources)
        else:
            logger.info("No sources found; using mock data")
            result = _mock_cross_check([claim])[0]
        checked_claims.append(result)

    # Step 3: Compute overall reliability
    verdicts = [c["verdict"] for c in checked_claims]
    false_count = verdicts.count("likely_false") + verdicts.count("disputed")
    true_count = verdicts.count("likely_true")
    total = len(verdicts)

    if total == 0:
        overall = "insufficient_data"
    elif false_count > total / 2:
        overall = "unreliable"
    elif false_count > 0:
        overall = "questionable"
    elif true_count > total / 2:
        overall = "reliable"
    else:
        overall = "insufficient_data"

    return {
        "claims_checked": len(checked_claims),
        "claims": checked_claims,
        "platforms_searched": platforms_searched,
        "overall_reliability": overall,
    }
