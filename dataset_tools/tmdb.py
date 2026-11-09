"""Validate manually cached TMDB metadata without fetching any external data."""
from __future__ import annotations

from collections import Counter
from datetime import date
import json
from pathlib import Path
import sqlite3

from .io import IssueCollector, base_report, fingerprint_file, snapshot_file, write_json_new
from .recordio import (
    RecordFormatError, input_files, iter_records, parse_json, stable_inputs,
    strict_int, utc_time, validation_workspace,
)


def _provenance(path) -> tuple[dict | None, list[str]]:
    if path is None or not Path(path).is_file():
        return None, ["tmdb_provenance_manifest_missing"]
    value = Path(path)
    if value.stat().st_size > 65536:
        raise ValueError("Provenance manifest exceeds the 64KiB limit.")
    try:
        manifest = parse_json(value.read_text(encoding="utf-8-sig"))
    except (RecordFormatError, UnicodeError):
        return None, ["tmdb_provenance_manifest_invalid"]
    if not isinstance(manifest, dict):
        return None, ["tmdb_provenance_manifest_invalid"]
    required = ("snapshot_version", "terms_version")
    valid = (
        manifest.get("source") == "tmdb"
        and all(isinstance(manifest.get(key), str) and manifest[key].strip() for key in required)
        and utc_time(manifest.get("retrieved_at")) is not None
        and manifest.get("usage_approved") is True
        and manifest.get("attribution_acknowledged") is True
    )
    return (manifest, []) if valid else (None, ["tmdb_provenance_manifest_invalid"])


def validate_tmdb_record(record: dict) -> tuple[list[str], list[str]]:
    errors, missing = [], []
    identifier = strict_int(record.get("id"), 1)
    if identifier is None or identifier > 9223372036854775807:
        errors.append("id")
    if not isinstance(record.get("title"), str) or not record["title"].strip():
        errors.append("title")
    overview = record.get("overview")
    if overview is None or overview == "":
        missing.append("overview")
    elif not isinstance(overview, str):
        errors.append("overview")
    release = record.get("release_date")
    if release is None or release == "":
        missing.append("release_date")
    elif isinstance(release, str):
        try:
            date.fromisoformat(release)
            if len(release) != 10:
                errors.append("release_date")
        except ValueError:
            errors.append("release_date")
    else:
        errors.append("release_date")
    runtime = record.get("runtime")
    if runtime in (None, "") or (runtime == 0 and not isinstance(runtime, bool)):
        missing.append("runtime")
    elif strict_int(runtime, 1) is None:
        errors.append("runtime")
    language = record.get("original_language")
    if language is None or language == "":
        missing.append("original_language")
    elif not isinstance(language, str) or not 2 <= len(language) <= 3 or not language.isalpha():
        errors.append("original_language")
    genres = record.get("genres")
    if genres is None:
        missing.append("genres")
    elif not isinstance(genres, list):
        errors.append("genres")
    else:
        genre_ids = set()
        for genre in genres:
            if (not isinstance(genre, dict) or strict_int(genre.get("id"), 1) is None
                    or not isinstance(genre.get("name"), str) or not genre["name"].strip()):
                errors.append("genre_record")
                continue
            identifier = strict_int(genre["id"], 1)
            if identifier in genre_ids:
                errors.append("duplicate_genre")
            genre_ids.add(identifier)
        if not genres:
            missing.append("genres")
    for field in ("poster_path", "backdrop_path"):
        path = record.get(field)
        if path is not None and not isinstance(path, str):
            errors.append(field)
    for field in ("credits", "keywords"):
        value = record.get(field)
        if value is not None and not isinstance(value, (dict, list)):
            errors.append(field)
    return list(dict.fromkeys(errors)), missing


