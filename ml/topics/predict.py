"""Variational document-topic inference using actually fitted topic-word counts."""
def predict(texts, state):
    import numpy as np
    from scipy.special import psi
    from sklearn.feature_extraction.text import CountVectorizer
    if len(texts) > 10000:
        raise ValueError("Bound topic inference documents.")
    components = np.asarray(state["components"], dtype=np.float64)
    if components.ndim != 2 or not np.isfinite(components).all() or (components <= 0).any():
        raise ValueError("Invalid fitted topic counts.")
    vocabulary = state["vocabulary"]
    if components.shape[1] != len(vocabulary) or len(set(vocabulary)) != len(vocabulary):
        raise ValueError("Topic vocabulary dimensions differ.")
    features = CountVectorizer(vocabulary={token: index for index, token in enumerate(vocabulary)}).transform(texts)
    beta = np.exp(psi(components) - psi(components.sum(axis=1))[:, None])
    result = []
    for row in features:
        ids, counts = row.indices, row.data
        gamma = np.ones(components.shape[0])
        for _ in range(100):
            theta = np.exp(psi(gamma) - psi(gamma.sum()))
            phi_normalizer = theta @ beta[:, ids] + 1e-100
            updated = float(state["doc_topic_prior"]) + theta * ((counts / phi_normalizer) @ beta[:, ids].T)
            if np.mean(np.abs(updated - gamma)) < 1e-3:
                gamma = updated
                break
            gamma = updated
        result.append((gamma / gamma.sum()).tolist())
    return {"topic_distributions": result, "known_token_counts": features.sum(axis=1).A1.tolist(),
            "prior_only_documents": [index for index, row in enumerate(features) if not row.nnz],
            "curated_theme_mapping": None, "inference": "bounded_variational_approximation"}
