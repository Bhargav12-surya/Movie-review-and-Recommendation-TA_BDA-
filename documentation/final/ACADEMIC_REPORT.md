# A Big Data-Driven Movie Review Intelligence and Personalized Recommendation System

## Report status and title page

Prepared 10 November 2026, Asia/Calcutta. Academic subjects: Big Data Analytics
and Text Analytics. Product name: Framewise. This is a source-backed report
template with a specified experimental method. The model, recommendation,
application and demonstration results are **unmeasured** until the operator runs
the approved experiments and attaches their exact evidence. Replace title-page
metadata with the actual student, institution, supervisor, course and submission
details. Do not add invented affiliations or author names.

## Abstract

This project specifies a locally executable platform for movie-linked review
intelligence, personalized recommendations and grounded conversational discovery.
Scala and Apache Spark process MovieLens ratings/tags and train MLlib ALS;
Python supplies classical baselines, compact Transformer sentiment and aspect
models, controlled themes, review-risk analytics and evidence-grounded summaries.
FastAPI, PostgreSQL/pgvector and Next.js connect shared identities, revisions,
approved model artifacts and audience evidence. The design separates metadata,
star ratings, review sentiment, theme relevance, audience reception and personal
match scores. Its laptop resource policy targets one substantial model at a
time on an RTX5050 with8GB VRAM and16GB nominal RAM. Source generation and static
checks do not establish successful training or deployment. This report defines
the experiments, acceptance criteria and evidence needed to assess the system;
no predictive or runtime performance conclusion is yet justified.

Keywords: Apache Spark, Scala, Transformer, sentiment, aspect extraction,
calibration, recommender system, evidence retrieval, PostgreSQL, local inference.

## 1. Problem and objectives

Movie star ratings, textual opinions and personal preferences answer different
questions. A movie may have a relevant theme without reviewers liking its
treatment; a user may prefer it despite a mixed public response. Combining these
signals without provenance creates misleading scores and explanations. The
project therefore connects three modules through canonical movie IDs and
versioned evidence:

1. Review intelligence: real positive/negative/neutral predictions, extracted
   aspects and target polarity, eligible audience aggregation, theme evidence,
   grounded summaries and moderation-support signals.
2. Personalized recommendation: actual Spark ALS factors, content/semantic
   features and consented explicit/inferred preferences with cold-start handling.
3. Conversational discovery: catalogue entity resolution, exact constraints,
   semantic retrieval, review evidence and the same recommendation service, with
   bounded private context and optional offline speech.

The research contribution to assess is the defensible integration and measured
behavior of these components on a constrained local machine. No novel algorithm,
state-of-the-art result or representative global audience measurement is claimed.

## 2. Research questions and preregistered comparisons

Record the chosen hypotheses and primary metrics before final-test access.
These are questions to test, not results:

| ID | Question | Primary comparison / outcome |
|---|---|---|
| RQ1 | Does a compact fine-tuned encoder improve the same-task sentiment baseline? | Transformer vs TF-IDF LR and calibrated Linear SVM; held-out macro-F1 |
| RQ2 | How reliable are probabilities used in public aggregation? | Independently held-out NLL, Brier, ECE/reliability and per-class support |
| RQ3 | How does extraction error affect target sentiment? | Gold-target classifier vs predicted-span end-to-end exact target/polarity evaluation |
| RQ4 | Where do informal/language errors concentrate? | Genuine language/script/slang/emoji/sarcasm/mixed-aspect cohort supports and metrics |
| RQ5 | Does validated hybrid ranking improve the stated temporal candidate protocol? | Popularity/content/ALS/hybrid plus prespecified channel ablations |
| RQ6 | Are summaries and chat claims supported by retrieved evidence? | Human entailment/contradiction/coverage and unsupported-claim rate |
| RQ7 | Can the integrated system operate locally with reliable revision/replay behavior? | Actual journey/failure/offline tests, p50/p95 latency and measured RAM/VRAM |

Select one primary outcome per study and report all prespecified comparisons.
If the dataset is too small for a stable conclusion, report uncertainty and the
sample limitation. Do not hide a baseline that outperforms the Transformer.

## 3. Data, identity and annotation

### 3.1 Sources and observational scope

