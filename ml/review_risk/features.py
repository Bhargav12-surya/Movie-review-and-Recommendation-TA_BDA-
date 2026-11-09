import hashlib
import math

BEHAVIOUR_FEATURES = ("submissions_1h", "distinct_movies_1h", "duplicate_text_fraction_7d")


def text_signals(text, existing_texts):
    if not isinstance(text, str) or not text.strip() or len(text) > 20000 or len(existing_texts) > 10000:
        raise ValueError("Bound legitimate review text/history.")
    normalized = " ".join(text.casefold().split())
    exact = sum(" ".join(other.casefold().split()) == normalized for other in existing_texts)
    maximum_similarity = None
    if existing_texts:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=30000)
        try:
            history = vectorizer.fit_transform(existing_texts)
            query = vectorizer.transform([text])
            maximum_similarity = float((query @ history.T).max())
        except ValueError:
            # No usable lexical vocabulary is missing evidence, not low fraud risk.
            maximum_similarity = None
    return {"exact_duplicate_count": exact, "maximum_tfidf_cosine": maximum_similarity,
            "history_count": len(existing_texts), "sentiment_used": False}


def behaviour_vector(row):
    if row.get("behaviour_use_permitted") is not True or not row.get("provenance_reference"):
        raise ValueError("Legitimately collected permitted behavioural records are required.")
    values = []
    for name in BEHAVIOUR_FEATURES:
        value = row.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("Missing/invalid real behavioural feature: " + name)
        if name.endswith("fraction_7d") and value > 1:
            raise ValueError("Duplicate fraction exceeds1.")
        values.append(float(value))
    return values
