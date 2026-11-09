"""Inference from owned portable linear-model weights; never unpickle artifacts."""
from __future__ import annotations
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import platform
from ml.common.artifacts import read_json, safe_path, sha256
from ml.common.calibration import softmax
from ml.common.config import LABELS, load_config

MAX_ARTIFACT_BYTES = 64 * 1024**2


def logits_from_scores(scores, class_count: int) -> list[list[float]]:
    """Binary scikit decision scores describe class1 relative to class0.

    [0,margin] preserves LogisticRegression's sigmoid probabilities. SVM scores
    have no probability interpretation until calibration on held-out examples.
    """
    import numpy as np
    values = np.asarray(scores, dtype=np.float64)
    if class_count == 2:
        if values.ndim == 2 and values.shape[1] == 1:
            values = values[:, 0]
        if values.ndim != 1:
            raise ValueError("Binary model must have one decision score per example.")
        result = np.column_stack((np.zeros_like(values), values))
    else:
        if values.ndim != 2 or values.shape[1] != class_count:
            raise ValueError("Decision score dimensions disagree with the task label map.")
        result = values
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite model decision scores.")
    return result.tolist()


def load_model(config: dict, run_directory: str | Path):
    """Reconstruct fixed vocabulary/IDF and numeric weights without fitting.

    Only bounded JSON is loaded. Exact recorded sklearn/NumPy versions avoid
    silently changing feature behavior; a future migration needs review.
    """
    import numpy as np
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    # Evaluation appends reports/reservations to this owned run; raw sources are
    # never a permissible run location even for the read-only inference command.
    root = safe_path(run_directory, config["_workspace"], output=True)
    report = read_json(safe_path(root / "training_report.json", config["_workspace"]))
    model_file = safe_path(root / "model.json", config["_workspace"])
    if report.get("component") != "tfidf" or report.get("trained") is not True:
        raise ValueError("A completed owned TF-IDF training report is required.")
    if model_file.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError("Portable model exceeds its bounded artifact size.")
    if sha256(model_file) != report.get("model_sha256"):
        raise ValueError("Portable model changed after training; inference is unavailable.")
    state = read_json(model_file, max_bytes=MAX_ARTIFACT_BYTES)
    task = state.get("task")
    if task != config["task"] or task not in LABELS or state.get("labels") != LABELS[task]:
        raise ValueError("Artifact task/label map does not match this configuration.")
    if report.get("task") != task or report.get("labels") != state["labels"]:
        raise ValueError("Artifact and completed report disagree about their task.")
    if state.get("manifest_hashes") != report.get("manifest_hashes"):
        raise ValueError("Artifact and report disagree about their frozen experiment.")
    if state.get("format") != "movieintel-linear-v1" or state.get("estimator") not in {
            "logistic_regression", "linear_svm"}:
        raise ValueError("Unknown portable model format/estimator.")
    for package in ("scikit-learn", "numpy"):
        if state.get("dependencies", {}).get(package) != importlib.metadata.version(package):
            raise ValueError("Inference dependencies differ from the recorded model environment.")
    if state.get("python_minor") != ".".join(platform.python_version_tuple()[:2]):
        raise ValueError("Python Unicode/tokenization version differs from the trained artifact.")
    tokens = state.get("vocabulary")
    if not isinstance(tokens, list) or not 1 <= len(tokens) <= 100000 or any(
            not isinstance(token, str) or not token or len(token.encode("utf-8")) > 8192 for token in tokens):
        raise ValueError("Portable vocabulary is absent or outside its bounded contract.")
    if len(tokens) != len(set(tokens)):
        raise ValueError("Portable vocabulary contains duplicate feature indices.")
    classes = len(state["labels"])
    if state.get("classes") != list(range(classes)):
        raise ValueError("Portable class order is not the exact task label order.")
    count_rows = 1 if classes == 2 else classes
    coefficients = np.asarray(state.get("coefficients"), dtype=np.float64)
    intercept = np.asarray(state.get("intercept"), dtype=np.float64)
    if coefficients.shape != (count_rows, len(tokens)) or intercept.shape != (count_rows,) or not (
            np.isfinite(coefficients).all() and np.isfinite(intercept).all()):
        raise ValueError("Portable coefficient dimensions/values are invalid.")
    settings = state.get("vectorizer", {})
    common = {"analyzer": "word", "lowercase": settings.get("lowercase"),
              "token_pattern": settings.get("token_pattern"), "stop_words": None,
              "strip_accents": None, "ngram_range": tuple(settings.get("ngram_range", [])),
              "binary": settings.get("binary"), "dtype": np.float64,
              "vocabulary": {token: index for index, token in enumerate(tokens)}}
    if type(common["lowercase"]) is not bool or type(common["binary"]) is not bool or not (
            isinstance(common["token_pattern"], str) and len(common["token_pattern"]) <= 2048):
        raise ValueError("Portable tokenization settings are invalid.")
    if common["ngram_range"] not in {(1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3)}:
        raise ValueError("Portable n-gram range is invalid.")
    if state.get("representation") == "tfidf":
        if settings.get("norm") not in {None, "l1", "l2"} or type(settings.get("sublinear_tf")) is not bool:
            raise ValueError("Portable TF-IDF settings are invalid.")
        vectorizer = TfidfVectorizer(**common, use_idf=True, smooth_idf=True,
            norm=settings["norm"], sublinear_tf=settings["sublinear_tf"])
        idf = np.asarray(state.get("idf"), dtype=np.float64)
        if idf.shape != (len(tokens),) or not np.isfinite(idf).all() or (idf < 1).any():
            raise ValueError("Portable inverse document frequencies are invalid.")
        vectorizer.idf_ = idf
    elif state.get("representation") == "bow" and state.get("idf") is None:
        vectorizer = CountVectorizer(**common)
    else:
        raise ValueError("Portable feature representation is invalid.")
    calibration = state.get("calibration", {})
    temperature = calibration.get("temperature")
    if calibration.get("method") != "temperature_on_decision_scores" or calibration.get("fitted_on") != "calibration" or (
            not isinstance(temperature, (int, float)) or isinstance(temperature, bool) or
            not math.isfinite(temperature) or temperature <= 0):
        raise ValueError("Real held-out calibration metadata is required.")
    if calibration.get("manifest_sha256") != state.get("manifest_hashes", {}).get("calibration"):
        raise ValueError("Calibration is not tied to the frozen calibration manifest.")
    scope = state.get("language_scope")
    if not isinstance(scope, list) or not scope or any(not isinstance(item, str) or not item for item in scope):
        raise ValueError("Artifact language scope is absent or invalid.")
    return {"directory": root, "state": state, "report": report, "vectorizer": vectorizer,
            "coefficients": coefficients, "intercept": intercept}