MovieLens32M supplies interactions, ratings, tags and link candidates; it is not
a full-text review dataset. Stanford aclImdb is a separate binary benchmark with
an official held-out test split and no validated application-movie mapping.
First-party/permitted movie-linked reviews and human annotations are required
for the final three-class, aspect, theme and language studies. Metadata/artwork
may be manually supplied under reviewed terms and cached for the local demo.
No dataset/model is fetched by the evaluation workflow.

Historical measured audits and their precise artifacts are listed in
[DATASET_AUDIT.md](../../DATASET_AUDIT.md). Those counts are data-audit evidence,
not model results or a promise that the same snapshot remains current. Recheck
hashes before a later experiment. Do not use old synthetic demo reviews as
training, test or public audience evidence.

### 3.2 Canonical identity and consent

Keep internal movie IDs separate from MovieLens/TMDB/IMDb IDs. Preserve IMDb
leading zeros and quarantine conflicting mappings. Title similarity can propose
a manual-resolution candidate; it does not approve a join. Application UUID
accounts remain separate from MovieLens users. Publishing, audience evidence,
research training, moderation similarity and personalization have separate
purpose records. A `source=user` field is insufficient to prove consent or
authenticity. See [PRIVACY_AND_CONSENT.md](PRIVACY_AND_CONSENT.md).

### 3.3 Annotation and split design

Define neutral as an adjudicated semantic label. Keep mixed polarity,
uncertainty, unsupported language and annotation disagreement separate from
that class. Humans annotate language/script/code-switching and independent
sarcasm labels. Retain original Unicode text and code-point aspect spans
`[start,end)`, exact hashes, annotator/adjudicator IDs, permissions and taxonomy
versions. Report agreement on an overlapping independently labelled subset and
the adjudication procedure; its value is currently unmeasured.

Freeze distinct train, tuning, calibration and test manifests with review,
reviewer/movie and duplicate groups appropriate to the generalization question.
Fit vocabularies, weights, transforms and anomaly estimators on training data.
Choose models/thresholds on tuning data; fit calibration on its separate subset;
freeze selection before final-test access. Do not reuse official IMDb test text
for fitting or neutral-label creation. Record exact/normalized and bounded
near-duplicate checks and their limitations. A failed final-test run/reservation
must remain visible rather than silently reopening selection.

## 4. Implemented source architecture

See [ARCHITECTURE_AND_ER.md](ARCHITECTURE_AND_ER.md) for the current diagrams.
Scala independently implements ingestion, cleaning, RDD/DataFrame/Dataset/SQL
operations, movie/user analytics, temporal ALS and Structured Streaming. Python
does not substitute for the Scala BDA processing.

FastAPI uses authenticated ownership, idempotent submissions and expected-review
revisions. Accepted edits invalidate derived snapshots immediately. Durable
PostgreSQL jobs feed one leased local worker; publication rechecks revisions and
model versions. The Next.js pages use actual typed API calls. Missing artifacts
or evidence produce pending/unavailable/null states, not mock predictions.
The source has20 ORM entities in a frozen PostgreSQL/pgvector migration;
column-parity checking is narrower than a real migration/constraint test.

The application view is PostgreSQL. Text-free outbox files feed separate Spark
analytics and can lag while reanalysis is unavailable. Replay-safe source code
does not prove end-to-end exactly-once delivery. The evaluation must compare
matching final event/evidence/model/policy snapshots and document residual lag.

## 5. Text analytics methods

### 5.1 Classical and Transformer sentiment

`ml/sentiment_tfidf` compares BoW/TF-IDF with Logistic Regression and Linear SVM.
`ml/sentiment_transformer` and `ml/multilingual_sentiment` use the shared local
Transformer engine and permission/fingerprint/checkpoint controls. Compare
binary IMDb experiments separately from the genuine domain three-class task.
Linear SVM margins are not probabilities; calibrate on the specified separate
subset before aggregation. A pretrained checkpoint is not evidence of local
fine-tuning unless a real owned run exists.

Report model/tokenizer revision and license, selected configuration, optimizer,
seed, sequence length, micro-batch, accumulation, epochs/steps, precision,
checkpoint selection, resume state and actual resource measurements. The initial
laptop trials use sequence128, small batches and zero Windows loader workers;
these are configurations, not proven memory limits. Verify the exact installed
torch/driver capability and small CUDA/precision operations before training.

Language/slang/emoji handling preserves original text. No universal emoji
polarity table or sarcasm-based sentiment reversal is used. The sarcasm model is
an independent diagnostic. Learned fusion is a separate experiment requiring
proper out-of-fold/separate signals and an actual ablation; it is not claimed
implemented by the diagnostic alone.

