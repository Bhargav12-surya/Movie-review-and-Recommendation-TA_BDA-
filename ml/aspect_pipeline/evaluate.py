"""Full predicted-target evaluation, distinct from gold-target classification."""
from pathlib import Path
import time
from ml.aspect_common.data import load_experiment
from ml.aspect_common.metrics import pipeline_metrics
from ml.common.artifacts import read_json, safe_path, sha256, write_json
from ml.common.gates import reserve_final_test
from .predict import predict


def evaluate(extraction_config, extraction_run, sentiment_config, sentiment_run, output_directory,
             split="tuning", final_test=False, selection_path=None, device_name="cpu"):
    if split not in {"tuning", "calibration", "test"}:
        raise ValueError("Pipeline evaluation excludes train.")
    bundle = load_experiment(extraction_config)
    root = extraction_config["_workspace"]
    model_hashes = {"extraction": sha256(safe_path(extraction_run, root) / "model_manifest.json"),
                    "sentiment": sha256(safe_path(sentiment_run, root) / "model_manifest.json")}
    if split == "test":
        selection = read_json(safe_path(selection_path, root))
        if selection.get("model_frozen") is not True or selection.get("selected_for_final_test") is not True or not selection.get("reviewed_by") or (
            selection.get("model_hashes") != model_hashes or selection.get("manifest_hashes") != bundle.manifest_hashes):
            raise ValueError("A human-reviewed frozen paired-model selection record is required.")
        # Reserve against the extractor's owned run, not a fresh output directory,
        # so changing output names does not silently repeat this final pipeline test.
        reserve_final_test(safe_path(extraction_run, root, output=True) / "pipeline_test", bundle, split, final_test)
    output = safe_path(output_directory, root, output=True)
    output.mkdir(parents=True, exist_ok=False)
    rows = bundle.records[split]
    predictions = predict(rows, extraction_config, extraction_run, sentiment_config, sentiment_run, device_name)
    names = ["negative", "neutral", "positive"]
    gold = {row.record_id: [{"aspect": span.aspect, "start": span.start, "end": span.end,
             "sentiment": names[span.sentiment]} for span in row.aspects] for row in rows}
    predicted = {row["record_id"]: row["aspects"] for row in predictions}
    metrics = pipeline_metrics(gold, predicted, extraction_config["taxonomy"]["aspects"])
    report = {"task": "aspect_pipeline", "split": split, "manifest_hashes": bundle.manifest_hashes,
              "model_hashes": model_hashes, "metrics": metrics, "gold_targets_used_for_inference": False}
    write_json(output / "evaluation.json", report)
    return report
