# BDA and TA syllabus evidence map

Prepared 10 November 2026, Asia/Calcutta. This map follows the syllabus topics
listed in the root architecture. Verify the official course handout/unit names
before submission. A source path establishes where an implementation lives;
it does not establish a completed execution, a measured learning outcome or
coverage of every topic in a subject.

For every demonstrated row attach an evidence ID, current source hash, input
snapshot, command, outcome and permitted screenshot/log. Leave absent evidence
unavailable. Static parser reports are not Spark/model test results.

## Big Data Analytics

All Scala paths below are relative to `scala/src/main/scala/com/movieintel/`.

| Unit / concept | Actual source anchor | Evidence required from a later real run | Claim boundary |
|---|---|---|---|
| BDA1: volume/variety/velocity/veracity/value | `ingestion/MovieLensIngestion.scala`, `ingestion/ReviewIngestion.scala`; root dataset audits | Source sizes/counts, rating/tag/text distinctions, quality/quarantine records and stream input | Dataset size is not proof of distributed performance; the laptop uses local mode |
| BDA1: Hadoop ecosystem and storage | Parquet writes in `io/PipelineIO.scala`; Spark distribution configuration | Explain Spark/Parquet roles and actual selected local filesystem | No HDFS/YARN cluster or Hadoop MapReduce job is claimed executed |
| BDA1: Mapper/Reducer concepts | `transformations/RddExamples.scala` wordCounts/map/reduceByKey | Genuine tag input, DAG/partition/shuffle report and bounded token outputs | This is a Spark MapReduce-style computation, not an independently deployed Hadoop job |
| BDA2: immutable values/collections and higher-order functions | `RddExamples.scala` normalizeTag/tokenize/wordCounts; collection transformations throughout Scala source | Explain `val`, `Option`, `Either`, map/flatMap/filter, closure and associative reduction on inspected code | Source explanations must match the exact version shown |
| BDA2: recursion/pattern matching/case classes | `RddExamples.scala` sumTail, SourceTag, RatingExample; config/case classes | Actual small checks, input/output and tail-recursive base/recursive cases | A small teaching exercise does not establish large distributed recursion |
| BDA2: OOP and error handling | Separate config/ingestion/cleaning/analytics/recommendation/streaming objects; `config/JobConfig.scala`, `PathPolicy.scala` | Explain object responsibility, reusable functions and invalid-input behavior | Do not claim unimplemented actor/Future/concurrent collection demonstrations |
| BDA2: concurrency | Spark task/partition scheduling controlled by local configuration | Spark UI concurrent tasks and measured CPU/RAM under selected local parallelism | Spark task parallelism is not multi-machine speedup or a general Scala concurrency study |
| BDA3: driver/executors/jobs/stages/tasks | `Main.scala` SparkSession and jobs; actual event logs/UI | Live Spark UI4040 during the job; explain driver/local tasks, action boundaries and shuffle stages | A historical screenshot is historical evidence, not a live cluster |
| BDA3: RDD transformations/actions | `RddExamples.scala` map/flatMap/filter/reduceByKey/sortBy/take/count | Correct tag outputs and DAG; bounded groupByKey teaching sample | No full MovieLens collect; different tokenizers must not be described as equivalent without reconciliation |
| BDA3: DataFrames/joins/aggregations/SQL | `cleaning/DataCleaning.scala`, `transformations/DataFrameTransformations.scala`, `analytics/MovieAnalytics.scala`, `UserAnalytics.scala` | Explicit schemas, validation/rejection counts, referential join counts, actual SQL/aggregate outputs | MovieLens rating/tag analytics are not review sentiment |
| BDA3: typed Datasets | `DataFrameTransformations.scala` actual typed Dataset transformations | Current compiler/runtime output and typed records with bounded examples | Do not substitute a Python pandas example for Scala Dataset evidence |
| BDA3: partitions/lazy evaluation/DAG/cache | `RddExamples.scala`; configuration/partitioning in `Main.scala` | Explain plan before action, first/reused actions, partitions, DAG, shuffle and unpersist | Timing differences need measured repetitions; no guaranteed caching speedup |
| BDA4: MLlib estimator/model/tuning | `recommendation/AlsTraining.scala`, `TemporalSplit.scala`, `RecommendationJob.scala` | Actual ALS configuration, train/validation/test split, factor export and genuine quality reports | Model selection on validation only; no large training during the live evaluation |
| BDA4: ranking evaluation/cold start | `recommendation/RankingEvaluation.scala`; Python `recommender/evaluation.py` | Precision/Recall/NDCG@K, candidate protocol, cold cohort counts and exclusions | Generated sampled ranking is not full-catalogue performance; Python diversity needs actual joined metadata |
| Streaming / applied extension | `streaming/ReviewStreamJob.scala`, `ingestion/ReviewIngestion.scala`, backend outbox | New event, checkpoint/sink snapshots, replay/late/conflict/edit/delete tests and final reconciliation | Source replay guards do not prove end-to-end exactly-once semantics |

## Text Analytics

Python paths below are relative to the repository root. The mandatory language
extension supersedes the original architecture's optional multilingual wording.

