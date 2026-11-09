# Phase 3: generated files and later execution

Prepared9 November2026,Asia/Calcutta. The latest user instruction is **generate
files only; the user will implement/run them later**. No training, evaluation,
model download, Spark job or application startup is part of this delivery.
Static source validation is separate from runtime acceptance.

## Objectives and generated components

Compare TF-IDF/BoW Logistic Regression and Linear SVM with compact Transformer
experiments on identical frozen splits. Keep IMDb binary results separate from
genuine negative/neutral/positive movie-domain experiments. Add multilingual
and independent sarcasm experiments without claiming that they are trained.

| Path | Responsibility |
|---|---|
| ml/common/config,artifacts,data,gates | Versioned labels, bounded local manifests, raw hashes, leakage/consent/approval and fresh artifacts |
| ml/common/metrics,calibration | Classification metrics and separate held-out temperature scaling |
| ml/common/hardware,checkpointing | Explicit device/AMP probe, resource guards, owned optimizer/scheduler/scaler/RNG checkpoints |
| ml/common/transformer_engine,transformer_cli,model_source | Actual shared local-only train/evaluate/predict logic and source/license checks |
| ml/sentiment_tfidf | Actual train-only sparse baseline and portable fitted-state inference |
| ml/sentiment_transformer | English binary comparison or genuine three-class domain training |
| ml/multilingual_sentiment | Shared supervised model loop with human-labelled English/Hindi/Romanized Hindi/code-mixed data |
| ml/sarcasm | Independently labelled/evaluated sarcasm classifier; never a polarity reversal rule |
| ml/informal_language | Immutable Unicode originals, aligned feature views, symbol/script observations and reviewed optional adapters |
| configs/training | Binary experiment configs and blank manual approval/source/model permission forms |
| scripts/prepare_sentiment_splits.py | Divide verified validation references into disjoint tuning/calibration groups |
| scripts/train_models.ps1 | Explicit manual entry points; preflight is the default action |
| tests/ml and notebooks03–06 plus language notebooks | Generated contract tests and reproducible experiment entry points, not saved results |

Dependencies: selected root Python3.11, approved scientific/NLP requirements,
local licensed base-model safetensors/tokenizer files, reviewed source rights,
the valid frozen manifests, genuine annotations and actual baseline reports.
The Phase2 Spark runtime gate remains open. File generation does not close it.

## Exact order when the user is ready

1. Finish/review Phase2 actual Spark compilation,unit contracts,Parquet smoke,
   MovieLens reconciliation and streaming/UI evidence. Its generated runbook
   retains those checks. Do not call phase completion from source presence.
2. Recheck the manually installed Python packages,driver,CUDA tensor and AMP
   support. The current manual cu132 build must be checked; an earlier cu130
   tensor pass is not proof for a different installation. Do not reinstall tools
   or resolve requirements implicitly. Preserve at least20GiB disk reserve.
3. Review Phase1 source permission,mapping and split reports. IMDb is the only
   supplied text benchmark currently audited. Domain neutral,Hindi/Hinglish,
   sarcasm and aspect annotations remain human inputs; no labels are generated.
4. Prepare independent tuning/calibration references from the existing verified
   validation split. Official IMDb train/test references remain unchanged.
5. Create separate configs/output paths for Logistic Regression and Linear SVM.
   Compare actual tuning metrics. Each baseline fits vocabulary/IDF/model only
   on train; calibration uses calibration, never tuning/test.
6. Select a licensed compact English baseline and a multilingual candidate only
   after license/script/memory review. User supplies the local files. Fill model
   permission hashes/revision; no command here downloads checkpoints.
7. Set up a bounded forward/backward/checkpoint smoke as a separately approved
   config (for example maximum_updates2,one epoch),then review its real outputs.
8. Authorize a larger bounded run only after that smoke succeeds. Train one
   substantial model at a time; do not run Spark concurrently.
9. Choose model/hyperparameters using tuning only. Fit temperature on the separate
   calibration split; freeze the selected artifact and preprocessing policy.
10. Evaluate test once after selection using the explicit final-test action.
    Evaluate human-labelled language/slang/emoji/sarcasm/mixed-aspect cohorts and
    controlled ablations; disclose counts and missing coverage.
