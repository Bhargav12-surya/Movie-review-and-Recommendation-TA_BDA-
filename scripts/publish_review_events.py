"""Validate supplied analysis events; optionally publish a new atomic JSONL file.

No predictions are generated. Source files stay unchanged. Synthetic events
need an explicit flag and remain labelled. No HTTP/model/database calls occur.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spark_job_launcher import local_path

FIELDS = {"event_id", "review_id", "review_revision", "movie_id", "operation", "event_time",
          "positive_probability", "neutral_probability", "negative_probability", "model_version",
          "canonical_movie_validated", "consent_eligible", "moderation_eligible", "is_synthetic"}
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9:_-]{0,127}\Z")
MAX_BYTES = 32 * 1024 * 1024
MAX_ROWS = 100000
MAX_LINE = 65536


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite_json_number")


def validate_event(event: dict, allow_synthetic: bool = False) -> None:
    if not isinstance(event, dict) or set(event) != FIELDS:
        raise ValueError("event_fields_mismatch")
    if not all(isinstance(event[key], str) and IDENTIFIER.fullmatch(event[key])
               for key in ("event_id", "review_id", "movie_id")):
        raise ValueError("invalid_identifiers")
    revision = event["review_revision"]
    if type(revision) is not int or not 1 <= revision <= 2**63 - 1:
        raise ValueError("invalid_revision")
    if event["operation"] not in ("upsert", "delete"):
        raise ValueError("invalid_operation")
    for key in ("canonical_movie_validated", "consent_eligible", "moderation_eligible", "is_synthetic"):
        if type(event[key]) is not bool:
            raise ValueError("explicit_boolean_flags_required")
    if not event["canonical_movie_validated"]:
        raise ValueError("unvalidated_canonical_movie")
    if event["is_synthetic"] and not allow_synthetic:
        raise ValueError("synthetic_permission_required")
    stamp = event["event_time"]
    try:
        if not isinstance(stamp, str) or not re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?Z", stamp):
            raise ValueError()
        parsed = datetime.fromisoformat(stamp[:-1] + "+00:00")
    except (ValueError, TypeError):
        raise ValueError("invalid_utc_event_time") from None
    if parsed > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise ValueError("future_event")
    eligible = event["operation"] == "upsert" and event["consent_eligible"] and event["moderation_eligible"]
    if eligible:
        values = [event[key] for key in ("positive_probability", "neutral_probability", "negative_probability")]
        if not all(type(value) in (float, int) and math.isfinite(value) and 0 <= value <= 1 for value in values):
            raise ValueError("invalid_sentiment_probabilities")
        if abs(sum(values) - 1.0) > 0.000001:
            raise ValueError("invalid_sentiment_probabilities")
        if not isinstance(event["model_version"], str) or not IDENTIFIER.fullmatch(event["model_version"]):
            raise ValueError("missing_model_version")
    # Optional values still need the physical types expected by the Scala schema.
    for key in ("positive_probability", "neutral_probability", "negative_probability"):
        value = event[key]
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1):
            raise ValueError("invalid_optional_probability_type")
    if event["model_version"] is not None and not isinstance(event["model_version"], str):
        raise ValueError("invalid_optional_model_type")


def process(root: Path, source: Path, destination: Path | None, allow_synthetic: bool = False) -> dict:
    root = root.resolve()
    source = local_path(root, source)
    if not source.is_file() or source.stat().st_size > MAX_BYTES:
        raise ValueError("source_missing_or_size_limit")
    before = (source.stat().st_size, source.stat().st_mtime_ns)
    folder = local_path(root, destination, output=True) if destination is not None else None
    if folder and source.is_relative_to(folder):
        raise ValueError("source_must_be_outside_watched_directory")
    unpublished = published = None
    stream = None
    rows = synthetic_rows = 0
    try:
        if folder:
            folder.mkdir(parents=True, exist_ok=True)
            identity = uuid.uuid4().hex
            unpublished = folder / (".unpublished-" + identity)
            published = folder / ("events-" + identity + ".jsonl")
            stream = unpublished.open("xb")
        with source.open("rb") as input_stream:
            while True:
                line = input_stream.readline(MAX_LINE + 1)
                if not line:
                    break
                if len(line) > MAX_LINE or not line.strip():
                    raise ValueError("oversized_or_blank_jsonl_line")
                rows += 1
                if rows > MAX_ROWS:
                    raise ValueError("source_row_limit")
                try:
                    event = json.loads(line.decode("utf-8"), object_pairs_hook=unique_object,
                                       parse_constant=reject_constant)
                    validate_event(event, allow_synthetic)
                except (ValueError, UnicodeError, RecursionError):
                    # Do not echo values, review text or untrusted field names.
                    raise ValueError("invalid_event_at_line_" + str(rows)) from None
                synthetic_rows += int(event["is_synthetic"])
                if stream:
                    stream.write((json.dumps(event, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8"))
        if rows == 0:
            raise ValueError("empty_event_file")
        if before != (source.stat().st_size, source.stat().st_mtime_ns):
            raise ValueError("source_changed_during_validation")
        if stream:
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            stream = None
            # Same directory/volume. On Windows os.rename refuses existing destinations.
            # Unique file identity and single publisher policy also avoid filename reuse.
            if published.exists():
                raise ValueError("publication_destination_exists")
            os.rename(unpublished, published)
        return {"status": "published" if folder else "validated_only", "rows": rows,
                "synthetic_rows": synthetic_rows, "source_unchanged": True,
                "published_file": str(published) if published else None}
    finally:
        if stream:
            stream.close()
        # Failed partial files remain dot-prefixed and invisible to Spark; never reused.


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--input", required=True)
    parser.add_argument("--publish-to", help="Explicit watched directory; omit to validate only.")
    parser.add_argument("--allow-synthetic-events", action="store_true")
    args = parser.parse_args()
    try:
        report = process(Path(args.workspace), Path(args.input), Path(args.publish_to) if args.publish_to else None,
                         args.allow_synthetic_events)
        print(json.dumps(report, indent=2))
        return 0
    except (ValueError, OSError) as error:
        code = str(error) if isinstance(error, ValueError) else "filesystem_error"
        print(json.dumps({"status": "rejected", "reason": code, "published": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
