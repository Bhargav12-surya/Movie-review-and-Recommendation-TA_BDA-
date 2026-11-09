"""Validate permitted, canonical-movie-linked review revision exports."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sqlite3

from .io import IssueCollector, base_report, fingerprint_file, snapshot_file, write_json_new
from .recordio import (
    RecordFormatError, anonymous_key, bool_value, input_files, iter_records,
    load_registry, stable_inputs, strict_int, text_hash, utc_time,
    validation_workspace,
)

MODERATION_STATES = {"published", "approved", "pending", "held", "rejected"}


def validate_review_record(record: dict, movie_ids: set[str] | None = None) -> list[str]:
    """Return field/policy errors without returning private source values."""
    errors = []
    review_id = record.get("review_id")
    if not isinstance(review_id, str) or not review_id.strip():
        errors.append("review_id")
    movie_id = record.get("movie_id")
    if movie_id is None or isinstance(movie_id, bool) or not str(movie_id).strip():
        errors.append("movie_id")
    elif movie_ids is not None and str(movie_id) not in movie_ids:
        errors.append("movie_id_not_in_approved_registry")
    revision = strict_int(record.get("revision"), 1)
    if revision is None:
        errors.append("revision")
    text = record.get("review_text")
    deleted = bool_value(record.get("is_deleted")) is True
    if deleted and text in (None, ""):
        if record.get("text_sha256") not in (None, "") and not (
                isinstance(record["text_sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", record["text_sha256"])):
            errors.append("text_sha256")
    elif not isinstance(text, str) or not text.strip():
        errors.append("review_text")
    elif record.get("text_sha256") not in (None, "", text_hash(text)):
        errors.append("text_sha256")
    if not isinstance(record.get("language_code"), str) or not re.fullmatch(
            r"[a-z]{2,3}(?:-[A-Z]{2})?", record.get("language_code", "")):
        errors.append("language_code")
    created = utc_time(record.get("created_at"))
    updated = utc_time(record.get("updated_at", record.get("created_at")))
    if created is None:
        errors.append("created_at")
    if updated is None or (created is not None and updated < created):
        errors.append("updated_at")
    if record.get("moderation_status") not in MODERATION_STATES:
        errors.append("moderation_status")
    if bool_value(record.get("is_deleted")) is None:
        errors.append("is_deleted")
    source = record.get("source")
    if not isinstance(source, str) or not source.strip():
        errors.append("source")
    if (bool_value(record.get("is_synthetic")) is True
            or any(term in str(source).casefold() for term in ("synthetic", "demo", "fictional"))):
        errors.append("synthetic_source_not_eligible")
    source_type = record.get("source_type")
    if source_type == "first_party":
        if not isinstance(record.get("consent_version"), str) or not record["consent_version"].strip():
            errors.append("consent_version")
        permitted = bool_value(record.get("analysis_permitted"))
        if permitted is None or (not deleted and permitted is not True):
            errors.append("analysis_permission")
        if bool_value(record.get("training_permitted")) is None:
            errors.append("training_permission")
    elif source_type == "licensed":
        if not isinstance(record.get("license"), str) or not record["license"].strip():
            errors.append("license")
        if not isinstance(record.get("terms_version"), str) or not record["terms_version"].strip():
            errors.append("terms_version")
        if bool_value(record.get("usage_approved")) is not True:
            errors.append("usage_approval")
        if bool_value(record.get("training_permitted")) is None:
            errors.append("training_permission")
    else:
        errors.append("source_type")
    return errors


def validate_reviews(source, registry=None, output=None, workspace=None,
                     write_accepted: bool = False) -> dict:
    """Audit revisions and optionally export eligible copies to a fresh directory.

    The accepted stream contains versioned records, not an audience aggregation.
    Deletions and moderation-inactive rows are counted but excluded from it.
    A canonical registry is required before any record becomes eligible.
    """
    report = base_report("movie_linked_reviews")
    files = input_files(source)
    if not files:
        report.update(status="missing", blockers=["review_input_missing"])
        return report
    if write_accepted and output is None:
        raise ValueError("Accepted export requires an explicit fresh output directory.")
    movie_ids, blockers = load_registry(registry)
    report["blockers"].extend(blockers)
    issues = IssueCollector()
    counts: Counter = Counter(records=0, accepted=0, rejected=0, inactive=0,
                              duplicate_revision_keys=0, duplicate_normalized_texts=0)
    before = {str(path): snapshot_file(path) for path in files}
    if registry and Path(registry).is_file():
        before[str(Path(registry))] = snapshot_file(registry)
    lengths = {"minimum": None, "maximum": None}
    with validation_workspace(output, workspace) as (folder, database):
        database.execute("CREATE TABLE revisions (key TEXT PRIMARY KEY, normalized_hash TEXT)")
        database.execute("CREATE TABLE texts (hash TEXT PRIMARY KEY)")
        accepted = (folder / "accepted.jsonl").open("x", encoding="utf-8", newline="\n") if (
            folder and write_accepted) else None
        rejected = (folder / "rejected.jsonl").open("x", encoding="utf-8", newline="\n") if folder else None
        try:
            for path in files:
                try:
                    for record in iter_records(path):
                        counts["records"] += 1
                        number = counts["records"]
                        errors = validate_review_record(record, movie_ids if not blockers else None)
                        original = record.get("review_text")
                        if isinstance(original, str):
                            size = len(original)
                            lengths["minimum"] = size if lengths["minimum"] is None else min(lengths["minimum"], size)
                            lengths["maximum"] = size if lengths["maximum"] is None else max(lengths["maximum"], size)
                        if not errors:
                            identity = str(record["review_id"]) + "\0" + str(strict_int(record["revision"], 1))
                            digest = text_hash(" ".join(original.casefold().split())) if isinstance(original, str) else None
                            try:
                                database.execute("INSERT INTO revisions VALUES (?,?)", (text_hash(identity), digest))
                            except sqlite3.IntegrityError:
                                counts["duplicate_revision_keys"] += 1
                                errors.append("duplicate_review_revision")
                            if digest is not None:
                                duplicate = database.execute("SELECT 1 FROM texts WHERE hash=?", (digest,)).fetchone()
                                if duplicate:
                                    counts["duplicate_normalized_texts"] += 1
                                    issues.add("duplicate_normalized_text", number, severity="warning")
                                else:
                                    database.execute("INSERT INTO texts VALUES (?)", (digest,))
                        for field in errors:
                            issues.add("invalid_" + field, number, field=field)
                        if errors:
                            counts["rejected"] += 1
                            if rejected:
                                rejected.write(json.dumps({"record": number, "reasons": errors,
                                    "review_key_hash": anonymous_key(record.get("review_id", "")),
                                    "text_sha256": text_hash(original) if isinstance(original, str) else None}) + "\n")
                        elif blockers:
                            counts["blocked_registry_records"] += 1
                        elif (bool_value(record["is_deleted"])
                              or record["moderation_status"] not in {"published", "approved"}):
                            counts["inactive"] += 1
                            if bool_value(record["is_deleted"]) and original in (None, ""):
                                counts["tombstones_without_text"] += 1
                        else:
                            counts["accepted"] += 1
                            if accepted:
                                copy = dict(record)
                                copy["revision"] = strict_int(record["revision"], 1)
                                for name in ("is_deleted", "training_permitted", "analysis_permitted", "usage_approved"):
                                    if name in copy:
                                        copy[name] = bool_value(copy[name])
                                copy["text_sha256"] = text_hash(original)
                                copy["normalization"] = "identity-v1"
                                accepted.write(json.dumps(copy, ensure_ascii=False, allow_nan=False) + "\n")
                except RecordFormatError:
                    issues.add("invalid_source_format", counts["records"] + 1)
                    report["blockers"].append("source_format_requires_correction")
        finally:
            if accepted:
                accepted.close()
            if rejected:
                rejected.close()
        if not counts["records"]:
            report["blockers"].append("review_input_empty")
        unchanged = stable_inputs(before)
        if not unchanged:
            issues.add("input_changed_during_validation")
            report["blockers"].append("input_snapshot_changed")
        report["counts"] = dict(counts)
        report["text_lengths_characters"] = lengths
        report["issues"] = issues.as_dict()
        report["checks_complete"] = ["streaming_schema", "consent_and_provenance",
            "original_text_hash", "canonical_registry" if not blockers else "canonical_registry_blocked",
            "disk_backed_exact_revision_and_normalized_text_duplicates", "input_stat_preservation"]
        report["notes"] = [
            "Accepted counts describe eligible revision records, not distinct audience members.",
            "Original review text is unchanged; character offsets remain in the original text.",
            "Deleted tombstones may omit removed text; its old content hash cannot be reverified without that text.",
            "Source/consent assertions are validated structurally, not independently authenticated.",
            "Near-duplicate clustering and split leakage are separate checks; not claimed here.",
        ]
        report["status"] = "invalid" if issues.has_errors else "partial" if report["blockers"] else "complete"
        report["input_fingerprints"] = {str(path): fingerprint_file(path) for path in files}
        if registry and Path(registry).is_file():
            report["input_fingerprints"]["canonical_registry"] = fingerprint_file(registry)
        if folder:
            report["artifacts"] = {"report": str(folder / "report.json"),
                                  "rejected": str(folder / "rejected.jsonl")}
            if accepted:
                report["artifacts"]["accepted"] = str(folder / "accepted.jsonl")
            write_json_new(folder / "report.json", report, workspace)
    return report
