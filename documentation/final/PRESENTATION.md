# Presentation source and viva preparation

Prepared11 November2026,Asia/Calcutta. This is an editable Markdown slide
narrative for later export. It is not an executed demonstration or a rendered
PowerPoint file. Replace result placeholders only with genuine evidence from
the evaluation register. The report and this presentation must agree.

## Slide1 — Research question

**Title:** Movie Review Intelligence and Personalized Discovery with Spark and
Transformer NLP.

Explain the problem: ratings alone do not reveal which aspects audiences
discuss; recommendation and discovery need consistent catalogue identities.
State BDA and TA objectives and the locally executable laptop constraint.
Do not open with an unmeasured accuracy or claimed production deployment.

## Slide2 — What the product connects

Show the actual catalogue → movie → evidence summary → reviews → recommendation
→ grounded conversation journey. Use permitted screenshots from the executed
application later. A source-only UI screenshot cannot establish model inference.

## Slide3 — Architecture and identities

Use ARCHITECTURE_AND_ER.md. Explain Next.js → FastAPI → PostgreSQL/pgvector,
one durable local worker,and independent Scala/Spark ingestion/ALS/streaming.
Separate canonical movie IDs,external IDs,MovieLens users and app UUIDs.
Explain why each technology has its assigned responsibility.

## Slide4 — Data,rights and limitations

MovieLens supplies ratings/tags; Stanford IMDb is a separate binary benchmark;
licensed metadata and consented movie-linked human annotations serve different
purposes. Show actual audited counts only from matching audit artifacts.
Show annotation/permission/mapping coverage and unresolved inputs honestly.

## Slide5 — Big Data processing

Demonstrate actual Scala RDD/DataFrame/SQL ingestion,cleaning,joins,aggregation,
partitioning,lazy plans,caching and Parquet output. Present real Spark UI
evidence after execution. Local mode demonstrates Spark execution semantics;
it does not establish multi-machine speedup. Explain quarantine/rejection counts.

## Slide6 — Leakage-resistant experiments

Describe disjoint train/tuning/calibration/test roles,frozen manifests and
duplicate/reviewer/movie grouping. IMDb's official test is preserved. Show
the actual split/selection/checkpoint hashes and human review records later.

## Slide7 — Classical versus Transformer sentiment

Use separate binary and domain three-class tables from RESULTS_TEMPLATE.md.
Compare actual LR/SVM/Transformer reports only on the same task and protocol.
Report macro/per-class F1,support/confusion and calibration,not only accuracy.
**Current results: unmeasured.** A binary classifier is not a neutral detector.

## Slide8 — Informal and multilingual language

Explain preserved Unicode,slang/emojis,Hindi,Romanized Hindi,Hinglish,negation
and sarcasm. Present actual human-annotated subgroup support/results later.
Script identification is not language understanding; sarcasm does not trigger
heuristic polarity inversion. Keep diagnostic versus learned fusion separate.

## Slide9 — Aspects,themes and summary evidence

Show real extracted original-text spans plus target-specific polarity after
evaluation. Separate gold-target classification from full predicted-span results.
Theme relevance/mentions do not establish theme reception. Explain bounded
deduplicated evidence retrieval and human approval of novel summary claims.
Use only permitted examples and source references,not fabricated reviews.

## Slide10 — Audience scoring and review risk

Explain calibrated per-review index,eligibility,reviewer dedupe,reviewed weights,
effective evidence,shrinkage,minimum-evidence nulls and model/method versions.
Display “Not enough audience reviews yet.” for a genuinely sparse movie.
Review risk supports moderation using legitimate similarity/behavior signals;
strong sentiment alone is not evidence of fakery. Do not call a risk index a
validated fake-review probability without legitimate ground truth/calibration.

## Slide11 — Hybrid recommendation

Explain actual Spark MLlib ALS,semantic content,genre/theme preferences and
consented history. App accounts never borrow MovieLens identities. Show actual
channel explanations,seen exclusion and cold-start behavior later. Report
Precision/Recall/NDCG@K,coverage,diversity,novelty and cold cohorts with candidate
protocols. **Current ranking results: unmeasured.**

## Slide12 — Grounded conversational discovery and voice

Demonstrate the six required query types using the actual catalogue/evidence.
Show title ambiguity,constraints and bounded context. Identify the current
English analytical parser honestly; it is not proven multilingual query NLU.
Voice uses an optional cached local CPU model and always retains text fallback.
Report human grounding/query evaluation and permitted-recording WER only after
measurement. Offline flags alone do not prove offline execution.

## Slide13 — Integration correctness and measured resources

Present actual disposable-DB/browser/model-load/parity/failure/replay evidence
after execution. Distinguish AST/type checks from runtime tests; skips do not
pass full acceptance. Explain the bounded queue child reserve and its actual
later contention test. Show genuine latency/error/resource observations and
sampling limits. Do not present whole-device GPU usage as model peak allocation.

## Slide14 — Results and ablations

Use the actual frozen evidence register and notebook15 exports. Every table
cell needs an artifact ID,JSON field,hash,task/role/protocol and support. Compare
validation-selected ablations without retuning on the final test. Keep all
currently absent cells “Unmeasured”; never replace them with illustrative scores.

## Slide15 — Limits,next work and reproducibility

Disclose annotation/data gaps,theme/genre reception gaps,query-parser limits,
sampling/online-catalogue bounds,summary hallucination risk and source/runtime
gates. Point to actual model/dataset cards,rights register,source/lock hashes,
rehearsal evidence and reviewed bundle. State only conclusions supported by
the final executed results. No paid inference or evaluation-time retraining is
required by the intended core demonstration.

## Viva questions to rehearse

1. Why is MovieLens not the text-review sentiment dataset?
2. How are neutral,mixed,uncertain and unsupported-language cases separated?
3. How do duplicate/movie/reviewer groups prevent leakage?
4. Why are SVM margins not directly used as calibrated probabilities?
5. How do original Unicode offsets differ from browser UTF16 offsets?
6. Why can't overall sentiment determine every aspect/theme sentiment?
7. What keeps a sparse movie from receiving a fabricated audience score?
8. Why are personalized match and audience sentiment different quantities?
9. How are new app users treated when ALS was trained on MovieLens users?
10. What candidate/relevance/temporal protocol defines each ranking metric?
11. How are edits,deletion,duplicate submissions,worker crashes and retries handled?
12. What distinguishes final-state parity from exactly-once/replay proof?
13. What proves a summary claim or chat answer is grounded?
14. What is actual offline evidence and what remains a browser/runtime dependency?
15. Which syllabus concepts have executed evidence and which are unimplemented?

Each answer should refer to actual code and a measured artifact where required.
If a result is unavailable,explain the open dependency rather than improvising.
