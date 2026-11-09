"""Preserve MovieLens identities and quarantine conflicting external links."""
from __future__ import annotations

from collections import Counter
import csv
import json
from pathlib import Path

from .io import (IssueCollector, base_report, create_output_dir,
                 fingerprint_file, snapshot_file, write_json_new)
from .movielens import _integer


def _mapping_data(source: Path) -> tuple[dict, dict[int, dict], dict[str, list[int]]]:
    report = base_report("movielens_identity_mapping")
    issues = IssueCollector()
    paths = [source / name for name in ("movies.csv", "links.csv")]
    if not all(path.is_file() for path in paths):
        report.update(status="missing", blockers=["movies.csv and links.csv are required."])
        return report, {}, {}
    before = {path.name: snapshot_file(path) for path in paths}
    movies: dict[int, dict] = {}
    groups: dict[str, list[int]] = {}
    imdb_groups: dict[str, list[int]] = {}
    try:
        with paths[0].open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != ["movieId", "title", "genres"]:
                raise ValueError("movies header")
            for number, row in enumerate(reader, 1):
                try:
                    movie = _integer(row["movieId"])
                    if movie in movies:
                        issues.add("mapping.duplicate_movielens_movie", number)
                        continue
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError
                    movies[movie] = {"source_movie_key": f"movielens:{movie}",
                                     "movielens_id": movie, "canonical_movie_id": None,
                                     "mapping_status": "provisional",
                                     "externally_verified": False,
                                     "imdb_id_raw": None, "imdb_id_normalized": None,
                                     "tmdb_id_raw": None, "tmdb_id": None,
                                     "tmdb_mapping_status": "missing",
                                     "link_present": False}
                except (ValueError, TypeError):
                    issues.add("mapping.invalid_movie_row", number)
        with paths[1].open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != ["movieId", "imdbId", "tmdbId"]:
                raise ValueError("links header")
            for number, row in enumerate(reader, 1):
                try:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError
                    movie = _integer(row["movieId"])
                    if movie not in movies:
                        issues.add("mapping.orphan_source_movie", number)
                        continue
                    item = movies[movie]
                    if item["link_present"]:
                        issues.add("mapping.duplicate_movie_link", number)
                        continue
                    item["link_present"] = True
                    _integer(row["imdbId"])
                    item["imdb_id_raw"] = row["imdbId"]
                    item["imdb_id_normalized"] = "tt" + row["imdbId"]
                    imdb_groups.setdefault(row["imdbId"], []).append(movie)
                    item["tmdb_id_raw"] = row["tmdbId"] or None
                    if row["tmdbId"]:
                        _integer(row["tmdbId"])
                        candidate = str(int(row["tmdbId"]))
                        item["tmdb_id"] = candidate
                        item["tmdb_mapping_status"] = "provisional"
                        groups.setdefault(candidate, []).append(movie)
                except (ValueError, TypeError):
                    issues.add("mapping.invalid_external_id", number)
        conflicts = {key: ids for key, ids in groups.items() if len(ids) > 1}
        imdb_conflicts = {key: ids for key, ids in imdb_groups.items() if len(ids) > 1}
        for key, ids in conflicts.items():
            issues.add("mapping.tmdb_conflict", identifiers={"tmdb_id": key, "movie_ids": ids})
            for movie in ids:
                movies[movie]["tmdb_id"] = None
                movies[movie]["tmdb_mapping_status"] = "conflict"
        for key, ids in imdb_conflicts.items():
            issues.add("mapping.imdb_conflict", identifiers={"imdb_id": key, "movie_ids": ids})
            for movie in ids:
                movies[movie]["imdb_id_normalized"] = None
        for path in paths:
            report["input_fingerprints"][path.name] = fingerprint_file(path)
            if snapshot_file(path) != before[path.name]:
                issues.add("mapping.input_changed")
        missing_links = sum(not item["link_present"] for item in movies.values())
        if missing_links:
            for _ in range(missing_links):
                issues.add("mapping.movie_link_missing", severity="warning")
        report["counts"] = {
            "source_movies": len(movies), "missing_link_rows": missing_links,
            "missing_tmdb_ids": sum(item["tmdb_id_raw"] is None for item in movies.values()),
            "tmdb_conflict_groups": len(conflicts),
            "tmdb_conflict_rows": sum(map(len, conflicts.values())),
            "imdb_conflict_groups": len(imdb_conflicts),
            "canonical_ids_approved": 0,
        }
        report["tmdb_conflicts"] = conflicts
        report["imdb_conflicts"] = imdb_conflicts
        report["checks_complete"] = ["source_identity_uniqueness", "external_id_types",
                                     "leading_zero_preservation", "conflict_quarantine",
                                     "source_reference_coverage", "input_stat_preservation"]
    except (OSError, ValueError, UnicodeError, csv.Error) as error:
        issues.add("mapping.read_failed")
        report["blockers"].append(f"Mapping input could not be validated: {type(error).__name__}.")
        conflicts = {}
    report["issues"] = issues.as_dict()
    report["status"] = "invalid" if issues.has_errors else "partial"
    report["blockers"].append("Canonical application movie IDs and external mappings remain unapproved.")
    report["notes"] = [
        "movielens:<id> is a provisional source key, not an approved application ID.",
        "No title similarity, external API query or inferred merge was used.",
        "Missing and conflicting external IDs remain explicit; raw values remain preserved.",
    ]
    return report, movies, conflicts


