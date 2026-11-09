"""Latest revisions, distinct people and independent target evidence."""
import math
from datetime import datetime


def probabilities_index(probabilities):
    if not isinstance(probabilities, dict) or set(probabilities) != {"negative", "neutral", "positive"}:
        raise ValueError("Calibrated genuine three-class probabilities are required.")
    values = list(probabilities.values())
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1 for value in values) or abs(sum(values) - 1) > 1e-6:
        raise ValueError("Invalid sentiment probability distribution.")
    return 100 * (probabilities["positive"] + 0.5 * probabilities["neutral"])


def eligible(rows, movie_id, policy):
    latest, rejected = {}, {}
    def reject(reason):
        rejected[reason] = rejected.get(reason, 0) + 1
    for index, row in enumerate(rows):
        if index >= 100000:
            raise ValueError("Prepare bounded movie-linked score inputs.")
        if str(row.get("movie_id")) != str(movie_id):
            continue
        identifier, revision = row.get("review_id"), row.get("review_revision")
        if not isinstance(identifier, str) or not identifier or type(revision) is not int or revision < 1:
            raise ValueError("Invalid review identity/revision.")
        previous = latest.get(identifier)
        if previous and previous["review_revision"] == revision and previous != row:
            raise ValueError("Conflicting payloads at an identical review revision; reconcile before scoring.")
        if not previous or revision > previous["review_revision"]:
            latest[identifier] = row
    def timestamp(row):
        value = datetime.fromisoformat(str(row.get("created_at", "")).replace("Z", "+00:00"))
        if value.tzinfo is None:
            raise ValueError("Actual timezone-aware creation timestamps are required for reviewer deduplication.")
        return value.timestamp()
    selected, hashes, reviewers = [], set(), set()
    for identifier, row in sorted(latest.items(), key=lambda item: (timestamp(item[1]), item[0]), reverse=True):
        if row.get("is_deleted") is not False or row.get("is_synthetic") is not False or row.get("evidence_permitted") is not True or row.get("moderation_status") != "published":
            reject("ineligible_review")
            continue
        if row.get("model_version") != policy.model_version or row.get("calibrated") is not True or row.get("prediction_approved") is not True:
            reject("unapproved_or_stale_prediction")
            continue
        reviewer, text_hash = row.get("reviewer_id"), row.get("text_sha256")
        if not isinstance(reviewer, str) or not reviewer or not isinstance(text_hash, str) or len(text_hash) != 64 or any(c not in "0123456789abcdef" for c in text_hash):
            reject("identity_or_hash_missing")
            continue
        if reviewer in reviewers or text_hash in hashes:
            reject("dependent_or_duplicate_evidence")
            continue
        score = probabilities_index(row["probabilities"])
        weight = row.get("quality_weight", 1.0)
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or not 0 <= weight <= 1:
            raise ValueError("A documented moderation-quality weight in0..1 is required.")
        selected.append({"review_id": identifier, "revision": row["review_revision"], "reviewer_id": reviewer,
                         "text_sha256": text_hash, "score": score, "weight": float(weight),
                         "label": max(("negative", "neutral", "positive"), key=row["probabilities"].__getitem__)})
        reviewers.add(reviewer)
        hashes.add(text_hash)
    return selected, rejected
