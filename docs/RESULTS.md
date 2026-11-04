# Results and interpretation

The delivered sentiment model achieved **90.05% accuracy and 0.90052 macro-F1** on a deduplicated held-out IMDb test set. This supports using it as a baseline for binary review sentiment, but does not validate every aspect score, identify fake reviews or establish performance on current multilingual social reviews. Runtime serving adds contextual negation plus Mixed and Neutral decisions; those four-label decisions require a separately annotated four-class evaluation and must not inherit the binary benchmark number.

The MovieLens-small ALS model achieved **0.95287 test RMSE with 90.72% scorable coverage**. It did **not** outperform the train-popularity baseline for top-10 retrieval in this run. This is a useful experimental finding: minimizing explicit-rating error does not guarantee the best ranking, especially with rare items and candidate truncation.

The hybrid serving code adds content, genre/theme combinations, dislikes, recency and diversity. It handles new users/items functionally. Its quality improvement must be measured separately; the project does not infer that improvement from the ALS RMSE.

Exact machine-readable measurements are in `artifacts/sentiment_tfidf_metrics.json`, `artifacts/als_metrics.json` and `artifacts/ranking_metrics.json`. Model and dataset information are in `models/model-card.json` and `docs/data-provenance.json`.