11. Review actual reports/model cards,checkpoint reload/resume and CPU inference.
    Phase9 later registers approved artifacts and connects real backend APIs.

## Prepare binary tuning/calibration references

Run later from D:\BDA_TA. These are instructions, not actions already performed:

~~~powershell
.\.venv\Scripts\python.exe -B scripts/prepare_sentiment_splits.py --validation-manifest 'artifacts/data_quality/imdb-20261108-full-fe07af53/validation.jsonl' --verification-report 'artifacts/data_quality/imdb-manifest-verification-20261109-bdf9f8fa/manifest_verification.json' --output 'data/processed/sentiment/imdb-splits-001'
~~~

The script requires the existing independent verification hash. It assigns whole
connected source-movie/duplicate groups, reports actual class counts and refuses
empty/missing-class partitions. The hash split is not a temporal claim. Do not
try seeds repeatedly to select attractive test performance. Near-duplicate
candidate limitations in Phase1 still apply; no perfect leakage guarantee exists.

Set tuning and calibration paths in configs/training/imdb_binary_*.yaml to those
new reference files. They retain split=validation plus experiment_split. Do not
pass the same validation file for both roles. Domain/sarcasm manifests need
reviewed train,tuning,calibration,test roles,group IDs,original text hashes and an
approved canonical registry. No movie IDs are inferred from IMDb reviews.

## Human-labelled annotation additions

The normal movie sentiment map is negative0,neutral1,positive2. IMDb remains
negative0,positive1. Sarcasm uses an independent sarcasm field and
not_sarcastic0,sarcastic1; a sentiment label is never a sarcasm label.

Use the Phase1 annotation contract plus the language addendum. Domain manifests
contain split,group_id,review_id,review_revision,movie_id,review_text,text_sha256,
annotation_status=adjudicated,adjudicator_id,training_permitted=true and
consent_or_license_ref. Sentiment annotations retain label_schema_version,
taxonomy and the original aspect evidence. Sarcasm uses
label_schema_version=sarcasm-binary-v1 and an independent human sarcasm label.

Group-by-movie is the conservative default; reviewer_group_id also stays split
isolated when supplied. If a different generalization question requires a
different approved protocol, document that choice. Source/movie/revision/duplicate
groups must never silently cross evaluation boundaries. Every split must have
real support for all task classes; lack of data is a blocker, not a neutral label.

language_code and cohorts are supplied annotations. Suggested codes are en,hi,
hi-Latn and mul, with languages=[en,hi] for annotated code-mixed text. Script alone
cannot identify Romanized Hindi/Hinglish. No trained language detector or optional
transliterator is bundled. Symbol detection is conservative, not complete Unicode
grapheme segmentation. These limitations remain explicit in reports.

## Approval and model-source forms

