# Evaluation plan

Use the notebooks to generate results; this document is a protocol, not a table of assumed scores.

| Component | Required measures | Leakage and interpretation controls |
|---|---|---|
| Binary sentiment model | Accuracy, macro precision/recall/F1, confusion, ROC-AUC, ECE | Official IMDb test; movie-group validation when IDs exist; deduplicate by normalized text; fit vectorizer only on train |
| Four-label runtime policy | Per-class precision/recall/F1, macro-F1, confusion, coverage and selective accuracy by confidence | Separately human-annotated Positive/Negative/Mixed/Neutral set containing negation, neutral phrasing, sarcasm, short reviews and model/rule disagreements |
| Aspects | Macro-F1 per aspect, evidence coverage, annotation agreement | Human labels; movie-disjoint train/validation/test; absent aspect stays absent |
| Recommendations | RMSE, prediction coverage, Recall@10, NDCG@10, Precision@10, item coverage/diversity | Per-user temporal split; popularity uses train only; include unserved eligible users as zero; report candidate cap |
| Review screening | Precision, recall, false positive rate against a human audit | No fake labels inferred from sentiment, punctuation or writing style; source/author holdout if training |
| Summaries | Human factual support, polarity coverage, relevance; ROUGE with human references | All-review aggregation vs first-page sample clearly distinguished; movie-disjoint reference set |
| Chat | Retrieval relevance, hard-filter compliance, source fidelity | Fixed human query set; deterministic vs semantic vs transformer wording ablation |
| Speech | WER/CER and latency | Consented recordings with reference transcripts, accents/noise, no training/test speaker reuse |
| Scalability | Input rows/bytes, wall time, shuffle, peak memory, partitions/executors | Same snapshot, hardware and execution settings; local Spark is not proof of cluster-scale throughput |

Ablate genre-only vs genre+theme, positive-only vs signed profiles, recency on/off, ALS on/off, semantic retrieval on/off, screening on/off and diversity on/off. Tune on validation data. Keep final test results untouched until the design is selected.

The transformer notebook trains/evaluates first-chunk sentiment while the API aggregates chunks. Report this difference and evaluate the runtime policy separately on long reviews. Report both the number of requested test interactions and the number ALS could score.
