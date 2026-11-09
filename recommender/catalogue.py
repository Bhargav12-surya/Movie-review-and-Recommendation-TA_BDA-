"""Join actual canonical catalogue rows with versioned content artifacts."""
import hashlib


def join_features(movies, vectors, embedding_manifest, theme_predictions, training_counts):
    if not embedding_manifest.get("model_revision") or not embedding_manifest.get("dimension"):
        raise ValueError("Actual embedding revision/dimension manifest required.")
    by_vector = {}
    for row in vectors:
        if row["record_id"] in by_vector or len(row["embedding"]) != embedding_manifest["dimension"]:
            raise ValueError("Duplicate content row or embedding dimension mismatch.")
        by_vector[row["record_id"]] = row
    by_theme = {row["record_id"]: row for row in theme_predictions}
    if len(by_theme) != len(theme_predictions):
        raise ValueError("Duplicate theme prediction record.")
    result, seen = [], set()
    for movie in movies:
        identifier = str(movie["movie_id"])
        if identifier in seen or movie.get("canonical_mapping_approved") is not True:
            raise ValueError("A unique approved canonical catalogue is required.")
        seen.add(identifier)
        row = {**movie, "movie_id": identifier, "training_popularity": training_counts.get(identifier, 0)}
        vector = by_vector.get(movie.get("embedding_record_id"))
        if vector is not None:
            text = movie.get("embedding_text")
            if not isinstance(text, str) or hashlib.sha256(text.encode()).hexdigest() != vector["content_sha256"]:
                raise ValueError("Embedding content differs from the catalogue snapshot.")
            row.update(embedding=vector["embedding"], embedding_model_version=embedding_manifest["model_revision"])
        theme = by_theme.get(movie.get("theme_record_id"))
        if theme is not None:
            if theme.get("kind") != "theme_relevance" or theme.get("audience_theme_sentiment") is not None:
                raise ValueError("Keep theme relevance and audience reception separate.")
            row.update(themes=theme["theme_labels"], theme_relevance=theme["relevance"])
        result.append(row)
    return result