| Unit / concept | Actual source / notebook | Evidence required | Claim boundary |
|---|---|---|---|
| TA1: text processing, Unicode, normalization and tokenization | `ml/informal_language/preprocess.py`, `slang_normalization.py`, `emoji_processing.py`, `ml/common/data.py`; `notebooks/03_review_preprocessing.ipynb` | Original/aligned text views, hashes, versioned preprocessing, supported-language cases | Script/symbol observations are not universal language recognition or emoji sentiment |
| TA1: morphology/syntax/semantics/collocation | Preprocessing and n-gram features provide limited related examples | A separate executed linguistic analysis is needed for any claimed morphology/POS/collocation coverage | No complete morphology/POS parser or linguistic study is claimed from tokenization alone |
| TA2: BoW/TF-IDF/n-grams | `ml/sentiment_tfidf`; `notebooks/04_tfidf_baseline.ipynb` | Train-only fitted features, LR/LinearSVM baselines, comparable held-out reports and vocabulary settings | SVM margins are not calibrated probabilities; no final-test preprocessing fit |
| TA2: dense/sentence embeddings | `ml/embeddings/predict.py`, `evaluate.py`; `notebooks/12_embeddings_semantic_search.ipynb` | Exact local checkpoint/revision, compatible vectors, human relevance judgments and retrieval metrics | Pretrained inference is not local embedding fine-tuning |
| TA3: deep learning/sequence/Transformer/BERT-style encoder | `ml/common/transformer_engine.py`, sentiment modules; notebooks05/06 | Approved actual fine-tuning, optimizer/AMP/accumulation, checkpoint/resume, held-out metrics | No LLM training from scratch or invented three-class neutral labels |
| TA3: token classification | `ml/aspect_extraction/alignment.py`, `windows.py`, `decoding.py`, `task.py`; notebook07 | Exact code-point spans, subword/window alignment, span/category F1 and errors | Explicit spans only; token accuracy alone is insufficient |
| TA3/4: target sentiment | `ml/aspect_sentiment/targeting.py`, `task.py`, `ml/aspect_pipeline`; notebook08 | Gold-span and predicted-span full-pipeline evaluation on genuine annotations | Overall sentiment is never assigned to every aspect |
| TA3: topic modelling | `ml/topics`; `notebooks/09_theme_extraction.ipynb` | Actual fitted train-only topics/descriptors, stability/coherence if justified, curator review | Exploratory LDA is not stable semantic truth; BERTopic is optional and not assumed fitted |
| TA3: controlled multi-label themes | `ml/themes/data.py`, `task.py`; notebook09 | Human theme labels, thresholds/independent calibration, per-theme support/F1 | Theme relevance/mention probability is distinct from theme reception |
| TA4: sentiment evaluation | `ml/common/metrics.py`, `calibration.py`; notebook06 | Macro/weighted/per-class F1, confusion matrix/support, NLL/Brier/ECE and held-out cohort tables | Binary IMDb and final domain three-class results stay separate |
| TA4: informal/language robustness | `ml/multilingual_sentiment`, `ml/sarcasm`, informal-language modules; Hinglish/emoji/sarcasm notebooks | Genuine English/Hindi/Romanized Hindi/Hinglish/slang/emoji/sarcasm cohorts and error analysis | No cohort support means unavailable; sarcasm diagnostic is not learned fusion or polarity reversal |
| TA4: summarization | `ml/common/evidence.py`, `ml/summarization`; notebook10 | Actual evidence snapshot, quoted/generative distinction, human factuality/contradiction/coverage; permitted-reference overlap metrics if available | ROUGE/BERTScore are not currently measured and do not prove entailment |
| TA4: QA/retrieval/conversational discovery | `discovery/parser.py`, `backend/app/services/chat.py`, pgvector catalogue repository | Actual entity/constraint/retrieval/grounding and follow-up tests | Current parser is analytical English rules, not universal trained multilingual NLU |
| TA4: visualization/results | Existing notebooks and `notebooks/15_final_model_comparison.ipynb` when generated | Standalone plots/tables derived only from genuine evidence and labelled supports/splits | No chart may turn a missing metric into zero or compare incompatible tasks/candidates |
| Applied moderation | `ml/review_risk`; notebook11 | Duplicate/anomaly signals, permitted behavioral data, human-labelled false-positive study when possible | No fake-review accuracy or calibrated risk probability without legitimate validation |

## Topics not claimed implemented by the core product

Explicit one-hot teaching examples, POS tagging, general NER, machine
translation, HMM, CRF decoding and graph NLP require separate inspected and
executed coursework exercises if required by the official syllabus. A movie
title SQL resolver is not a trained general NER system. This repository must
not claim those topics covered simply because the architecture mentions them.
Keep optional teaching exercises isolated from product predictions and real
scientific evaluation; no optional dataset acquisition is authorized by this
map. Add exact sources/results here only after the owner implements them.

## Syllabus evidence record

For every claimed row record: course/unit/topic, source path and SHA256, run
report ID/path/hash, real input snapshot, what was observed, screenshot/log
permission, limits and reviewer. Mark the row as **source only**, **executed**,
**failed**, **unavailable** or **not applicable with rationale**. A skipped test
must remain skipped, and a required unavailable item blocks the corresponding
claim. [ACCEPTANCE_CHECKLIST.md](ACCEPTANCE_CHECKLIST.md) keeps the final gates.
