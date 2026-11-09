"""Attach a separately trained auxiliary result without changing sentiment.

Learned fusion is a different experiment requiring out-of-fold base predictions,
separate calibration and controlled held-out evaluation. It is not fabricated by
an arithmetic polarity inversion or by claiming this diagnostic is a fusion model.
"""
from copy import deepcopy


def attach_sarcasm_context(sentiment: dict, sarcasm: dict) -> dict:
    if sentiment.get("task") not in {"three_class_movie", "multilingual_movie"}:
        raise ValueError("Auxiliary movie context requires a genuine three-class sentiment result.")
    if sarcasm.get("task") != "sarcasm":
        raise ValueError("The auxiliary result must come from the independent sarcasm task.")
    result = deepcopy(sentiment)
    result["sarcasm_context"] = deepcopy(sarcasm)
    result["fusion_status"] = "independent_diagnostics_only"
    result["sentiment_modified"] = False
    return result
