"""Multi-label BCE training, per-theme calibration and tuning-only thresholds."""
import math
from ml.common.calibration import fit_temperature


def iter_rows(examples, tokenizer, config):
    maximum = config.get("tokenization", {}).get("maximum_sequence_length", 128)
    for row in examples:
        encoded = tokenizer(row.text, truncation=True, max_length=maximum)
        yield {**encoded, "labels": list(row.targets)}


def collate(rows, tokenizer):
    import torch
    from transformers import DataCollatorWithPadding
    targets = [row.get("labels") for row in rows]
    features = [{key: value for key, value in row.items() if key != "labels"} for row in rows]
    result = DataCollatorWithPadding(tokenizer, padding=True, return_tensors="pt")(features)
    if any(target is not None for target in targets):
        if any(target is None for target in targets):
            raise ValueError("Mixed labelled/unlabelled theme batch.")
        result["labels"] = torch.tensor(targets, dtype=torch.float32)
    return result


def logits(model, tokenizer, examples, config, device, dtype=None):
    import torch
    from contextlib import nullcontext
    result = []
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(examples), 4):
            batch = list(iter_rows(examples[start:start + 4], tokenizer, config))
            for row in batch:
                row.pop("labels", None)
            inputs = {key: value.to(device) for key, value in collate(batch, tokenizer).items()}
            with torch.autocast("cuda", dtype=dtype) if dtype is not None else nullcontext():
                values = model(**inputs).logits.float().cpu().tolist()
            if any(not math.isfinite(value) for row in values for value in row):
                raise RuntimeError("Nonfinite theme logits.")
            result.extend(values)
    return result


def _sigmoid(value):
    return 1 / (1 + math.exp(-max(-700, min(700, value))))


def multilabel_metrics(targets, probabilities, names, thresholds):
    if not targets or len(targets) != len(probabilities):
        raise ValueError("Actual aligned multi-label evaluation rows are required.")
    per_theme, all_tp, all_fp, all_fn = {}, 0, 0, 0
    for index, name in enumerate(names):
        truth = [bool(row[index]) for row in targets]
        guess = [row[index] >= thresholds[index] for row in probabilities]
        tp = sum(a and b for a, b in zip(truth, guess))
        fp = sum(not a and b for a, b in zip(truth, guess))
        fn = sum(a and not b for a, b in zip(truth, guess))
        precision, recall = tp / (tp + fp) if tp + fp else 0, tp / (tp + fn) if tp + fn else 0
        per_theme[name] = {"precision": precision, "recall": recall,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0, "support": sum(truth)}
        all_tp, all_fp, all_fn = all_tp + tp, all_fp + fp, all_fn + fn
    micro = 2 * all_tp / (2 * all_tp + all_fp + all_fn) if 2 * all_tp + all_fp + all_fn else 0
    return {"count": len(targets), "micro_f1": micro, "macro_f1": sum(row["f1"] for row in per_theme.values()) / len(names), "per_theme": per_theme}


def calibrate(model, tokenizer, bundle, config, device, dtype=None):
    values = logits(model, tokenizer, bundle.records["calibration"], config, device, dtype)
    temperatures, calibration_supported = [], []
    for index in range(len(config["labels"])):
        targets = [int(row.targets[index]) for row in bundle.records["calibration"]]
        temperatures.append(fit_temperature([[0, row[index]] for row in values], targets) if set(targets) == {0, 1} else 1.0)
        calibration_supported.append(set(targets) == {0, 1})
    tuning = logits(model, tokenizer, bundle.records["tuning"], config, device, dtype)
    thresholds = []
    for index in range(len(temperatures)):
        probabilities = [_sigmoid(row[index] / temperatures[index]) for row in tuning]
        truth = [row.targets[index] for row in bundle.records["tuning"]]
        def f1(threshold):
            tp = sum(actual and predicted >= threshold for actual, predicted in zip(truth, probabilities))
            fp = sum(not actual and predicted >= threshold for actual, predicted in zip(truth, probabilities))
            fn = sum(actual and predicted < threshold for actual, predicted in zip(truth, probabilities))
            return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0
        thresholds.append(max([0.1 + 0.05 * step for step in range(17)], key=f1) if any(truth) else 1.0)
    return {"method": "independent_binary_temperature", "temperatures": temperatures, "thresholds": thresholds,
            "calibration_supported": calibration_supported, "calibration_split": "calibration", "threshold_selection_split": "tuning", "test_used": False}


def predict_examples(model, tokenizer, examples, config, device, dtype=None, temperature=1.0):
    calibration = config.get("_calibration", {})
    temperatures = calibration.get("temperatures", [1.0] * len(config["labels"]))
    thresholds = calibration.get("thresholds", [0.5] * len(config["labels"]))
    values = logits(model, tokenizer, examples, config, device, dtype)
    result = [{"record_id": row.record_id, "probabilities": [_sigmoid(value / scale) for value, scale in zip(output, temperatures)],
             "thresholds": thresholds, "audience_theme_sentiment": None, "kind": "theme_relevance", "experimental": True}
            for row, output in zip(examples, values)]
    for row in result:
        row["relevance"] = dict(zip(config["labels"], row["probabilities"]))
        row["theme_labels"] = [name for index, name in enumerate(config["labels"]) if row["probabilities"][index] >= thresholds[index]]
    return result


def score(examples, predictions, config):
    if [row.record_id for row in examples] != [row["record_id"] for row in predictions]:
        raise ValueError("Theme prediction identity mismatch.")
    thresholds = predictions[0]["thresholds"]
    metrics = multilabel_metrics([row.targets for row in examples], [row["probabilities"] for row in predictions], list(config["labels"]), thresholds)
    return {"primary_score": metrics["micro_f1"], "metrics": metrics}
