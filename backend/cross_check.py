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
SERPER_URL = "https://google.serper.dev/search"

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
    "award", "oscar", "grammy",
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
    """Return True if *text* mentions a relationship or notable event."""
    words = set(re.findall(r'[a-z]+', text.lower()))
    return bool(words & (_RELATIONSHIP_WORDS | _EVENT_WORDS))


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
    is_relationship = bool(set(re.findall(r'[a-z]+', claim_lower)) & _RELATIONSHIP_WORDS)

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

        if is_relationship:
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

    contradiction_score = 0
    support_score = 0
    correction_snippets = []
    relevant_sources = []

    for src in sources:
        snippet_lower = (src.get("snippet", "") + " " + src.get("title", "")).lower()

        is_contradiction = False
        is_support = False

        for kw in contradiction_keywords:
            if kw in snippet_lower:
                contradiction_score += 1
                is_contradiction = True
                break

        for kw in support_keywords:
            if kw in snippet_lower:
                support_score += 1
                is_support = True
                break

        if is_contradiction:
            correction_snippets.append(src.get("snippet", ""))
            relevant_sources.append({
                "platform": src["platform"],
                "title": src.get("title", ""),
                "url": src.get("url", ""),
                "source": src.get("source", ""),
                "snippet": src.get("snippet", ""),
                "stance": "contradicts",
            })
        elif is_support:
            relevant_sources.append({
                "platform": src["platform"],
                "title": src.get("title", ""),
                "url": src.get("url", ""),
                "source": src.get("source", ""),
                "snippet": src.get("snippet", ""),
                "stance": "supports",
            })
        else:
            relevant_sources.append({
                "platform": src["platform"],
                "title": src.get("title", ""),
                "url": src.get("url", ""),
                "source": src.get("source", ""),
                "snippet": src.get("snippet", ""),
                "stance": "neutral",
            })

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

    # Build corrected info from the most relevant contradiction snippets
    corrected_info = None
    if verdict in ("likely_false", "disputed") and correction_snippets:
        corrected_info = " ".join(correction_snippets[:2])[:500]

    return {
        "claim": claim,
        "verdict": verdict,
        "confidence": round(confidence, 2),
        "corrected_info": corrected_info,
        "sources": relevant_sources[:6],
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

    checked_claims = []
    for claim in claims:
        # --- Try entity-aware person verification FIRST ---
        person_names = _extract_person_names(claim)
        if not person_names and query_is_claim:
            person_names = query_names  # use names from the original query
        if person_names and _is_relationship_or_event_claim(claim):
            logger.info(f"Person-claim detected: names={person_names}, claim='{claim}'")
            person_result = _verify_person_claim(claim, person_names)
            if person_result and person_result["verdict"] != "unverified":
                checked_claims.append(person_result)
                continue  # skip generic check – we got a definitive answer

        # --- Fall back to generic cross-check ---
        if has_api:
            if "Google Search" not in platforms_searched:
                platforms_searched.extend(["Google Search", "Google News", "Fact-Check Sites"])
            all_sources = []
            all_sources.extend(_search_serper_general(claim, num=3))
            all_sources.extend(_search_serper_news(claim, num=2))
            all_sources.extend(_search_fact_check_sites(claim))
            all_sources.extend(_search_wikipedia(claim))
            result = _analyze_claim_against_sources(claim, all_sources)
        else:
            logger.info("No Serper API key; using Wikipedia + mock data")
            wiki_results = _search_wikipedia(claim)
            if wiki_results:
                result = _analyze_claim_against_sources(claim, wiki_results)
            else:
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
