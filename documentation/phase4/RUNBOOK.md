# Phase 4: aspect extraction and target sentiment

Follow-up10 November2026: the user expanded source generation through Phase8.
See [the combined runbook](../phases4-8/RUNBOOK.md). The Phase4 execution/data
acceptance conditions below remain open. dataset_review_path must bind actual
EDA/leakage/baseline review and exact manifests before supervised fitting.

Prepared 9 November 2026, Asia/Calcutta. **Source-generation delivery only.**
The user requested the next phase while retaining the instruction to generate
files for later implementation/execution. No datasets, models or packages are
downloaded. No model is trained, evaluated, deployed or claimed to work by the
presence of source. Phase 2 runtime acceptance and Phase 3 training/evaluation
remain open; this source preparation does not waive their criteria.

## Objectives and dependencies

Train an explicit aspect-span extractor and a separate classifier conditioned
on each target. A review can praise acting and criticize story without either
target inheriting the overall review label. Preserve original Unicode offsets,
evaluate exact spans and target polarity, and report unsupported implicit or
mixed aspects honestly. The multilingual requirement applies only to the extent
supported by genuine human-labelled data and measured held-out results.

Required later inputs are permission-backed movie-linked review annotations,
an approved canonical movie registry, disjoint review/group manifests, the
reviewed 16-category taxonomy, local licensed tokenizer/safetensors artifacts,
explicit run approval, and an environment that passes actual CPU/CUDA checks.
MovieLens ratings/tags and the binary IMDb corpus do not supply aspect labels.

| Path | Responsibility |
|---|---|
| ml/aspect_common | Shared configuration, bounded annotation manifests, metric contracts, training/evaluation engine and CLI |
| ml/aspect_extraction | Tokenization alignment, BIO extraction, overlapping-window prediction and component bundle |
| ml/aspect_sentiment | Exact-target context preparation, target-conditioned classification and component bundle |
| ml/aspect_pipeline | Sequential extraction/classification and full-pipeline prediction/evaluation |
| scripts/train_aspects.ps1 | Manual component entry points; preflight is the default action |
| schemas/datasets/phase4_aspect_manifest.schema.json | Adjudicated explicit-span input contract |
| schemas/predictions/aspects.schema.json | Review evidence/span prediction contract |
| tests/aspects | Isolated synthetic contract tests for later execution |
| notebooks/07_aspect_extraction.ipynb,08_aspect_sentiment.ipynb | Unexecuted academic experiments calling shared source |

Each trainable component has train.py,evaluate.py,predict.py,config.yaml,
README.md and model_card.md. Artifacts remain under ignored models/ and
artifacts/ paths. Source generation does not produce model weights or metrics.

## Exact later execution order

1. Close the relevant earlier-phase execution gates and review current
   Python/package/driver/CUDA/resource evidence. A previous tensor pass for a
   different torch installation is not proof for the current installation.
2. Review source permissions, canonical IDs, annotation guidelines, taxonomy,
   original text hashes, class/aspect/language counts and overlapping annotator
   agreement. Resolve mixed/uncertain/implicit annotations before admitting data.
3. Freeze train,tuning,calibration,test manifests with duplicate/source/movie/
   reviewer groups isolated according to the approved generalization protocol.
   Keep all targets from one review/revision in the same partition.
4. Populate separate extraction and target-sentiment configurations. Copy blank
   Phase 3 provenance/model/run forms to reviewed local paths; fill genuine
   values rather than treating examples as approval. Do not modify raw data.
5. Run preflight. Review class/aspect support and missing inputs. Do not create
   synthetic replacements or infer aspect labels from a review-wide score.
6. With explicit approval, run a tiny extraction forward/backward/checkpoint
   experiment first. Verify subword alignment, windows, exact offsets and actual
   resume/reload before a larger bounded extractor run.
7. Inspect extraction tuning errors and rare-category supports. Choose the
   model/window policy using tuning only; do not inspect test for selection.
8. Train the separate target-conditioned sentiment model on human aspect
   labels. Reuse review splits; fit calibration on the dedicated calibration
   partition, not tuning or test. Train one substantial model at a time.
9. Freeze both selected artifacts and their input contracts, then perform the
   prespecified held-out component and full-pipeline evaluations. Do not tune
   another run after reading test reports. Keep failed final attempts visible.