def validate_tmdb_snapshots(source, provenance=None, output=None, workspace=None,
                            write_accepted: bool = False) -> dict:
    report = base_report("tmdb_local_metadata")
    files = input_files(source, exclude=(provenance,))
    if not files:
        report.update(status="missing", blockers=["tmdb_snapshot_input_missing"])
        return report
    if write_accepted and output is None:
        raise ValueError("Accepted export requires an explicit fresh output directory.")
    manifest, blockers = _provenance(provenance)
    report["blockers"].extend(blockers)
    before = {str(path): snapshot_file(path) for path in files}
    if provenance and Path(provenance).is_file():
        before[str(Path(provenance))] = snapshot_file(provenance)
    issues = IssueCollector()
    counts = Counter(records=0, valid=0, rejected=0, duplicates=0)
    missing_fields = Counter()
    with validation_workspace(output, workspace) as (folder, database):
        database.execute("CREATE TABLE identifiers (id INTEGER PRIMARY KEY)")
        accepted = (folder / "accepted.jsonl").open("x", encoding="utf-8", newline="\n") if (
            folder and write_accepted) else None
        rejected = (folder / "rejected.jsonl").open("x", encoding="utf-8", newline="\n") if folder else None
        try:
            for path in files:
                try:
                    for container in iter_records(path):
                        records = container.get("results") if "results" in container else [container]
                        if not isinstance(records, list):
                            issues.add("invalid_results_container")
                            continue
                        for record in records:
                            counts["records"] += 1
                            if not isinstance(record, dict):
                                errors, absent = ["record_object"], []
                            else:
                                errors, absent = validate_tmdb_record(record)
                                if not errors:
                                    try:
                                        database.execute("INSERT INTO identifiers VALUES (?)",
                                            (strict_int(record["id"], 1),))
                                    except sqlite3.IntegrityError:
                                        counts["duplicates"] += 1
                                        errors.append("duplicate_tmdb_id")
                            missing_fields.update(absent)
                            for field in errors:
                                issues.add("invalid_" + field, counts["records"], field=field)
                            if errors:
                                counts["rejected"] += 1
                                if rejected:
                                    rejected.write(json.dumps({"record": counts["records"], "reasons": errors}) + "\n")
                            else:
                                counts["valid"] += 1
                                if accepted and manifest:
                                    copy = dict(record)
                                    copy["tmdb_id"] = strict_int(record["id"], 1)
                                    copy["canonical_movie_id"] = None
                                    copy["metadata_source"] = "tmdb_snapshot"
                                    copy["snapshot_version"] = manifest["snapshot_version"]
                                    copy["retrieved_at"] = manifest["retrieved_at"]
                                    accepted.write(json.dumps(copy, ensure_ascii=False, allow_nan=False) + "\n")
                except RecordFormatError:
                    issues.add("invalid_source_format", counts["records"] + 1)
        finally:
            if accepted:
                accepted.close()
            if rejected:
                rejected.close()
        if not counts["records"]:
            report["blockers"].append("tmdb_snapshot_input_empty")
        if not stable_inputs(before):
            issues.add("input_changed_during_validation")
        report["counts"] = dict(counts)
        report["nullable_field_counts"] = dict(missing_fields)
        report["issues"] = issues.as_dict()
        report["checks_complete"] = ["local_json_schema", "metadata_nullable_fields",
            "disk_backed_source_id_duplicates", "provenance_manifest", "input_stat_preservation"]
        report["notes"] = [
            "Only local files were read; no TMDB endpoint, poster URL or external resource was fetched.",
            "Validated source IDs are not approved canonical application movie IDs.",
            "A structurally valid terms manifest does not independently authenticate usage rights.",
            "Accepted copies use JSONL. Parquet export waits for a manually installed and verified PyArrow.",
            "Artwork paths remain metadata; no artwork redistribution permission is inferred.",
        ]
        report["status"] = "invalid" if issues.has_errors else "partial" if report["blockers"] else "complete"
        report["input_fingerprints"] = {str(path): fingerprint_file(path) for path in files}
        if provenance and Path(provenance).is_file():
            report["input_fingerprints"]["provenance"] = fingerprint_file(provenance)
        if folder:
            report["artifacts"] = {"report": str(folder / "report.json"),
                                  "rejected": str(folder / "rejected.jsonl")}
            if accepted:
                report["artifacts"]["accepted"] = str(folder / "accepted.jsonl")
            write_json_new(folder / "report.json", report, workspace)
    return report
