"""Token-classification adapter for the shared, local-only Phase 4 trainer."""
from __future__ import annotations
from contextlib import nullcontext
import math
from .alignment import labelled_windows
from .decoding import decode_window, merge_candidates
from .metrics import with_cohorts
from .windows import encode_windows, window_settings


def iter_rows(examples, tokenizer, config: dict):
    maximum = window_settings(config, tokenizer)["maximum_training_rows"]
    emitted = 0
    for example in examples:
        text = example.read_text()
        windows = encode_windows(text, tokenizer, config)
        rows, _ = labelled_windows(windows, example.aspects, text, config["labels"])
        for row in rows:
            emitted += 1
            if emitted > maximum:
                raise ValueError("Extraction training-row budget exceeded; review the run size explicitly.")
            yield row


def collate(rows, tokenizer):
    from transformers import DataCollatorForTokenClassification
    if getattr(tokenizer, "padding_side", "right") != "right":
        raise ValueError("The extraction collator requires explicit right padding.")
    return DataCollatorForTokenClassification(tokenizer, padding=True,
        label_pad_token_id=-100, return_tensors="pt")(rows)


def alignment_report(examples, tokenizer, config: dict) -> dict:
    """Audit actual tokenizer coverage before fitting; never prints review text."""
    totals = {"review_count": 0, "window_count": 0, "training_row_count": 0,
              "gold_span_count": 0, "fully_represented_gold_spans": 0,
              "masked_partial_span_occurrences": 0}
    maximum = window_settings(config, tokenizer)["maximum_training_rows"]
    for example in examples:
        text = example.read_text()
        _, report = labelled_windows(encode_windows(text, tokenizer, config), example.aspects, text, config["labels"])
        totals["review_count"] += 1
        for key, value in report.items():
            totals[key] += value
        if totals["training_row_count"] > maximum:
            raise ValueError("Alignment audit exceeds the configured row budget.")
    return {**totals, "policy": "all_subwords_bio_exact_original_boundaries_partial_spans_masked_v1"}


def _forward(model, tokenizer, window, device, dtype):
    import torch
    inputs = tokenizer.pad([window.features], padding=True, return_tensors="pt")
    inputs = {key: value.to(device) for key, value in inputs.items()}
    context = torch.autocast(device_type="cuda", dtype=dtype) if dtype is not None else nullcontext()
    with context:
        logits = model(**inputs).logits[0, :len(window.offsets)]
    if not torch.isfinite(logits).all().item():
        raise RuntimeError("Nonfinite extractor logits; do not fabricate a replacement prediction.")
    return logits


def predict_examples(model, tokenizer, examples, config: dict, device, dtype=None,
                     temperature: float = 1.0) -> list[dict]:
    import torch
    if not math.isfinite(temperature) or temperature != 1.0:
        raise ValueError("Extraction token confidence is explicitly uncalibrated; no fitted span-confidence claim.")
    if getattr(tokenizer, "padding_side", "right") != "right":
        raise ValueError("Extraction inference requires right padding.")
    names = sorted(config["labels"], key=config["labels"].get)
    model.eval()
    results = []
    with torch.inference_mode():
        for example in examples:
            if example.language_code not in config["language_scope"]:
                results.append({"record_id": example.record_id, "status": "unsupported_language", "aspects": None})
                continue
            text = example.read_text()
            windows = encode_windows(text, tokenizer, config)
            candidates, repaired, clipped = [], 0, 0
            for window in windows:
                logits = _forward(model, tokenizer, window, device, dtype)
                values, indices = torch.softmax(logits.float(), dim=-1).max(dim=-1)
                decoded, diagnostics = decode_window(window, indices.cpu().tolist(), values.cpu().tolist(), text, names)
                candidates.extend(decoded)
                repaired += diagnostics["invalid_i_repaired_as_b"]
                clipped += diagnostics["boundary_candidates_discarded"]
            aspects, merge = merge_candidates(candidates)
            results.append({"record_id": example.record_id, "status": "analysed", "aspects": aspects,
                "language_code": example.language_code, "offset_unit": "original_unicode_code_points",
                "confidence_calibrated": False, "experimental": True,
                "coverage": {"window_count": len(windows), "boundary_candidates_discarded": clipped,
                             "invalid_i_repaired_as_b": repaired, **merge},
                "implicit_aspects_supported": False})
    return results


def score(examples, predictions, config: dict) -> dict:
    return with_cohorts(examples, predictions, list(config["taxonomy"]["aspects"]))


def token_diagnostics(model, tokenizer, examples, config: dict, device, dtype=None) -> dict:
    """Secondary all-subword/window-token metrics; never replace exact span F1.

    Duplicate overlapping-window positions contribute repeatedly under this
    disclosed protocol. Partial gold spans and special/pad tokens are masked.
    No calibration/production confidence claim is made from token accuracy.
    """
    import torch
    from ml.common.metrics import classification_metrics
    names = sorted(config["labels"], key=config["labels"].get)
    confusion = [[0 for _ in names] for _ in names]
    model.eval()
    with torch.inference_mode():
        for example in examples:
            text = example.read_text()
            windows = encode_windows(text, tokenizer, config)
            rows, _ = labelled_windows(windows, example.aspects, text, config["labels"])
            # Validate full coverage first, then preserve the exact window masks.
            from .alignment import aligned_labels
            for window in windows:
                targets, _, _ = aligned_labels(window, example.aspects, text, config["labels"])
                indices = _forward(model, tokenizer, window, device, dtype).argmax(dim=-1).cpu().tolist()
                for target, predicted in zip(targets, indices):
                    if target != -100:
                        confusion[target][predicted] += 1
    count = sum(map(sum, confusion))
    per_label = {}
    for index, name in enumerate(names):
        true_positive, support = confusion[index][index], sum(confusion[index])
        predicted = sum(row[index] for row in confusion)
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / support if support else 0.0
        per_label[name] = {"precision": precision, "recall": recall, "support": support,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}
    positive = [row for name, row in per_label.items() if name != "O"]
    return {"count": count, "accuracy": sum(confusion[i][i] for i in range(len(names))) / count if count else None,
            "labels": names, "confusion_matrix": confusion, "per_label": per_label,
            "non_o_macro_f1": sum(row["f1"] for row in positive) / len(positive) if positive else None,
            "weighting_policy": "all_subwords_and_overlapping_window_occurrences; specials/pads/partial spans=-100",
            "secondary_metric_only": True}
