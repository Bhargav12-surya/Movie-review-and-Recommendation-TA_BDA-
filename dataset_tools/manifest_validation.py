"""Independently verify saved IMDb reference manifests against a static audit index."""
from __future__ import annotations

from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from .io import IssueCollector, base_report, create_output_dir, fingerprint_file, write_json_new

SPLITS = ("train", "validation", "test", "excluded", "unsup")


def validate_imdb_manifests(run: str | Path, output: str | Path, *,
                            workspace: str | Path | None = None) -> dict:
    run = Path(run).resolve()
    report = base_report("imdb_reference_manifest_verification")
    required = [run / "review_index.sqlite3", *(run / f"{name}.jsonl" for name in SPLITS)]
    if not all(path.is_file() for path in required):
        report.update(status="missing", blockers=["Completed audit index/reference manifests are absent."])
        return report
    target = create_output_dir(output, workspace)
    issues, counts, classes = IssueCollector(), Counter(), Counter()
    # Static completed index: immutable prevents SQLite bookkeeping writes.
    uri = (run / "review_index.sqlite3").as_uri() + "?mode=ro&immutable=1"
    with closing(sqlite3.connect(uri, uri=True)) as source, \
            closing(sqlite3.connect(target / "verification_index.sqlite3")) as seen:
        seen.execute("PRAGMA cache_size=-8192")
        seen.execute("CREATE TABLE entries(path TEXT PRIMARY KEY,destination TEXT,gid TEXT,norm TEXT,movie TEXT)")
        for destination in SPLITS:
            path = run / f"{destination}.jsonl"
            report["input_fingerprints"][destination] = fingerprint_file(path)
            with path.open(encoding="utf-8") as handle:
                for number, line in enumerate(handle, 1):
                    try:
                        row = json.loads(line)
                        if not isinstance(row, dict):
                            raise ValueError
                        original = source.execute(
                            "SELECT split,label,movie,raw_sha256,norm_sha256 FROM records WHERE path=?",
                            (row.get("source_path"),)).fetchone()
                        if original is None:
                            issues.add("unknown_source_record", number, destination)
                            continue
                        split, label, movie, raw_hash, norm_hash = original
                        expected_label = {"neg": 0, "pos": 1, "unsup": None}[label]
                        if (row.get("split") != destination or row.get("source_split") != split
                                or row.get("label") != expected_label or isinstance(row.get("label"), bool)
                                or row.get("source_movie_id") != movie
                                or row.get("raw_sha256") != raw_hash
                                or row.get("normalized_sha256") != norm_hash
                                or row.get("application_movie_id") is not None
                                or row.get("label_task") != "binary_imdb"):
                            issues.add("manifest_source_contract_mismatch", number, destination)
                        if split == "test" and destination != "test":
                            issues.add("official_test_moved", number, destination)
                        if destination == "test" and split != "test":
                            issues.add("nonofficial_test_record", number, destination)
                        if (label == "unsup") != (destination == "unsup"):
                            issues.add("unlabelled_supervised_contamination", number, destination)
                        if label != "unsup" and not row.get("group_id"):
                            issues.add("missing_group_id", number, destination)
                        try:
                            seen.execute("INSERT INTO entries VALUES(?,?,?,?,?)",
                                         (row["source_path"], destination, row.get("group_id"), norm_hash, movie))
                        except sqlite3.IntegrityError:
                            issues.add("duplicate_manifest_record", number, destination)
                        counts[destination] += 1
                        if expected_label is not None:
                            classes[(destination, expected_label)] += 1
                    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                        issues.add("malformed_manifest_record", number, destination)
            seen.commit()
        expected_rows = source.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        actual_rows = seen.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        expected_test = source.execute("SELECT COUNT(*) FROM records WHERE split='test'").fetchone()[0]
        if expected_rows != actual_rows:
            issues.add("source_record_coverage_mismatch")
        if counts["test"] != expected_test:
            issues.add("official_test_count_changed")
        overlap = {}
        for column in ("gid", "norm", "movie"):
            overlap[column] = seen.execute(
                f"SELECT COUNT(*) FROM (SELECT {column} FROM entries "
                "WHERE destination IN ('train','validation','test') "
                f"AND {column} IS NOT NULL GROUP BY {column} "
                "HAVING COUNT(DISTINCT destination)>1)").fetchone()[0]
            if overlap[column]:
                issues.add(f"cross_split_{column}_overlap")
        for split in ("train", "validation"):
            if not counts[split] or any(classes[(split, label)] == 0 for label in (0, 1)):
                issues.add("empty_or_unsupported_split", field=split)
    report.update(
        status="invalid" if issues.has_errors else "complete",
        counts=dict(counts), class_support={split: {str(label): classes[(split, label)] for label in (0, 1)}
                                           for split in ("train", "validation", "test")},
        cross_split_overlap_groups=overlap, issues=issues.as_dict(),
        checks_complete=["all_source_references_resolve", "raw_and_normalized_hashes_match_index",
                         "official_test_records_preserved", "all_source_records_covered_once",
                         "no_unlabelled_supervised_data", "group_text_movie_split_isolation", "class_support"],
        notes=["This verifies static reference manifests, not provenance rights or model performance."],
        artifacts={"report": str(target / "manifest_verification.json")},
        implementation_fingerprint=fingerprint_file(Path(__file__)),
    )
    write_json_new(target / "manifest_verification.json", report, workspace)
    return report
