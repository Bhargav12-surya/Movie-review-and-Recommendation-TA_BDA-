"""Transparent classification/calibration metrics; no training-set performance claims."""
import math
from numbers import Integral


def classification_metrics(y_true, probabilities, label_names, bins: int = 15) -> dict:
    y_true, probabilities, label_names = list(y_true), list(probabilities), list(label_names)
    n, classes = len(y_true), len(label_names)
    if not n or n != len(probabilities) or classes < 2 or not 1 <= bins <= 100:
        raise ValueError("Nonempty aligned labels/probabilities and valid class/bin dimensions required.")
    confusion = [[0] * classes for _ in range(classes)]
    buckets = [[0, 0.0, 0.0] for _ in range(bins)]
    nll = brier = 0.0
    for label, supplied in zip(y_true, probabilities):
        row = list(map(float, supplied))
        if isinstance(label, bool) or not isinstance(label, Integral) or not 0 <= label < classes or len(row) != classes:
            raise ValueError("Label/probability class dimensions do not match the artifact.")
        label = int(label)
        if any(not math.isfinite(value) or not 0 <= value <= 1 for value in row) or abs(sum(row) - 1) > 1e-6:
            raise ValueError("Invalid probability distribution.")
        prediction = max(range(classes), key=row.__getitem__)
        confusion[label][prediction] += 1
        confidence = row[prediction]
        bucket = buckets[min(int(confidence * bins), bins - 1)]
        bucket[0] += 1
        bucket[1] += confidence
        bucket[2] += int(prediction == label)
        nll -= math.log(max(row[label], 1e-15))
        brier += sum((probability - int(index == label)) ** 2 for index, probability in enumerate(row))
    per_class = {}
    for index, name in enumerate(label_names):
        true_positive = confusion[index][index]
        support = sum(confusion[index])
        predicted = sum(row[index] for row in confusion)
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / support if support else 0.0
        per_class[name] = {"precision": precision, "recall": recall,
                           "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
                           "support": support}
    return {"count": n, "labels": label_names, "confusion_matrix": confusion,
            "accuracy": sum(confusion[i][i] for i in range(classes)) / n,
            "macro_f1": sum(row["f1"] for row in per_class.values()) / classes,
            "weighted_f1": sum(row["f1"] * row["support"] for row in per_class.values()) / n,
            "per_class": per_class, "negative_log_likelihood": nll / n,
            "multiclass_brier": brier / n,
            "ece": sum(count / n * abs(correct / count - confidence / count)
                       for count, confidence, correct in buckets if count),
            "ece_bins": bins, "ece_policy": "equal_width_top_label_confidence",
            "zero_denominator_policy": "precision/recall/F1=0; observed support remains explicit"}
