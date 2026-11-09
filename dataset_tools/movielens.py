"""Bounded-memory MovieLens CSV validation, independent of pandas and Spark."""
from __future__ import annotations

from collections import Counter
import csv
import ctypes
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time

from .io import (IssueCollector, base_report, create_output_dir, fingerprint_file,
                 project_root, snapshot_file, write_json_new)


HEADERS = {
    "movies.csv": ("movieId", "title", "genres"),
    "links.csv": ("movieId", "imdbId", "tmdbId"),
    "ratings.csv": ("userId", "movieId", "rating", "timestamp"),
    "tags.csv": ("userId", "movieId", "tag", "timestamp"),
}
GENRES = {"Action", "Adventure", "Animation", "Children", "Comedy", "Crime",
          "Documentary", "Drama", "Fantasy", "Film-Noir", "Horror", "IMAX",
          "Musical", "Mystery", "Romance", "Sci-Fi", "Thriller", "War",
          "Western", "(no genres listed)"}


def _integer(value: str, minimum: int = 1) -> int:
    if not value or not value.isascii() or not value.isdecimal():
        raise ValueError("Expected an ASCII integer.")
    result = int(value)
    if result < minimum:
        raise ValueError("Integer below allowed minimum.")
    return result


def _rows(path: Path, issues: IssueCollector, max_rows: int | None):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        header = next(reader, None)
        if header != list(HEADERS[path.name]):
            issues.add(f"{path.name}.invalid_header")
            return
        for record, row in enumerate(reader, 1):
            if max_rows is not None and record > max_rows:
                return
            if len(row) != len(header):
                issues.add(f"{path.name}.field_count", record=record)
                yield record, None
            else:
                yield record, row


def _read_checksums(source: Path, issues: IssueCollector) -> dict[str, str]:
    path = source / "checksums.txt"
    if not path.is_file():
        issues.add("checksums.missing", severity="warning")
        return {}
    result = {}
    with path.open(encoding="utf-8-sig") as handle:
        for line_no, line in enumerate(handle, 1):
            fields = line.split()
            if not fields:
                continue
            if (len(fields) != 2 or len(fields[0]) != 32
                    or any(char not in "0123456789abcdefABCDEF" for char in fields[0])):
                issues.add("checksums.invalid_line", record=line_no)
                continue
            filename = fields[1].lstrip("*")
            if filename not in HEADERS or filename in result:
                issues.add("checksums.unexpected_or_duplicate_file", record=line_no)
                continue
            result[filename] = fields[0].lower()
    return result