Copy configs/training/*.example.json to a chosen local reviewed path. Do not
change the source examples to claim approval. Fill actual attribution,source
permission,license references,model revision and file SHA256s. Set approval_path,
data.provenance_path,model.local_path and model.permission_path in the config.

Run approval requires the exact config SHA256 and all manifest hashes returned
by preflight. Baseline and Transformer approvals identify different components.
Unknown/false approvals block training. Both real LR and SVM reports are required
before Transformer fitting; baseline_reports must reference their training reports
with the same task and split fingerprints. No source is approved by its filename.

Base weights must be supplied as local safetensors with tokenizer/config files.
Model code uses local_files_only=true,trust_remote_code=false,use_safetensors=true.
No Hugging Face ID is resolved on the network. Pretrained-only weights are not
misrepresented as locally fine-tuned weights. Inference loads only a trained,
hash-verified experiment artifact and returns unavailable if it is missing.

## Manual entry points

Module commands intentionally use -m from the repository root without -I;
isolated Python mode would remove the uninstalled source package from sys.path.
The PowerShell launcher temporarily selects that directory and restores it.

~~~powershell
Set-Location -LiteralPath 'D:\BDA_TA'
.\scripts\train_models.ps1 -Component sentiment_transformer -Action Preflight
.\scripts\train_models.ps1 -Component sentiment_tfidf -Action Preflight -ConfigPath 'configs/training/imdb_binary_tfidf.yaml'
~~~

After separate source/model/run approvals are complete, these commands actually
execute work; do not run them merely to inspect the generated files:

~~~powershell
.\scripts\train_models.ps1 -Component sentiment_tfidf -Action Train -ConfigPath 'configs/training/imdb_binary_tfidf.yaml' -ExecuteApprovedRun
.\scripts\train_models.ps1 -Component sentiment_transformer -Action Train -ConfigPath 'configs/training/imdb_binary_transformer.yaml' -ExecuteApprovedRun
.\scripts\train_models.ps1 -Component sentiment_transformer -Action Resume -ConfigPath 'configs/training/imdb_binary_transformer.yaml' -ResumeCheckpoint 'models/sentiment_transformer/imdb-binary-run-001/checkpoints/checkpoint-00000200' -ExecuteApprovedRun
.\scripts\train_models.ps1 -Component sentiment_transformer -Action Evaluate -ConfigPath 'configs/training/imdb_binary_transformer.yaml' -RunDirectory 'models/sentiment_transformer/imdb-binary-run-001' -Split test -FinalTest -Device cpu
~~~

Choose a fresh output for every experiment. Resume uses the identical config,
split fingerprints and an owned checkpoint; never a legacy joblib/pickle file.
Only optimizer-boundary checkpoints are resumable. States include model,optimizer,
scheduler,FP16 scaler and Python/NumPy/torch/CUDA RNG states. The same epoch seed
recreates the shuffled order and resumes the recorded next batch. This needs
actual equivalence testing before claiming bitwise reproducibility. GPU kernels
and package changes may still be nondeterministic. No automatic OOM retry,
dependency install,CPU training fallback or checkpoint deletion is performed.

Checkpoint count/disk budgets stop the run rather than removing prior artifacts.
Model selection uses tuning macro-F1. The saved final model comes from the best
tuning epoch; calibration fits a positive temperature by a documented bounded
one-dimensional search. NLL,Brier and15-bin top-label ECE are calculations, not
guarantees of reliable confidence. Sarcasm is independent and never reverses
the sentiment output. Missing/unsupported languages produce explicit status.

## Evaluation, tests and outputs

Run the generated tests later:

~~~powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests/ml -v
~~~

These tests use isolated synthetic contract fixtures, excluded from real training,
evaluation and audience evidence. They do not establish movie-domain model quality.
No test in the current file-generation delivery has been executed as a new model
experiment. A static AST parse is not a passed runtime test.

Expected real outputs after approved execution: immutable experiment metadata,
source/config/environment hashes,actual tuning/calibration reports,portable
baseline or local safetensors artifacts,owned checkpoints,one reserved test report,
cohort supports and updated model cards. No metrics are prepopulated.

Final acceptance:

- [ ] Source/model permissions,neutral/mixed/sarcasm policies and canonical IDs approved.
- [ ] Disjoint grouping and train/tuning/calibration/test fingerprints independently reviewed.
- [ ] Both real classical baselines fitted/evaluated on comparable splits.
- [ ] Tiny GPU forward/backward/AMP/checkpoint/resume smoke completed.
- [ ] English,multilingual and sarcasm experiments trained within measured resources.
- [ ] Final selected models tested once; all required subgroup supports/results saved.
- [ ] Emoji/transliteration/sarcasm ablations isolate the changed factor.
- [ ] Actual CPU inference,artifact reload,unsupported-language and failure behavior pass.
- [ ] No fabricated labels/metrics,audience scores or fake-review claims.
- [ ] Model cards distinguish source generation,pretraining,fine-tuning and demonstrated limits.

Official interfaces used: [PyTorch AMP](https://docs.pytorch.org/docs/stable/amp.html),
[checkpoint state dictionaries](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html),
[Transformers local model loading](https://huggingface.co/docs/transformers/v4.57.3/en/main_classes/model),
[Datasets from local generators](https://huggingface.co/docs/datasets/v4.4.1/en/package_reference/main_classes#datasets.Dataset.from_generator),
[scikit-learn text features](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction).
