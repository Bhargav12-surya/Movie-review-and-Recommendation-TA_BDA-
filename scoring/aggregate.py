from datetime import datetime, timezone
from dataclasses import asdict
import hashlib
import json
import random
from .eligibility import eligible, probabilities_index

EMPTY_MESSAGE = "Not enough audience reviews yet."


def aggregate(rows, movie_id, policy, target_type="overall", target_key=None):
    if target_type not in {"overall", "aspect", "theme", "genre"} or (target_type != "overall" and not target_key):
        raise ValueError("Explicit separate score target required.")
    evidence, exclusions = eligible(rows, movie_id, policy)
    total = sum(row["weight"] for row in evidence)
    squared = sum(row["weight"] ** 2 for row in evidence)
    effective = total * total / squared if squared else 0.0
    distinct = len({row["reviewer_id"] for row in evidence if row["weight"] > 0})
    included = [row for row in evidence if row["weight"] > 0]
    snapshot_hash = hashlib.sha256(json.dumps({"evidence": included, "policy": asdict(policy), "target_type": target_type,
        "target_key": target_key}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    result = {"movie_id": str(movie_id), "score_type": target_type, "target_key": target_key, "score": None,
        "review_count": len(included), "distinct_reviewers": distinct, "effective_review_count": effective,
        "updated_at": datetime.now(timezone.utc).isoformat(), "model_version": policy.model_version,
        "method_version": policy.method_version, "snapshot_sha256": snapshot_hash, "exclusions": exclusions,
        "message": EMPTY_MESSAGE, "uncertainty": None, "weight_policy": "moderation_quality_only; missing=1; never_model_confidence"}
    if len(included) < policy.minimum_reviews or distinct < policy.minimum_distinct_reviewers or effective < policy.minimum_effective_reviews:
        result["status"] = "insufficient_evidence"
        return result
    raw = sum(row["weight"] * row["score"] for row in included) / total
    alpha = effective / (effective + policy.shrinkage_strength)
    score = alpha * raw + (1 - alpha) * policy.prior if policy.shrinkage_strength else raw
    result.update(status="available", score=score, raw_score=raw, message=None,
                  shrinkage_strength=policy.shrinkage_strength,
                  predicted_class_distribution={name: sum(row["label"] == name for row in included) for name in ("negative", "neutral", "positive")},
                  confidence_status="meets_reviewed_minimum_evidence; model_error_not_estimated",
                  evidence=[{key: value for key, value in row.items() if key != "reviewer_id"} for row in included])
    if policy.bootstrap_samples and len(included) > 1:
        rng, estimates = random.Random(policy.seed), []
        for _ in range(policy.bootstrap_samples):
            sample = [included[rng.randrange(len(included))] for _ in included]
            sw = sum(row["weight"] for row in sample)
            ss = sum(row["weight"] ** 2 for row in sample)
            neff = sw * sw / ss
            value = sum(row["weight"] * row["score"] for row in sample) / sw
            a = neff / (neff + policy.shrinkage_strength)
            estimates.append(a * value + (1 - a) * policy.prior if policy.shrinkage_strength else value)
        estimates.sort()
        result["uncertainty"] = {"lower": estimates[int(0.025 * (len(estimates) - 1))], "upper": estimates[int(0.975 * (len(estimates) - 1))],
            "method": "95_percent_percentile_review_bootstrap_one_review_per_reviewer", "samples": len(estimates),
            "not_included": "model_error,population_selection_bias,residual_cross_reviewer_dependence"}
    return result


def target_records(reviews, target_type, target_key):
    """Use trained target probabilities, never metadata relevance or overall polarity."""
    if target_type not in {"aspect", "theme", "genre"}:
        raise ValueError("Unknown target-specific evidence type.")
    result = []
    for row in reviews:
        targets = [item for item in row.get("target_predictions", []) if item.get("target_type") == target_type and item.get("target_key") == target_key and item.get("prediction_approved") is True and item.get("calibrated") is True]
        if not targets:
            # Retain newer absent/withdrawn target analysis as an ineligible
            # revision so an older target prediction cannot reappear.
            result.append({**row, "prediction_approved": False, "calibrated": False, "model_version": None})
            continue
        versions = {item["model_version"] for item in targets}
        if len(versions) != 1:
            raise ValueError("Target mentions use incompatible model versions.")
        for item in targets:
            probabilities_index(item["probabilities"])
        probabilities = {name: sum(item["probabilities"][name] for item in targets) / len(targets) for name in ("negative", "neutral", "positive")}
        result.append({**row, "probabilities": probabilities, "model_version": next(iter(versions)), "calibrated": True, "prediction_approved": True})
    return result
