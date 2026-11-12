# Recommendation model card

Updated 12 November 2026 (Asia/Calcutta). One real Scala Spark MLlib ALS validation
trial has completed. Final-test evaluation, serving approval, the full five-channel
hybrid and application cold-start fold-in remain open. Existing trained artifacts
are preserved; a completed validation trial is not a deployment approval.

## Completed experiment

- Run: `als-validation-c8378830710a4feeb97d5671a9542ba1`.
- Local MovieLens32M; training permission recorded in that run's
  `configs/local/.../approval-approved.json`. Original usage terms and citation
  remain `data/raw/movielens/ml-32m/README.txt`; no commercial permission inferred.
- Explicit-feedback ALS: rank32, regParam0.1, maxIter10, seed42, two user/item
  blocks. Spark4.3.0/Scala2.13.18/JDK21, CPU local[2],3GiB driver heap.
- Train through2021-12-31UTC:30,293,045 ratings. Validation2022:913,105 ratings.
  Test2023:794,054 ratings; no final-test quality evaluation has run.
- Exported user factors193,618; item factors73,483; rank32. All factor files were
  hash-verified and checked for valid unique Int32 IDs and finite32-element vectors.
- Approved mapping covers87,585 canonical movies and every trained item.14,102
  catalogue movies have no trained item factor. App account UUIDs never borrow
  anonymous MovieLens user factors.

## Measured sampled validation

The same100 hash-selected positive-support users are evaluated with all eligible
held-out positives plus up to100 hash-sampled unseen training items per user.
Relevance is rating>=4; K=10. There are15,760 candidate/user pairs. This is not
full-catalogue evaluation or a representative guarantee for every user.

| Method | Precision@10 | Recall@10 | NDCG@10 |
|---|---:|---:|---:|
| ALS with documented popularity fallback |0.597000|0.268105|0.620118|
| Training-popularity baseline, identical candidates |0.691000|0.396345|0.813080|

The baseline outperformed this ALS trial. Do not present the combined result as
pure ALS accuracy or a proven personalization improvement.39users had all-cold
candidates,28had no cold candidates and33had mixed candidates.8,318candidate
predictions(52.78%) were cold. On the28-user no-cold cohort,ALS NDCG@10was0.388489
and popularity NDCG@10was0.782956. No result is hidden or replaced by a mock.

The matched comparison verified Spark's installed XXH64 hash primitives, source
fingerprints, ordered float32 prediction accumulation, exact saved top-K sequences
and all aggregate/per-user metrics. It decoded training and validation histories;
all794,054test-period rows remained outside decoded row groups.

Scala coverage0.00816977 uses train-union-validation catalogue scope and100sampled
lists; novelty14.720331bits uses training-only smoothed popularity. Genre diversity
on current approved metadata is0.797832under the existing missing-genre convention,
or0.783005when excluding pairs with missing genres.4,152of4,500pairs(92.27%) had
listed genres for both films;39of651distinct recommended movies lacked genres.
Genre measurements are retrospective metadata analysis, not audience reception.

## Evidence

- [Completed run](../models/recommendation/als-validation-c8378830710a4feeb97d5671a9542ba1/factor_manifest.json)
- [Factor/cohort review](../artifacts/als-validation-review-6d1c85901f104ca59b82d92f98a92a05/report.json)
- [Matched baseline comparison](../artifacts/als-popularity-comparison-0021d34c0f87402eb6f1a989424b2c91/report.json)
- [Genre-diversity audit](../artifacts/als-diversity-fb136836e4414284866f33afe1863411/report.json)
- [Canonical factor mapping](../data/processed/recommendation/als-validation-c8378830710a4feeb97d5671a9542ba1/mapping_report.json)

## Pending study and acceptance

`hybrid_validation_grid.json` declares15 quarter-step weight combinations over
available ALS,genre and training-popularity channels. Its actual evaluation is
pending user execution. It uses the original matched candidates and training-only
rating-derived profiles; no application personalization consent is inferred.
Semantic and theme channels remain unavailable in this interim study. Selected
research weights remain unapproved for serving. A popularity-only win is valid
and must not be changed to force an ALS contribution.

Further work: complete the remaining channels,validate a catalogue-scale candidate
strategy,review app-user fold-in and cold-start behaviour,freeze final choices
before final test,measure final cohorts and serving resources,and record model
promotion/revocation decisions. Personalized match scores remain separate from
audience sentiment,star ratings and theme relevance.