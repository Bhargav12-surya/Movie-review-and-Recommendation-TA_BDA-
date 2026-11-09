# File-generation handoff

The user requested generated files for later implementation/execution. This
delivery includes real source paths,configuration forms,notebooks and tests.
It does not contain trained model artifacts,model performance,final audience
scores,a running API or a finished multilingual system.

Review RUNBOOK.md first. Fill only genuine approved data/model/permission paths.
The empty approval forms are intentionally not approvals. Default training
commands run preflight only; explicit execution still checks the records.

Earlier Phase2 full main-source compilation succeeded using the manually
installed Spark distribution,without SBT resolution. Later file-generation
changes include explicit RFC CSV quote handling and strict delete-event flags;
recompile/retest those final files before runtime acceptance. Source generation
does not mark Phase2 complete. Its runtime work remains in the BDA runbook.

The current file-only source checks are listed in IMPLEMENTATION_STATUS.md.
No new unit-test,training,evaluation,service or Spark execution is claimed from
these generated files. Carry out the runbook acceptance checklist when ready.

Generated source groups:

| Files | Purpose |
|---|---|
| ml/sentiment_tfidf | Train-only sparse vocabulary/IDF, Logistic Regression/Linear SVM, separate calibration and portable actual-weight inference |
| ml/sentiment_transformer,ml/multilingual_sentiment,ml/sarcasm | Local supervised Transformer train/evaluate/predict bundles with untrained model cards |
| ml/common | Shared manifests/leakage/permissions, metrics/calibration, model-source verification, hardware, checkpoint and CLI utilities |
| ml/informal_language | Original Unicode/alignment, optional feature views, script/symbol/cue observations and explicit missing-adapter states |
| configs/training | Binary experiment configs and blank source/model/run/final-selection forms |
| scripts/prepare_sentiment_splits.py,train_models.ps1,verify_phase3_sources.py | Later split preparation/manual model entry points; current static-only verification |
| tests/ml | 20 authored test methods; not executed in this delivery |
| notebooks03-06 plus five language notebooks | 9 unexecuted notebooks,63 cells,27 code cells; no stored metrics |
| schemas/datasets/phase3_review_manifest.schema.json | Human-annotation manifest schema plus stricter Python eligibility checks |
| documentation/dataset/LANGUAGE_ANNOTATION_ADDENDUM.md | Versioned original-text/language/sarcasm/permission obligations |

The static checker also covers the previously generated offline Scala build,
toolchain discovery,environment verifier and launcher source. This does not
rerun their historical checks. The original architecture is preserved with an
explicit user-requested section33 addendum; AGENTS.md and IMPLEMENTATION_PLAN.md
record the later file-only scope. User-edited dependency manifests stay intact.
