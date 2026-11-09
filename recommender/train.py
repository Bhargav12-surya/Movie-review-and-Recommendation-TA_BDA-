"""Tune only hybrid weights on supplied genuine validation cohorts; ALS is Scala."""
from .hybrid import recommend
from .evaluation import evaluate
from ml.common.artifacts import read_json


def select_als_trial(run_directories):
    """Select among actual comparable validation reports, never test reports."""
    from pathlib import Path
    if not run_directories or len(run_directories) > 100:
        raise ValueError("Supply1..100 actual sequential ALS trial directories.")
    trials, protocol = [], None
    for directory in run_directories:
        directory = Path(directory)
        manifest = read_json(directory / "factor_manifest.json")
        current = {key: manifest[key] for key in ("train_end", "validation_end", "input_files_sha256", "sampled_ranking")}
        if manifest.get("evaluation_split") != "validation" or (protocol is not None and current != protocol):
            raise ValueError("ALS selection requires the same validation/candidate/input protocol.")
        protocol = current
        parts = list((directory / "ranking_metrics").glob("part-*.json"))
        if len(parts) != 1:
            raise ValueError("One actual Spark aggregate metric record is required.")
        metrics = read_json(parts[0])
        if not metrics.get("evaluatedUsers") or metrics.get("ndcgAt10") is None:
            raise ValueError("Actual validation support and NDCG are required.")
        trials.append((metrics["ndcgAt10"], manifest, str(directory)))
    _, manifest, source = max(trials, key=lambda row: row[0])
    return {"selected_from": source, "rank": manifest["rank"], "regularization": manifest["regularization"],
            "iterations": manifest["iterations"], "protocol": protocol, "test_used": False}


def tune(candidates, movies, validation_profiles, relevant, training_counts, collaborative_by_user, k=10):
    if len(candidates) > 100 or not candidates:
        raise ValueError("Supply1..100 prespecified validation trials.")
    trials = []
    for candidate in candidates:
        trial = {**candidate, "weights_validated": True}
        rankings = {user: [row["movie_id"] for row in recommend(movies, profile, trial, collaborative_by_user.get(user), k)["recommendations"]]
                    for user, profile in validation_profiles.items()}
        metrics = evaluate(rankings, relevant, movies, training_counts, k)
        trials.append((metrics["ndcg@k"], trial, metrics))
    _, selected, metrics = max(trials, key=lambda row: row[0])
    return {"selected_config": selected, "validation_metrics": metrics, "trial_count": len(trials),
            "test_used": False, "als_training": "actual Scala Spark MLlib only"}
