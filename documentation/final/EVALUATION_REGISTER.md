# Evaluation register

Prepared 10 November 2026, Asia/Calcutta. All model, recommendation, retrieval,
application and demonstration result values in this register are **unmeasured**.
The current delivery generates source/documents; it does not execute these
experiments. Historical environment/data/static-source evidence is recorded
separately in the root audits and is not a new model-performance result.

## Required experiment record

For each executed experiment retain: actual timestamp/operator, question/task,
code revision and source hashes, selected interpreter/dependency lock, dataset
source/rights/hash, canonical mapping version, exact frozen split IDs and leakage
groups, train/tuning/calibration/test role, label/annotation policy and support,
base model/license/revision/tokenizer hashes, config/run approval, seed,
hyperparameters, checkpoint selection and calibration protocol, hardware/device,
metrics with denominators, resource observations, failures and limitations.

Final-test access is reserved after selection. Do not repeatedly tune on the
test split. Keep same-task/split comparisons and ablations aligned. Report a
confidence interval only if its calculation and sampling assumptions are
documented. Do not fabricate results for a missing cohort or ground truth.

## Model and analytical results to collect

| Study | Required measurements/protocol | Current result | Required artifact |
|---|---|---|---|
| Binary IMDb LR/SVM/Transformer | Comparable fixed splits; accuracy, macro/per-class F1, confusion matrix and support | Unmeasured | Actual per-model held-out reports and frozen selection |
| Domain three-class sentiment | Genuine neutral/positive/negative support; macro/weighted/per-class F1, confusion matrix | Unmeasured | Held-out domain report; binary benchmark is separate |
| Calibration | NLL, Brier, ECE/reliability; calibration split distinct from tuning/final test | Unmeasured | Calibrator fit record plus independent held-out diagnostics |
| Language/informal cohorts | English/Hindi/Romanized Hindi/Hinglish, code-switching, emoji/slang/sarcasm and mixed-aspect supports | Unmeasured | Genuine human-labelled cohort report with unavailable cohorts explicit |
| Sarcasm diagnostic | Independent annotation/precision/recall/F1 and an actual fusion ablation if claiming fusion | Unmeasured | Diagnostic report; no heuristic polarity inversion |
| Aspect extraction | Exact original-character span precision/recall/F1, category breakdown and overlap/window diagnostics | Unmeasured | Frozen extraction test report and error examples |
| Aspect-conditioned sentiment | Macro/per-class/per-aspect F1 using true target spans; separate end-to-end predicted-span pipeline metrics | Unmeasured | Classifier and full-pipeline reports |
| Theme relevance | Multi-label micro/macro/per-theme F1, support and held-out calibration/threshold protocol | Unmeasured | Theme report; relevance is not reception |
| LDA/BERTopic exploration | Actual fitted topic descriptors, stability/coherence when justified and curator review | Unmeasured | Versioned exploratory output, never objective movie facts |
| Semantic retrieval | Human-approved queries/relevance judgments; Recall@K, MRR/NDCG, unknown-title and filter behavior | Unmeasured | Retrieval judgments, vector/model/content hashes and report |
| Review summaries | Human factuality, unsupported/contradicted claim rate, coverage; ROUGE/BERTScore only with permitted references | Unmeasured | Snapshot/evidence references and actual human/model evaluation |
| Review risk | Duplicate retrieval validation; precision/recall/F1/PR-AUC/false-positive rate only with legitimate labels | Unmeasured | Source/cohort audit and moderation-support limitations |
| Audience scoring | Distinct/eligible/effective counts, policy/shrinkage sensitivity, stale/deletion handling, Python/Scala parity | Unmeasured | Reviewed policy plus same-input comparison and replay results |

## Recommendation evaluation

Use earlier interactions for fitting and later interactions for validation/test.
Freeze relevance definition, K, eligible users/items, candidate universe and
seen exclusions. Calculate novelty/popularity using training-period data only.
Record every empty/cold/unsupported user rather than silently dropping them.
Disclose whether evaluation samples negatives/users or ranks the full catalogue.
The generated Scala sampled protocol is not full-catalogue performance.

| Comparison | Precision@K | Recall@K | NDCG@K | Coverage | Diversity | Novelty | Cold-start cohorts |
|---|---|---|---|---|---|---|---|
| Train-only popularity baseline | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Content/genre/theme baseline | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Spark MLlib ALS | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Validation-selected hybrid | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured |
| Hybrid channel ablations | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured | Unmeasured |

Define diversity precisely, for example pairwise genre distance or semantic
distance over the recommended list; those measures are not interchangeable.
State denominators for coverage and K-based metrics, including lists shorter
than K. RMSE/MAE may supplement ranking results. Application accounts absent
from MovieLens need explicit cold-start handling or reviewed fold-in, never
another source user's factors.

## Big Data and complete application

| Experiment | Measurements | Current result | Evidence |
|---|---|---|---|
| Final Scala build/test | Exact sources/JAR/compiler/Spark/Scala/JDK and test count/results | Not executed for final source | New build/test reports needed; earlier snapshot compile remains historical |
| MovieLens batch | Counts/rejections/joins/partitions, elapsed time, throughput, shuffle and RAM | Unmeasured for final batch | Input/output manifests and Spark UI/job logs |
| Structured Streaming | Restart/replay/late/conflict/deletion outcomes, micro-batch lag and row reconciliation | Unmeasured | Exact event/checkpoint/sink snapshots and logs |
| PostgreSQL migration/API | Schema/vector/constraint/ownership/idempotency/concurrency/revision outcomes | Not executed | Disposable-DB test report |
| Full browser journey | Actual search → details → review → predictions → refresh → recommendations → discovery | Not executed | Real browser/API/DB evidence |
| Query understanding | Intent/entity/constraint accuracy, ambiguity and negation, follow-up/grounding correctness | Unmeasured | Permitted query expectations and actual outputs |
| Offline speech | WER only on permitted transcribed recordings; practical success/latency/failure fallback | Unmeasured | Cached-model hash, recordings permission and actual report |
| Latency/resource test | Cold/warm model load, p50/p95 API/queue/snapshot lag, throughput/error rate, peak RAM/VRAM | Unmeasured | Bounded real load config and raw timings/resource samples |
| Offline/demo recovery | Complete journey and recovery times, cached-only operation, worker/model/DB failure behavior | Not executed | Signed rehearsal checklist and logs |

No local Spark result should be described as a multi-machine speedup. A
successful `/health` request proves only that endpoint's liveness. Static Python,
JSON, Scala or TypeScript parsing does not establish library compatibility,
GPU training, database behavior, frontend rendering or inference quality.

## Result publication checklist

- [ ] Every reported number has an actual artifact path and exact snapshot hash.
- [ ] Training/tuning/calibration/test results are clearly separated.
- [ ] Baselines and claims share a comparable task, split and candidate protocol.
- [ ] Missing classes/languages/ground truth remain unavailable.
- [ ] Failures, exclusions, cold cases, sampled ranking and resource limits are disclosed.
- [ ] Synthetic fixtures and legacy demo records are excluded from real results.
- [ ] Private texts, consent records and secrets are not included in public exports.
- [ ] Tables, model cards, report and presentation agree with the saved evidence.
