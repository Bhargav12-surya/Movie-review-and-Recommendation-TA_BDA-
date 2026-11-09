"""Train-only BoW/TF-IDF linear baselines; default command only reports readiness."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import time
from ml.common.artifacts import create_run, sha256, write_json
from ml.common.calibration import fit_temperature, softmax
from ml.common.config import load_config
from ml.common.data import load_experiment
from ml.common.gates import require_training_approval, training_preflight
from ml.common.hardware import guard_resources
from ml.common.metrics import classification_metrics
from .predict import logits_from_scores


def settings(config: dict) -> dict:
    value = {"estimator": "logistic_regression", "representation": "tfidf", "max_features": 50000,
        "ngram_range": [1, 2], "minimum_document_frequency": 2, "maximum_document_frequency": 1.0,
        "token_pattern": r"(?u)\w+(?:['’]\w+)*|[^\w\s]", "lowercase": True,
        "binary_counts": False, "norm": "l2", "sublinear_tf": True,
        "regularization_c": 1.0, "max_iterations": 2000, "class_weight": None,
        "seed": 42, "maximum_materialized_text_bytes": 256 * 1024**2}
    value.update(config.get("tfidf", {}))
    if value["estimator"] not in {"logistic_regression", "linear_svm"} or value["representation"] not in {"tfidf", "bow"}:
        raise ValueError("Choose a documented linear estimator and BoW/TF-IDF representation.")
    for key, lower, upper in (("max_features", 100, 100000), ("max_iterations", 100, 10000),
                              ("minimum_document_frequency", 1, 1000),
                              ("maximum_materialized_text_bytes", 1024, 512 * 1024**2)):
        if type(value[key]) is not int or not lower <= value[key] <= upper:
            raise ValueError("TF-IDF integer setting is outside its laptop bound: " + key)
    if tuple(value["ngram_range"]) not in {(1, 1), (1, 2), (1, 3), (2, 2), (2, 3), (3, 3)}:
        raise ValueError("Choose an explicit unigram/bigram/trigram range.")
    for key in ("regularization_c", "maximum_document_frequency"):
        if isinstance(value[key], bool) or not isinstance(value[key], (int, float)) or not math.isfinite(value[key]):
            raise ValueError("TF-IDF numeric settings must be finite.")
    if not 0 < value["regularization_c"] <= 100 or not 0 < value["maximum_document_frequency"] <= 1:
        raise ValueError("Invalid regularization or maximum-document-frequency bound.")
    if value["norm"] not in {None, "l1", "l2"} or value["class_weight"] not in {None, "balanced"}:
        raise ValueError("Unknown normalization/class-weight policy.")
    if any(type(value[key]) is not bool for key in ("lowercase", "binary_counts", "sublinear_tf")):
        raise ValueError("Text-view flags must be booleans.")
    if type(value["seed"]) is not int or not 0 <= value["seed"] <= 2**32 - 1:
        raise ValueError("A bounded explicit random seed is required.")
    pattern = value["token_pattern"]
    if not isinstance(pattern, str) or not pattern or len(pattern) > 2048:
        raise ValueError("A bounded reviewed token pattern is required.")
    import re
    compiled = re.compile(pattern)
    if compiled.groups or compiled.match(""):
        raise ValueError("Token patterns cannot capture groups or emit empty tokens.")
    languages = config.get("language_scope", [])
    if not isinstance(languages, list) or not languages or any(not isinstance(item, str) or not item for item in languages):
        raise ValueError("An explicit, later evaluated language scope is required.")
    return value


def preflight(config: dict) -> dict:
    report = training_preflight(config, component="tfidf")
    try:
        report["settings"] = settings(config)
    except (ValueError, TypeError) as error:
        report["blockers"].append("TF-IDF configuration is invalid: " + type(error).__name__)
    for package in ("scikit-learn", "numpy", "scipy"):
        try:
            importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            report["blockers"].append("Missing manually installed dependency: " + package)
    report["component"] = "tfidf"
    report["ready"] = not report["blockers"]
    return report


def train(config: dict) -> dict:
    options = settings(config)
    bundle = load_experiment(config)
    require_training_approval(config, bundle, component="tfidf")
    resource_before = guard_resources(config)
    import numpy as np
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    run = create_run(config, "tfidf")
    started = time.perf_counter()
    try:
        # This is the sole vocabulary/IDF fit. Test text is never opened in training.
        train_texts, train_labels = bundle.texts_labels("train", options["maximum_materialized_text_bytes"])
        common = dict(analyzer="word", lowercase=options["lowercase"], stop_words=None,
            strip_accents=None, token_pattern=options["token_pattern"],
            ngram_range=tuple(options["ngram_range"]), binary=options["binary_counts"],
            min_df=options["minimum_document_frequency"], max_df=options["maximum_document_frequency"],
            max_features=options["max_features"], dtype=np.float64)
        if options["representation"] == "tfidf":
            vectorizer = TfidfVectorizer(**common, use_idf=True, smooth_idf=True,
                norm=options["norm"], sublinear_tf=options["sublinear_tf"])
        else:
            vectorizer = CountVectorizer(**common)
        train_features = vectorizer.fit_transform(train_texts)
        del train_texts
        if options["estimator"] == "logistic_regression":
            estimator = LogisticRegression(C=options["regularization_c"], solver="lbfgs",
                max_iter=options["max_iterations"], class_weight=options["class_weight"],
                random_state=options["seed"])
        else:
            estimator = LinearSVC(C=options["regularization_c"], dual="auto",
                max_iter=options["max_iterations"], class_weight=options["class_weight"],
                random_state=options["seed"])
        import warnings
        from sklearn.exceptions import ConvergenceWarning
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            estimator.fit(train_features, train_labels)
        del train_features, train_labels
        if estimator.classes_.tolist() != list(range(len(bundle.labels))):
            raise ValueError("Fitted estimator class order differs from the task contract.")
        tuning_texts, tuning_labels = bundle.texts_labels("tuning", options["maximum_materialized_text_bytes"])
        tuning_features = vectorizer.transform(tuning_texts)
        del tuning_texts
        tuning_logits = logits_from_scores(estimator.decision_function(tuning_features), len(bundle.labels))
        tuning_metrics = classification_metrics(tuning_labels, softmax(tuning_logits), bundle.label_names)
        tuning_metrics["probability_status"] = "uncalibrated_decision_scores"
        if options["estimator"] == "linear_svm":
            for key in ("negative_log_likelihood", "multiclass_brier", "ece", "ece_bins", "ece_policy"):
                tuning_metrics.pop(key, None)
        tuning_zero_features = int((tuning_features.getnnz(axis=1) == 0).sum())
        del tuning_features, tuning_logits, tuning_labels
        calibration_texts, calibration_labels = bundle.texts_labels("calibration", options["maximum_materialized_text_bytes"])
        calibration_features = vectorizer.transform(calibration_texts)
        del calibration_texts
        calibration_logits = logits_from_scores(estimator.decision_function(calibration_features), len(bundle.labels))
        temperature = fit_temperature(calibration_logits, calibration_labels)
        calibration_metrics = classification_metrics(calibration_labels,
            softmax(calibration_logits, temperature), bundle.label_names)
        calibration_metrics["evaluation_scope"] = "calibration_fit_split_not_unbiased_heldout_performance"
        del calibration_features, calibration_logits, calibration_labels
        tokens = [""] * len(vectorizer.vocabulary_)
        for token, index in vectorizer.vocabulary_.items():
            tokens[index] = token
        dependencies = {name: importlib.metadata.version(name) for name in ("scikit-learn", "numpy", "scipy")}
        state = {"format": "movieintel-linear-v1", "task": config["task"], "labels": bundle.labels,
            "classes": estimator.classes_.tolist(), "estimator": options["estimator"],
            "representation": options["representation"], "vocabulary": tokens,
            "idf": vectorizer.idf_.tolist() if options["representation"] == "tfidf" else None,
            "coefficients": estimator.coef_.tolist(), "intercept": estimator.intercept_.tolist(),
            "vectorizer": {"lowercase": options["lowercase"], "token_pattern": options["token_pattern"],
                "ngram_range": options["ngram_range"], "binary": options["binary_counts"],
                "norm": options["norm"], "sublinear_tf": options["sublinear_tf"]},
            "calibration": {"method": "temperature_on_decision_scores", "temperature": temperature,
                "fitted_on": "calibration", "manifest_sha256": bundle.manifest_hashes["calibration"]},
            "language_scope": config["language_scope"], "manifest_hashes": bundle.manifest_hashes,
            "dependencies": dependencies, "python_minor": ".".join(platform.python_version_tuple()[:2])}
        write_json(run / "model.json", state)
        if (run / "model.json").stat().st_size > 64 * 1024**2:
            raise ValueError("Model exceeds portable artifact bounds; retain failed run for inspection.")
        report = {"schema_version": 1, "component": "tfidf", "task": config["task"],
            "labels": bundle.labels, "manifest_hashes": bundle.manifest_hashes, "trained": True,
            "estimator": options["estimator"], "representation": options["representation"],
            "model_sha256": sha256(run / "model.json"), "config_sha256": sha256(config["_config_path"]),
            "tuning_metrics": tuning_metrics, "tuning_zero_feature_rows": tuning_zero_features,
            "calibration_metrics": calibration_metrics, "feature_count": len(tokens),
            "elapsed_seconds": time.perf_counter() - started, "dependencies": dependencies,
            "resources_before": resource_before, "finished_at": datetime.now(timezone.utc).isoformat(),
            "official_test_text_read": False, "test_metrics": None,
            "approval_status": "research_run_not_automatically_approved_for_serving"}
        write_json(run / "training_report.json", report)
        write_json(run / "model_card.json", {"component": "tfidf", "task": config["task"],
            "trained": True, "training_report": "training_report.json", "labels": bundle.labels,
            "declared_language_scope": config["language_scope"], "heldout_test_evaluated": False,
            "limitations": ["MovieLens reviews were not used as text.", "IMDb is binary only.",
                "Calibration metrics on fitting examples are not unbiased generalization evidence.",
                "No sarcasm-specific model or language support is established by this baseline."]})
        return report
    except Exception as error:
        write_json(run / "failure.json", {"status": "failed", "error_type": type(error).__name__,
            "training_completed": False, "note": "Retain this fresh directory; never overwrite/retry it in place."})
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    parser.add_argument("--execute", action="store_true", help="Run only this separately approved bounded configuration.")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        report = train(config) if args.execute else preflight(config)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if args.execute or report["ready"] else 2
    except Exception:
        print(json.dumps({"status": "blocked_or_failed", "training_started_by_default": False,
            "detail": "Review prerequisites, source/approval/configuration and retained run reports."}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
