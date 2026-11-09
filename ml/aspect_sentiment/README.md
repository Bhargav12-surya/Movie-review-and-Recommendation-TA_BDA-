# Aspect-conditioned sentiment

Status: source generated for later execution; no checkpoint has been trained,
calibrated, evaluated or deployed. The requested English/Hindi/Hinglish scope
is an experiment scope, not demonstrated model support.

This component predicts negative/neutral/positive **for one supplied explicit
aspect mention**. It never copies the whole-review label or assigns universal
polarity to slang, emojis or sarcasm. Each training label must be a separately
adjudicated aspect opinion. Implicit aspects and mixed aspect polarity remain
outside the current approved annotation scheme; unresolved cases block fitting.

The shared ABSA engine owns model loading, training, hardware/permission gates,
checkpoint/resume, selection and calibration. task.py owns the actual target
input/collation/inference and gold-target metrics. targeting.py selects context
from original fast-tokenizer offsets and constructs a query plus marked context.

## Frozen target conditioning

The query contains the category and target surface. The second sequence retains
a bounded original context and inserts ordinary-text <target> and </target>
markers around the **specific occurrence**. No tokenizer vocabulary or model
embedding is silently extended. This distinguishes two identical words at
different review positions. Original Unicode text and code-point offsets remain
unchanged in the review record and returned evidence.

The actual final pair is tokenized without truncation and measured against the
configured128-token starting budget. Context shrinks around the target until
the complete pair fits. Exact original and marked target boundaries must align
with the fast tokenizer; missing/partial targets and overlong targets raise an
explicit error. Text containing reserved marker strings requires separate review
rather than ambiguous conditioning. This protocol needs real multilingual
coverage tests; source generation does not demonstrate tokenizer compatibility.

Changing context policy/markers/tokenizer requires a fresh reviewed run. The
configuration and input contract must freeze the conditioning version and all
base/tokenizer hashes. Only original-text identity preprocessing is used here;
slang/emoji normalization must not silently invalidate offsets.

## Later execution

Supply permission-backed movie-linked manifests with train,tuning,calibration,
test roles; approved canonical IDs; explicit complete aspect annotations;
reviewed taxonomy; local licensed safetensors/tokenizer files; baseline and run
approval records. The empty config fields and example approval forms are not
approvals. Never repurpose IMDb binary labels as movie-linked aspect labels.

From the repository root, preflight only:

~~~powershell
.\\.venv\\Scripts\\python.exe -B -m ml.aspect_sentiment.train
~~~

Explicit later execution uses the Phase4 runbook and shared CLI. Train one
substantial model at a time, verify the current GPU/AMP installation and retain
owned checkpoints. The CPU option must be explicit for training. No module in
this bundle downloads model weights or data.

## Metrics and limitations

Tuning selects gold-aspect macro-F1. Separate calibration uses **gold target**
logits and genuine target labels from a dedicated split. Report accuracy,
macro/per-class F1, confusion matrix,NLL,Brier,ECE and per-aspect/language/cohort
supports. Empty aspect categories remain no_evidence, not successful predictions.
Gold-aspect classification is not end-to-end extraction quality: the separate
pipeline must classify predicted spans and report exact span+category+polarity
precision/recall/F1, including extraction false positives and misses.

Models may fail on long reviews, tokenizer-unrepresentable spans, rare categories,
negation, ambiguous/mixed opinions and unsupported language. A temperature value
or configured language does not prove confidence validity. No audience score or
fake-review risk is produced here. All runtime tests and measurements are pending.

