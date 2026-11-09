"""Retrieval quality from actual human relevance judgments and real rankings."""
import math


def evaluate(rankings, judgments, k=10):
    if not judgments or set(rankings) != set(judgments) or k < 1:
        raise ValueError("Every human-judged query must be evaluated.")
    rows = []
    for query, relevant in judgments.items():
        relevant = set(relevant)
        if not relevant:
            raise ValueError("A judged query requires positive support; report unjudged queries separately.")
        found = rankings[query][:k]
        if len(found) != len(set(found)):
            raise ValueError("Duplicate retrieved IDs.")
        hits = [int(identifier in relevant) for identifier in found]
        ideal = sum(1 / math.log2(index + 2) for index in range(min(k, len(relevant))))
        rows.append({"recall": sum(hits) / len(relevant), "mrr": next((1 / (index + 1) for index, hit in enumerate(hits) if hit), 0),
                     "ndcg": sum(hit / math.log2(index + 2) for index, hit in enumerate(hits)) / ideal})
    return {"queries": len(rows), "k": k, **{name + "@k": sum(row[name] for row in rows) / len(rows) for name in rows[0]}}
