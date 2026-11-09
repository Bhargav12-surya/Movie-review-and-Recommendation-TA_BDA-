# Model card — TF-IDF / BoW sentiment baseline source

Status: **untrained source template**. Files generated for later implementation.
No model was fitted, evaluated, approved or demonstrated by creating this card.
Metrics: null. Training dataset version: not approved. Weights: not created.

Task variants are binary_imdb (negative0/positive1) and genuine annotated movie
sentiment (negative0/neutral1/positive2). These label spaces are separate. IMDb
provides no neutral or validated application movie identity. Source text must
have explicit research/training permission, validated hashes and frozen splits.

Methods: train-only BoW or TF-IDF word/punctuation n-grams with CPU Logistic
Regression or Linear SVM. LR and SVM are separate runs on identical experiment
references. The default source configuration is a planning starting point,
not a measured optimal configuration. Fit/selection/calibration/test roles are
kept separate. SVM raw margins are never called calibrated probabilities.

The default reviewed-feature pattern retains slang/emoji/punctuation as input;
it has no fixed sentiment mapping. Hindi/Hinglish/sarcasm support has not been
established. A declared language scope is not subgroup performance evidence.
Negation, mixed polarity, long reviews and vocabulary gaps remain error risks.

Planned evaluation: accuracy, per-class precision/recall/F1 and support,
macro/weighted-F1, confusion matrix, NLL, Brier/ECE protocol, zero-feature rate,
language/cohort analyses, actual latency/RAM and model comparison. Calibration
fit-split metrics must remain labelled; final test is attempted only after model
selection/freeze. No result or hypothetical score is supplied here.

The future portable artifact contains vocabulary/IDF/coefficients in bounded
JSON, integrity/dependency metadata and task labels. It must not load untrusted
pickle/joblib or the legacy demo artifacts. Derived vocabulary and weights may
carry privacy/licensing restrictions. Production serving and audience evidence
require separate approval and later integration; no score is fabricated here.

A future successful run creates its own model_card.json and actual
training_report.json. Update the experiment-specific card with genuine source
hashes, license/consent, code/environment fingerprints, hyperparameters, measured
metrics, limitations, calibration and approval. Preserve this template as source.
