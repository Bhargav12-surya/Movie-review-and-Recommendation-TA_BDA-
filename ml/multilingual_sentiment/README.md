# multilingual_sentiment

Status: source generated for later implementation; no model trained or evaluated.
Task: multilingual_movie. The fixed label map is enforced by ml/common/config.py.

This component reuses the actual shared Transformer loop in ml/common. It uses
local safetensors/tokenizers, dynamic padding, bounded batches, gradient
accumulation, tested-at-run-time AMP, optional checkpointing, early stopping,
optimizer/scheduler/scaler/RNG resume, validation-only model selection and a
separate calibration split. Training never reads held-out test text.

Keep original Unicode text. Emoji removal and reviewed lexical expansion are
explicit optional ablations; no slang/emoji polarity lookup is used. Sarcasm
predictions never invert sentiment. Language scope is declared experiment scope,
not a claim of demonstrated English/Hindi/Hinglish performance.

Fill real manifests, provenance, canonical registry, run approval, local model
permission/hashes and both actual TF-IDF baseline report paths before execution.
The config YAML uses the JSON subset for unambiguous types. Missing inputs cause
an explicit blocked result; they are never generated as replacement training data.

From the repository root, preflight only:

~~~powershell
.\.venv\Scripts\python.exe -B -m ml.multilingual_sentiment.train
~~~

See [Phase 3 runbook](../../documentation/phase3/RUNBOOK.md) for explicit approved
training/resume/evaluation/prediction commands. CPU training must be selected
explicitly; a missing GPU never silently starts a long CPU run.
