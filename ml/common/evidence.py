"""Permission-backed movie review snapshots for retrieval, never IMDb joins."""
from dataclasses import dataclass
import hashlib
import json
import re
from .artifacts import read_json
from .data import _rows


@dataclass(frozen=True)
class Evidence:
    review_id: str
    revision: int
    movie_id: str
    text: str
    text_sha256: str
    language_code: str
    sentiment: str | None
    aspects: tuple[str, ...]


def snapshot(rows, movie_id, maximum_reviews=10000):
    """Latest revision, then eligibility, then exact-normalized text deduplication."""
    if not movie_id:
        raise ValueError("A validated canonical movie ID is required.")
    latest = {}
    for index, row in enumerate(rows):
        if index >= 100000:
            raise ValueError("Evidence input exceeds the bounded local review budget.")
        if str(row.get("movie_id")) != str(movie_id):
            continue
        identifier, revision = row.get("review_id"), row.get("review_revision")
        if not isinstance(identifier, str) or not identifier or type(revision) is not int or revision < 1:
            raise ValueError("Review identity/revision is invalid.")
        if identifier in latest and revision == latest[identifier]["review_revision"] and row != latest[identifier]:
            raise ValueError("Conflicting payloads for the same review revision.")
        if identifier not in latest or revision > latest[identifier]["review_revision"]:
            latest[identifier] = row
    result, seen = [], set()
    for identifier, row in sorted(latest.items()):
        if row.get("is_deleted") is not False or row.get("is_synthetic") is not False or row.get("evidence_permitted") is not True or row.get("moderation_status") != "published" or not row.get("consent_or_license_ref"):
            continue
        text = row.get("review_text")
        if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 512 * 1024:
            raise ValueError("Original evidence text is missing or oversized.")
        checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if checksum != row.get("text_sha256"):
            raise ValueError("Evidence original-text fingerprint mismatch.")
        normalized = " ".join(text.casefold().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        sentiment = row.get("sentiment_label") if row.get("prediction_approved") is True else None
        if sentiment not in {None, "negative", "neutral", "positive"}:
            raise ValueError("Unknown evidence polarity.")
        aspects = row.get("aspect_categories", []) if row.get("prediction_approved") is True else []
        if not isinstance(aspects, list) or any(not isinstance(item, str) for item in aspects):
            raise ValueError("Invalid aspect evidence metadata.")
        result.append(Evidence(identifier, row["review_revision"], str(movie_id), text, checksum,
                               row.get("language_code", "unknown"), sentiment, tuple(aspects)))
        if len(result) > maximum_reviews:
            raise ValueError("Movie evidence budget exceeded; prepare a reviewed bounded snapshot.")
    manifest = [{"review_id": row.review_id, "revision": row.revision, "text_sha256": row.text_sha256} for row in result]
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return result, {"movie_id": str(movie_id), "snapshot_sha256": digest, "review_count": len(result), "evidence": manifest}


def balanced_retrieval(evidence, limit=24):
    if not 1 <= limit <= 64:
        raise ValueError("Select1..64 evidence reviews.")
    buckets = {name: [] for name in ("negative", "neutral", "positive", None)}
    for row in evidence:
        buckets[row.sentiment].append(row)
    # Stable round robin balances polarity; within each group, prioritize unseen
    # discussed aspects, then source ID. This does not change population counts.
    selected, covered = [], set()
    while len(selected) < limit and any(buckets.values()):
        for bucket in buckets.values():
            if bucket and len(selected) < limit:
                bucket.sort(key=lambda row: (-len(set(row.aspects) - covered), row.review_id))
                chosen = bucket.pop(0)
                selected.append(chosen)
                covered.update(chosen.aspects)
    return selected


def snapshot_stale(saved, current):
    return saved.get("movie_id") != current.get("movie_id") or saved.get("snapshot_sha256") != current.get("snapshot_sha256")
