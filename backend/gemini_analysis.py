"""
Gemini AI analysis module.

Uses Google's Gemini API to provide AI-powered analysis of claims
by synthesizing cross-check results, sentiment data, and news coverage.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def _build_prompt(query: str, cross_check: dict, sentiment: dict,
                  risk_level: str, news_snippets: list[str]) -> str:
    """Build a detailed prompt for Gemini from all available data."""
    # Gather cross-check evidence
    claims_text = ""
    for c in cross_check.get("claims", []):
        claims_text += f"\n- Claim: \"{c['claim']}\"\n"
        claims_text += f"  Verdict: {c['verdict']} (confidence: {c['confidence']})\n"
        if c.get("corrected_info"):
            claims_text += f"  Correction: {c['corrected_info']}\n"
        for src in c.get("sources", [])[:3]:
            claims_text += f"  Source [{src.get('platform', '')}]: {src.get('title', '')} — {src.get('snippet', '')[:150]}\n"

    news_text = ""
    if news_snippets:
        for i, snippet in enumerate(news_snippets[:5], 1):
            news_text += f"\n{i}. {snippet}"

    prompt = f"""You are a misinformation detection expert. Analyze the following user query and the evidence gathered from multiple sources.

USER QUERY: "{query}"

CROSS-CHECK RESULTS:
Overall reliability: {cross_check.get('overall_reliability', 'unknown')}
Platforms searched: {', '.join(cross_check.get('platforms_searched', []))}
{claims_text}

SENTIMENT ANALYSIS:
Positive: {sentiment.get('positive', 0)}%, Neutral: {sentiment.get('neutral', 0)}%, Negative: {sentiment.get('negative', 0)}%

RISK LEVEL: {risk_level}

NEWS COVERAGE:{news_text if news_text else ' No recent news articles found.'}

Based on ALL the above evidence, provide a concise analysis in this exact format:

VERDICT: [TRUE / FALSE / MISLEADING / UNVERIFIED / PARTIALLY TRUE]
ANALYSIS: [2-3 sentences explaining your reasoning based on the evidence]
KEY FACTS: [2-4 bullet points of verified facts relevant to this query]
RECOMMENDATION: [1 sentence advising the reader]

Be factual and evidence-based. Do not speculate beyond what the sources say."""

    return prompt


def analyze_with_gemini(query: str, cross_check: dict, sentiment: dict,
                        risk_level: str) -> dict | None:
    """
    Send gathered evidence to Gemini for AI-powered analysis.

    Returns:
        {
            "verdict": str,
            "analysis": str,
            "key_facts": [str],
            "recommendation": str,
            "raw_response": str,
        }
    or None if Gemini is unavailable.
    """
    if not GEMINI_API_KEY:
        logger.info("Gemini API key not set; skipping AI analysis")
        return None

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)

        # Extract news snippets from cross-check sources
        news_snippets = []
        for claim in cross_check.get("claims", []):
            for src in claim.get("sources", []):
                if src.get("platform", "").startswith("NewsAPI"):
                    title = src.get("title", "")
                    snippet = src.get("snippet", "")
                    source = src.get("source", "")
                    news_snippets.append(f"[{source}] {title} — {snippet[:150]}")

        prompt = _build_prompt(query, cross_check, sentiment, risk_level, news_snippets)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = response.text.strip()
        raw = response.text.strip()
        logger.info(f"Gemini response length: {len(raw)} chars")

        # Parse the structured response
        result = _parse_gemini_response(raw)
        result["raw_response"] = raw
        return result

    except Exception as e:
        logger.warning(f"Gemini analysis failed: {e}")
        return None


def _parse_gemini_response(text: str) -> dict:
    """Parse Gemini's structured response into a dict."""
    result = {
        "verdict": "",
        "analysis": "",
        "key_facts": [],
        "recommendation": "",
    }

    lines = text.split("\n")
    current_section = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        upper = stripped.upper()

        if upper.startswith("VERDICT:"):
            result["verdict"] = stripped.split(":", 1)[1].strip().strip("*[] ")
            current_section = "verdict"
        elif upper.startswith("ANALYSIS:"):
            result["analysis"] = stripped.split(":", 1)[1].strip()
            current_section = "analysis"
        elif upper.startswith("KEY FACTS:") or upper.startswith("KEY_FACTS:"):
            rest = stripped.split(":", 1)[1].strip()
            if rest:
                result["key_facts"].append(rest.lstrip("- •*"))
            current_section = "key_facts"
        elif upper.startswith("RECOMMENDATION:"):
            result["recommendation"] = stripped.split(":", 1)[1].strip()
            current_section = "recommendation"
        elif current_section == "analysis" and not any(
            stripped.upper().startswith(k) for k in ["KEY FACTS", "RECOMMENDATION", "VERDICT"]
        ):
            result["analysis"] += " " + stripped
        elif current_section == "key_facts" and (
            stripped.startswith("-") or stripped.startswith("•") or stripped.startswith("*")
        ):
            result["key_facts"].append(stripped.lstrip("- •*").strip())
        elif current_section == "recommendation" and not any(
            stripped.upper().startswith(k) for k in ["KEY FACTS", "ANALYSIS", "VERDICT"]
        ):
            result["recommendation"] += " " + stripped

    # Clean up
    result["analysis"] = result["analysis"].strip()
    result["recommendation"] = result["recommendation"].strip()
    result["key_facts"] = [f for f in result["key_facts"] if f]

    return result
