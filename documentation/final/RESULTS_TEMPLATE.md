# Results tables and error-analysis forms

Prepared 10 November 2026, Asia/Calcutta. **All predictive, retrieval, ranking,
runtime and rehearsal values below are unmeasured.** These cells are publication
templates, not fictional data. Replace a cell only with a genuine saved report
and a traceable evidence ID. Keep missing values unavailable; never encode them
as zero, a dash indistinguishable from zero, or an estimated pass.

## Sentiment comparison: one table per task/split

Task, dataset/split hashes, label policy, selected experiment and cohort:
not yet recorded. Do not combine binary IMDb and three-class movie sentiment.

| Model | Test support / per-class supports | Accuracy | Macro-F1 | Weighted-F1 | NLL | Brier | ECE / bins | Evidence ID |
|---|---|---|---|---|---|---|---|---|
| TF-IDF Logistic Regression | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unavailable |
| TF-IDF calibrated Linear SVM | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unavailable |
| Selected compact Transformer | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unavailable |

Attach the actual confusion matrix and per-class precision/recall/F1. Include
class supports and the zero-denominator policy. Report calibration-fit metrics
as fit diagnostics separately from independent held-out confidence estimates.

## Language and informal-text cohorts

| Cohort | Genuine held-out support | Primary metric / interval method | Failure analysis | Evidence ID |
|---|---|---|---|---|
| English | Unmeasured | Unmeasured | Not reviewed | Unavailable |
| Hindi Devanagari | Unmeasured | Unmeasured | Not reviewed | Unavailable |
| Romanized Hindi | Unmeasured | Unmeasured | Not reviewed | Unavailable |
| Hinglish/code-switching | Unmeasured | Unmeasured | Not reviewed | Unavailable |
| Slang-heavy | Unmeasured | Unmeasured | Not reviewed | Unavailable |
| Emoji/emoticon-heavy | Unmeasured | Unmeasured | Not reviewed | Unavailable |
| Sarcastic | Unmeasured | Unmeasured | Not reviewed | Unavailable |
| Mixed-aspect / contrast / negation | Unmeasured | Unmeasured | Not reviewed | Unavailable |

Cohorts may overlap; disclose that and their annotation definition. No support
means unavailable. Do not infer cohort labels solely from a script heuristic.

## Aspects and themes

| Study | Support | Primary measure | Secondary breakdown / calibration | Evidence ID |
|---|---|---|---|---|
| Explicit aspect extraction | Unmeasured | Exact span/category precision, recall and F1: unmeasured | Per-aspect/window/truncation diagnostics: unmeasured | Unavailable |
| Gold-target polarity | Unmeasured | Macro-F1: unmeasured | Per-class/per-aspect confusion: unmeasured | Unavailable |
| Predicted-span full pipeline | Unmeasured | Exact target+polarity precision/recall/F1: unmeasured | Extraction and polarity failure decomposition: unmeasured | Unavailable |
| Multi-label theme relevance | Unmeasured | Micro/macro-F1: unmeasured | Per-theme support/F1/threshold/calibration: unmeasured | Unavailable |
| Theme-specific reception | Unmeasured | Unavailable until valid target evidence/model exists | No overall-sentiment substitution | Unavailable |
| Genre-specific reception | Unmeasured | Unavailable until valid target evidence/method exists | Metadata genres alone are insufficient | Unavailable |

## Recommendation comparison

Record K, relevance definition, train/validation/test cutoffs, users/items,
candidate universe, negative sampling, seen exclusions, train-only popularity,
short-list policy, empty/cold cases and diversity definition before entering
results. Sampled and full-catalogue metrics need separate tables.

| Method | Precision@K | Recall@K | NDCG@K | Coverage / denominator | Diversity / definition | Novelty / train prior | Evidence ID |
|---|---|---|---|---|---|---|---|
| Train-only popularity | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unavailable |
| Content/preferences | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unavailable |
| Spark ALS | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unavailable |
| Validation-selected hybrid | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unavailable |
| Prespecified channel ablations | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unavailable |

