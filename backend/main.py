import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from input_detector import is_url
from scraper import scrape_url
from credibility import score_domain_trust, score_sources
from sentiment import analyze_sentiment
from coordination import detect_coordination
from risk import compute_risk
from related import fetch_related_info, get_topic_urls
from cross_check import cross_check_content
from gemini_analysis import analyze_with_gemini

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Real-Time Narrative Risk Detection System",
    description="Analyze URLs or text topics for narrative risk, sentiment, and coordination.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    input: str


@app.get("/")
async def root():
    return {"message": "Real-Time Narrative Risk Detection System API", "status": "running"}


@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    user_input = request.input.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Input cannot be empty.")

    logger.info(f"Analyzing input: {user_input[:100]}")

    # ââ Step 1: Detect input type ââââââââââââââââââââââââââââââââââââââââââ
    input_type = "url" if is_url(user_input) else "text"
    logger.info(f"Input type detected: {input_type}")

    # ââ Step 2: Fetch content ââââââââââââââââââââââââââââââââââââââââââââââ
    source_urls = []
    all_texts = []

    if input_type == "url":
        source_urls = [user_input]
        content = scrape_url(user_input)
        if not content:
            raise HTTPException(
                status_code=422,
                detail="Could not extract content from the provided URL."
            )
        all_texts = [content]
        query = user_input  # Use URL as query for related info

    else:
        # Text/topic: search for top URLs and scrape them
        query = user_input
        top_urls = get_topic_urls(query, num=5)
        logger.info(f"Top URLs from search: {top_urls}")

        # Filter out known mock/fake URLs before scraping
        MOCK_URLS = {"https://reuters.com/world/analysis", "https://bbc.com/news/world",
                     "https://apnews.com/article/sample"}
        real_urls = [u for u in top_urls if u not in MOCK_URLS]

        for url in real_urls:
            try:
                text = scrape_url(url)
                if text and len(text) > 100:
                    all_texts.append(text)
                    source_urls.append(url)
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")

        # If no real URLs were scraped, fetch content from Wikipedia
        if not all_texts:
            logger.info("No scrapeable URLs; fetching from Wikipedia as fallback")
            try:
                import requests as req
                params = {
                    "action": "query", "list": "search",
                    "srsearch": query, "format": "json",
                    "srlimit": 3, "srprop": "snippet",
                }
                headers = {"User-Agent": "NarrativeRiskDetector/1.0"}
                resp = req.get("https://en.wikipedia.org/w/api.php",
                               params=params, headers=headers, timeout=10)
                resp.raise_for_status()
                import re, html
                for item in resp.json().get("query", {}).get("search", []):
                    snippet = html.unescape(re.sub(r'<[^>]+>', '', item.get("snippet", "")))
                    if snippet and len(snippet) > 30:
                        all_texts.append(snippet)
                        source_urls.append(
                            f"https://en.wikipedia.org/wiki/{item['title'].replace(' ', '_')}")
            except Exception as e:
                logger.warning(f"Wikipedia fallback failed: {e}")

        if not all_texts:
            # Final fallback: use the query itself as content
            all_texts = [query]

        content = " ".join(all_texts)

    # ââ Step 3: Source trust scoring âââââââââââââââââââââââââââââââââââââââ
    if input_type == "url":
        source_trust_score = score_domain_trust(user_input)
    else:
        source_trust_score = score_sources(source_urls) if source_urls else 0.3

    logger.info(f"Source trust score: {source_trust_score}")

    # ââ Step 4: Sentiment analysis âââââââââââââââââââââââââââââââââââââââââ
    sentiment = analyze_sentiment(content)
    logger.info(f"Sentiment: {sentiment}")

    # ââ Step 5: Coordination detection ââââââââââââââââââââââââââââââââââââ
    coord_result = detect_coordination(all_texts)
    similarity_score = coord_result["similarity_score"]
    logger.info(f"Similarity score: {similarity_score}")

    # -- Step 6: Cross-platform fact verification --
    logger.info("Running cross-platform fact verification...")
    cross_check = cross_check_content(content, query)
    logger.info(f"Cross-check: {cross_check['claims_checked']} claims, reliability={cross_check['overall_reliability']}")

    # -- Step 7: Risk scoring (now includes cross-check) --
    risk_result = compute_risk(sentiment, similarity_score, source_trust_score, cross_check)
    logger.info(f"Risk level: {risk_result['risk_level']}")

    # -- Step 8: Related information --
    related = fetch_related_info(query, content)

    # -- Step 8.5: Gemini AI analysis --
    logger.info("Running Gemini AI analysis...")
    gemini_result = analyze_with_gemini(query, cross_check, sentiment, risk_result["risk_level"])
    if gemini_result:
        logger.info(f"Gemini verdict: {gemini_result.get('verdict', 'N/A')}")
    else:
        logger.info("Gemini analysis skipped or failed")

    # -- Step 8.6: Gemini verdict OVERRIDES risk level (highest priority) --
    final_risk_level = risk_result["risk_level"]
    final_reasons = list(risk_result["reasons"])

    if gemini_result:
        gv = (gemini_result.get("verdict") or "").upper().strip()
        gemini_analysis_text = gemini_result.get("analysis", "")

        if gv in ("FALSE", "MISLEADING"):
            if final_risk_level != "HIGH":
                final_risk_level = "HIGH"
                final_reasons.insert(
                    0, f"Gemini AI analysis verdict: {gv}. {gemini_analysis_text[:200]}"
                )
                logger.info(f"Gemini override: risk escalated to HIGH (verdict={gv})")

        elif gv in ("UNVERIFIED", "PARTIALLY TRUE"):
            if final_risk_level == "LOW":
                final_risk_level = "MEDIUM"
                final_reasons.insert(
                    0, f"Gemini AI analysis verdict: {gv}. {gemini_analysis_text[:200]}"
                )
                logger.info(f"Gemini override: risk escalated to MEDIUM (verdict={gv})")

        # Recalculate summary with updated risk level
        if final_risk_level != risk_result["risk_level"]:
            risk_result["summary"] = (
                f"Gemini AI analysis flagged this content as {gv}. "
                + risk_result["summary"]
            )

    # -- Step 9: Build response --
    return {
        "input_type": input_type,
        "source_trust_score": source_trust_score,
        "sentiment": sentiment,
        "similarity_score": similarity_score,
        "risk_level": final_risk_level,
        "reasons": final_reasons,
        "misinformation_score": risk_result["misinformation_score"],
        "reputation_risk_score": risk_result["reputation_risk_score"],
        "reputation_risk_level": risk_result["reputation_risk_level"],
        "confidence": risk_result["confidence"],
        "summary": risk_result["summary"],
        "related": related,
        "cross_check": cross_check,
        "sources_checked": source_urls,
        "gemini_analysis": gemini_result,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
