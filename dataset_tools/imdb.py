"""Local, streaming Stanford aclImdb inspection and leakage-aware manifests."""
from __future__ import annotations

from collections import Counter
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid

from .io import (IssueCollector, base_report, create_output_dir, fingerprint_file,
                 snapshot_file, write_json_new)
from .splits import (Groups, candidate_fingerprints, normalized_text,
                     shingle_jaccard, validation_group)
from .resources import peak_working_set_bytes, preflight

BUCKETS = (("train", "neg"), ("train", "pos"), ("train", "unsup"),
           ("test", "neg"), ("test", "pos"))
EXPECTED = {"train/neg": 12500, "train/pos": 12500, "train/unsup": 50000,
            "test/neg": 12500, "test/pos": 12500}
FILE_NAME = re.compile(r"^(\d+)_(\d+)\.txt$")
MOVIE_URL = re.compile(r"^https?://(?:www\.)?imdb\.com/title/(tt\d+)(?:/|$)", re.I)


def resolve_layout(source: str | Path) -> Path:
    source = Path(source).resolve()
    for candidate in (source, source / "aclImdb"):
        if (candidate / "train").is_dir() and (candidate / "test").is_dir():
            return candidate
    return source


def _folder_files(folder: Path):
    # At most one source bucket's filenames are retained; no review text corpus.
    if folder.is_dir():
        with os.scandir(folder) as entries:
            names = sorted(entry.name for entry in entries if entry.is_file(follow_symlinks=False)
                           and entry.name.lower().endswith(".txt"))
        for name in names:
            yield folder / name


def _urls(root: Path, split: str, label: str, issues: IssueCollector) -> list[str | None]:
    path = root / split / f"urls_{label}.txt"
    if not path.is_file():
        issues.add("missing_movie_url_file", field=f"{split}/{label}", severity="warning")
        return []
    result: list[str | None] = []
    with path.open("rb") as handle:
        number = 0
        while True:
            raw_line = handle.readline(8193)
            if not raw_line:
                break
            number += 1
            if len(raw_line) > 8192:
                while raw_line and not raw_line.endswith(b"\n"):
                    raw_line = handle.readline(8193)
                issues.add("oversized_movie_url", record=number, field=f"{split}/{label}")
                result.append(None)
                continue
            try:
                line = raw_line.decode("utf-8-sig" if number == 1 else "utf-8")
            except UnicodeError:
                issues.add("invalid_movie_url_utf8", record=number, field=f"{split}/{label}")
                result.append(None)
                continue
            match = MOVIE_URL.match(line.strip())
            result.append(match.group(1) if match else None)
            if not match:
                issues.add("invalid_movie_url", record=number, field=f"{split}/{label}")
    return result


