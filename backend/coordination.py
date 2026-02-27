import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def split_into_chunks(text: str, chunk_size: int = 200) -> list[str]:
    """Split text into word-based chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk.strip()) > 20:
            chunks.append(chunk)
    return chunks


def detect_coordination(texts: list[str]) -> dict:
    """
    Detect coordinated messaging using TF-IDF + cosine similarity.
    Returns similarity_score (0.0 to 1.0) and count of highly similar pairs.
    """
    # Flatten all texts into chunks
    all_chunks = []
    for text in texts:
        all_chunks.extend(split_into_chunks(text))

    if len(all_chunks) < 2:
        return {"similarity_score": 0.0, "coordinated_pairs": 0}

    # Cap chunks to avoid memory issues
    all_chunks = all_chunks[:100]

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=5000,
            min_df=1
        )
        tfidf_matrix = vectorizer.fit_transform(all_chunks)
        sim_matrix = cosine_similarity(tfidf_matrix)

        # Extract upper triangle (excluding diagonal)
        n = sim_matrix.shape[0]
        pairs = []
        high_sim_pairs = 0
        threshold = 0.8

        for i in range(n):
            for j in range(i + 1, n):
                val = sim_matrix[i][j]
                pairs.append(val)
                if val > threshold:
                    high_sim_pairs += 1

        avg_sim = float(np.mean(pairs)) if pairs else 0.0
        return {
            "similarity_score": round(avg_sim, 4),
            "coordinated_pairs": high_sim_pairs,
        }
    except Exception as e:
        return {"similarity_score": 0.0, "coordinated_pairs": 0}
