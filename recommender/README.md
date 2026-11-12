# Hybrid recommendations

Actual Scala Spark MLlib ALS trains anonymous MovieLens source users/items.
Python loads hash-verified numeric Parquet factors with an approved canonical
mapping. One real ALS validation trial and matched popularity comparison have
completed; measured results and limitations are in [model_card.md](model_card.md).

`compare_popularity.py` reconstructs the exact Spark validation sample and checks
saved ranking parity before comparing against training popularity. See
[VALIDATION_COMPARISON.md](VALIDATION_COMPARISON.md).

`validate_hybrid.py` evaluates a fixed15-trial grid using the actual shared hybrid
ranker and evaluator,training-only source rating profiles,and cached matched
validation candidates. Actual study execution is pending. The grid is
`configs/recommendation/hybrid_validation_grid.json`. Run explicitly from root:

```powershell
.\.venv\Scripts\python.exe -B -m recommender.validate_hybrid `
  --comparison-directory 'artifacts/als-popularity-comparison-0021d34c0f87402eb6f1a989424b2c91' `
  --grid 'configs/recommendation/hybrid_validation_grid.json' `
  --execute
```

Source benchmark profiles do not grant application consent. The interim study
includes ALS,genre and training popularity; semantic/theme components still need
real validated artifacts. It uses retrospective genre metadata and sampled
candidate sets,so results do not establish full-catalogue quality. The purity
control must reproduce the exact matched popularity baseline. Selection uses
NDCG@10,then Precision@10,Recall@10,fewer nonzero channels,and declared trial order.
Cold candidates have no invented ALS prediction. Missing channels are handled by
the existing shared ranker's active-channel normalization. Empty lists retain the
fixedK denominator. A popularity-only result is retained honestly.

Each run creates fresh evidence files. Selected research weights intentionally
retain `weights_validated=false` and `serving_approved=false`; no backend config
is changed. Actual final test,full five-channel quality,app-user ALS fold-in and
catalogue-scale serving remain open. The backend's5000-candidate gate is not
waived by these offline studies.

App users use explicit genre/theme preferences and consented interactions.They
never borrow numeric MovieLens identities. Optional ALS-WR fold-in needs reviewed
method approval and sufficient genuine ratings. Normalization precedes bounded
diversity reranking; explanations expose actual contributing inputs. Match scores
are separate from audience sentiment.

Focused hybrid-study contracts:8passed,including train-only profile construction,
no inferred application consent,cold-score handling,and honest model selection.
No real study metrics are claimed until manual execution.