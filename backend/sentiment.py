import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences using simple regex."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def analyze_sentiment(text: str) -> dict:
    """
    Run VADER sentiment analysis on text chunks.
    Returns percentage breakdown of positive, neutral, negative.
    """
    sentences = split_into_sentences(text)
    if not sentences:
        return {"positive": 0, "neutral": 100, "negative": 0}

    pos_count = 0
    neu_count = 0
    neg_count = 0

    for sentence in sentences:
        scores = analyzer.polarity_scores(sentence)
        compound = scores["compound"]
        if compound >= 0.05:
            pos_count += 1
        elif compound <= -0.05:
            neg_count += 1
        else:
            neu_count += 1

    total = len(sentences)
    return {
        "positive": round((pos_count / total) * 100),
        "neutral": round((neu_count / total) * 100),
        "negative": round((neg_count / total) * 100),
    }
