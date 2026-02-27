def _compute_misinfo_score(
    sentiment: dict,
    similarity_score: float,
    source_trust_score: float,
    cross_check: dict | None = None,
) -> int:
    """Return a misinformation risk score from 0-100."""
    score = 0

    # Cross-check signals (up to 50 pts)
    if cross_check:
        claims = cross_check.get("claims", [])
        if claims:
            false_count = sum(1 for c in claims if c.get("verdict") in ("likely_false", "disputed"))
            ratio = false_count / len(claims)
            score += int(ratio * 50)
        overall = cross_check.get("overall_reliability", "")
        if overall == "unreliable":
            score += 15
        elif overall == "questionable":
            score += 8

    # Negative sentiment (up to 20 pts)
    neg = sentiment.get("negative", 0)
    score += min(int(neg * 0.4), 20)

    # Coordination/similarity (up to 15 pts)
    score += min(int(similarity_score * 25), 15)

    # Low source trust (up to 15 pts)
    score += min(int((1 - source_trust_score) * 15), 15)

    return min(max(score, 0), 100)


def _compute_reputation_score(
    sentiment: dict,
    cross_check: dict | None = None,
) -> int:
    """Return a reputation risk score from 0-100 for identified entities."""
    score = 0

    # False claims about people/orgs are huge reputation risks (up to 60 pts)
    if cross_check:
        claims = cross_check.get("claims", [])
        false_claims = [c for c in claims if c.get("verdict") in ("likely_false", "disputed")]
        score += min(len(false_claims) * 30, 60)

        overall = cross_check.get("overall_reliability", "")
        if overall == "unreliable":
            score += 15
        elif overall == "questionable":
            score += 8

    # Strong negative sentiment damages reputation (up to 25 pts)
    neg = sentiment.get("negative", 0)
    score += min(int(neg * 0.5), 25)

    return min(max(score, 0), 100)


def _generate_summary(
    reasons: list[str],
    risk_level: str,
    misinfo_score: int,
    reputation_score: int,
    cross_check: dict | None = None,
) -> str:
    """Build a 3-5 sentence evidence-based summary."""
    parts = []

    parts.append(
        f"The analysis indicates a {risk_level} risk level with a misinformation score of "
        f"{misinfo_score}/100 and a reputation risk score of {reputation_score}/100."
    )

    if cross_check:
        claims = cross_check.get("claims", [])
        false_claims = [c for c in claims if c.get("verdict") in ("likely_false", "disputed")]
        if false_claims:
            corrections = []
            for fc in false_claims:
                corr = fc.get("corrected_info", "")
                if corr:
                    corrections.append(corr)
            if corrections:
                parts.append(
                    f"Cross-platform verification flagged {len(false_claims)} claim(s) as "
                    f"false or disputed. {corrections[0]}"
                )
            else:
                parts.append(
                    f"Cross-platform verification flagged {len(false_claims)} claim(s) as "
                    "false or disputed."
                )
        checked = cross_check.get("claims_checked", 0)
        if checked and not false_claims:
            parts.append(
                f"All {checked} claim(s) checked across trusted sources appear consistent."
            )

    # Summarise dominant reasons
    if len(reasons) > 1:
        key_reason = reasons[0]
        parts.append(f"Key finding: {key_reason}")

    if risk_level == "HIGH":
        parts.append("Exercise extreme caution before sharing or acting on this content.")
    elif risk_level == "MEDIUM":
        parts.append("We recommend verifying this information with additional trusted sources.")
    else:
        parts.append("The content appears generally reliable based on available evidence.")

    return " ".join(parts)


def _score_to_confidence(misinfo_score: int) -> str:
    if misinfo_score >= 70:
        return "High"
    if misinfo_score >= 35:
        return "Medium"
    return "Low"


def compute_risk(
    sentiment: dict,
    similarity_score: float,
    source_trust_score: float,
    cross_check: dict | None = None,
) -> dict:
    """
    Compute risk level, numeric scores, reputation risk, and evidence summary.

    Returns:
        {
            "risk_level": "LOW" | "MEDIUM" | "HIGH",
            "reasons": [str, ...],
            "misinformation_score": 0-100,
            "reputation_risk_score": 0-100,
            "reputation_risk_level": "LOW" | "MEDIUM" | "HIGH",
            "confidence": "Low" | "Medium" | "High",
            "summary": str
        }
    """
    reasons = []
    risk_level = "LOW"

    # ── Cross-check override: false/disputed claims -> immediate HIGH ────
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
            risk_level = "HIGH"

        if risk_level != "HIGH":
            overall = cross_check.get("overall_reliability", "")
            if overall == "unreliable":
                reasons.append("Cross-platform verification rated this content as unreliable.")
                risk_level = "HIGH"
            elif overall == "questionable":
                reasons.append("Cross-platform verification found questionable claims.")

    negative_pct = sentiment.get("negative", 0)
    positive_pct = sentiment.get("positive", 0)

    if risk_level != "HIGH":
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
        else:
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
            else:
                reasons.append("Content appears to be from credible sources with balanced sentiment.")
                if positive_pct > 40:
                    reasons.append(f"Predominantly positive content: {positive_pct}% positive sentiment.")

    # ── Numeric scores ──────────────────────────────────────────────────
    misinfo_score = _compute_misinfo_score(sentiment, similarity_score, source_trust_score, cross_check)
    reputation_score = _compute_reputation_score(sentiment, cross_check)

    rep_level = "LOW"
    if reputation_score >= 60:
        rep_level = "HIGH"
    elif reputation_score >= 30:
        rep_level = "MEDIUM"

    confidence = _score_to_confidence(misinfo_score)
    summary = _generate_summary(reasons, risk_level, misinfo_score, reputation_score, cross_check)

    return {
        "risk_level": risk_level,
        "reasons": reasons,
        "misinformation_score": misinfo_score,
        "reputation_risk_score": reputation_score,
        "reputation_risk_level": rep_level,
        "confidence": confidence,
        "summary": summary,
    }
