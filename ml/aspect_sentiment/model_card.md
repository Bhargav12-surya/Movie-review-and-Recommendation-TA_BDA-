# Aspect sentiment model card

Status: **not trained; no model quality or runtime measurements**.

- Task: target-conditioned explicit movie-aspect sentiment.
- Labels: negative0,neutral1,positive2; mixed/uncertain/unsupported are not fabricated classes.
- Base architecture/license/revision: pending manually supplied licensed sequence-classification encoder.
- Inputs: immutable original review, human aspect category/surface/code-point span,
  bounded context and ordinary-text target markers under category-surface-marked-context-v1.
- Targets: genuine adjudicated per-aspect polarity; never the overall review label.
- Data/permission/canonical registry/split hashes: pending approved local records.
- Splits: train,tuning,calibration,test with duplicate/movie/reviewer groups isolated.
- Initial resource settings: length128,micro-batch4,accumulation8,zero workers;
  validated AMP and optional checkpointing, one substantial model at a time.
- Selection: tuning gold-target macro-F1; separate temperature calibration.
- Evaluation: gold-target classification plus separate full-pipeline exact target+polarity F1;
  human language/script/emoji/slang/sarcasm/mixed-aspect cohort supports and limitations.
- Hardware/VRAM/latency/resume equivalence: unmeasured.
- Limits: no implicit-aspect classifier, no trained language-ID adapter, no automatic
  sarcasm inversion, no proven English/Hindi/Hinglish capability, strict tokenizer-boundary
  support and reserved marker collisions require attention.
- Deployment: experimental files only, no registered production artifact or audience evidence.

Populate from actual retained reports after approved execution. Keep missing
coverage and calibration-fit diagnostics distinct from held-out performance.

