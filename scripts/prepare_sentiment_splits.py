"""Split a verified IMDb validation manifest into tuning/calibration references.

Never reads review text, rewrites raw data, changes the official test, or fits a
model. Source and outputs remain distinct. Run manually after split review.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dataset_tools.splits import Groups, validation_group
from ml.common.artifacts import read_json, safe_path, sha256, write_json
from ml.common.data import _rows


def prepare(validation: Path, verification: Path, output: Path, workspace: Path,
            fraction: float = 0.5, seed: int = 42) -> dict:
    validation = safe_path(validation, workspace)
    verification = safe_path(verification, workspace)
    output = safe_path(output, workspace, output=True)
    if not 0 < fraction < 1 or output.exists() or validation.stat().st_size > 64 * 1024**2:
        raise ValueError("Choose valid fractions, bounded metadata and a fresh output path.")
    report = read_json(verification)
    checksum = sha256(validation)
    if report.get("status") != "complete" or report.get("input_fingerprints", {}).get("validation", {}).get("sha256") != checksum:
        raise ValueError("Independent Phase1 verification does not cover this validation manifest.")
    records = list(_rows(validation))
    if len(records) > 100000:
        raise ValueError("Metadata record limit exceeded.")
    groups = Groups()
    seen_ids = set()
    for row in records:
        if row.get("split") != "validation" or row.get("source_split") != "train" or row.get("label_task") != "binary_imdb":
            raise ValueError("Only the existing verified binary validation split can be divided.")
        if type(row.get("label")) is not int or row["label"] not in (0, 1) or not row.get("group_id"):
            raise ValueError("Invalid class/group metadata.")
        if row["source_path"] in seen_ids:
            raise ValueError("Duplicate source reference.")
        seen_ids.add(row["source_path"])
        key = "group:" + row["group_id"]
        groups.find(key)
        for field in ("source_movie_id", "normalized_sha256", "raw_sha256"):
            if row.get(field):
                groups.union(key, field + ":" + row[field])
    partitions = {"tuning": [], "calibration": []}
    for row in records:
        role = "calibration" if validation_group(groups.find("group:" + row["group_id"]), fraction, seed) else "tuning"
        partitions[role].append({**row, "experiment_split": role})
    counts = {role: dict(Counter(row["label"] for row in rows)) for role, rows in partitions.items()}
    if any(set(counts[role]) != {0, 1} for role in partitions):
        raise ValueError("The fixed group split lacks class support; review data/protocol, not test labels.")
    if sha256(validation) != checksum:
        raise ValueError("Input manifest changed during preparation.")
    output.mkdir(parents=True, exist_ok=False)
    for role, rows in partitions.items():
        with (output / (role + ".jsonl")).open("x", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    result = {"schema_version": 1, "status": "complete", "source_validation_sha256": checksum,
        "verification_report_sha256": sha256(verification), "seed": seed, "calibration_fraction": fraction,
        "class_counts": counts, "counts": {key: len(rows) for key, rows in partitions.items()},
        "output_sha256": {role: sha256(output / (role + ".jsonl")) for role in partitions},
        "review_text_read": False, "model_trained": False, "official_train_and_test_unchanged": True}
    write_json(output / "split_report.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--validation-manifest", required=True)
    parser.add_argument("--verification-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--calibration-fraction", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(Path(args.validation_manifest), Path(args.verification_report), Path(args.output),
                                 Path(args.workspace), args.calibration_fraction, args.seed), indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "error_type": type(error).__name__, "training_started": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