10. Measure actual CPU inference, GPU RAM/VRAM, latency, checkpoint equivalence
    and language/negation/contrast/window-boundary failures. Populate model cards
    from real reports, then consider later registry/API integration in Phase 9.

## Annotation contract

Use JSONL with one complete review/revision per record. Required fields include:
split,group_id,review_id,review_revision,movie_id,review_text,text_sha256,
language_code,annotation_status,annotator_id,adjudicator_id,
annotation_guideline_version,label_schema_version,taxonomy_version,
aspect_schema_version,aspects_complete,training_permitted,
consent_or_license_ref,sentiment and aspects. Sentiment here is the independently
annotated overall field retained for Phase 1 compatibility; the aspect classifier
uses each aspect's own sentiment.

Fixed versions are label_schema_version=sentiment-three-class-v1,
taxonomy_version=movie-aspects-v1 and
aspect_schema_version=explicit-aspect-spans-v1. aspects_complete=true certifies
human review of all explicit targets. An empty aspects array can be a reviewed
negative extraction example; an unannotated review is not a negative example.

Each aspect has aspect,start,end,text,sentiment. Offsets are zero-based Python
Unicode code-point [start,end) positions into the unchanged review_text; require
review_text[start:end]==text. Multibyte UTF-8 and browser UTF-16 indices are
different representations. Do not normalize/transliterate text before applying
the original offsets. Repeated identical words require their distinct positions.

The fixed starting categories are acting,story,screenplay,direction,characters,
cinematography,visual_effects,editing,pacing,music,sound_design,dialogue,
worldbuilding,emotional_impact,originality,runtime. Aspect polarity is
negative0,neutral1,positive2. A human mixed label is not silently converted to
neutral; implicit and overlapping/nested aspect schemes are not supported by
the initial explicit flat BIO contract. Quarantine them for a separately
approved schema/model experiment.

Human annotations must resolve English,Hindi Devanagari,Romanized Hindi or
Hinglish/code-mixed language within the configured experiment scope. Script
observations do not determine language. Preserve explicit cohorts for slang,
emoji,sarcasm and mixed-aspect evaluation, including genuine Hindi/Hinglish
movie-domain examples. Missing subgroup labels are not measured support.

JSON Schema cannot prove rights, canonical identity, SHA256 equality, exact
substring boundaries, probability sums, duplicate isolation or representability
by the chosen tokenizer. Python validators and held-out execution check those
conditions. A schema parse alone does not establish data acceptance.

## Tokenization and model behavior

The extractor requires a local fast tokenizer with original-text offset maps.
BIO uses O plus B-category/I-category pairs. Specials/padding are ignored with
-100 labels. Continuation subwords must retain the correct inside label rather
than becoming independent beginning spans. Nonrepresentable annotation
boundaries must be rejected explicitly; do not snap a human span and pretend it
was the original annotation. Partial targets at window boundaries must not
create false outside labels or extra gold examples.

Use bounded overlapping windows, initially maximum sequence length128 and
stride32. A long review is not silently treated as a single short prefix.
Window-count/token budgets can reject an input; they must not silently drop its
tail. The extractor documents deterministic duplicate/overlap conflict handling
and BIO repair. Exact-match scoring counts both false positives and missed gold
spans; token accuracy is only a secondary diagnostic.

Target sentiment receives an exact target/category and bounded review context.
The tokenizer must preserve the whole target inside its actual paired input.
Conditioning distinguishes repeated target strings by their positions. An absent
target, invalid span or unsupported language yields explicit unavailability,
never a copy of whole-review sentiment. The pipeline obtains targets from the
trained extractor and loads the two substantial models sequentially to limit
GPU residency. No keyword-only extractor or polarity fallback is used.

## Manual commands for later use

From the workspace root, inspect readiness after the prerequisites are supplied:

~~~powershell
Set-Location -LiteralPath 'D:\BDA_TA'
.\scripts\train_aspects.ps1 -Component aspect_extraction -Action Preflight
.\scripts\train_aspects.ps1 -Component aspect_sentiment -Action Preflight
~~~

The following commands execute work and must be used only after separate data,
model and bounded-run approvals. Review actual configured output paths first:

