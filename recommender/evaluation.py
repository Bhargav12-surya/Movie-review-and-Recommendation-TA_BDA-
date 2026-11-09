"""Fixed-denominator ranking, coverage, diversity and train-only novelty."""
import math


def evaluate(recommendations, relevant, catalogue, training_counts, k=10):
    if not relevant or set(recommendations) != set(relevant) or k < 1:
        raise ValueError("Include every declared evaluation user, including empty/cold rankings.")
    catalogue = {row["movie_id"]: row for row in catalogue}
    total_count = sum(training_counts.values())
    aggregate, recommended = [], set()
    for user, truth in relevant.items():
        truth, items = set(truth), recommendations[user][:k]
        if not truth:
            raise ValueError("Users without eligible positives need a separately reported non-ranking cohort.")
        if truth - set(catalogue):
            raise ValueError("Ground-truth catalogue exclusions must be resolved/reported before ranking evaluation.")
        if len(items) != len(set(items)) or any(item not in catalogue for item in items):
            raise ValueError("Invalid recommendation IDs or duplicates.")
        hits = [int(item in truth) for item in items]
        ideal = sum(1 / math.log2(index + 2) for index in range(min(k, len(truth))))
        pairs = [(set(catalogue[a].get("genres", [])), set(catalogue[b].get("genres", []))) for index, a in enumerate(items) for b in items[index + 1:]]
        diversity = sum(1 - len(a & b) / len(a | b) if a | b else 0 for a, b in pairs) / len(pairs) if pairs else None
        novelty = sum(-math.log2((training_counts.get(item, 0) + 1) / (total_count + len(catalogue))) for item in items) / len(items) if items and total_count else None
        aggregate.append({"precision": sum(hits) / k, "recall": sum(hits) / len(truth),
            "ndcg": sum(hit / math.log2(index + 2) for index, hit in enumerate(hits)) / ideal,
            "diversity": diversity, "novelty": novelty})
        recommended.update(items)
    result = {"users": len(aggregate), "k": k, "coverage": len(recommended) / len(catalogue) if catalogue else 0,
              "empty_rankings": sum(not values for values in recommendations.values()), "precision_denominator": "K_even_for_short_or_empty_lists"}
    for name in aggregate[0]:
        values = [row[name] for row in aggregate if row[name] is not None]
        result[name + ("@k" if name in {"precision", "recall", "ndcg"} else "")] = sum(values) / len(values) if values else None
        result[name + "_supported_users"] = len(values)
    return result
