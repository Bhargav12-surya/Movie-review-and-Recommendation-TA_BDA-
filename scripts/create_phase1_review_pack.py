"""Prepare owner-review forms from local evidence without resolving identities."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dataset_tools.io import create_output_dir, fingerprint_file, snapshot_file, write_json_new


def create_review_pack(source: Path, quarantine: Path, output: Path,
                       workspace: Path = ROOT) -> dict:
    source, quarantine, workspace = source.resolve(), quarantine.resolve(), workspace.resolve()
    paths = (source / "movies.csv", source / "links.csv", quarantine)
    before = {str(path): snapshot_file(path) for path in paths}
    with quarantine.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    required: set[int] = set()
    for row in rows:
        key = row.get("source_movie_key", "")
        if (row.get("source") != "tmdb" or row.get("canonical_movie_id") is not None
                or not key.startswith("movielens:") or not key[10:].isdigit()
                or not str(row.get("external_id", "")).isdigit()):
            raise ValueError("Quarantine contains an unsupported relationship.")
        movie = int(key[10:])
        if movie not in row.get("conflict_movie_ids", []):
            raise ValueError("Quarantine group does not contain its source movie.")
        required.add(movie)
    titles, links = {}, {}
    with paths[0].open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["movieId", "title", "genres"]:
            raise ValueError("Unexpected MovieLens movie schema.")
        for row in reader:
            movie = int(row["movieId"])
            if movie in required:
                titles[movie] = row["title"]
    with paths[1].open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["movieId", "imdbId", "tmdbId"]:
            raise ValueError("Unexpected MovieLens link schema.")
        for row in reader:
            movie = int(row["movieId"])
            if movie in required:
                links[movie] = row
    if required != titles.keys() or required != links.keys():
        raise ValueError("Quarantine references absent source records.")
    for row in rows:
        if links[int(row["source_movie_key"][10:])]["tmdbId"] != str(row["external_id"]):
            raise ValueError("Quarantined external ID disagrees with the current raw source.")
    if any(snapshot_file(path) != before[str(path)] for path in paths):
        raise ValueError("Input changed during review-pack creation.")
    target = create_output_dir(output, workspace)
    fields = ["conflicting_tmdb_id", "source_movie_key", "movielens_title",
              "imdb_id_raw", "canonical_movie_id", "decision", "evidence_reference", "reviewed_by"]
    with (target / "mapping_decisions.csv").open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            movie = int(row["source_movie_key"][10:])
            writer.writerow({"conflicting_tmdb_id": row["external_id"],
                             "source_movie_key": row["source_movie_key"],
                             "movielens_title": titles[movie],
                             "imdb_id_raw": links[movie]["imdbId"],
                             "canonical_movie_id": "", "decision": "",
                             "evidence_reference": "", "reviewed_by": ""})
    for name, version in (("movielens", "ml-32m"), ("imdb", "aclImdb-v1.0")):
        write_json_new(target / f"{name}_provenance_to_complete.json", {
            "form_status": "unapproved_owner_input_required", "source_version": version,
            "source_url": None, "retrieved_at": None, "license_or_terms": None,
            "permitted_use": None, "approved_for_training": False, "reviewed_by": None,
            "note": "Fill from actual acquisition/permission records; never infer a retrieval date."
        }, workspace)
    report = {"schema_version": 1, "status": "partial",
              "relationship_rows": len(rows),
              "conflict_groups": len({str(row["external_id"]) for row in rows}),
              "decisions_filled": 0, "canonical_ids_assigned": 0,
              "input_fingerprints": {path.name: fingerprint_file(path) for path in paths},
              "artifacts": {"mapping_form": str(target / "mapping_decisions.csv")},
              "blockers": ["Owner provenance and evidence-based mapping decisions are still required."]}
    write_json_new(target / "review_pack_report.json", report, workspace)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/raw/movielens/ml-32m")
    parser.add_argument("--quarantine", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = create_review_pack(args.source, args.quarantine, args.output)
    except (ValueError, OSError, KeyError):
        print(json.dumps({"status": "invalid", "error": "Review inputs/output could not be validated safely."}))
        return 2
    print(json.dumps(report))
    return 4  # A blank review form is deliberately not an approved mapping.


if __name__ == "__main__":
    raise SystemExit(main())