### 5.2 Aspect extraction and polarity

The compact token classifier extracts explicit original-offset BIO spans with
subword/window alignment. The target-conditioned classifier receives the review
and a specific target. It never copies overall review polarity to every aspect.
Report exact span/category precision, recall and F1, token diagnostics, gold-span
target macro-F1 and the full predicted-span pipeline separately. Implicit
aspects need a separately approved annotation scheme and remain unsupported.

### 5.3 Themes, topics and semantic representations

The controlled theme classifier is multi-label; its per-theme thresholds are
tuned without the final test. A review's predicted theme mentions are distinct
from curated movie themes and target-specific audience reception. Metadata
keywords do not establish audience polarity. LDA/topic outputs remain exploratory
until curated; optional BERTopic is not claimed fitted merely because it is
listed as an available method. Semantic embeddings use actual approved local
Sentence Transformer weights, compatible dimensions/content versions and real
retrieval judgments. Pretrained inference is labelled separately from local
fine-tuning.

### 5.4 Summaries and risk

Summaries retrieve one eligible movie snapshot, deduplicate and balance
sentiment/aspect evidence in bounded chunks. Quoted extracts are the default.
Optional local hierarchical generation produces a candidate; public novel text
requires a matching human factuality approval bound to snapshot/candidate hashes.
Database calculations supply numerical statistics. ROUGE/BERTScore are
unavailable without permitted references and suitable locally prepared metrics;
overlap does not establish entailment.

Risk combines documented duplicate/similarity checks and only legitimately
collected behavioral inputs. Current online text similarity uses a bounded
consenting corpus. It is moderation support, not a proven fake label or
calibrated probability. Sentiment extremity is not a risk feature. Without
legitimate fake/genuine labels, report signal validation and false-positive
limitations rather than invented classification accuracy or PR-AUC.

## 6. Audience scoring and confidence

For approved calibrated probabilities, the individual sentiment index is
`s_i = 100 * (p_positive + 0.5 * p_neutral)`. After current-revision eligibility,
permission, moderation, duplicate and reviewer rules, compute
`s_raw = sum(w_i*s_i)/sum(w_i)` and
`n_eff = sum(w_i)^2/sum(w_i^2)`. Reviewed minimum review/distinct-reviewer/effective
evidence thresholds must be met before optional shrinkage:
`s = n_eff/(n_eff+k)*s_raw + k/(n_eff+k)*prior`.

The prior, shrinkage strength and minimum thresholds require actual review and
validation; example null settings are not usable scientific decisions. Missing
helpfulness or behavioral quality data is not invented. Model confidence is not
silently a review-quality weight. If evidence is insufficient, return a null
score and **"Not enough audience reviews yet."** Never display the prior as
observed audience evidence. Record source/model/method/snapshot versions,
counts, effective count, update time and any review-bootstrap interval with its
assumptions. Such an interval does not include model error or selection bias.

Aspect/theme/genre reception requires target-specific evidence. A positive
pacing opinion does not by itself measure objective film speed, and positive
emotional-impact sentiment does not by itself prove a particular viewer mood.
The corresponding discovery proxy/threshold needs genuine validation and an
honest explanation; default unavailable behavior is appropriate.

## 7. Recommendations and discovery

Spark MLlib ALS fits actual temporally split ratings with reversible source ID
maps. Content/semantic/genre/theme channels and consented history are normalized
before validation-selected hybrid weighting. Exclude seen/ineligible movies and
explain actual contributing inputs. New application users cannot borrow a
MovieLens user's factors; optional item-factor fold-in is a separately reviewed
method. Report cold user, cold movie, sparse-history and empty-candidate cohorts.

The generated Scala ranking protocol samples up to100 eligible users and100
training negatives per user while retaining eligible held-out positives. Those
are protocol settings, not measured sample counts or full-catalogue evaluation.
Its disclosed popularity fallback and scale need validation. Freeze relevance,
K, candidate universe, negatives, seen exclusions and train-only popularity
before comparison. The online source's5000-movie limit is a resource boundary;
larger catalogues require a prepared candidate strategy. Do not silently call a
small serving pool full-catalogue coverage.