def probabilities(model: dict, texts: list[str]) -> tuple[list[list[float]], list[int]]:
    features = model["vectorizer"].transform(texts)
    scores = features @ model["coefficients"].T + model["intercept"]
    logits = logits_from_scores(scores, len(model["state"]["labels"]))
    values = softmax(logits, model["state"]["calibration"]["temperature"])
    return values, features.getnnz(axis=1).tolist()


def predict(config: dict, run_directory: str | Path, texts: list[str], language: str) -> dict:
    if not isinstance(texts, list) or not 1 <= len(texts) <= 64 or any(
            not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 512 * 1024 for text in texts):
        raise ValueError("Supply1..64 nonempty bounded review strings.")
    model = load_model(config, run_directory)
    scope = model["state"].get("language_scope", [])
    if not isinstance(language, str) or language not in scope:
        raise ValueError("Requested language is outside this artifact's declared training scope.")
    values, feature_counts = probabilities(model, texts)
    names = sorted(model["state"]["labels"], key=model["state"]["labels"].get)
    predictions = []
    for row, feature_count in zip(values, feature_counts):
        index = max(range(len(row)), key=row.__getitem__)
        predictions.append({"status": "analysed" if feature_count else "insufficient_vocabulary_evidence",
            "label": names[index] if feature_count else None,
            "probabilities": dict(zip(names, row)), "known_feature_count": feature_count,
            "uncertainty_index": 1.0 - max(row), "needs_review": feature_count == 0,
            "calibration_method": "temperature_on_decision_scores",
            "audience_score_eligible": False})
    return {"task": model["state"]["task"], "labels": model["state"]["labels"],
            "model_version": model["directory"].name, "model_sha256": model["report"]["model_sha256"],
            "release_status": "research_artifact_requires_separate_serving_approval",
            "language": language, "predictions": predictions}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--language", required=True, help="Explicit language; no keyword-based language guess.")
    args = parser.parse_args()
    try:
        print(json.dumps(predict(load_config(args.config), args.run_dir, [args.text], args.language), indent=2))
        return 0
    except Exception:
        print(json.dumps({"status": "model_unavailable", "predictions": None}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