~~~powershell
.\scripts\train_aspects.ps1 -Component aspect_extraction -Action Train -ConfigPath 'ml/aspect_extraction/config.yaml' -ExecuteApprovedRun
.\scripts\train_aspects.ps1 -Component aspect_sentiment -Action Train -ConfigPath 'ml/aspect_sentiment/config.yaml' -ExecuteApprovedRun
.\scripts\train_aspects.ps1 -Component aspect_extraction -Action Resume -ConfigPath 'ml/aspect_extraction/config.yaml' -ResumeCheckpoint 'models/aspect_extraction/run-001/checkpoints/checkpoint-00000200' -ExecuteApprovedRun
.\scripts\train_aspects.ps1 -Component aspect_extraction -Action Evaluate -ConfigPath 'ml/aspect_extraction/config.yaml' -RunDirectory 'models/aspect_extraction/run-001' -Split tuning -Device cpu
~~~

Train/Resume require the explicit execution switch plus valid reviewed records;
that switch is not approval by itself. A CLI preflight result is not an executed
training experiment. Module commands use python -B -m from the repository root;
do not add -I to uninstalled-package module commands.

Resume uses the same frozen config,data,tokenizer/model/taxonomy/offset contract
and an owned checkpoint. Checkpoint state includes model,optimizer,scheduler,
scaler,RNG and progress. Resume equivalence must be tested before reproducibility
claims. Use a fresh output for every new run; do not overwrite failures or delete
checkpoints to bypass resource budgets. No OOM retry, CPU training fallback or
network model resolution happens implicitly.

For final evaluation, prepare the trained run's reviewed selection.json with
the genuine frozen artifact/manifest hashes and use -Split test -FinalTest.
The final attempt is reserved before test inference. Component gold-target
evaluation and full-pipeline evaluation answer different questions; neither
may replace the other. Pipeline paired-run commands are documented in
ml/aspect_pipeline/README.md once its actual entry points are inspected.

## Tests, metrics and expected outputs

Run the authored tests later, after checking their documented dependencies:

~~~powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests/aspects -v
~~~

Synthetic fixtures are isolated test contracts and never real training,
evaluation or audience evidence. The file-generation delivery does not execute
these tests. Static Python/notebook parsing is not a runtime test pass.

Report extraction exact span micro precision/recall/F1 and per-aspect supports,
plus secondary token diagnostics where available. Report target sentiment
accuracy,macro/per-class F1,confusion matrices,NLL,Brier and documented-bin ECE
on gold targets. Report full-pipeline exact (review,category,start,end,polarity)
precision/recall/F1 using predicted targets. An unmatched prediction is a false
positive; a missed gold target is a false negative, including extraction misses.
Do not evaluate sentiment only on successfully matched predictions and call it
end-to-end performance.

Report real subgroup supports and metrics for English,Hindi,Romanized Hindi,
Hinglish,slang/emoji-heavy,sarcastic and mixed-aspect reviews. Small or missing
cohorts limit conclusions. Token confidence is a diagnostic unless separately
calibrated/validated; it is not exact-span correctness probability. Calibration
fit-split metrics are diagnostics, not unbiased confidence generalization.

Expected real outputs after execution are immutable experiment and input
contracts, actual data/config/source/model hashes, tuning/calibration/final
reports, safetensors/tokenizer artifacts, retained checkpoints, exact-span
evidence, paired pipeline metrics, resource observations and updated model cards.
No measured result is prepopulated by this delivery.

## Completion checklist

- [ ] Legitimate complete explicit-span annotations,canonical IDs and permissions approved.
- [ ] Taxonomy,neutral/mixed/implicit policy and original Unicode offsets reviewed.
- [ ] Train/tuning/calibration/test groups and class/aspect/language support audited.
- [ ] Fast-tokenizer subword and overlap-window contracts pass executed tests.
- [ ] Tiny CPU/GPU forward/backward/AMP/checkpoint/reload/resume tests pass.
- [ ] Separate extractor and target-sentiment models trained and selected on tuning.
- [ ] Target probabilities calibrated on a distinct calibration partition.
- [ ] Frozen component and full-pipeline final evaluations saved honestly.
- [ ] Required Hindi/Hinglish and informal/mixed-aspect cohorts evaluated.
- [ ] Actual latency,RAM/VRAM and bounded long-input failures measured.
- [ ] Missing models/languages/targets return explicit unavailable or unsupported states.
- [ ] Model cards and later serving integration distinguish source from validated capability.

The next phase is theme/topic/embedding/summary source work. It does not make
Phase4 trained or complete; the execution requirements above remain open.
