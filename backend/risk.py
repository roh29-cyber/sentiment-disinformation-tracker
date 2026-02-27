def compute_risk(
    sentiment: dict,
    similarity_score: float,
    source_trust_score: float,
    cross_check: dict | None = None,
) -> dict:
    """
    Compute risk level and reasons based on sentiment, similarity, trust,
    and cross-platform fact-check results.

    Returns:
        {
            "risk_level": "LOW" | "MEDIUM" | "HIGH",
            "reasons": [str, ...]
        }
    """
    reasons = []
    risk_level = "LOW"

    # ── Cross-check override: false/disputed claims → immediate HIGH ────
    if cross_check:
        claims = cross_check.get("claims", [])
        false_claims = [c for c in claims if c.get("verdict") in ("likely_false", "disputed")]
        if false_claims:
            for fc in false_claims:
                label = fc["verdict"].replace("_", " ").title()
                corrected = fc.get("corrected_info") or "No correction available."
                reasons.append(
                    f"Cross-platform check: claim \"{fc['claim'][:80]}\" is {label}. {corrected}"
                )
            return {"risk_level": "HIGH", "reasons": reasons}

        overall = cross_check.get("overall_reliability", "")
        if overall == "unreliable":
            reasons.append("Cross-platform verification rated this content as unreliable.")
            return {"risk_level": "HIGH", "reasons": reasons}
        elif overall == "questionable":
            reasons.append("Cross-platform verification found questionable claims.")
            # Don't return yet — let other signals combine

    negative_pct = sentiment.get("negative", 0)
    positive_pct = sentiment.get("positive", 0)

    # HIGH risk conditions
    high_conditions = []
    if negative_pct > 50:
        high_conditions.append(True)
        reasons.append(
            f"High negative sentiment detected: {negative_pct}% of content is negative."
        )
    if similarity_score > 0.6:
        high_conditions.append(True)
        reasons.append(
            f"Strong coordinated messaging detected: similarity score {similarity_score:.2f} exceeds 0.6 threshold."
        )
    if source_trust_score < 0.3:
        high_conditions.append(True)
        reasons.append(
            f"Low source credibility: trust score {source_trust_score:.2f} is below 0.3."
        )

    if any(high_conditions):
        risk_level = "HIGH"
        return {"risk_level": risk_level, "reasons": reasons}

    # MEDIUM risk conditions
    medium_conditions = []
    if negative_pct > 30:
        medium_conditions.append(True)
        reasons.append(
            f"Elevated negative sentiment: {negative_pct}% of content is negative."
        )
    if similarity_score > 0.4:
        medium_conditions.append(True)
        reasons.append(
            f"Moderate coordinated messaging: similarity score {similarity_score:.2f} exceeds 0.4 threshold."
        )
    if source_trust_score < 0.6:
        medium_conditions.append(True)
        reasons.append(
            f"Moderate source credibility concern: trust score {source_trust_score:.2f} is below 0.6."
        )

    if any(medium_conditions):
        risk_level = "MEDIUM"
        return {"risk_level": risk_level, "reasons": reasons}

    # LOW risk
    reasons.append("Content appears to be from credible sources with balanced sentiment.")
    if positive_pct > 40:
        reasons.append(f"Predominantly positive content: {positive_pct}% positive sentiment.")
    return {"risk_level": "LOW", "reasons": reasons}