Conversational discovery uses documented analytical English rules, catalogue
title/year resolution and SQL/vector/evidence/hybrid routing. This is distinct
from multilingual review classification and is not universal trained NLU.
Questions, constraints and context need human evaluation, ambiguity handling
and evidence checks. Context is private, bounded to40turns and24hours in the
current source. Optional speech uses a cached hash-checked model on CPU int8;
text remains available. Do not claim browser speech or an untested codec is
guaranteed offline.

## 8. Experimental design and acceptance

Follow [EVALUATION_REGISTER.md](EVALUATION_REGISTER.md). Run data/model studies
only after their approvals and freeze inputs before results collection. Then
execute Phase12 tests against an explicitly disposable PostgreSQL database and
manually started real services. Isolated synthetic fixtures test mechanics;
they do not measure real model quality or become public reviews.

Prespecified ablations may compare classical vs Transformer, identity text vs
an approved aligned text view, language subgroup behavior, no-calibration vs
calibration, gold vs predicted aspects, retrieval/summarization choices and
hybrid channel removals. Select ablations on validation or preregister the
frozen final comparison; never repeatedly tune using final-test feedback.
For paired comparisons keep the same held-out units/candidates and document
uncertainty computation. Do not calculate unsupported significance claims from
aggregate scores without predictions or an appropriate resampling unit.

Measure cold/warm model load, API and queue/end-to-end latency separately,
snapshot lag, failures, throughput under bounded load and peak measured
RAM/VRAM. Local Spark timings demonstrate this machine's behavior, not
multi-machine distributed speedup. The offline rehearsal must actually block
or otherwise verify external access by operator choice; offline flags alone
are not proof. Record microphone-denied/model-absent fallback as well as success.

## 9. Results and discussion — unmeasured

Use [RESULTS_TEMPLATE.md](RESULTS_TEMPLATE.md) for every result table. All current
model, retrieval, ranking, grounding, runtime and rehearsal cells remain
unmeasured. Existing static/environment/data audits are evidence for their own
exact snapshots only. Do not paste a historical metric into the current model
row or replace missing measurements with an attractive example.

Each published claim must resolve through an evidence ID to a genuine report,
JSON field, source/data/model/config hashes, support and candidate protocol.
The generated comparison notebook consolidates existing reports; it must not
retrain, retune, reopen a held-out test or convert template nulls into zeros.
Interpret negative or inconclusive outcomes alongside successful ones.

## 10. Validity, fairness and limitations

Internal threats include leakage, duplicated reviewers/texts, mistaken movie
joins, calibration reuse, label noise, stale revisions, event replay and
sampling/candidate mismatch. External threats include English binary benchmark
transfer, limited genuine neutral/Hinglish/sarcasm support, review selection
bias, nonrepresentative ratings users and domain transfer of risk labels.
Construct validity requires separating sentiment from artistic quality,
metadata from reception and ranking scores from enjoyment probabilities.

Small cohorts need explicit supports and uncertainty; no support means
unavailable, not zero accuracy. Summaries can omit minority evidence even when
quoted; generated candidates can contradict sources. Human factuality review is
not a guarantee of universal truth. No automatic high-impact moderation claim,
full model unlearning, public production hardening, unmeasured hardware fit or
complete syllabus implementation is asserted. See [LIMITATIONS.md](LIMITATIONS.md).

## 11. Reproducibility and conclusion

Preserve raw data, exact manifests, permissions, source hashes, selected
dependencies/locks, checkpoint/tokenizer/config/policy versions and every failed
as well as successful test report. A curated bundle includes only specifically
approved shareable files, not environments, credentials, private texts, raw
datasets or unlicensed weights/artwork. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md)
and [LICENSES_AND_ATTRIBUTION.md](../../LICENSES_AND_ATTRIBUTION.md).

The source provides an integrated architecture and a reproducible evaluation
method. Whether it improves predictive quality and meets the laptop/runtime
acceptance criteria remains an empirical question. Replace this concluding
paragraph only after actual results support a more specific conclusion.

## References and evidence appendix

Record the exact bibliographic entries required by the supplied dataset/model
cards and course style. The existing project register includes Harper and
Konstan's MovieLens reference and Maas et al.'s IMDb reference; verify those
against the local source records before submission. Use official versioned
documentation and actual selected model papers/cards. Do not cite unreviewed
alternative datasets. Attach the source/evaluation manifest and the source-to-
evidence syllabus mapping rather than presenting illustrative code output as
an experiment.
