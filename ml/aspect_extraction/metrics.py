"""Exact original-span metrics, with explicit zero-support and cohort policies."""
from __future__ import annotations
from collections import Counter


def _prf(gold: set, predicted: set) -> dict:
    true_positive = len(gold & predicted)
    precision = true_positive / len(predicted) if predicted else 0.0
    recall = true_positive / len(gold) if gold else 0.0
    return {"precision": precision, "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "true_positive": true_positive, "false_positive": len(predicted - gold),
            "false_negative": len(gold - predicted), "gold_support": len(gold), "predicted_count": len(predicted)}


def exact_metrics(examples, predictions, categories: list[str]) -> dict:
    examples = list(examples)
    by_id = {row["record_id"]: row for row in predictions}
    if len(by_id) != len(predictions) or set(by_id) != {row.record_id for row in examples}:
        raise ValueError("Predictions must cover exactly the requested review identities once.")
    gold, predicted = set(), set()
    empty_reviews = false_positive_empty = 0
    for example in examples:
        text = example.read_text()
        row = by_id[example.record_id]
        if row.get("status", "analysed") != "analysed" or not isinstance(row.get("aspects"), list):
            raise ValueError("Unavailable extraction must not masquerade as an empty model prediction.")
        for span in example.aspects:
            gold.add((example.record_id, span.aspect, span.start, span.end))
        for span in row["aspects"]:
            if span["aspect"] not in categories or type(span["start"]) is not int or type(span["end"]) is not int or (
                not 0 <= span["start"] < span["end"] <= len(text)) or span.get("text") != text[span["start"]:span["end"]]:
                raise ValueError("Predicted evidence must address the unchanged original review.")
            key = example.record_id, span["aspect"], span["start"], span["end"]
            if key in predicted:
                raise ValueError("Duplicate predicted evidence must be resolved before scoring.")
            predicted.add(key)
        if not example.aspects:
            empty_reviews += 1
            false_positive_empty += bool(row["aspects"])
    overall = _prf(gold, predicted)
    per_aspect = {category: _prf({key for key in gold if key[1] == category},
                               {key for key in predicted if key[1] == category}) for category in categories}
    return {"count": len(examples), **overall, "primary_score": overall["f1"],
        "primary_metric": "exact_category_and_original_span_micro_f1", "per_aspect": per_aspect,
        "unsupported_gold_categories": [category for category, result in per_aspect.items() if result["gold_support"] == 0],
        "reviewed_empty_reviews": empty_reviews, "empty_reviews_with_false_positive": false_positive_empty,
        "zero_denominator_policy": "precision/recall/F1=0; all empty cases remain visible",
        "overlap_match_credit": False, "offset_unit": "original_unicode_code_points"}


def with_cohorts(examples, predictions, categories: list[str]) -> dict:
    examples = list(examples)
    result = exact_metrics(examples, predictions, categories)
    cohorts = {}
    by_id = {row["record_id"]: row for row in predictions}
    for example in examples:
        tags = set(example.cohorts or ())
        if example.language_code:
            tags.add("language:" + example.language_code)
        if example.script:
            tags.add("script:" + example.script)
        if any(not isinstance(tag, str) or not tag.strip() for tag in tags):
            raise ValueError("Cohorts require explicit human/source annotation strings.")
        for tag in tags:
            cohorts.setdefault(tag, []).append(example)
    result["cohorts"] = {tag: exact_metrics(rows, [by_id[row.record_id] for row in rows], categories)
                         for tag, rows in sorted(cohorts.items())}
    result["cohort_policy"] = "Explicit human/source strata; may overlap; absent support establishes no language capability."
    return result
