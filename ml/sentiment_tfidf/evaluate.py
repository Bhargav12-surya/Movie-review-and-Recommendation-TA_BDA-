"""Evaluate real portable baseline artifacts on frozen local split references."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from ml.common.artifacts import read_json, safe_path, write_json
from ml.common.config import load_config
from ml.common.data import load_experiment
from ml.common.gates import reserve_final_test
from ml.common.metrics import classification_metrics
from .predict import load_model, probabilities


def cohort_metrics(records, labels, values, label_names) -> dict:
    """Score only explicit human/source cohorts; never infer labels from text.

    Cohorts can overlap. Macro-F1 retains the full task label space even when a
    particular cohort lacks a class, and per-class support makes this visible.
    """
    if not (len(records) == len(labels) == len(values)):
        raise ValueError("Cohort records and actual model outputs must align.")
    cohorts = {}
    for index, record in enumerate(records):
        tags = list(record.metadata.get("cohorts") or [])
        for key in ("language_code", "script"):
            supplied = record.metadata.get(key)
            if supplied is not None:
                if not isinstance(supplied, str) or not supplied:
                    raise ValueError("Cohort metadata must be an explicit nonempty annotation string.")
                tags.append(("language" if key == "language_code" else "script") + ":" + supplied)
        if any(not isinstance(tag, str) or not tag for tag in tags):
            raise ValueError("Cohort annotations must be nonempty strings.")
        for tag in set(tags):
            cohorts.setdefault(tag, []).append(index)
    return {tag: classification_metrics([labels[index] for index in indices],
        [values[index] for index in indices], label_names) for tag, indices in sorted(cohorts.items())}


def evaluate(config: dict, run_directory: str | Path, split: str = "tuning", final_test: bool = False) -> dict:
    if split not in {"tuning", "calibration", "test"}:
        raise ValueError("Only frozen tuning/calibration/test roles may be evaluated.")
    bundle = load_experiment(config)
    model = load_model(config, run_directory)
    run = model["directory"]
    if model["report"].get("manifest_hashes") != bundle.manifest_hashes or (
            model["state"].get("manifest_hashes") != bundle.manifest_hashes):
        raise ValueError("Evaluation manifests differ from this model's recorded experiment.")
    if split == "test":
        selection = read_json(safe_path(run / "selection.json", config["_workspace"]))
        if selection.get("model_frozen") is not True or selection.get("selected_for_final_test") is not True or (
                selection.get("model_sha256") != model["report"]["model_sha256"] or
                selection.get("manifest_hashes") != bundle.manifest_hashes or not selection.get("reviewed_by")):
            raise ValueError("Final test needs a human-reviewed frozen model selection record.")
    reserve_final_test(run, bundle, split, final_test)
    maximum_bytes = int(config.get("tfidf", {}).get("maximum_materialized_text_bytes", 256 * 1024**2))
    if not 1024 <= maximum_bytes <= 512 * 1024**2:
        raise ValueError("Evaluation text materialization budget is outside the laptop bound.")
    # The first test text read happens only after explicit selection + reservation.
    texts, labels = bundle.texts_labels(split, maximum_bytes)
    values, known_features = probabilities(model, texts)
    report = {"schema_version": 1, "component": "tfidf", "task": config["task"], "split": split,
        "labels": bundle.labels, "manifest_hashes": bundle.manifest_hashes,
        "model_sha256": model["report"]["model_sha256"],
        "metrics": classification_metrics(labels, values, bundle.label_names),
        "cohorts": cohort_metrics(bundle.records[split], labels, values, bundle.label_names),
        "cohort_policy": "Human/source metadata only; cohorts may overlap and absent cohorts establish no language capability.",
        "zero_feature_rows": sum(count == 0 for count in known_features),
        "prediction_policy": "Full classifier evaluation includes zero-feature rows; serving flags them for review.",
        "calibration_scope": "fit_split_diagnostic" if split == "calibration" else "held_out_from_calibration",
        "generated_at": datetime.now(timezone.utc).isoformat()}
    path = safe_path(run / "evaluations" / (split + "-" + uuid.uuid4().hex + ".json"),
                     config["_workspace"], output=True)
    write_json(path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--split", choices=("tuning", "calibration", "test"), default="tuning")
    parser.add_argument("--final-test", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(evaluate(load_config(args.config), args.run_dir, args.split, args.final_test), indent=2))
        return 0
    except Exception:
        print(json.dumps({"status": "evaluation_unavailable", "metrics": None}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
