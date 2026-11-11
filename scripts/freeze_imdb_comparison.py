"""Review and explicitly freeze the three completed local IMDb experiments.

Default validates saved artifacts/reports and prints the proposed comparison.
--freeze --reviewed-by ID records the human review represented by that command.
Final test evaluation is performed through the existing evaluate entry points.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.common.artifacts import read_json, safe_path, sha256
from ml.common.config import load_config
from ml.common.data import load_experiment

LABELS = {"negative": 0, "positive": 1}


def compatible(existing, expected):
    return all(existing.get(key) == value for key, value in expected.items() if key != "reviewed_at")


def publish_selection(path, payload):
    """Publish a complete JSON file without replacing an existing decision."""
    if path.exists():
        if not compatible(read_json(path), payload):
            raise ValueError("Existing selection differs from this reviewed comparison: " + str(path))
        return "already_recorded"
    partial = path.with_name("." + path.name + "-" + uuid.uuid4().hex)
    with partial.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        if os.name == "nt":
            os.rename(partial, path)  # Windows refuses an existing destination.
        else:
            os.link(partial, path)  # Atomic exclusive publication on POSIX.
    except FileExistsError:
        if not compatible(read_json(path), payload):
            raise ValueError("A concurrent selection differs from this comparison.")
        return "already_recorded"
    return "recorded"


def inspect(plan_path):
    plan = read_json(plan_path)
    if (plan.get("schema_version") != 1 or plan.get("task") != "binary_imdb"
            or plan.get("primary_selection_metric") != "macro_f1"):
        raise ValueError("Expected the reviewed binary IMDb macro-F1 comparison plan.")
    candidates = plan.get("candidates", [])
    if len(candidates) != 3 or {c.get("key") for c in candidates} != {"lr", "svm", "bert"}:
        raise ValueError("The plan must name the three completed LR/SVM/BERT experiments.")
    results, manifest_hashes, configs, seen_runs = [], None, [], set()
    for candidate in candidates:
        component = candidate["component"]
        if component not in {"sentiment_tfidf", "sentiment_transformer"}:
            raise ValueError("Unsupported comparison component.")
        config_path = safe_path(candidate["config"], ROOT)
        config = load_config(config_path)
        if config["_workspace"] != ROOT or config["task"] != "binary_imdb" or config.get("language_scope") != ["en"]:
            raise ValueError("Comparison requires the local English binary IMDb configurations.")
        run = safe_path(candidate["run"], ROOT, output=True)
        if run in seen_runs or run != safe_path(config["output_dir"], ROOT, output=True):
            raise ValueError("Duplicate run or configuration/output mismatch.")
        seen_runs.add(run)
        report_path = safe_path(candidate["tuning_report"], ROOT)
        if not report_path.is_relative_to(run):
            raise ValueError("Tuning report is outside its owned run.")
        report = read_json(report_path)
        trained = read_json(run / "training_report.json")
        experiment = read_json(run / "experiment.json")
        if (trained.get("trained") is not True or trained.get("task") != "binary_imdb"
                or report.get("split") != "tuning" or report.get("task") != "binary_imdb"
                or report.get("labels", LABELS) != LABELS
                or report.get("metrics", {}).get("labels") != ["negative", "positive"]
                or report.get("calibration_scope") != "held_out_from_calibration"):
            raise ValueError("Completed training and held-out-from-calibration tuning reports are required.")
        if sha256(config_path) != candidate["config_sha256"] or experiment.get("source_config_sha256") != candidate["config_sha256"]:
            raise ValueError("Configuration changed since the recorded experiment/plan.")
        if sha256(report_path) != candidate["tuning_report_sha256"]:
            raise ValueError("Tuning evidence differs from the proposed comparison.")
        actual_hashes = {role: sha256(safe_path(value, ROOT))
                         for role, value in config["data"]["manifests"].items()}
        if set(actual_hashes) != {"train", "tuning", "calibration", "test"}:
            raise ValueError("All four frozen manifest roles are required.")
        if trained.get("manifest_hashes") != actual_hashes or report.get("manifest_hashes") != actual_hashes:
            raise ValueError("Training/tuning/actual manifest fingerprints differ.")
        if manifest_hashes is not None and manifest_hashes != actual_hashes:
            raise ValueError("Comparison models use different frozen splits.")
        manifest_hashes = actual_hashes
        if component == "sentiment_tfidf":
            artifact = run / "model.json"
            digest_key = "model_sha256"
            state = read_json(artifact, max_bytes=64 * 1024**2)
            if state.get("labels") != LABELS or state.get("manifest_hashes") != actual_hashes:
                raise ValueError("TF-IDF state differs from its recorded task/splits.")
            expected_estimator = "logistic_regression" if candidate["key"] == "lr" else "linear_svm"
            if trained.get("estimator") != expected_estimator or state.get("estimator") != expected_estimator:
                raise ValueError("TF-IDF comparison estimator differs from its plan.")
        else:
            artifact = run / "model_manifest.json"
            digest_key = "model_manifest_sha256"
            state = read_json(artifact)
            if state.get("trained") is not True or state.get("labels") != LABELS or state.get("manifest_hashes") != actual_hashes:
                raise ValueError("BERT manifest differs from its recorded task/splits.")
            files = state.get("files_sha256", {})
            if set(files) != {str(p.relative_to(run)) for p in (run / "model").iterdir() if p.is_file()}:
                raise ValueError("BERT model/tokenizer file set differs from its manifest.")
            for name, expected in files.items():
                path = safe_path(run / name, ROOT)
                if not path.is_relative_to(run) or sha256(path) != expected:
                    raise ValueError("BERT file hash mismatch: " + name)
        artifact_hash = sha256(artifact)
        if (artifact_hash != candidate["artifact_sha256"] or trained.get(digest_key) != artifact_hash
                or report.get(digest_key) != artifact_hash):
            raise ValueError("Saved model/training/tuning/plan hashes differ.")
        if ((run / "final_test_reservation.json").exists() or list((run / "evaluations").glob("test-*.json"))
                or list(run.glob("evaluation-test-*.json"))):
            raise ValueError("A final-test attempt is already recorded for " + candidate["key"] + ". Review it before continuing.")
        metrics = report["metrics"]
        for key in ("accuracy", "macro_f1", "negative_log_likelihood", "multiclass_brier", "ece"):
            value = metrics.get(key)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError("Invalid measured tuning metric: " + key)
        configs.append(config)
        results.append(dict(key=candidate["key"], name=candidate["name"], component=component,
                            config=candidate["config"], run=candidate["run"], metrics=metrics,
                            config_sha256=candidate["config_sha256"],
                            tuning_report=candidate["tuning_report"],
                            tuning_report_sha256=candidate["tuning_report_sha256"],
                            digest_key=digest_key, artifact_sha256=artifact_hash))
    bundle = load_experiment(configs[0])  # References/labels only, without reading review text.
    if bundle.manifest_hashes != manifest_hashes:
        raise ValueError("Independent manifest validation differs from recorded artifacts.")
    tuning_count = len(bundle.records["tuning"])
    if any(r["metrics"].get("count") != tuning_count for r in results):
        raise ValueError("Tuning report supports differ from the actual frozen role.")
    primary = max(results, key=lambda r: (r["metrics"]["macro_f1"], r["metrics"]["accuracy"]))["key"]
    if plan.get("expected_primary_model") != primary:
        raise ValueError("Measured selection differs from the proposed primary model. Review the plan.")
    return results, primary, bundle.summary()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", default="configs/local/imdb-final-comparison-plan.json")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--reviewed-by")
    args = parser.parse_args()
    try:
        if args.freeze and (not args.reviewed_by or not args.reviewed_by.strip() or len(args.reviewed_by) > 128):
            raise ValueError("--freeze requires a nonempty reviewer name/research identifier.")
        plan_path = safe_path(args.plan, ROOT)
        results, primary, data = inspect(plan_path)
        frozen = []
        if args.freeze:
            comparisons = [{k: r[k] for k in ("key", "config", "run", "config_sha256",
                            "artifact_sha256", "tuning_report", "tuning_report_sha256")} for r in results]
            payloads = []
            for result in results:
                payload = dict(schema_version=1, task="binary_imdb", model_frozen=True,
                    selected_for_final_test=True, reviewed_by=args.reviewed_by.strip(),
                    reviewed_at=datetime.now(timezone.utc).isoformat(),
                    manifest_hashes=data["manifest_hashes"],
                    comparison_plan_sha256=sha256(plan_path),
                    comparison_candidates=comparisons, primary_selection_metric="macro_f1",
                    primary_model_key=primary, is_primary_selected_model=result["key"] == primary,
                    tuning_report=result["tuning_report"],
                    tuning_report_sha256=result["tuning_report_sha256"],
                    purpose="Frozen English binary IMDb academic comparison")
                payload[result["digest_key"]] = result["artifact_sha256"]
                path = safe_path(Path(result["run"]) / "selection.json", ROOT, output=True)
                if path.exists() and not compatible(read_json(path), payload):
                    raise ValueError("Existing selection differs from this comparison: " + str(path))
                payloads.append((path, payload))
            # Check every existing decision before writing any missing record.
            for path, payload in payloads:
                frozen.append(dict(path=str(path.relative_to(ROOT)), status=publish_selection(path, payload)))
        print(json.dumps(dict(ready=True, primary_model=primary, primary_selection_metric="macro_f1",
              tuning_comparison=[dict(model=r["name"], **{k: r["metrics"][k] for k in
                ("accuracy", "macro_f1", "negative_log_likelihood", "multiclass_brier", "ece")}) for r in results],
              data=data, selection_records=frozen, freeze_completed=args.freeze,
              final_test_evaluated=False), indent=2))
        return 0
    except Exception as error:
        print(json.dumps(dict(ready=False, error_type=type(error).__name__, detail=str(error),
              note="Review retained records. An identical freeze command can finish missing compatible selections."), indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

