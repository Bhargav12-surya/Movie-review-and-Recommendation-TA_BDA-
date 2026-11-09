import math
from ml.common.artifacts import read_json, sha256
from .features import behaviour_vector, text_signals, BEHAVIOUR_FEATURES


def _average_path(n):
    return 0.0 if n <= 1 else 1.0 if n == 2 else 2 * (math.log(n - 1) + 0.5772156649015329) - 2 * (n - 1) / n


def anomaly_score(values, state):
    if state.get("features") != list(BEHAVIOUR_FEATURES) or not state.get("trees") or len(state["trees"]) > 1000:
        raise ValueError("Unknown or oversized owned isolation model.")
    lengths = []
    for tree in state["trees"]:
        node, depth, visited = 0, 0, set()
        while tree["children_left"][node] != -1:
            if node in visited or len(visited) > 10000:
                raise ValueError("Invalid cyclic/oversized isolation tree.")
            visited.add(node)
            feature = tree["selected_features"][tree["feature"][node]]
            node = tree["children_left"][node] if values[feature] <= tree["threshold"][node] else tree["children_right"][node]
            depth += 1
        lengths.append(depth + _average_path(tree["samples"][node]))
    normalizer = _average_path(state["max_samples"])
    if not normalizer:
        raise ValueError("Isolation training sample support is invalid.")
    return 2 ** (-sum(lengths) / len(lengths) / normalizer)


def predict(text, existing_texts, behaviour=None, model_state=None):
    signals = text_signals(text, existing_texts)
    anomaly = anomaly_score(behaviour_vector(behaviour), model_state) if behaviour is not None and model_state is not None else None
    available = []
    if signals["history_count"]:
        available.append(float(signals["exact_duplicate_count"] > 0))
    if signals["maximum_tfidf_cosine"] is not None:
        available.append(signals["maximum_tfidf_cosine"])
    if anomaly is not None:
        available.append(anomaly)
    return {"risk_index": 100 * max(available) if available else None, "risk_band": None,
        "method_version": "duplicate_similarity_anomaly_max_v1", "signals": signals,
        "relative_behaviour_anomaly": anomaly, "calibrated_fraud_probability": False,
        "automated_fake_verdict": None, "moderation_action": "human_review_only",
        "limitations": "Similarity can be legitimate quotation/repetition. Index and thresholds require validation; sentiment is excluded."}


def load_owned(run):
    report = read_json(run / "training_report.json")
    if report.get("trained") is not True or sha256(run / "model.json") != report.get("model_sha256"):
        raise ValueError("Actual owned risk artifact required.")
    return read_json(run / "model.json", max_bytes=32 * 1024**2)
