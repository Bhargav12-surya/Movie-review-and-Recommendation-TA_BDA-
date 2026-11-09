# Phases 4-8: source handoff and later execution

Prepared 10 November 2026, Asia/Calcutta. The user requested files through
Phase8 in one pass. This is **source generation**, with static validation only.
No new fitting,training,evaluation,unit tests,model inference,Spark jobs,
dependency resolution,installation,download or application startup is performed.
Earlier phase/runtime/data gates remain open; files do not close them.

## Delivery and dependencies

| Phase | Objective and source | Prerequisites before execution |
|---|---|---|
|4|ml/aspect_common,aspect_extraction,aspect_sentiment,aspect_pipeline; explicit BIO spans and independent target sentiment|Complete human aspect annotations,approved canonical IDs,original offsets,reviewed EDA/baseline,local licensed weights and run permission|
|5|ml/themes,topics,embeddings,summarization and common/evidence; relevance,exploratory topics,semantic vectors and grounded summaries|Permitted complete theme labels,metadata/review snapshots,local reviewed model assets; legitimate relevance/summary evaluation judgments|
|6|ml/review_risk; duplicate/similarity and trained behavioural anomaly|Legitimate history,behaviour-use consent/provenance and approved train/split records; real moderation ground truth for performance claims|
|7|scoring and Scala analytics/ReviewAnalytics.scala; nullable audience/target snapshots|Approved calibrated model predictions,eligibility/latest revisions and reviewed minimum-evidence/shrinkage methodology|
|8|Scala recommendation/{TemporalSplit,RankingEvaluation,RecommendationJob}.scala and recommender|Validated cleaned MovieLens Parquet,approved global cutoffs/config/input hashes,final compiled JAR,canonical mapping,actual embeddings/preferences and validation-selected hybrid weights|

Each NLP bundle has separate train.py,evaluate.py,predict.py,config.yaml,
README.md and model_card.md. Embeddings/summarization initially use actual
licensed pretrained weights; their train entry points explicitly reject
unapproved optional fine-tuning instead of manufacturing training results.
Topics use actual train-only LDA. BERTopic is optional and not claimed fitted.
The common supervised engine supports actual aspect and multi-label Transformer
training,with separate task adapters rather than copied model loops.

## Exact execution order later

1. Review Phase1 source rights,canonical mappings and genuine labels. MovieLens
   is ratings/tags; IMDb is binary,unmapped and not an aspect/neutral source.
2. Verify the user's current manual installation and measured RAM/disk/GPU.
   The historical cu130 tensor pass does not validate a changed cu132 build.
   Finish final-source Scala compilation,Phase2 Parquet/batch/stream/UI checks.
3. Complete Phase3 actual comparable classical baselines,small approved GPU
   smoke,training/calibration/frozen final tests before claiming integrated NLP.
4. Prepare actual Phase4 train,tuning,calibration,test annotation manifests.
   Freeze taxonomy,original spans,all duplicate/movie/reviewer groups and rights.
5. Compute and review Phase4 EDA/baselines. Fill dataset_review.example.json
   with genuine hashes and real baseline report; fill source/model/run forms.
6. Run one bounded aspect model at a time. Test actual CPU/GPU,AMP,save/reload
   and optimizer/scheduler/scaler/RNG resume before larger approved training.
7. Select on tuning,calibrate aspect polarity on calibration,freeze and reserve
   final component/pipeline tests. Evaluate predicted spans end-to-end,including
   missed/spurious targets,language cohorts and reviewed empty negative reviews.
8. Prepare Phase5 complete theme labels. Train/evaluate multi-label relevance;
   curate exploratory topic results separately. Generate local embeddings and
   evaluate retrieval using genuine human judgments before indexing later.
9. Build eligible movie snapshots and grounded summaries. Human factuality
   review must approve generated candidates before publication; default quoted
   extractive evidence remains available when no generative model is supplied.
10. Audit available Phase6 signals. Run bounded similarity/behaviour experiments
    only with permitted history. Tune moderation thresholds on validation and
    quantify false positives on real held-out labels before any automated use.
11. Review Phase7 support/shrinkage/uncertainty policy using genuine predictions.
    Reconcile Python/Scala numeric outputs and deletion/reanalysis/replay cases.
