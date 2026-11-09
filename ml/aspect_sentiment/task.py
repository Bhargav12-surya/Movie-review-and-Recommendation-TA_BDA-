"""Actual target-conditioned training/inference adapter for the shared ABSA engine."""
from __future__ import annotations
from contextlib import nullcontext
from ml.common.calibration import softmax
from ml.common.metrics import classification_metrics
from .targeting import CONDITIONING_VERSION, target_input

LABELS = {"negative": 0, "neutral": 1, "positive": 2}
LABEL_NAMES = ["negative", "neutral", "positive"]


def iter_rows(examples, tokenizer, config: dict):
    count = 0
    maximum = int(config.get("tokenization", {}).get("maximum_training_rows", 30000))
    for example in examples:
        for span in example.aspects:
            if type(span.sentiment) is not int or span.sentiment not in (0, 1, 2):
                raise ValueError("Aspect training requires its own genuine target sentiment label.")
            count += 1
            if count > maximum:
                raise ValueError("Aspect-target row budget exceeded; review the run size.")
            inputs = target_input(example, span, tokenizer, config)
            yield {**inputs.features, "labels": span.sentiment}


def collate(rows, tokenizer):
    from transformers import DataCollatorWithPadding
    return DataCollatorWithPadding(tokenizer=tokenizer, padding=True, return_tensors="pt")(rows)


def _requests(examples, tokenizer, config):
    maximum = int(config.get("tokenization", {}).get("maximum_training_rows", 30000))
    count = 0
    for example_index, example in enumerate(examples):
        for span in example.aspects:
            count += 1
            if count > maximum:
                raise ValueError("Aspect inference/calibration target count exceeds its bounded policy.")
            yield example_index, span, target_input(example, span, tokenizer, config)


def _batched_logits(model, tokenizer, requests, config, device, dtype=None):
    import torch
    batch_size = int(config.get("inference", {}).get("micro_batch_size", 4))
    if not 1 <= batch_size <= 16:
        raise ValueError("Inference micro-batch must remain within1..16.")
    pending = []
    model.eval()
    with torch.inference_mode():
        for request in requests:
            pending.append(request)
            if len(pending) == batch_size:
                features = collate([item[2].features for item in pending], tokenizer)
                features = {key: value.to(device) for key, value in features.items()}
                context = torch.autocast(device_type="cuda", dtype=dtype) if dtype is not None else nullcontext()
                with context:
                    logits = model(**features).logits.float().cpu().tolist()
                if len(logits) != len(pending) or any(len(row) != 3 for row in logits):
                    raise ValueError("Aspect sentiment model must return three logits per target.")
                yield from zip(pending, logits)
                pending = []
        if pending:
            features = collate([item[2].features for item in pending], tokenizer)
            features = {key: value.to(device) for key, value in features.items()}
            context = torch.autocast(device_type="cuda", dtype=dtype) if dtype is not None else nullcontext()
            with context:
                logits = model(**features).logits.float().cpu().tolist()
            if len(logits) != len(pending) or any(len(row) != 3 for row in logits):
                raise ValueError("Aspect sentiment model must return three logits per target.")
            yield from zip(pending, logits)


def calibration_logits(model, tokenizer, examples, config, device, dtype=None):
    values, labels = [], []
    for (_, span, _), logits in _batched_logits(model, tokenizer, _requests(examples, tokenizer, config), config, device, dtype):
        if type(span.sentiment) is not int or span.sentiment not in (0, 1, 2):
            raise ValueError("Calibration requires an independent human target sentiment label.")
        values.append(logits)
        labels.append(span.sentiment)
    if not values:
        raise ValueError("Calibration has no genuine annotated aspect targets.")
    return values, labels


def predict_examples(model, tokenizer, examples, config, device, dtype=None, temperature=1.0):
    examples = list(examples)
    results = [{"record_id": example.record_id, "aspects": [], "language_code": example.language_code,
                "conditioning_version": CONDITIONING_VERSION, "experimental": True} for example in examples]
    for (index, span, inputs), logits in _batched_logits(model, tokenizer,
            _requests(examples, tokenizer, config), config, device, dtype):
        probabilities = softmax([logits], temperature)[0]
        results[index]["aspects"].append({"aspect": span.aspect, "start": span.start, "end": span.end,
            "text": span.text, "label": LABEL_NAMES[max(range(3), key=probabilities.__getitem__)],
            "probabilities": dict(zip(LABEL_NAMES, probabilities)), "temperature": temperature,
            "calibration_status": "temperature_applied; inspect model manifest for calibration provenance",
            "context_start": inputs.context_start, "context_end": inputs.context_end,
            "offset_unit": "original_unicode_code_points"})
    return results


def score(examples, predictions, config: dict) -> dict:
    examples, predictions = list(examples), list(predictions)
    if len(examples) != len(predictions) or len({row["record_id"] for row in predictions}) != len(predictions):
        raise ValueError("Gold-target predictions must align one-to-one with review identities.")
    supplied = {row["record_id"]: row for row in predictions}
    actual, probabilities, categories, groups = [], [], [], {}
    for example in examples:
        if example.record_id not in supplied:
            raise ValueError("A gold review is absent from target-conditioned evaluation.")
        by_target = {}
        for item in supplied[example.record_id]["aspects"]:
            key = (item["aspect"], item["start"], item["end"])
            if key in by_target:
                raise ValueError("Duplicate target prediction.")
            by_target[key] = item
        gold_keys = {(span.aspect, span.start, span.end) for span in example.aspects}
        if set(by_target) != gold_keys:
            raise ValueError("Gold-target classification must not omit or add extraction targets.")
        for span in example.aspects:
            if type(span.sentiment) is not int or span.sentiment not in (0, 1, 2):
                raise ValueError("Gold aspect sentiment is missing.")
            item = by_target[(span.aspect, span.start, span.end)]
            if set(item["probabilities"]) != set(LABELS):
                raise ValueError("Aspect probability labels do not match the fixed three-class contract.")
            values = [item["probabilities"][name] for name in LABEL_NAMES]
            index = len(actual)
            actual.append(span.sentiment)
            probabilities.append(values)
            categories.append(span.aspect)
            tags = list(example.cohorts)
            tags.append("language:" + example.language_code)
            if example.script:
                tags.append("script:" + example.script)
            for tag in set(tags):
                groups.setdefault(tag, []).append(index)
    if not actual:
        raise ValueError("No gold aspect targets exist for sentiment evaluation.")
    metrics = classification_metrics(actual, probabilities, LABEL_NAMES)
    def selected(indices):
        return classification_metrics([actual[i] for i in indices], [probabilities[i] for i in indices], LABEL_NAMES)
    per_aspect = {}
    for aspect in config["taxonomy"]["aspects"]:
        indices = [index for index, category in enumerate(categories) if category == aspect]
        per_aspect[aspect] = selected(indices) if indices else {"count": 0, "status": "no_evidence", "metrics": None}
    return {"primary_score": metrics["macro_f1"], "metrics": metrics, "per_aspect": per_aspect,
            "cohorts": {tag: selected(indices) for tag, indices in sorted(groups.items())},
            "condition": "gold_target_sentiment_not_end_to_end_extraction",
            "cohort_policy": "Explicit human/source metadata; overlapping cohorts and all task classes retained."}
