"""Validate human annotation contracts and measure observed overlap agreement."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sqlite3

from .io import IssueCollector, base_report, fingerprint_file, snapshot_file, write_json_new
from .recordio import (
    RecordFormatError, anonymous_key, bool_value, input_files, iter_records, load_registry,
    nested, stable_inputs, strict_int, text_hash, validation_workspace,
)

SENTIMENTS = {"negative": 0, "neutral": 1, "positive": 2}
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "configs/data/annotations.json"


def load_annotation_config(path=None) -> dict:
    source = Path(path) if path else DEFAULT_CONFIG
    if source.stat().st_size > 65536:
        raise ValueError("Annotation configuration exceeds the 64KiB limit.")
    try:
        value = json.loads(source.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeError):
        raise ValueError("Malformed annotation configuration.") from None
    if (not isinstance(value, dict) or value.get("schema_version") != 1
            or value.get("sentiment_labels") != SENTIMENTS
            or not all(isinstance(label, int) and not isinstance(label, bool)
                       for label in value.get("sentiment_labels", {}).values())
            or value.get("offset_unit") != "original_unicode_code_points"
            or value.get("normalization") != "identity-v1"
            or not isinstance(value.get("sentiment_schema_version"), str)
            or not value["sentiment_schema_version"]
            or not isinstance(value.get("aspect_taxonomy_version"), str)
            or not value["aspect_taxonomy_version"]
            or strict_int(value.get("maximum_record_bytes"), 1) is None):
        raise ValueError("Annotation configuration has an unsupported schema or label/offset contract.")
    for field in ("aspects", "themes"):
        entries = value.get(field)
        if (not isinstance(entries, list) or not entries
                or not all(isinstance(item, str) and item for item in entries)
                or len(set(entries)) != len(entries)):
            raise ValueError("Annotation taxonomy must contain unique nonempty labels.")
    return value


def sentiment_label(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value in (0, 1, 2) else None
    if isinstance(value, str):
        if value in SENTIMENTS:
            return SENTIMENTS[value]
        if value in {"0", "1", "2"}:
            return int(value)
    return None


def _span(item: dict, text: str) -> bool:
    start, end = item.get("start"), item.get("end")
    return (isinstance(start, int) and not isinstance(start, bool)
            and isinstance(end, int) and not isinstance(end, bool)
            and 0 <= start < end <= len(text)
            and isinstance(item.get("text"), str)
            and text[start:end] == item["text"])


def validate_annotation_record(record: dict, movie_ids: set[str] | None = None,
                               allow_mixed: bool = False, config=None) -> list[str]:
    config = config if config is not None else load_annotation_config()
    errors = []
    if not isinstance(record.get("review_id"), str) or not record["review_id"].strip():
        errors.append("review_id")
    if strict_int(record.get("review_revision"), 1) is None:
        errors.append("review_revision")
    movie_id = record.get("movie_id")
    if movie_id is None or isinstance(movie_id, bool) or not str(movie_id).strip():
        errors.append("movie_id")
    elif movie_ids is not None and str(movie_id) not in movie_ids:
        errors.append("movie_id_not_in_approved_registry")
    text = record.get("review_text")
    if not isinstance(text, str) or not text.strip():
        errors.append("review_text")
        text = ""
    if record.get("text_sha256") != text_hash(text):
        errors.append("text_sha256")
    if sentiment_label(record.get("sentiment")) is None:
        errors.append("sentiment")
    if record.get("label_schema_version") != config["sentiment_schema_version"]:
        errors.append("label_schema_version")
    if record.get("taxonomy_version") != config["aspect_taxonomy_version"]:
        errors.append("taxonomy_version")
    if not isinstance(record.get("annotator_id"), str) or not record["annotator_id"].strip():
        errors.append("annotator_id")
    state = record.get("annotation_status")
    if state not in {"annotated", "adjudicated"}:
        errors.append("annotation_status")
    if state == "adjudicated" and (
            not isinstance(record.get("adjudicator_id"), str)
            or not record["adjudicator_id"].strip()):
        errors.append("adjudicator_id")
    if not isinstance(record.get("annotation_guideline_version"), str) or not record["annotation_guideline_version"].strip():
        errors.append("annotation_guideline_version")
    if bool_value(record.get("training_permitted")) is not True:
        errors.append("training_permission")
    if (bool_value(record.get("is_synthetic")) is True
            or any(term in str(record.get("source", "")).casefold()
                   for term in ("synthetic", "demo", "fictional"))):
        errors.append("synthetic_annotation_not_eligible")
    if not isinstance(record.get("consent_or_license_ref"), str) or not record["consent_or_license_ref"].strip():
        errors.append("consent_or_license_ref")
    try:
        aspects = nested(record.get("aspects"), [])
        themes = nested(record.get("themes"), [])
    except RecordFormatError:
        return errors + ["nested_annotation_json"]
    if not isinstance(aspects, list):
        errors.append("aspects")
        aspects = []
    if not isinstance(themes, list):
        errors.append("themes")
        themes = []
    spans = []
    polarities = set(SENTIMENTS) | ({"mixed"} if allow_mixed else set())
    for index, aspect in enumerate(aspects):
        if not isinstance(aspect, dict):
            errors.append("aspect_object")
            continue
        if aspect.get("aspect") not in config["aspects"]:
            errors.append("aspect_category")
        if aspect.get("implicit") is True:
            errors.append("implicit_aspect_policy_not_supported")
        if not _span(aspect, text):
            errors.append("aspect_span")
        else:
            spans.append((aspect["start"], aspect["end"], index))
        if aspect.get("sentiment") not in polarities:
            errors.append("aspect_sentiment")
    spans.sort()
    if any(current[0] < previous[1] for previous, current in zip(spans, spans[1:])):
        errors.append("overlapping_aspect_spans")
    for theme in themes:
        if not isinstance(theme, dict):
            errors.append("theme_object")
            continue
        if theme.get("theme") not in config["themes"]:
            errors.append("theme_category")
        if not isinstance(theme.get("relevant"), bool):
            errors.append("theme_relevance")
        reception = theme.get("sentiment")
        if reception is not None:
            if reception not in polarities:
                errors.append("theme_sentiment")
            if not _span(theme, text):
                errors.append("theme_reception_evidence")
        elif any(key in theme for key in ("start", "end", "text")) and not _span(theme, text):
            errors.append("theme_span")
    return list(dict.fromkeys(errors))


def _agreement(database) -> dict:
    """Exact pairwise Cohen kappa; hashed annotator IDs, no source text."""
    pairs = {}
    query = """
    SELECT a.annotator,b.annotator,a.label,b.label
    FROM annotations a JOIN annotations b
      ON a.review_key=b.review_key AND a.annotator<b.annotator
    ORDER BY a.annotator,b.annotator
    """
    for first, second, left, right in database.execute(query):
        key = first + ":" + second
        matrix = pairs.setdefault(key, [[0] * 3 for _ in range(3)])
        matrix[left][right] += 1
    results = []
    for key, matrix in sorted(pairs.items()):
        count = sum(sum(row) for row in matrix)
        row_totals = [sum(row) for row in matrix]
        column_totals = [sum(row[j] for row in matrix) for j in range(3)]
        observed = sum(matrix[i][i] for i in range(3)) / count
        expected = sum(row_totals[i] * column_totals[i] for i in range(3)) / count**2
        kappa = (observed - expected) / (1 - expected) if expected < 1 else None
        results.append({"annotator_pair_hash": key, "overlapping_items": count,
                        "confusion_counts": matrix, "observed_agreement": observed,
                        "chance_agreement": expected, "cohen_kappa": kappa,
                        "undefined_reason": "constant identical marginals" if kappa is None else None})
    return {"pairs": results, "pair_count": len(results),
            "method": "pairwise Cohen kappa on valid overlapping three-class sentiment annotations",
            "limitations": "No aspect-span agreement or adjudication quality is inferred. Different pairs may overlap the same review."}


def validate_annotations(source, registry=None, output=None, workspace=None,
                         allow_mixed: bool = False,
                         write_accepted: bool = False, config_path=None) -> dict:
    report = base_report("human_movie_review_annotations")
    files = input_files(source)
    if not files:
        report.update(status="missing", blockers=["annotation_input_missing"])
        return report
    if write_accepted and output is None:
        raise ValueError("Accepted export requires an explicit fresh output directory.")
    config = load_annotation_config(config_path)
    movie_ids, blockers = load_registry(registry)
    report["blockers"].extend(blockers)
    before = {str(path): snapshot_file(path) for path in files}
    if registry and Path(registry).is_file():
        before[str(Path(registry))] = snapshot_file(registry)
    issues = IssueCollector()
    counts = Counter(records=0, valid=0, rejected=0, adjudicated=0)
    labels = Counter()
    aspect_labels = Counter()
    theme_labels = Counter()
    with validation_workspace(output, workspace) as (folder, database):
        database.execute("CREATE TABLE annotations (review_key TEXT,annotator TEXT,label INTEGER,"
                         "text_hash TEXT,PRIMARY KEY(review_key,annotator))")
        accepted = (folder / "accepted.jsonl").open("x", encoding="utf-8", newline="\n") if (
            folder and write_accepted) else None
        rejected = (folder / "rejected.jsonl").open("x", encoding="utf-8", newline="\n") if folder else None
        try:
            for path in files:
                try:
                    for record in iter_records(path, max_record_bytes=config["maximum_record_bytes"]):
                        counts["records"] += 1
                        number = counts["records"]
                        errors = validate_annotation_record(record, movie_ids if not blockers else None,
                                                            allow_mixed, config)
                        if not errors:
                            key = text_hash(record["review_id"] + "\0" + str(strict_int(record["review_revision"], 1)))
                            annotator = anonymous_key(record["annotator_id"])
                            prior_text = database.execute(
                                "SELECT text_hash FROM annotations WHERE review_key=? LIMIT 1", (key,)).fetchone()
                            if prior_text and prior_text[0] != record["text_sha256"]:
                                errors.append("inconsistent_review_text_across_annotators")
                            try:
                                if not errors:
                                    database.execute("INSERT INTO annotations VALUES (?,?,?,?)",
                                        (key, annotator, sentiment_label(record["sentiment"]), record["text_sha256"]))
                            except sqlite3.IntegrityError:
                                errors.append("duplicate_annotator_review_revision")
                        for field in errors:
                            issues.add("invalid_" + field, number, field=field)
                        if errors:
                            counts["rejected"] += 1
                            if rejected:
                                rejected.write(json.dumps({"record": number, "reasons": errors,
                                    "review_key_hash": anonymous_key(record.get("review_id", ""))}) + "\n")
                        else:
                            counts["valid"] += 1
                            labels[str(sentiment_label(record["sentiment"]))] += 1
                            counts["adjudicated"] += record["annotation_status"] == "adjudicated"
                            for aspect in nested(record.get("aspects"), []):
                                aspect_labels[aspect["aspect"]] += 1
                            for theme in nested(record.get("themes"), []):
                                theme_labels[theme["theme"]] += 1
                            if accepted and not blockers:
                                copy = dict(record)
                                copy["aspects"] = nested(record.get("aspects"), [])
                                copy["themes"] = nested(record.get("themes"), [])
                                copy["sentiment"] = sentiment_label(record["sentiment"])
                                copy["review_revision"] = strict_int(record["review_revision"], 1)
                                copy["training_permitted"] = bool_value(record["training_permitted"])
                                accepted.write(json.dumps(copy, ensure_ascii=False, allow_nan=False) + "\n")
                except RecordFormatError:
                    issues.add("invalid_source_format", counts["records"] + 1)
        finally:
            if accepted:
                accepted.close()
            if rejected:
                rejected.close()
        if not counts["records"]:
            report["blockers"].append("annotation_input_empty")
        if not stable_inputs(before):
            issues.add("input_changed_during_validation")
        report["counts"] = dict(counts)
        report["sentiment_class_counts"] = dict(labels)
        report["aspect_counts"] = dict(aspect_labels)
        report["theme_counts"] = dict(theme_labels)
        report["agreement"] = _agreement(database)
        report["issues"] = issues.as_dict()
        report["checks_complete"] = ["annotation_schema", "original_unicode_character_offsets",
            "text_hash_and_revision", "label_and_taxonomy_versions", "consent_reference",
            "pairwise_sentiment_agreement", "input_stat_preservation"]
        report["notes"] = [
            "Positive/negative/neutral labels are supplied by annotators; no label was generated.",
            "Mixed aspect/theme sentiment is rejected unless explicitly enabled by the caller's approved policy.",
            "Explicit spans are nonoverlapping for a single-label BIO target; implicit aspects need a separate approved scheme.",
            "Training/validation/test split construction is separate and is not claimed by this annotation audit.",
        ]
        report["status"] = "invalid" if issues.has_errors else "partial" if report["blockers"] else "complete"
        report["input_fingerprints"] = {str(path): fingerprint_file(path) for path in files}
        report["configuration_fingerprint"] = fingerprint_file(config_path or DEFAULT_CONFIG)
        if registry and Path(registry).is_file():
            report["input_fingerprints"]["canonical_registry"] = fingerprint_file(registry)
        if folder:
            report["artifacts"] = {"report": str(folder / "report.json"),
                                  "rejected": str(folder / "rejected.jsonl")}
            if accepted:
                report["artifacts"]["accepted"] = str(folder / "accepted.jsonl")
            write_json_new(folder / "report.json", report, workspace)
    return report