12. Freeze Phase8 global time cutoffs and candidate protocol. Establish popularity
    and content baselines; train sequential real Scala ALS trials. Select actual
    validation NDCG,verify factor mappings/dot products,then tune hybrid weights.
13. Freeze the selected ranking configuration and test once,reporting warm/cold
    cohorts,candidate sets,coverage,diversity,novelty and all exclusions. APIs,
    PostgreSQL and frontend integration belong to subsequent phases9-13.

## Phase4 data and manual entry points

Use the Phase1 annotation fields plus aspects_complete=true and
aspect_schema_version=explicit-aspect-spans-v1. All target sentiments are genuine
negative/neutral/positive strings; the current policy rejects mixed target
polarity,implicit and overlapping gold spans rather than silently mapping them.
An empty aspects array is a negative extraction example only after the human
confirms complete annotation. Overall sentiment is not a target label.

Fast-tokenizer offsets address unchanged Python Unicode code points. All
subwords receive BIO supervision; special/pad/partial-boundary labels use-100.
Every gold span must be fully representable in at least one bounded window.
Original offsets and browser UTF16 indexing remain distinct. Inference merges
overlap candidates deterministically; assigned-token confidence is uncalibrated.
Target sentiment constructs an exact marked target/context pair and checks the
actual token budget,including repeated mention identity. It never silently
truncates the selected target. Marker collisions require review.

Commands below are instructions for later manual execution,not past results:

~~~powershell
Set-Location -LiteralPath 'D:\BDA_TA'
.\.venv\Scripts\python.exe -B scripts/prepare_aspect_baseline.py --config 'ml/aspect_extraction/config.yaml' --output 'artifacts/aspect-baseline-extraction-001.json'
.\scripts\train_aspects.ps1 -Component aspect_extraction -Action Preflight
.\scripts\train_aspects.ps1 -Component aspect_sentiment -Action Preflight
.\scripts\train_aspects.ps1 -Component themes -Action Preflight
~~~

After genuine approvals and a successful small smoke:

~~~powershell
.\scripts\train_aspects.ps1 -Component aspect_extraction -Action Train -ExecuteApprovedRun
.\scripts\train_aspects.ps1 -Component aspect_sentiment -Action Train -ExecuteApprovedRun
.\scripts\train_aspects.ps1 -Component aspect_sentiment -Action Evaluate -RunDirectory 'models/aspect_sentiment/run-001' -Split tuning -Device cpu
~~~

Resume uses -Action Resume -ResumeCheckpoint with the identical config and an
owned checkpoint. Source/model/tokenizer/taxonomy/data/conditioning hashes are
frozen; a changed input at the same path is not an authorized resume. Final
test requires selection.json binding the actual model_manifest SHA and frozen
data,then -Split test -FinalTest. The pipeline has a separate paired-model
selection and exclusive reservation. Functions in ml/aspect_pipeline compose
models sequentially so both substantial encoders are not retained on GPU.

## Phase5 contracts

Theme manifests use record_id,movie_id,text,text_sha256,language_code,group_id,
split,theme_labels,themes_complete=true,adjudication and source/consent fields.
Labels are complete multi-label movie-themes-v1 annotations; an empty list is
not assumed annotated unless completeness is explicit. The Transformer uses
BCE logits,per-theme binary temperatures on calibration and thresholds on tuning.
Relevance outputs always keep audience_theme_sentiment=null. Audience reception
needs a different target-specific labelled model/evidence and cannot reuse
metadata keywords or whole-review polarity.

Generic permitted text rows require original text/text_sha256,record_id,
is_synthetic=false,is_deleted=false,consent_or_license_ref and the relevant
permission: training_permitted,inference_permitted,evidence_permitted or
moderation_use_permitted. Consent for one purpose does not imply the others.
Training manifests additionally require split and group_id. Review summary rows
use review_text,review_id,review_revision,movie_id,text_sha256 and published
moderation/evidence permission. All movie IDs must come from the approved registry;
the later application owns catalogue validation before requesting inference.

~~~powershell
.\.venv\Scripts\python.exe -B scripts/run_offline_phase.py --component embeddings --config 'ml/embeddings/config.yaml'
.\.venv\Scripts\python.exe -B scripts/run_offline_phase.py --component summarization --config 'ml/summarization/config.yaml'
~~~

