# Delivery validation — 26 September 2026

## Completed checks

- **14 backend tests passed**: four-label sentiment, contextual negation (including “not bad”), binary-model disagreement, absent evidence, review screening, aggregate updates and deduplication, idempotent submissions, response hardening, browser/backend taxonomy parity, genre intersection, dislikes, cold-start titles, ALS loading/ID isolation, API validation, persisted history/reviews, conversational context and metric denominators.
- **9 notebook files** passed nbformat validation and Python syntax checks; all code cells passed **in-process execution with the default download/training switches disabled**. The hosted execution environment prevented the normal Jupyter kernel transport from starting, so this does not claim a browser-based JupyterLab run. Optional transformer/speech cells were not executed.
- **6 Scala source files compiled**, producing 28 JVM classes with Scala 2.12.18 / Spark 3.5.7 dependencies.
- **Scala ALS job executed successfully** on the real MovieLens small ratings dataset using Java 17 and `local[2]`; model selection used validation RMSE.
- Frontend JavaScript syntax and browser-demo engine workflows passed: review aspect scores, rating persistence, combined genres, title-linked summaries, new-review aggregate updates and exclusions. Asset references were checked against the bundled files. Full browser visual QA was not performed in this environment.
- The real **IMDb TF-IDF/logistic model trained successfully**, and its trusted local artifact is included.

## Measured sentiment result

| Measure | Result |
|---|---:|
| Training reviews | 19,733 |
| Validation reviews | 5,046 |
| Held-out test reviews | 24,799 |
| Test accuracy | 90.052% |
| Test macro-F1 | 0.90052 |
| Test ROC-AUC | 0.96315 |
| Selected C | 2.0 |

These are measured outputs in `artifacts/sentiment_tfidf_metrics.json`, not illustrative values. The official IMDb test partition was deduplicated to 24,799 reviews and exact overlaps were removed from training. This is **not the untouched official 25,000-row benchmark**, and the number should not be presented as directly interchangeable with published benchmark scores. Validation used movie groups when URL-derived IDs were available. The model card records the training library version and provenance.

## Measured recommendation result

| Measure | Result |
|---|---:|
| Selected ALS rank | 32 |
| Selected regularization | 0.1 |
| Validation RMSE | 0.91635 |
| Test RMSE on scorable interactions | 0.95287 |
| Test prediction coverage | 90.722% |
| ALS Recall@10 | 0.01047 |
| Train-popularity Recall@10 | 0.04230 |
| ALS NDCG@10 | 0.00903 |
| Train-popularity NDCG@10 | 0.04227 |

Ranking used 573 users with at least one held-out rating ≥4, a 100-item ALS candidate cap, and seen-training-item exclusion. Users with no returned relevant items count as zero. The test set contained 10,358 interactions. ALS's explicit-rating objective and rare-item recommendations produced weaker top-K retrieval than popularity in this run. **Do not claim ALS beat the baseline.** Hybrid ranking, diversity, semantic retrieval and revised candidate policies require their own validation-set experiments and an untouched final test protocol; no measured improvement is asserted for them.

## Not validated here

- DistilBERT/ABSA fine-tuning and GPU inference; human aspect annotations.
- Supervised fake-review detection: no ground-truth deception corpus is supplied.
- Authenticated TMDB ingestion: requires your token.
- Optional downloaded sentence-transformer, T5 and Whisper models; microphone/browser support.
- Multi-node Spark/Hadoop throughput or production deployment of the Python backend.
- Scala sentiment training, Hadoop job execution and a long-running streaming job. These programs compiled; only the Scala ALS job was run on real data.

The preview is a static demonstration. The downloaded application includes the actual local Python backend and trained CPU sentiment artifact. Its `/api/health` endpoint makes the active model explicit.
