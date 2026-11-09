"""Actual bounded Isolation Forest fit, saved as numeric trees rather than pickle."""
from ml.common.artifacts import create_run, write_json, sha256
from ml.common.gates import require_training_approval
from .features import behaviour_vector, BEHAVIOUR_FEATURES


def train(config, bundle):
    require_training_approval(config, bundle, component="review_risk")
    rows = bundle.records["train"]
    if not 32 <= len(rows) <= 10000:
        raise ValueError("Require32..10000 legitimate training behaviour rows; no synthetic replacement.")
    values = [behaviour_vector(row) for row in rows]
    from sklearn.ensemble import IsolationForest
    model = IsolationForest(n_estimators=100, max_samples=min(256, len(values)), contamination="auto", random_state=42, n_jobs=1)
    model.fit(values)
    run = create_run(config, "review_risk")
    trees = []
    for estimator, selected in zip(model.estimators_, model.estimators_features_):
        tree = estimator.tree_
        trees.append({"children_left": tree.children_left.tolist(), "children_right": tree.children_right.tolist(),
            "feature": tree.feature.tolist(), "threshold": tree.threshold.tolist(), "samples": tree.n_node_samples.tolist(),
            "selected_features": selected.tolist()})
    state = {"schema_version": 1, "method": "isolation_forest_relative_anomaly_v1", "features": list(BEHAVIOUR_FEATURES),
        "max_samples": int(model.max_samples_), "trees": trees, "manifest_hashes": bundle.manifest_hashes,
        "calibrated_fraud_probability": False}
    write_json(run / "model.json", state)
    write_json(run / "training_report.json", {"trained": True, "task": "review_risk", "training_rows": len(rows),
        "model_sha256": sha256(run / "model.json"), "test_evaluated": False, "fake_detection_accuracy": None})
    return run
