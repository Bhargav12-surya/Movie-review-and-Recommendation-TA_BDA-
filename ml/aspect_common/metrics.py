"""Exact original-span and target-plus-polarity set metrics, without token inflation."""


def _counts(gold, predicted):
    true_positive = len(gold & predicted)
    false_positive, false_negative = len(predicted - gold), len(gold - predicted)
    precision = true_positive / len(predicted) if predicted else 0.0
    recall = true_positive / len(gold) if gold else 0.0
    return {"precision": precision, "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "true_positive": true_positive, "false_positive": false_positive, "false_negative": false_negative,
        "gold_support": len(gold), "predicted_support": len(predicted)}


def _sets(gold_by_id, predicted_by_id, taxonomy, with_polarity):
    if set(gold_by_id) != set(predicted_by_id):
        raise ValueError("Every gold review, including empty ones, requires exactly one prediction record.")
    result = []
    for supplied in (gold_by_id, predicted_by_id):
        keys = set()
        for record_id, rows in supplied.items():
            targets = set()
            for row in rows:
                if row["aspect"] not in taxonomy or type(row["start"]) is not int or type(row["end"]) is not int or not 0 <= row["start"] < row["end"]:
                    raise ValueError("Invalid exact-span evaluation key.")
                target = (record_id, row["aspect"], row["start"], row["end"])
                if target in targets:
                    raise ValueError("Duplicate target must not inflate evaluation support.")
                targets.add(target)
                if with_polarity:
                    sentiment = row.get("sentiment", row.get("label"))
                    if sentiment not in {"negative", "neutral", "positive"}:
                        raise ValueError("Pipeline targets require actual three-class polarity predictions.")
                    target += (sentiment,)
                keys.add(target)
        result.append(keys)
    return result


def extraction_metrics(gold_by_id: dict, predicted_by_id: dict, taxonomy) -> dict:
    gold, predicted = _sets(gold_by_id, predicted_by_id, taxonomy, False)
    return {**_counts(gold, predicted), "per_aspect": {name: _counts(
        {key for key in gold if key[1] == name}, {key for key in predicted if key[1] == name}) for name in taxonomy},
        "reviews": len(gold_by_id), "match_policy": "exact_original_code_point_span_and_category",
        "zero_denominator_policy": "precision/recall/F1=0; supports remain explicit"}


def pipeline_metrics(gold_by_id: dict, predicted_by_id: dict, taxonomy) -> dict:
    gold, predicted = _sets(gold_by_id, predicted_by_id, taxonomy, True)
    result = _counts(gold, predicted)
    return {**result, "primary_score": result["f1"], "extraction": extraction_metrics(gold_by_id, predicted_by_id, taxonomy),
        "per_aspect": {name: _counts({key for key in gold if key[1] == name},
                                     {key for key in predicted if key[1] == name}) for name in taxonomy},
        "match_policy": "exact_original_span_category_and_polarity", "implicit_aspects_evaluated": False}