def audit_movielens(source: str | Path, output: str | Path | None = None,
                    max_rows: int | None = None, expected_counts: dict | None = None,
                    workspace: str | Path | None = None) -> dict:
    """Validate all local CSVs; sample mode never claims full-data validity."""
    if max_rows is not None and max_rows < 1:
        raise ValueError("max_rows must be positive.")
    source = Path(source).resolve()
    report = base_report("movielens_ml32m", "sample" if max_rows else "full")
    report["input_directory"] = str(source)
    missing = [name for name in HEADERS if not (source / name).is_file()]
    if missing:
        report.update(status="missing", blockers=["Missing files: " + ", ".join(missing)])
        return report
    from scripts._verification_common import resource_snapshot
    resources = resource_snapshot(Path(workspace or project_root()))
    report["resources_before"] = resources
    input_bytes = sum((source / name).stat().st_size for name in HEADERS)
    available = resources["memory"].get("available_bytes")
    if not max_rows and input_bytes >= 64 * 1024**2 and (
            resources["disk"]["free_bytes"] < 20 * 1024**3
            or available is not None and available < 512 * 1024**2):
        report.update(status="partial", blockers=[
            "Full scan requires a 20GiB disk reserve and at least512MiB available RAM; no scan/output started."])
        return report
    if output is not None and Path(output).resolve().is_relative_to(source):
        raise ValueError("Audit reports must be separate from the source directory.")
    destination = create_output_dir(output, workspace) if output is not None else None
    issues = IssueCollector()
    start = time.perf_counter()
    snapshots = {name: snapshot_file(source / name) for name in HEADERS}
    for name in ("checksums.txt", "README.txt"):
        if (source / name).is_file():
            snapshots[name] = snapshot_file(source / name)
    rejected = None
    if destination:
        rejected = (destination / "rejected_rows.jsonl").open("x", encoding="utf-8")
        report["artifacts"]["rejected_rows"] = str(destination / "rejected_rows.jsonl")

    def reject(filename: str, number: int, reason: str, identifiers: dict | None = None):
        issues.add(f"{filename}.{reason}", record=number, identifiers=identifiers)
        if rejected:
            rejected.write(json.dumps({"source_file": filename, "record": number,
                                       "reason": reason, "identifiers": identifiers or {}},
                                      ensure_ascii=False) + "\n")

    movie_ids: set[int] = set()
    users: Counter = Counter()
    rated: set[int] = set()
    tagged: set[int] = set()
    tag_users: set[int] = set()
    movie_genres: Counter = Counter()
    movie_counts = {"rows": 0, "accepted": 0, "rejected": 0,
                    "duplicate_movie_ids": 0, "no_genres_listed": 0}
    link_counts = {"rows": 0, "accepted": 0, "rejected": 0,
                   "missing_tmdb_ids": 0, "duplicate_movie_ids": 0}
    link_ids: set[int] = set()
    imdb_ids: set[str] = set()
    tmdb_groups: dict[str, list[int]] = {}
    maximum_timestamp = int(datetime.now(timezone.utc).timestamp()) + 86400
    try:
        for number, row in _rows(source / "movies.csv", issues, max_rows):
            movie_counts["rows"] += 1
            try:
                if row is None:
                    raise ValueError
                movie = _integer(row[0])
                if movie in movie_ids:
                    movie_counts["duplicate_movie_ids"] += 1
                    reject("movies.csv", number, "duplicate_movie_id", {"movieId": movie})
                    movie_counts["rejected"] += 1
                    continue
                movie_ids.add(movie)
                if not row[1].strip() or not row[2].strip():
                    raise ValueError
                genres = row[2].split("|")
                movie_genres.update(genres)
                if "(no genres listed)" in genres:
                    movie_counts["no_genres_listed"] += 1
                for genre in genres:
                    if genre not in GENRES:
                        issues.add("movies.csv.unrecognized_genre", number,
                                   severity="warning")
                movie_counts["accepted"] += 1
            except (ValueError, IndexError):
                movie_counts["rejected"] += 1
                reject("movies.csv", number, "invalid_or_blank_fields")

        for number, row in _rows(source / "links.csv", issues, max_rows):
            link_counts["rows"] += 1
            try:
                if row is None:
                    raise ValueError
                movie = _integer(row[0])
                if movie in link_ids:
                    link_counts["duplicate_movie_ids"] += 1
                    raise ValueError
                link_ids.add(movie)
                if movie not in movie_ids:
                    issues.add("links.csv.orphan_movie_id", number,
                               identifiers={"movieId": movie},
                               severity="warning" if max_rows else "error")
                    if not max_rows:
                        raise ValueError
                _integer(row[1])
                if row[1] in imdb_ids:
                    issues.add("links.csv.duplicate_imdb_id", number)
                imdb_ids.add(row[1])  # Preserve leading zeros in the source string.
                if row[2] == "":
                    link_counts["missing_tmdb_ids"] += 1
                    issues.add("links.csv.missing_tmdb_id", number, severity="warning")
                else:
                    _integer(row[2])
                    tmdb_groups.setdefault(str(int(row[2])), []).append(movie)
                link_counts["accepted"] += 1
            except (ValueError, IndexError):
                link_counts["rejected"] += 1
                reject("links.csv", number, "invalid_ids")
        conflicts = {key: values for key, values in tmdb_groups.items() if len(values) > 1}
        for key, values in conflicts.items():
            issues.add("links.csv.conflicting_tmdb_id",
                       identifiers={"tmdbId": key, "movielens_ids": values})
        link_counts.update(distinct_movie_ids=len(link_ids), distinct_imdb_ids=len(imdb_ids),
                           populated_tmdb_references=sum(map(len, tmdb_groups.values())),
                           distinct_tmdb_ids=len(tmdb_groups),
                           duplicated_tmdb_groups=len(conflicts),
                           affected_tmdb_conflict_rows=sum(map(len, conflicts.values())),
                           movie_ids_missing_link=len(movie_ids - link_ids))
        report["mapping_conflicts"] = conflicts

        for filename, is_tag in (("ratings.csv", False), ("tags.csv", True)):
            counts = {"rows": 0, "accepted": 0, "rejected": 0, "order_violations": 0,
                      "repeated_user_movie_pairs": 0, "adjacent_exact_duplicates": 0,
                      "exact_duplicates_in_sorted_groups": 0,
                      "duplicate_group_overflows": 0}
            distribution: Counter = Counter()
            last_key = last_row = None
            group_rows: set[tuple] = set()
            normalized_tags: set[str] = set()
            normalized_repeats = 0
            min_timestamp = max_timestamp = None
            min_length = max_length = None
            for number, row in _rows(source / filename, issues, max_rows):
                counts["rows"] += 1
                try:
                    if row is None:
                        raise ValueError
                    user, movie, stamp = _integer(row[0]), _integer(row[1]), _integer(row[3], 0)
                    key = (user, movie)
                    if movie not in movie_ids:
                        issues.add(f"{filename}.orphan_movie_id", number,
                                   identifiers={"movieId": movie},
                                   severity="warning" if max_rows else "error")
                        if not max_rows:
                            raise ValueError
                    if is_tag and user not in users:
                        issues.add("tags.csv.unknown_rating_user", number,
                                   identifiers={"userId": user},
                                   severity="warning" if max_rows else "error")
                        if not max_rows:
                            raise ValueError
                    if stamp > maximum_timestamp:
                        raise ValueError
                    if last_key is not None and key < last_key:
                        counts["order_violations"] += 1
                    if key == last_key:
                        counts["repeated_user_movie_pairs"] += 1
                    else:
                        group_rows.clear()
                        normalized_tags.clear()
                    original = tuple(row)
                    if original == last_row:
                        counts["adjacent_exact_duplicates"] += 1
                    if original in group_rows:
                        counts["exact_duplicates_in_sorted_groups"] += 1
                    elif len(group_rows) < 4096:
                        group_rows.add(original)
                    else:
                        counts["duplicate_group_overflows"] += 1
                    last_key, last_row = key, original
                    min_timestamp = stamp if min_timestamp is None else min(min_timestamp, stamp)
                    max_timestamp = stamp if max_timestamp is None else max(max_timestamp, stamp)
                    if is_tag:
                        tag_users.add(user)
                        tagged.add(movie)
                        length = len(row[2])
                        min_length = length if min_length is None else min(min_length, length)
                        max_length = length if max_length is None else max(max_length, length)
                        if not row[2].strip():
                            raise ValueError
                        normalized = " ".join(row[2].casefold().split())
                        if normalized in normalized_tags:
                            normalized_repeats += 1
                        elif len(normalized_tags) < 4096:
                            normalized_tags.add(normalized)
                    else:
                        rating = float(row[2])
                        if not math.isfinite(rating) or not 0.5 <= rating <= 5 or rating * 2 != int(rating * 2):
                            raise ValueError
                        users[user] += 1
                        rated.add(movie)
                        distribution[f"{rating:.1f}"] += 1
                    counts["accepted"] += 1
                except (ValueError, IndexError, OverflowError):
                    counts["rejected"] += 1
                    reject(filename, number, "invalid_or_blank_fields")
            duplicates_complete = counts["order_violations"] == 0 and counts["duplicate_group_overflows"] == 0
            counts["exact_duplicate_check_complete"] = duplicates_complete
            if not duplicates_complete:
                counts["exact_duplicates_in_sorted_groups"] = None
                issues.add(f"{filename}.duplicate_check_incomplete")
            elif counts["exact_duplicates_in_sorted_groups"]:
                issues.add(f"{filename}.exact_duplicate_rows")
            if not is_tag and counts["repeated_user_movie_pairs"]:
                issues.add("ratings.csv.repeated_user_movie_pairs")
            counts.update(min_timestamp=min_timestamp, max_timestamp=max_timestamp)
            if is_tag:
                counts.update(distinct_users=len(tag_users), distinct_movies=len(tagged),
                              min_text_characters=min_length, max_text_characters=max_length,
                              repeated_normalized_tags_in_user_movie_group=normalized_repeats)
            else:
                counts.update(distinct_users=len(users), distinct_movies=len(rated),
                              min_ratings_per_user=min(users.values()) if users else None,
                              max_ratings_per_user=max(users.values()) if users else None,
                              rating_distribution=dict(sorted(distribution.items())))
            report["counts"][filename.removesuffix(".csv")] = counts
        report["counts"]["movies"] = {**movie_counts, "distinct_ids": len(movie_ids),
                                      "genre_counts": dict(sorted(movie_genres.items()))}
        report["counts"]["links"] = link_counts
        report["counts"]["coverage"] = {
            "tag_only_movies": len(tagged - rated),
            "catalogue_movies_without_rating_or_tag": len(movie_ids - (rated | tagged))}
        if not max_rows and expected_counts:
            for key, expected in expected_counts.items():
                actual = (len(users) if key == "users" else
                          report["counts"].get(key, {}).get("rows"))
                if actual != expected:
                    issues.add(f"expected_count.{key}")
        checksums = _read_checksums(source, issues)
        report["checksum_comparison"] = {}
        for name in HEADERS:
            fingerprint = fingerprint_file(source / name, ("sha256", "md5"))
            report["input_fingerprints"][name] = fingerprint
            expected = checksums.get(name)
            result = "match" if expected == fingerprint["md5"] else "missing" if expected is None else "mismatch"
            report["checksum_comparison"][name] = result
            if result == "mismatch":
                issues.add(f"checksum_mismatch.{name}")
            if snapshot_file(source / name) != snapshots[name]:
                issues.add(f"input_changed.{name}")
        for name in snapshots.keys() - HEADERS.keys():
            report["input_fingerprints"][name] = fingerprint_file(source / name)
            if snapshot_file(source / name) != snapshots[name]:
                issues.add(f"input_changed.{name}")
        report["checks_complete"] = ["csv_headers", "utf8_decoding", "field_counts",
                                     "missingness_types_ranges", "source_references",
                                     "bounded_duplicate_checks", "rating_distribution",
                                     "external_link_conflicts", "streaming_checksums",
                                     "input_stat_preservation"]
    except (OSError, UnicodeError, csv.Error) as error:
        issues.add("scan.failed")
        report["blockers"].append(f"Input could not be fully scanned: {type(error).__name__}.")
    finally:
        if rejected:
            rejected.close()
    report["issues"] = issues.as_dict()
    report["elapsed_seconds"] = round(time.perf_counter() - start, 3)
    report["resources_after"] = resource_snapshot(Path(workspace or project_root()))
    report["peak_process_working_set_bytes"] = _peak_working_set()
    report["status"] = "invalid" if issues.has_errors else "partial" if max_rows else "complete"
    if (report["status"] == "complete"
            and any(value != "match" for value in report.get("checksum_comparison", {}).values())):
        report["status"] = "partial"
        report["blockers"].append("Not all supplied source checksums were available and verified.")
    if max_rows:
        report["blockers"].append("Sampled rows do not establish dataset-wide validity or duplicate absence.")
    if report.get("mapping_conflicts"):
        report["blockers"].append("TMDB collisions require explicit canonical mapping review.")
    report["notes"] = [
        "MovieLens ratings/tags are not full movie reviews or sentiment labels.",
        "Checksums compare supplied local files; the download channel was not authenticated.",
        "No raw data changed, dataset downloaded, canonical identity approved or model trained.",
        "Rejected metadata references original source records without copying text.",
    ]
    if destination:
        report["artifacts"]["report"] = str(destination / "report.json")
        write_json_new(destination / "report.json", report, workspace)
    return report


def _peak_working_set() -> int | None:
    """Windows peak process RSS, without a monitoring dependency."""
    import os
    if os.name != "nt":
        return None
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong),
                    ("peak", ctypes.c_size_t), ("working", ctypes.c_size_t),
                    ("peak_paged", ctypes.c_size_t), ("paged", ctypes.c_size_t),
                    ("peak_nonpaged", ctypes.c_size_t), ("nonpaged", ctypes.c_size_t),
                    ("pagefile", ctypes.c_size_t), ("peak_pagefile", ctypes.c_size_t)]
    value = Counters()
    value.cb = ctypes.sizeof(value)
    if ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.c_void_p(-1), ctypes.byref(value), value.cb):
        return value.peak
    return None
