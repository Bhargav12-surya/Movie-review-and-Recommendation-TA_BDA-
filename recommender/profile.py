"""Preferences derived from actual consented interactions and ratings."""
import math

def build_profile(explicit, interactions, movies, event_weights):
    catalogue = {row["movie_id"]: row for row in movies}
    genres, themes, seen, vector, mass = {}, {}, set(), None, 0.0
    versions = set()
    for row in interactions:
        if row.get("personalization_permitted") is not True:
            continue
        movie = catalogue.get(row.get("movie_id"))
        if movie is None:
            continue
        kind = row.get("event_type")
        if kind not in event_weights:
            continue
        weight = event_weights[kind]
        if isinstance(weight, bool) or not isinstance(weight, (int,float)) or not math.isfinite(weight) or weight < 0:
            raise ValueError("Interaction weights require a reviewed nonnegative policy.")
        if kind in {"watched", "rating"}:
            seen.add(movie["movie_id"])
        if kind == "rating":
            rating = row.get("rating")
            if isinstance(rating, bool) or not isinstance(rating, (int,float)) or not 0.5 <= rating <= 5:
                raise ValueError("Actual valid explicit star ratings required.")
            weight *= max(0, (rating - 2.75) / 2.25)
        for name in movie.get("genres", []):
            genres[name] = genres.get(name, 0) + weight
        for name in movie.get("themes", []):
            themes[name] = themes.get(name, 0) + weight
        if movie.get("embedding") is not None and weight:
            values = movie["embedding"]
            versions.add(movie.get("embedding_model_version"))
            if vector is None:
                vector = [0.0] * len(values)
            if len(vector) != len(values):
                raise ValueError("Mixed embedding dimensions.")
            vector = [a + weight*b for a,b in zip(vector,values)]
            mass += weight
    if len(versions) > 1 or (versions and None in versions):
        raise ValueError("Mixed/unknown semantic model versions in profile.")
    def normalized(values):
        total = sum(values.values())
        return {name:value/total for name,value in values.items()} if total else {}
    return {**explicit, "genre_preferences": explicit.get("genre_preferences", normalized(genres)),
        "theme_preferences": explicit.get("theme_preferences", normalized(themes)),
        "seen_movie_ids": sorted(seen | set(explicit.get("seen_movie_ids", []))),
        "semantic_embedding": [value/mass for value in vector] if mass else None,
        "embedding_model_version": next(iter(versions)) if versions else None,
        "preference_method": "consented_event_weights_and_positive_rating_utility; not_sentiment_labels"}