def _open_index(path: Path) -> sqlite3.Connection:
    # This is a NEW derived index, never an existing/legacy/raw database.
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA cache_size=-16384")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute("""CREATE TABLE records(
        rid INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL,
        split TEXT NOT NULL, label TEXT NOT NULL, source_id INTEGER NOT NULL,
        movie TEXT, raw_sha256 TEXT NOT NULL, norm_sha256 TEXT NOT NULL,
        bytes INTEGER NOT NULL, chars INTEGER NOT NULL, mtime_ns INTEGER NOT NULL,
        UNIQUE(split,label,source_id))""")
    connection.execute("CREATE INDEX records_raw ON records(raw_sha256,split)")
    connection.execute("CREATE INDEX records_norm ON records(norm_sha256,split)")
    connection.execute("CREATE INDEX records_movie ON records(movie,split)")
    connection.execute("CREATE TABLE fingerprints(value TEXT NOT NULL,rid INTEGER NOT NULL)")
    connection.execute("CREATE INDEX fingerprints_lookup ON fingerprints(value,rid)")
    connection.execute("""CREATE TABLE near_pairs(
        left_id INTEGER NOT NULL,right_id INTEGER NOT NULL,similarity REAL NOT NULL,
        PRIMARY KEY(left_id,right_id))""")
    return connection


def _read_review(path: Path, max_bytes: int) -> tuple[str, bytes, dict]:
    before = snapshot_file(path)
    if before["bytes"] > max_bytes:
        raise ValueError("review_exceeds_configured_byte_limit")
    with path.open("rb") as handle:
        raw = handle.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("review_exceeds_configured_byte_limit")
    text = raw.decode("utf-8", errors="strict")
    if not text.strip():
        raise ValueError("empty_review")
    if before != snapshot_file(path):
        raise ValueError("input_changed_during_read")
    return text, raw, before


def audit_imdb(source: str | Path, output: str | Path | None = None, *,
               workspace: str | Path | None = None, max_reviews: int | None = None,
               expected_counts: dict | None = None, near_duplicates: bool = False,
               near_threshold: float = .9, candidate_limit: int = 128,
               max_review_bytes: int = 2 * 1024 * 1024) -> dict:
    start = time.perf_counter()
    root = resolve_layout(source)
    report = base_report("stanford_acl_imdb", "sample" if max_reviews else "full")
    report["input_root"] = str(root)
    report["implementation_fingerprints"] = {
        name: fingerprint_file(Path(__file__).parent / name)
        for name in ("imdb.py", "splits.py", "io.py", "resources.py")}
    resources = preflight(workspace or Path(__file__).resolve().parents[1])
    report["resources_before"] = resources["measurements"]
    if max_reviews is not None and max_reviews < 1:
        raise ValueError("max_reviews must be positive.")
    if not 0 < near_threshold <= 1 or not 1 <= candidate_limit <= 10000:
        raise ValueError("Invalid near-duplicate threshold or candidate limit.")
    if max_review_bytes < 1:
        raise ValueError("max_review_bytes must be positive.")
    if not all((root / split / label).is_dir() for split, label in BUCKETS):
        report.update(status="missing", blockers=["Required aclImdb train/test/unsup folders are absent."])
        return report
    if max_reviews is None and resources["blockers"]:
        report.update(status="partial", blockers=resources["blockers"])
        return report
    workroot = Path(workspace or Path(__file__).resolve().parents[1])
    if output is None:
        output = workroot / "artifacts/data_quality" / f"imdb-{uuid.uuid4().hex}"
    target = create_output_dir(output, workspace)
    index_path = target / "review_index.sqlite3"
    issues = IssueCollector()
    counts, lengths = Counter(), Counter()
    changed, near_compared, near_capped, near_verified = 0, 0, 0, 0
    metadata_before: dict[str, dict] = {}
    for small in [root / "README", root / "README.txt",
                  *(root / s / f"urls_{l}.txt" for s, l in BUCKETS)]:
        if small.is_file():
            metadata_before[str(small)] = snapshot_file(small)
            report["input_fingerprints"][str(small.relative_to(root))] = fingerprint_file(small)
    manifest_hash = hashlib.sha256()
    with closing(_open_index(index_path)) as db, \
            (target / "rejected.jsonl").open("x", encoding="utf-8", newline="\n") as rejected:
        processed = 0
        for split, label in BUCKETS:
            urls = _urls(root, split, label, issues)
            bucket = f"{split}/{label}"
            for path in _folder_files(root / split / label):
                if max_reviews is not None and processed >= max_reviews:
                    break
                processed += 1
                counts[bucket] += 1
                relative = path.relative_to(root).as_posix()
                reason = None
                match = FILE_NAME.fullmatch(path.name)
                if not match:
                    reason = "invalid_review_filename"
                else:
                    source_id, rating = map(int, match.groups())
                    if not ((label == "pos" and 7 <= rating <= 10)
                            or (label == "neg" and 1 <= rating <= 4)
                            or (label == "unsup" and rating == 0)):
                        reason = "filename_rating_disagrees_with_source_bucket"
                try:
                    if reason:
                        raise ValueError(reason)
                    text, raw, before = _read_review(path, max_review_bytes)
                    movie = urls[source_id] if source_id < len(urls) else None
                    if movie is None:
                        issues.add("review_movie_url_unresolved", record=processed,
                                   field=bucket, severity="warning")
                    raw_hash = hashlib.sha256(raw).hexdigest()
                    norm_hash = hashlib.sha256(normalized_text(text).encode("utf-8")).hexdigest()
                    try:
                        cursor = db.execute(
                            "INSERT INTO records(path,split,label,source_id,movie,raw_sha256,"
                            "norm_sha256,bytes,chars,mtime_ns) VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (relative, split, label, source_id, movie, raw_hash, norm_hash,
                             len(raw), len(text), before["mtime_ns"]))
                    except sqlite3.IntegrityError:
                        raise ValueError("duplicate_source_review_id") from None
                    rid = cursor.lastrowid
                    manifest_hash.update((relative + "\0" + raw_hash + "\n").encode())
                    lengths[len(text) // 250 * 250] += 1
                    counts["accepted"] += 1
                    if near_duplicates and label != "unsup":
                        signature = candidate_fingerprints(text)
                        if signature:
                            marks = ",".join("?" for _ in signature)
                            # One bounded candidate list; exact normalized duplicates
                            # are already exhaustively checked in the disk index.
                            candidates = db.execute(
                                "SELECT r.rid,r.path FROM fingerprints f "
                                "JOIN records r ON r.rid=f.rid "
                                f"WHERE f.value IN ({marks}) AND r.label!='unsup' "
                                "AND r.norm_sha256!=? GROUP BY r.rid "
                                "HAVING COUNT(*)>=? ORDER BY r.rid LIMIT ?",
                                (*signature, norm_hash, min(4, len(signature)), candidate_limit + 1)).fetchall()
                            if len(candidates) > candidate_limit:
                                near_capped += 1
                            for other_id, other_path in candidates[:candidate_limit]:
                                try:
                                    other_text, _, _ = _read_review(root / other_path, max_review_bytes)
                                except (OSError, ValueError, UnicodeError):
                                    issues.add("near_candidate_unreadable", severity="error")
                                    continue
                                near_compared += 1
                                similarity = shingle_jaccard(text, other_text)
                                if similarity >= near_threshold:
                                    db.execute("INSERT OR IGNORE INTO near_pairs VALUES(?,?,?)",
                                               (other_id, rid, similarity))
                                    near_verified += 1
                            db.executemany("INSERT INTO fingerprints VALUES(?,?)",
                                           ((value, rid) for value in signature))
                    if processed % 2000 == 0:
                        db.commit()
                except (ValueError, UnicodeError, OSError) as error:
                    # Do not echo review contents or native decoding error strings.
                    code = str(error) if isinstance(error, ValueError) and not isinstance(error, UnicodeError) \
                        else "invalid_utf8_or_unreadable_review"
                    if code not in {"invalid_review_filename", "filename_rating_disagrees_with_source_bucket",
                                    "review_exceeds_configured_byte_limit", "empty_review",
                                    "input_changed_during_read", "duplicate_source_review_id"}:
                        code = "invalid_utf8_or_unreadable_review"
                    issues.add(code, record=processed, field=bucket)
                    counts["rejected"] += 1
                    rejected.write(json.dumps({"source_path": relative, "reason": code}) + "\n")
            if max_reviews is not None and processed >= max_reviews:
                break
        db.commit()
        # A second metadata pass detects source changes without retaining text.
        visited = set()
        second_counts = Counter()
        for split, label in BUCKETS:
            for path in _folder_files(root / split / label):
                second_counts[f"{split}/{label}"] += 1
                relative = path.relative_to(root).as_posix()
                row = db.execute("SELECT bytes,mtime_ns FROM records WHERE path=?", (relative,)).fetchone()
                if row is not None:
                    visited.add(relative)
                    current = snapshot_file(path)
                    if (current["bytes"], current["mtime_ns"]) != tuple(row):
                        changed += 1
        indexed = db.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        if len(visited) != indexed:
            changed += abs(indexed - len(visited))
        if max_reviews is None:
            changed += sum(abs(second_counts[bucket] - counts[bucket]) for bucket in second_counts)
        for path, before in metadata_before.items():
            if not Path(path).is_file() or snapshot_file(path) != before:
                changed += 1
        if changed:
            issues.add("input_changed_during_audit")
        duplicates = {}
        for column, name in (("raw_sha256", "byte_identical"), ("norm_sha256", "normalized")):
            duplicates[name] = {
                "groups": db.execute(
                    f"SELECT COUNT(*) FROM (SELECT {column} FROM records "
                    f"GROUP BY {column} HAVING COUNT(*)>1)").fetchone()[0],
                "redundant_rows": db.execute(
                    f"SELECT COALESCE(SUM(n-1),0) FROM (SELECT COUNT(*) n FROM records "
                    f"GROUP BY {column} HAVING COUNT(*)>1)").fetchone()[0],
                "labelled_train_test_groups": db.execute(
                    f"SELECT COUNT(*) FROM (SELECT {column} FROM records WHERE label!='unsup' "
                    f"GROUP BY {column} HAVING COUNT(DISTINCT split)>1)").fetchone()[0],
            }
        contradictory = db.execute(
            "SELECT COUNT(*) FROM (SELECT norm_sha256 FROM records WHERE label!='unsup' "
            "GROUP BY norm_sha256 HAVING COUNT(DISTINCT label)>1)").fetchone()[0]
        movie_overlap = db.execute(
            "SELECT COUNT(*) FROM (SELECT movie FROM records WHERE movie IS NOT NULL "
            "AND label!='unsup' GROUP BY movie HAVING COUNT(DISTINCT split)>1)").fetchone()[0]
        near_cross = db.execute(
            "SELECT COUNT(*) FROM near_pairs p JOIN records a ON a.rid=p.left_id "
            "JOIN records b ON b.rid=p.right_id WHERE a.split!=b.split").fetchone()[0]
        stats = db.execute("SELECT MIN(chars),MAX(chars),AVG(chars),SUM(bytes) FROM records").fetchone()
        if max_reviews is None:
            for bucket, expected in (expected_counts or EXPECTED).items():
                if counts[bucket] != expected:
                    issues.add("unexpected_bucket_count", field=bucket)
        report["duplicates"] = duplicates
        report["leakage"] = {
            "contradictory_normalized_label_groups": contradictory,
            "source_url_movie_train_test_overlap": movie_overlap,
            "source_url_mapping_is_not_a_validated_application_movie_mapping": True,
        }
        report["near_duplicates"] = {
            "performed": near_duplicates, "method": "bottom-16 token-trigram hash candidates + exact shingle Jaccard",
            "threshold": near_threshold, "verified_pairs": near_verified,
            "verified_cross_split_pairs": near_cross, "candidate_pairs_compared": near_compared,
            "candidate_capped_documents": near_capped, "candidate_limit_per_document": candidate_limit,
            "scope": "labelled reviews only",
            "exhaustive": False,
            "limitation": "Approximate retrieval can miss pairs; no semantic-duplicate-free claim is made.",
        }
        if not near_duplicates:
            report["blockers"].append("Near-duplicate candidate audit has not run.")
        if duplicates["normalized"]["labelled_train_test_groups"] or contradictory or movie_overlap or near_cross:
            report["blockers"].append("Leakage/contradictory groups require explicit training exclusions or adjudication.")
        if near_capped:
            report["blockers"].append("Some near-duplicate candidate lists were capped; expand/review before training.")
        if issues.counters.get("review_movie_url_unresolved") or issues.counters.get("missing_movie_url_file"):
            report["blockers"].append("Movie-aware grouping is incomplete because source URL associations are unresolved.")
        report["counts"] = dict(counts)
        report["text_statistics"] = {
            "min_characters": stats[0], "max_characters": stats[1],
            "mean_characters": stats[2], "total_review_bytes": stats[3],
            "character_histogram_250": dict(sorted(lengths.items())),
        }
        report["input_snapshot_sha256"] = manifest_hash.hexdigest()
        report["input_stability"] = {"changed_files": changed, "accepted_files_rechecked": len(visited)}
        report["checks_complete"] = [
            "binary_source_labels", "filename_rating_consistency", "strict_utf8",
            "bounded_review_read", "exact_and_normalized_duplicates", "source_movie_url_associations",
            "official_split_overlap", "input_metadata_stability",
        ]
    report["issues"] = issues.as_dict()
    report["status"] = "invalid" if issues.has_errors else (
        "partial" if report["blockers"] or max_reviews else "complete")
    report["elapsed_seconds"] = round(time.perf_counter() - start, 3)
    report["peak_working_set_bytes"] = peak_working_set_bytes()
    report["artifacts"] = {"index": str(index_path), "rejected": str(target / "rejected.jsonl"),
                           "report": str(target / "imdb_audit.json")}
    report["blockers"].append(
        "Acquisition provenance/license record must be supplied before training; local bytes do not authenticate origin.")
    if report["status"] == "complete":
        report["status"] = "partial"
    write_json_new(target / "imdb_audit.json", report, workspace)
    return report


def prepare_imdb(source: str | Path, output: str | Path, *,
                 workspace: str | Path | None = None, validation_fraction: float = .2,
                 seed: int = 42, near_duplicates: bool = True,
                 expected_counts: dict | None = None, provenance: str | Path | None = None) -> dict:
    """Create reference manifests, preserve every valid official test record.

    Connected exact/verified-near/movie groups that touch the official test are
    excluded from train/validation. No original review is removed or rewritten.
    Missing provenance still blocks academic training approval.
    """
    if not 0 < validation_fraction < 1:
        raise ValueError("Validation fraction must lie strictly between 0 and 1.")
    report = audit_imdb(source, output, workspace=workspace, near_duplicates=near_duplicates,
                        expected_counts=expected_counts)
    if report["status"] in {"missing", "invalid"} or "index" not in report["artifacts"]:
        return report
    root = resolve_layout(source)
    target = Path(report["artifacts"]["index"]).parent
    groups = Groups()
    manifest_counts = Counter()
    label_counts = Counter()
    with closing(sqlite3.connect(report["artifacts"]["index"])) as db:
        for rid, norm, movie in db.execute(
                "SELECT rid,norm_sha256,movie FROM records WHERE label!='unsup' ORDER BY path"):
            node = f"review:{rid}"
            groups.union(node, f"text:{norm}")
            if movie:
                groups.union(node, f"movie:{movie}")
        for left, right in db.execute("SELECT left_id,right_id FROM near_pairs"):
            groups.union(f"review:{left}", f"review:{right}")
        test_groups = {groups.find(f"review:{rid}") for (rid,) in
                       db.execute("SELECT rid FROM records WHERE split='test'")}
        bad_groups = {groups.find(f"review:{rid}") for (rid,) in db.execute(
            "SELECT rid FROM records WHERE norm_sha256 IN "
            "(SELECT norm_sha256 FROM records WHERE label!='unsup' GROUP BY norm_sha256 "
            "HAVING COUNT(DISTINCT label)>1) AND label!='unsup'")}
        outputs = {name: (target / f"{name}.jsonl").open("x", encoding="utf-8", newline="\n")
                   for name in ("train", "validation", "test", "excluded", "unsup")}
        try:
            for rid, path, split, label, movie, raw, norm in db.execute(
                    "SELECT rid,path,split,label,movie,raw_sha256,norm_sha256 FROM records ORDER BY path"):
                reason = None
                if label == "unsup":
                    destination, group = "unsup", None
                else:
                    group = groups.find(f"review:{rid}")
                    if split == "test":
                        destination = "test"
                    elif group in test_groups:
                        destination, reason = "excluded", "connected_to_official_test"
                    elif group in bad_groups:
                        destination, reason = "excluded", "contradictory_source_labels"
                    else:
                        # Representative hash is based on source movie/text metadata.
                        destination = "validation" if validation_group(group, validation_fraction, seed) else "train"
                row = {"source_path": path, "source_split": split, "split": destination,
                       "label": {"neg": 0, "pos": 1, "unsup": None}[label],
                       "label_task": "binary_imdb", "source_movie_id": movie,
                       "application_movie_id": None, "raw_sha256": raw,
                       "normalized_sha256": norm, "group_id": group, "exclusion_reason": reason}
                outputs[destination].write(json.dumps(row, ensure_ascii=False) + "\n")
                manifest_counts[destination] += 1
                label_counts[(destination, row["label"])] += 1
        finally:
            for handle in outputs.values():
                handle.close()
    provenance_validated = False
    if provenance is not None:
        with Path(provenance).open(encoding="utf-8") as handle:
            record = json.load(handle)
        provenance_validated = (isinstance(record, dict) and record.get("source_version")
                                and record.get("source_url") and record.get("retrieved_at")
                                and record.get("license_or_terms")
                                and record.get("permitted_use") == "research")
    summary = base_report("stanford_acl_imdb_split_manifests")
    summary.update(
        status="partial", counts=dict(manifest_counts),
        checks_complete=["official_test_preserved", "grouped_train_validation",
                         "exact_verified_near_and_source_movie_group_isolation"],
        blockers=[] if provenance_validated else ["Acquisition/permission provenance is missing or incomplete."],
        input_fingerprints={"snapshot_sha256": report["input_snapshot_sha256"]},
        configuration={"seed": seed, "validation_fraction": validation_fraction,
                       "near_duplicates": near_duplicates},
        artifacts={name: fingerprint_file(target / f"{name}.jsonl")
                   for name in outputs},
        audit=report["artifacts"]["report"],
        class_support={split: {str(label): label_counts[(split, label)] for label in (0, 1)}
                       for split in ("train", "validation", "test")},
        training_authorized=False,
    )
    nonempty = all(manifest_counts[split] > 0 for split in ("train", "validation"))
    supported = all(label_counts[(split, label)] > 0
                    for split in ("train", "validation") for label in (0, 1))
    summary["split_integrity"] = {
        "official_test_rows_preserved": manifest_counts["test"] == report["counts"].get("test/neg", 0)
                                       + report["counts"].get("test/pos", 0),
        "nonempty_train_and_validation": nonempty,
        "both_classes_in_train_and_validation": supported,
    }
    if not nonempty or not supported:
        summary["blockers"].append("Grouped exclusions/split produced empty or unsupported training/validation classes.")
    if not near_duplicates:
        summary["blockers"].append("Near-duplicate checks were not performed.")
    if report["near_duplicates"]["candidate_capped_documents"]:
        summary["blockers"].append("Capped near-duplicate candidates require review.")
    if any(report["issues"]["counters"].get(code) for code in
           ("missing_movie_url_file", "review_movie_url_unresolved")):
        summary["blockers"].append("Source movie grouping is incomplete.")
    summary["status"] = "invalid" if not nonempty or not supported else (
        "partial" if summary["blockers"] else "complete")
    summary["notes"] = ["Reference manifests are not model artifacts; training needs separate explicit approval."]
    write_json_new(target / "split_manifest_report.json", summary, workspace)
    return summary
