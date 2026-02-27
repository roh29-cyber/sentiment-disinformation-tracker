from urllib.parse import urlparse

TRUSTED_DOMAINS = {
    "bbc.com", "bbc.co.uk",
    "reuters.com",
    "nytimes.com",
    "theguardian.com",
    "apnews.com",
    "npr.org",
    "washingtonpost.com",
    "bloomberg.com",
    "economist.com",
    "ft.com",
    "wsj.com",
    "wikipedia.org",
    "britannica.com",
    "nature.com",
    "science.org",
    "who.int",
    "cdc.gov",
    "nih.gov",
    "gov.uk",
    "europa.eu",
    "un.org",
    "snopes.com",
    "factcheck.org",
    "politifact.com",
    "fullfact.org",
    "abc.net.au",
    "cbsnews.com",
    "nbcnews.com",
    "abcnews.go.com",
    "time.com",
    "newsweek.com",
    "theatlantic.com",
    "vox.com",
    "propublica.org",
    "statista.com",
    "pewresearch.org",
}

SEMI_TRUSTED_DOMAINS = {
    "medium.com",
    "substack.com",
    "forbes.com",
    "businessinsider.com",
    "techcrunch.com",
    "wired.com",
    "arstechnica.com",
    "thehill.com",
    "axios.com",
    "politico.com",
    "slate.com",
    "salon.com",
    "huffpost.com",
    "vice.com",
    "buzzfeednews.com",
    "cnn.com",
    "foxnews.com",
    "msnbc.com",
    "usatoday.com",
    "latimes.com",
    "nypost.com",
    "dailymail.co.uk",
}


def get_domain(url: str) -> str:
    """Extract root domain from URL."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        # Strip www.
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def score_domain_trust(url: str) -> float:
    """
    Assign a trust score (0.0 to 1.0) based on:
    - HTTPS usage
    - Known trusted domain list
    """
    score = 0.0
    parsed = urlparse(url)

    # HTTPS check
    if parsed.scheme == "https":
        score += 0.2

    domain = get_domain(url)

    # Check trusted domains (including subdomains)
    for trusted in TRUSTED_DOMAINS:
        if domain == trusted or domain.endswith("." + trusted):
            score += 0.8
            return min(score, 1.0)

    # Check semi-trusted domains
    for semi in SEMI_TRUSTED_DOMAINS:
        if domain == semi or domain.endswith("." + semi):
            score += 0.4
            return min(score, 1.0)

    # Unknown domain â small base score if HTTPS
    return min(score, 1.0)


def score_sources(urls: list[str]) -> float:
    """Average trust score across multiple source URLs."""
    if not urls:
        return 0.3
    scores = [score_domain_trust(url) for url in urls]
    return round(sum(scores) / len(scores), 3)
