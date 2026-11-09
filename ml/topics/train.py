"""Train-only bounded LDA exploration, portable numeric state, no downloads."""
from ml.common.artifacts import create_run, write_json, sha256
from ml.common.gates import require_training_approval


def train(config, bundle):
    require_training_approval(config, bundle, component="topics")
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    from importlib.metadata import version
    texts = [row["text"] if isinstance(row, dict) else row.text for row in bundle.records["train"]]
    if not texts or len(texts) > 10000 or sum(len(text.encode()) for text in texts) > 128 * 1024**2:
        raise ValueError("Bound the actual permitted train-only topic corpus.")
    topics = config.get("n_topics", 12)
    if type(topics) is not int or not 2 <= topics <= 32:
        raise ValueError("Choose2..32 exploratory topics.")
    run = create_run(config, "topics")
    vectorizer = CountVectorizer(max_features=20000, min_df=2)
    matrix = vectorizer.fit_transform(texts)
    model = LatentDirichletAllocation(n_components=topics, max_iter=10, learning_method="batch", random_state=42, n_jobs=1)
    model.fit(matrix)
    tokens = vectorizer.get_feature_names_out().tolist()
    state = {"schema_version": 1, "method": "lda_variational", "components": model.components_.tolist(),
        "vocabulary": tokens, "doc_topic_prior": model.doc_topic_prior_, "training_manifest_hashes": bundle.manifest_hashes,
        "sklearn_version": version("scikit-learn"), "curated_theme_mapping": None}
    write_json(run / "topic_model.json", state)
    write_json(run / "training_report.json", {"trained": True, "method": "lda_variational", "documents": len(texts),
        "topics": topics, "perplexity_train_diagnostic": float(model.perplexity(matrix)), "test_evaluated": False,
        "model_sha256": sha256(run / "topic_model.json"), "clusters_are_movie_facts": False})
    return run