Add separate cold-user, cold-item, sparse-history, unknown-identity and empty-
candidate rows with actual supports. Ranking percentages are not probabilities
of enjoyment. Report additional RMSE/MAE only on the stated observed-rating scope.

## Evidence, grounding, risk and scoring

| Outcome | Support / denominator | Result | Required interpretation |
|---|---|---|---|
| Retrieval Recall/MRR/NDCG@K | Unmeasured human-judged queries | Unmeasured | Exact model/content/candidate scope |
| Supported/unsupported/contradicted summary claims | Unmeasured human-reviewed claims | Unmeasured | Evidence IDs and entailment decision, not token overlap alone |
| Summary aspect/minority coverage | Unmeasured eligible snapshots | Unmeasured | Retrieval selection bias and reference policy |
| ROUGE/BERTScore | Unavailable permitted references/dependencies | Unmeasured | No substitute score without actual references |
| Chat intent/entity/constraint correctness | Unmeasured annotated queries | Unmeasured | Grammar limits, ambiguity and abstention outcomes |
| Chat evidence/unsupported-claim rate | Unmeasured reviewed responses/claims | Unmeasured | Retrieved snapshot and source provenance |
| Offline speech WER | Unmeasured permitted transcribed recordings | Unmeasured | Language/cohort, normalization, model and codec scope |
| Review-risk precision/recall/F1/PR-AUC/FPR | Unavailable legitimate labels | Unmeasured | Moderation support; no sentiment-extremity ground truth |
| Score parity and policy sensitivity | Unmeasured matched snapshots | Unmeasured | Counts/weights/method/model/revisions/rounding scope |

## BDA and application measurements

| Measurement | Configuration / support | Result | Evidence ID |
|---|---|---|---|
| Ingestion/cleaning/join row reconciliation | Actual input/output/rejection hashes and counts required | Unmeasured | Unavailable |
| Partitions/stages/shuffle/cache actions | Current Spark/Scala/JDK, input size and UI report required | Unmeasured | Unavailable |
| Batch elapsed time / throughput / peak RAM | Operation/time scope and warm/cold state required | Unmeasured | Unavailable |
| Stream replay/late/conflict/edit/delete | Exact event/checkpoint/sink snapshots required | Not executed | Unavailable |
| Migration/API/ownership/revision tests | Disposable PG schema and actual test report required | Not executed | Unavailable |
| Browser desktop/mobile journey | Real services, catalogue and artifact versions required | Not executed | Unavailable |
| Cold/warm inference and API p50/p95 | Bounded real timings and failures required | Unmeasured | Unavailable |
| Queue and snapshot lag | Accepted/current revision timestamps required | Unmeasured | Unavailable |
| Peak system RAM / process RAM / allocated VRAM | Exact sampling scope required | Unmeasured | Unavailable |
| Actual offline journey / startup / recovery time | Operator and frozen run required | Not executed / unmeasured | Unavailable |

## Error-analysis record

For each permitted example retain a private case ID, task/cohort, model/code/
snapshot, actual gold label or human judgment, actual output, error category,
cause hypothesis, whether the hypothesis was tested and its outcome. Use review
IDs/hashes or an approved excerpt in the shareable report; keep private full
texts and audio out of public exports. Select examples with a documented rule,
including successes and failures, rather than only persuasive anecdotes.

## Claim-to-evidence table

| Claim ID | Exact sentence/table cell | Evidence report path + SHA256 | Metric field / support | Task/split/model/data/protocol match | Reviewer / decision |
|---|---|---|---|---|---|
| No measured claim registered yet | Unavailable | Unavailable | Unmeasured | Not reviewed | Pending |

Delete the placeholder row only when a real claim record exists. The validation
reporting tools may consolidate genuine reports; a human must still verify that
the exact sentence is warranted and that licenses permit its supporting assets
to be shared.
