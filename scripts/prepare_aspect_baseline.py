"""Compute an explicit analytical baseline on real train/tuning manifests only."""
import argparse
from collections import Counter
from dataclasses import replace
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.aspect_common.config import load_config
from ml.aspect_common.data import load_experiment
from ml.common.artifacts import safe_path, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    bundle = load_experiment(config)
    if config["task"] == "aspect_extraction":
        from ml.aspect_extraction.task import score
        predictions = [{"record_id": row.record_id, "status": "analysed", "aspects": []} for row in bundle.records["tuning"]]
        method = "empty_extractor_baseline"
    else:
        from ml.aspect_sentiment.task import score
        counts = Counter(span.sentiment for row in bundle.records["train"] for span in row.aspects)
        majority = max(range(3), key=lambda label: (counts[label], -label))
        names = ["negative", "neutral", "positive"]
        predictions = [{"record_id": row.record_id, "aspects": [{"aspect": span.aspect, "start": span.start, "end": span.end,
            "probabilities": {name: float(index == majority) for index, name in enumerate(names)}} for span in row.aspects]} for row in bundle.records["tuning"]]
        method = "actual_training_majority_target_baseline_uncalibrated"
    result = {"task": config["task"], "manifest_hashes": bundle.manifest_hashes, "method": method,
              "tuning_metrics": score(bundle.records["tuning"], predictions, config), "test_used": False,
              "data_summary": bundle.summary(), "not_a_production_predictor": True}
    write_json(safe_path(args.output, config["_workspace"], output=True), result)


if __name__ == "__main__":
    main()
