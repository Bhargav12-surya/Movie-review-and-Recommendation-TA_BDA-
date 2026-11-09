# Phase 4 file-generation handoff

Prepared 9 November 2026, Asia/Calcutta. Read [RUNBOOK.md](RUNBOOK.md) first.
These files prepare actual supervised aspect extraction and target-conditioned
sentiment for later execution. They contain no trained artifacts, metric
claims, finished multilingual capability or running application.

| Files | Purpose |
|---|---|
| ml/aspect_common | Shared annotation/configuration contracts, training/evaluation/inference and exact-span metrics |
| ml/aspect_extraction | Per-model bundle plus original-offset BIO subword/window handling |
| ml/aspect_sentiment | Per-model bundle plus exact-target context and independent aspect polarity |
| ml/aspect_pipeline | Sequential model orchestration and full-pipeline target/polarity evaluation |
| scripts/train_aspects.ps1 | Explicit manual actions; default readiness inspection only |
| tests/aspects | Authored synthetic contract fixtures,not executed model evidence |
| notebooks/07_aspect_extraction.ipynb | Disabled-by-default extraction readiness and future real-report analysis |
| notebooks/08_aspect_sentiment.ipynb | Disabled-by-default gold-target and predicted-target evaluation analysis |
| schemas/datasets/phase4_aspect_manifest.schema.json | Permission-backed,complete explicit-span manifest shape |
| schemas/predictions/aspects.schema.json | Original-offset aspect evidence with optional actual polarity/confidence fields |

The manifest requires aspects_complete=true so missing labels cannot silently
become negative extraction examples. Original offsets,text hashes,canonical IDs,
split grouping and exact tokenizer alignment need Python validation and actual
tests in addition to schema parsing. Implicit/mixed/nested schemes are not
claimed as supported by the initial flat explicit-span contract.

Each notebook has empty outputs and null execution counts. Enabling its flag
later permits only the specifically guarded local inspection/report work;
training and evaluation remain explicit manual actions. The notebooks do not
download data,weights or packages and do not manufacture conclusions.

Static-check evidence and current acceptance status are recorded separately in
IMPLEMENTATION_STATUS.md. Phase2 runtime,Phase3 model training and Phase4 data,
training,evaluation and integration remain open. Do not call the complete
application or multilingual aspect system finished because these paths exist.