Explicit later inference uses --action predict --input <permitted-local-jsonl>
--output <fresh-output> --execute. Summarization also needs --movie-id. Embeddings
write actual vectors to Parquet with record IDs,content hashes,dimension and model
revision. Never insert a vector from a different dimension/model into one index.
Use ml/embeddings/evaluate.py for actual human-judged Recall/MRR/NDCG.

Topic training uses --component topics --action train --execute with real
train/tuning/calibration/test manifests and matching approval. Only train fits
the vocabulary/LDA. Portable topic counts support bounded variational inference;
train perplexity is a diagnostic,not a held-out accuracy result. Curated theme
mapping stays null until a human reviews clusters; no coherence/stability value
is invented. Evaluate optional BERTopic only as a separately documented experiment.

Summaries select latest eligible revisions,then deduplicate and balance polarity
and aspect coverage. Selected reviews are not a representative population sample;
reported population counts are computed from the full eligible snapshot. Optional
local hierarchical generation retains unioned source IDs and abstains on token
budget overflow. A retrieved citation is not entailment: novel text remains a
requires_factuality_review candidate until a matching human snapshot/candidate
approval. Deleted/changed evidence invalidates the snapshot. Reference-based
ROUGE/BERTScore remain unavailable without genuine permitted human references.

## Phase6 risk interpretation

Text features are exact normalized duplication and actual TF-IDF cosine against
permitted history. Legitimate quotation can resemble spam. The only behavioural
features are documented submission/distinct-movie counts and duplicate fraction;
they require behaviour_use_permitted and provenance_reference. Missing history
does not generate an account age or fraud probability. Isolation Forest trains
on genuine bounded behavioural rows and saves numeric trees,not pickle.

The max duplicate/similarity/anomaly value is an explicitly unvalidated relative
index. It is not calibrated fraud probability. No sentiment feature,automatic
fake verdict or removal action exists. Actual supervised labels are needed for
precision/recall/F1,PR metrics,false-positive rates and threshold selection.
Use review_risk.evaluate on held-out labels; otherwise report metric absence.

## Phase7 policy and outputs

Fill scoring/config.example.json and a matching methodology approval only after
inspecting genuine calibrated predictions. Thresholds and population prior are
intentionally null; no invented defaults are presented as established science.
The code chooses latest review revisions,excludes stale/unapproved/deleted/
synthetic evidence,deduplicates exact text and admits one review per reviewer.
It computes100*(p_positive+0.5*p_neutral),documented weights,effective support,
minimum evidence and optional reviewed shrinkage. A prior never bypasses support.

Missing support returns null and exactly **Not enough audience reviews yet.**
All counts,model/method versions,snapshot hashes and timestamps remain explicit.
Bootstrap intervals describe sampling sensitivity,not model certainty or freedom
from population bias. Target records require their own approved probabilities;
newer missing/deleted target analysis invalidates older evidence. Metadata genre,
theme relevance,star ratings and recommendation scores never substitute.

Scala ReviewAnalytics.aggregateEligible independently performs the same weighted
formula on already eligible one-row-per-reviewer inputs. Its input contract is
strict; it is not an end-to-end transactional or deletion-aware streaming sink.
Actual Python/Scala parity and connection to review events remain acceptance work.

## Phase8 actual ALS and recommendation execution

The Scala job consumes cleaned rating Parquet and uses strict global chronological
cutoffs. Source user/item Int32 bounds are checked before casts. ALS is explicit
feedback,not an implicit reinterpretation of star ratings. Each trial fits one
real Spark MLlib model and exports real numeric factors,training popularity,
per-user sampled ranking metrics and file hashes. No Python wrapper is claimed
to implement Scala processing.

Review configs/recommendation/als.json and als_approval.example.json. Supply
all cleaned input Parquet SHA256s,cutoffs,parameters,new output and exact config
approval. The current defaults are preparation examples,not permission. Later:

~~~powershell
.\scripts\run_recommendation.ps1 -Action Preflight
.\scripts\run_recommendation.ps1 -Action Train -ConfigPath 'configs/recommendation/als.json' -ApprovalPath '<actual-reviewed-approval.json>' -JarPath '<final-compiled-project.jar>' -ExecuteApprovedRun
~~~

