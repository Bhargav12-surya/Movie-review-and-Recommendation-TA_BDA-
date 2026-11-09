# BoW / TF-IDF sentiment baselines

This component supplies separate Logistic Regression and Linear SVM experiments
for the binary IMDb benchmark and genuine three-class movie annotations. Source
files were generated for later implementation. No training, evaluation, runtime
test or performance measurement has been executed for this component.

Each run chooses one estimator and one representation. Keep the same frozen
train/tuning/calibration/test references when comparing LR, SVM and Transformers.
For the second estimator, copy the reviewed config, select linear_svm and a fresh
output directory, then obtain approval for that exact config/hash. No parameter
grid, dataset acquisition or model download starts automatically.

## Source files and contracts

- train.py: explicit preflight or approved fitting; train-only vocabulary/IDF,
  CPU LR/SVM, tuning metrics and separate calibration.
- evaluate.py: frozen-artifact evaluation with matching manifest hashes and
  explicit language/script/cohort metrics, including observed class support; test
  requires a reviewed selection record and exclusive one-attempt reservation.
- predict.py: bounded JSON reconstruction and numeric inference; no pickle or
  joblib deserialization, lexicon fallback or invented neutral probability.
- config.yaml: intentionally incomplete three-class configuration. It is JSON
  syntax, a valid YAML subset. Null paths/approvals block execution.
- configs/training/imdb_binary_tfidf.yaml: actual existing train/test reference
  paths; tuning/calibration and provenance remain deliberately unresolved.
- model_card.md: untrained source template, separate from future trained cards.

Shared code lives in ml/common. Python modules are invoked from the repository
root using -m; direct script execution is not the supported import layout.

## Data, labels and gating

binary_imdb uses negative0/positive1 only. three_class_movie and
multilingual_movie use negative0/neutral1/positive2. The artifact stores this map
and exact class order. Binary probabilities are never padded with a fake neutral
class or presented as the production three-class model.

The first-party task requires an approved canonical movie registry, genuine
adjudicated labels, source/consent permission and disjoint leakage groups.
Unlabelled IMDb and excluded references cannot enter supervised fitting. Raw
texts are read lazily from hash-checked references and never rewritten. They are
materialized only for the requested role, with an explicit memory budget.

The existing IMDb validation manifest must be partitioned by its frozen group
IDs into tuning and calibration reference files. Do not use the same validation
records for both roles, re-split the official test or fabricate class labels.
The shared validator requires observed class support in every role. The original
validation file and all raw sources remain unchanged.

Before fitting, training_preflight checks the data/provenance and exact
config/split-bound approval. The execution path also checks measured resource
headroom. The current user instruction is file generation only: commands below
are future instructions and have not been run. Phase2 runtime acceptance and
the project's manual-data/model/training rules remain separate requirements.

## Features, models and calibration

The train role alone fits CountVectorizer (BoW) or TfidfVectorizer. Tuning,
calibration and test use transform only. Default unigrams/bigrams preserve word,
emoji and punctuation tokens with a configurable pattern and no stopword list,
stemming, polarity lookup or aggressive source normalization. Lowercasing is an
explicit baseline choice. This tokenization is not a claim of validated Hindi,
Hinglish, emoji or sarcasm understanding; subgroup results/ablations are required.

The LR solver is lbfgs. The SVM is LinearSVC with bounded iterations and dual=auto.
An unresolved convergence warning fails the run rather than publishing an
apparently completed model. SVM decision margins are not probabilities. A
one-dimensional temperature is fitted only on the dedicated calibration role
using shared NLL minimization. Its grid/range live in ml/common/calibration.py.
Both models store that calibration operation and source hash explicitly.

Tuning accuracy/F1 selects candidates before calibration. SVM tuning output
omits probability-based NLL/Brier/ECE because its raw margins have no such
interpretation. Calibration-fit metrics are marked as fit-split diagnostics;
they are not unbiased held-out performance. Later tuning/test evaluation uses
the frozen calibrated model. No test text is opened during training.

## Portable artifacts and inference

A successful future run writes experiment.json, model.json,
training_report.json and model_card.json. Failed runs retain failure.json and
their partial files in the fresh directory; never overwrite them. model.json
contains fixed feature indices/IDF, numeric coefficients/intercepts, task labels,
tokenization settings, calibration, dependency versions and manifest hashes.
training_report.json records the model SHA256 and actual computed metrics;
it has component=tfidf, trained=true and estimator=logistic_regression or
linear_svm for the Transformer baseline gate. Source templates are not reports.

Inference checks the SHA256, format, finite weights, dimensions, class ordering,
calibration identity and exact sklearn/NumPy/Python-minor versions. It rebuilds
the fixed vectorizer without fitting. Binary scores use [0,margin], which matches
the fitted LR sigmoid convention. Multiclass rows retain their actual class order.
There is no neural model, GPU allocation, external API or deserialized executable.

An explicit language argument must match the artifact's declared scope. This is
caller-supplied metadata, not a language detector. Missing artifacts or unsupported
language cause explicit unavailability. Zero-feature input is marked for review
with a null label; its numerical class probabilities still come from actual
model intercepts. Evaluation retains such rows in full-classifier metrics and
reports their count, rather than silently dropping difficult examples.

Predictions are research outputs. audience_score_eligible stays false: final
production approval, calibrated minimum-evidence scoring and audience aggregation
belong to later integration. The uncertainty index1-max(p) is a documented
calculation, not a proven error probability. Classifier weights/vocabulary can
contain derived private text; keep artifacts local/ignored and review rights
before sharing them.

## Future commands after the gates pass

~~~powershell
Set-Location -LiteralPath 'D:\BDA_TA'
.\.venv\Scripts\python.exe -B -m ml.sentiment_tfidf.train --config ml/sentiment_tfidf/config.yaml
.\.venv\Scripts\python.exe -B -m ml.sentiment_tfidf.train --config configs/training/imdb_binary_tfidf.yaml --execute
.\.venv\Scripts\python.exe -B -m ml.sentiment_tfidf.evaluate --config configs/training/imdb_binary_tfidf.yaml --run-dir models/sentiment_tfidf/imdb-binary-lr-run-001 --split tuning
.\.venv\Scripts\python.exe -B -m ml.sentiment_tfidf.predict --config configs/training/imdb_binary_tfidf.yaml --run-dir models/sentiment_tfidf/imdb-binary-lr-run-001 --text 'Your own review' --language en
~~~

These module commands run from the repository root without Python's -I option,
which would exclude the root package from module search. No editable installation
or reuse of the legacy environment is required.

Before the final test, a human writes selection.json inside the trained run with
model_frozen=true, selected_for_final_test=true, reviewed_by, the actual
model_sha256 and identical manifest_hashes. Then an explicit evaluate action with
--split test --final-test reserves the one final attempt before opening test
text. Failed reservations remain visible and need review; do not delete markers.

Use accuracy, per-class precision/recall/F1, macro/weighted-F1, confusion matrix,
NLL, multiclass Brier and ECE with its documented15 equal-width bins. Save real
latency/resource observations during later executed validation. None are claimed
by generating these files.

Cohort reports use only the explicit annotation/source metadata supplied with
each review. They may overlap; missing annotations do not imply absence of
sarcasm, code mixing, emojis or any language. Full task labels remain fixed in
cohort confusion matrices, and per-class support exposes missing classes. No
text-based heuristic manufactures a cohort or subgroup performance claim.
