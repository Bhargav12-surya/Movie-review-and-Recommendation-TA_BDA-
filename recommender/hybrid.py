"""Normalize real channels, exclude seen/ineligible items and explain contributions."""
import math


def cosine(left, right):
    if len(left) != len(right) or not left or any(not math.isfinite(value) for value in [*left, *right]):
        raise ValueError("Compatible finite semantic embeddings are required.")
    denominator = math.sqrt(sum(value * value for value in left) * sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


def recommend(movies, profile, config, collaborative_scores=None, k=10):
    if not 1 <= k <= 100 or len(movies) > 100000:
        raise ValueError("Bound recommendation output and catalogue size.")
    if config.get("weights_validated") is not True:
        raise ValueError("Hybrid weights require actual validation selection; no arbitrary production mix.")
    seen = set(profile.get("seen_movie_ids", [])) | set(profile.get("ratings", {}))
    wanted_genres, wanted_themes = profile.get("genre_preferences", {}), profile.get("theme_preferences", {})
    if any(not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1 for value in [*wanted_genres.values(), *wanted_themes.values()]):
        raise ValueError("Genre/theme preferences must be explicit bounded weights.")
    filters = config.get("filters", {})
    rows, ids = [], set()
    for movie in movies:
        identifier = movie["movie_id"]
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("Use normalized validated canonical movie ID strings at this serving boundary.")
        if identifier in ids:
            raise ValueError("Duplicate canonical catalogue movie ID.")
        ids.add(identifier)
        if identifier in seen or movie.get("eligible") is not True:
            continue
        if set(filters.get("required_genres", [])) - set(movie.get("genres", [])):
            continue
        if set(filters.get("excluded_genres", [])) & set(movie.get("genres", [])):
            continue
        if set(filters.get("required_themes", [])) - set(movie.get("themes", [])):
            continue
        if filters.get("maximum_runtime") is not None and (movie.get("runtime_minutes") is None or movie["runtime_minutes"] > filters["maximum_runtime"]):
            continue
        channels, evidence = {}, {}
        if collaborative_scores is not None and identifier in collaborative_scores:
            channels["als"] = collaborative_scores[identifier]
            evidence["als"] = {"method": "actual_spark_factor_dot_product"}
        if profile.get("semantic_embedding") is not None and movie.get("embedding") is not None:
            if movie.get("embedding_model_version") != profile.get("embedding_model_version"):
                raise ValueError("Semantic preference/catalogue model versions differ.")
            channels["semantic"] = cosine(profile["semantic_embedding"], movie["embedding"])
            evidence["semantic"] = {"model_version": movie["embedding_model_version"]}
        if wanted_genres:
            matches = {name: weight for name, weight in wanted_genres.items() if name in movie.get("genres", [])}
            channels["genre"] = sum(matches.values()) / sum(wanted_genres.values()) if sum(wanted_genres.values()) else 0
            evidence["genre"] = matches
        if wanted_themes:
            matches = {name: weight for name, weight in wanted_themes.items() if name in movie.get("themes", [])}
            channels["theme"] = sum(matches.values()) / sum(wanted_themes.values()) if sum(wanted_themes.values()) else 0
            evidence["theme"] = matches
        if movie.get("training_popularity") is not None:
            channels["popularity"] = math.log1p(movie["training_popularity"])
            evidence["popularity"] = {"count": movie["training_popularity"], "scope": "training_period_only"}
        if any(not math.isfinite(value) for value in channels.values()):
            raise ValueError("Nonfinite recommendation channel.")
        rows.append({"movie_id": identifier, "channels": channels, "evidence": evidence, "genres": movie.get("genres", [])})
    weights = config.get("weights", {})
    if not weights or any(not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0 for value in weights.values()):
        raise ValueError("Use finite nonnegative validation-selected channel weights.")
    ranges = {name: (min(values), max(values)) for name in weights if (values := [row["channels"][name] for row in rows if name in row["channels"]])}
    for row in rows:
        active = {name: weight for name, weight in weights.items() if weight > 0 and name in row["channels"]}
        total = sum(active.values())
        contributions = {}
        for name, weight in active.items():
            low, high = ranges[name]
            # Constant channels provide no ranking discrimination.
            normalized = (row["channels"][name] - low) / (high - low) if high > low else 0.0
            contributions[name] = normalized * weight / total
        row.update(match_score=sum(contributions.values()) if total else None, contributions=contributions,
                   score_kind="personalized_match_not_audience_sentiment", active_channel_weights=active)
    rows = sorted((row for row in rows if row["match_score"] is not None), key=lambda row: (-row["match_score"], str(row["movie_id"])))
    diversity = config.get("diversity_penalty", 0.0)
    if not isinstance(diversity, (int, float)) or not 0 <= diversity <= 1:
        raise ValueError("Validation-selected diversity penalty must be within0..1.")
    selected = []
    # Re-rank only the explicitly reported top bounded candidate pool after ALL
    # eligibility/seen filters; the original full eligible universe is retained in counts.
    pool_size = config.get("rerank_pool_size", 200)
    if type(pool_size) is not int or not k <= pool_size <= 2000:
        raise ValueError("Use a bounded rerank pool at leastK.")
    pool = rows[:pool_size]
    while pool and len(selected) < k:
        def marginal(row):
            genres = set(row["genres"])
            penalty = max((len(genres & set(other["genres"])) / len(genres | set(other["genres"]))
                           if genres | set(other["genres"]) else 0 for other in selected), default=0)
            return row["match_score"] - diversity * penalty
        winner = max(pool, key=lambda row: (marginal(row), -rows.index(row)))
        winner["rerank_score"] = marginal(winner)
        selected.append(winner)
        pool.remove(winner)
    return {"recommendations": selected, "eligible_candidate_count": len(rows), "rerank_pool_count": min(pool_size, len(rows)),
        "k": k, "cold_start": not bool(collaborative_scores), "normalization": "eligible_candidate_minmax_constant_channel_zero",
        "explanations": "evidence and nonzero contribution dictionaries use actual model/profile inputs"}