The launcher checks at least4GiB available RAM for3GiB heap+headroom,20GiB disk
reserve and localhost4040. No SBT/dependency resolver runs. It temporarily selects
the project JDK and restores process variables. Global Windows settings stay
unchanged. Final-source Scala compilation and the tiny Parquet smoke must pass
first; this handoff does not compile the newly generated Scala files.

Ranking uses up to100 deterministically selected users with eligible held-out
positives,all their eligible positives and up to100 hash-sampled unseen training
items. Relevance is rating>=4,K=10. This is **sampled ranking**,with explicit
candidate protocol and cold-candidate counts. Unknown factors get a disclosed
training-popularity fallback; they are not silently dropped. This raw fallback
mix needs further validation; it is not the normalized final hybrid ranker.
Cold-only users,missing positives and sampled population scope must be reported
separately from full-catalogue serving claims. Do not claim distributed speedup
from one local Spark process. Catalogue genre diversity requires actual metadata
and Python evaluation; Scala reports it unavailable until that join exists.

Select comparable actual validation trials with recommender.train.select_als_trial.
Freeze parameters before separately approved final-test mode. Retain exclusive
test reservations,including failures; changing experiment identifiers is not a
legitimate way to retune against test. No automated test-driven model selection.

Factor import verifies every actual factor Parquet part,rank and source namespace.
It needs a human-approved source-to-canonical mapping and matching registry hash.
Never turn MovieLens IDs into application IDs. Application cold start uses actual
content/genre/theme preferences and consented history. Optional ALS-WR fold-in
requires separate method approval and enough valid actual ratings.

Tune hybrid weights using recommender.train.tune on validation only. Normalization
uses the full eligible candidate set after seen/metadata filters; bounded diversity
reranking reports its pool. Constant channels add no discrimination. Explanations
show actual channel inputs and weighted contributions. The score is personalized
match,not audience sentiment. Report Precision/Recall/NDCG@K,coverage,genre
diversity and train-period smoothed novelty,including empty and cold lists.
Historical metadata/features need an as-of protocol before temporal claims.

## Tests, metrics and acceptance

Generated tests use tiny isolated synthetic contract fixtures,never real model
or audience evidence. Run them later after the relevant environment is verified:

~~~powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests/aspects -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests/phases4_8 -v
~~~

No such runtime tests have run in this delivery. Static AST/JSON/PowerShell parsing
does not establish library compatibility,CUDA kernels,trained quality or Scala
compilation. Genuine benchmark/error/subgroup/resource reports remain absent.

The generated AudienceAndTemporalSpec has four additional ScalaTest contracts
for the documented score formula,insufficient evidence,time-cutoff boundaries and
Int32 source identity protection. They have not run. The installed exact Scala
compiler's parser accepted24 main/test source files without typing,code generation
or execution. This is syntax evidence only; actual Spark APIs/build/Parquet still
need validation. Static parsers do not fit a model or establish runtime readiness.

Actual content integration is in recommender/catalogue.py: join explicit vector
record IDs and content hashes against a validated canonical catalogue and theme
relevance outputs. Missing vectors remain missing; no synthetic semantic features
or audience reception are inserted. Embedding/summarization inference permission
is distinct from training consent.

- [ ] Earlier phase execution/source/consent/mapping gates accepted.
- [ ] Phase4 actual annotated span/polarity and CPU/GPU/resume tests pass.
- [ ] Phase5 relevance/retrieval/topic/summary factuality measurements saved.
- [ ] Phase6 legitimate signal coverage and false-positive evaluation reviewed.
- [ ] Phase7 approved support/shrinkage,Python/Scala parity and replay invalidation pass.
- [ ] Phase8 actual ALS validation,factor parity,canonical maps,hybrid weights and all ranking cohorts evaluated.
- [ ] Model cards contain genuine measured results,rights,versions and limitations.
- [ ] Later API/database/frontend integration remains in phases9-13.

Official interfaces: [Transformers fast tokenizer](https://huggingface.co/docs/transformers/main_classes/tokenizer),
[PyTorch checkpoint state](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html),
[Spark ALS](https://spark.apache.org/docs/4.3.0/ml-collaborative-filtering.html),
[Sentence Transformers](https://www.sbert.net/),[scikit-learn LDA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.LatentDirichletAllocation.html).
These references do not establish an executed dependency lock or model result.