def validate_movie_ids(source: str | Path) -> dict:
    return _mapping_data(Path(source).resolve())[0]


def build_provisional_movie_map(source: str | Path, output: str | Path,
                                 workspace: str | Path | None = None) -> dict:
    source = Path(source).resolve()
    report, movies, conflicts = _mapping_data(source)
    if report["status"] == "missing":
        return report
    destination = create_output_dir(output, workspace)
    movies_path = destination / "provisional_movies.jsonl"
    candidates_path = destination / "external_id_candidates.jsonl"
    quarantine_path = destination / "quarantined_external_ids.jsonl"
    with movies_path.open("x", encoding="utf-8") as records, \
            candidates_path.open("x", encoding="utf-8") as candidates, \
            quarantine_path.open("x", encoding="utf-8") as quarantine:
        for movie in sorted(movies):
            item = movies[movie]
            records.write(json.dumps(item, ensure_ascii=False) + "\n")
            for source_name, field in (("imdb", "imdb_id_normalized"), ("tmdb", "tmdb_id")):
                if item[field]:
                    candidates.write(json.dumps({
                        "source_movie_key": item["source_movie_key"],
                        "canonical_movie_id": None, "source": source_name,
                        "external_id": item[field], "status": "provisional",
                        "externally_verified": False}) + "\n")
        for external_id, movie_ids in sorted(conflicts.items()):
            for movie in movie_ids:
                quarantine.write(json.dumps({
                    "source_movie_key": f"movielens:{movie}", "source": "tmdb",
                    "external_id": external_id, "reason": "multiple_movielens_movies",
                    "conflict_movie_ids": movie_ids, "canonical_movie_id": None}) + "\n")
        for external_id, movie_ids in report.get("imdb_conflicts", {}).items():
            for movie in movie_ids:
                quarantine.write(json.dumps({
                    "source_movie_key": f"movielens:{movie}", "source": "imdb",
                    "external_id": external_id, "reason": "multiple_movielens_movies",
                    "conflict_movie_ids": movie_ids, "canonical_movie_id": None}) + "\n")
    report["artifacts"] = {"provisional_movies": str(movies_path),
                           "external_id_candidates": str(candidates_path),
                           "quarantined_external_ids": str(quarantine_path),
                           "report": str(destination / "report.json")}
    # A completed provisional export is still partial, never an approved mapping.
    report["mapping_validation_status"] = report["status"]
    report["status"] = ("partial" if movies and "mapping.read_failed" not in
                        report.get("issues", {}).get("counters", {}) else "invalid")
    write_json_new(destination / "report.json", report, workspace)
    return report
