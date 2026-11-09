def evaluate(labels, scores, threshold):
    from sklearn.metrics import average_precision_score, precision_recall_fscore_support, confusion_matrix, precision_recall_curve, auc
    import math
    if not labels or len(labels) != len(scores) or set(labels) != {0, 1} or any(type(label) is not int for label in labels) or any(not math.isfinite(score) or not 0 <= score <= 1 for score in scores) or not 0 <= threshold <= 1:
        raise ValueError("Actual held-out binary moderation labels and bounded scores are required.")
    predicted = [int(score >= threshold) for score in scores]
    precision, recall, f1, _ = precision_recall_fscore_support(labels, predicted, average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
    pr_precision, pr_recall, _ = precision_recall_curve(labels, scores)
    return {"count": len(labels), "precision": float(precision), "recall": float(recall), "f1": float(f1),
        "average_precision": float(average_precision_score(labels, scores)), "false_positive_rate": float(fp / (fp + tn)),
        "pr_auc_trapezoidal": float(auc(pr_recall, pr_precision)),
        "threshold": threshold, "threshold_must_be_selected_on_validation": True}
