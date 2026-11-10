# Reproducibility, evidence freeze and sharing

Prepared 10 November 2026, Asia/Calcutta. This is an operator procedure. No
source/model freeze, replay, final test or evidence export has been executed
for this source-generation delivery. Follow earlier phase approvals and the
Phase12 runbook before executing the generated validation tools.

## 1. Separate the evidence classes

| Evidence class | What it establishes | What it does not establish |
|---|---|---|
| Static AST/JSON/TypeScript/PowerShell/Scala parser report | The named source/config syntax or type-check scope passed at its hashes | DB behavior, inference quality, CUDA correctness, UI rendering or a real Spark job |
| Environment observation | Versions/device/resources actually inspected at its timestamp | Compatibility after packages/drivers/configs change |
| Data audit | Counts/types/duplicates/identity checks actually performed on its source hashes | Approved rights, neutral labels, canonical joins or trained performance |
| Unit/disposable-DB test | The named behavioral contract under the stated fixtures/database | Real model quality or production data readiness |
| Actual model/ranking/retrieval evaluation | The stated task/split/candidate/cohort at exact versions | Other tasks/languages/candidate universes or later artifact revisions |
| Real-service integration/offline rehearsal | The observed journey and failure behavior on the frozen local stack | Unobserved paths, unlimited load or public production readiness |

Do not merge these classes into an undifferentiated pass rate. In particular,
an authored suite, skipped test or unapproved template is not a passed test.

## 2. Freeze the selected experiment before final evaluation

Record the study question, primary metric, relevance/label definitions,
exclusions, cohort supports, split/group manifests, model selection rule and
calibration policy before final-test access. Preserve actual dataset/card/rights
hashes and a reviewed canonical registry. Fit preprocessing only on training
data. Select on tuning, calibrate on its independent subset, then freeze the
selected model/config and reserve the final test according to the model entry
point. The model-comparison notebook reads saved reports; it is not a reason to
reopen the final test or select the best test score.

For ranking retain the temporal cutoffs, exact eligible user/item IDs, K,
positivity threshold, candidate universe, negative sampling seed/definition,
seen exclusions, cold/empty handling and training-only popularity. A sampled
study needs sampled labels in every result table; it cannot be relabelled
full-catalogue merely because its inputs came from MovieLens32M.

For grounding retain the allowed catalogue/evidence snapshot, query/task
expectations, actual retrieved IDs/revisions, human claim decisions and
reviewer/adjudication information. For speech retain permitted audio identity,
reference transcription/normalization, actual model hashes and per-language
support; do not include private audio in a public bundle by default.

## 3. Record the complete reproducibility identity

Each real result needs:

1. An immutable run/evidence ID, actual UTC timestamp and operator; report
   user-facing dates in Asia/Calcutta as well.
2. Repository revision plus current source hashes. If the working tree is dirty,
   a commit ID alone does not describe the demonstrated code. Preserve the
   user's existing changes; no automatic staging/reset/restore/commit is part
   of the freeze procedure.
3. Selected interpreter and actual resolved dependency/lock versions, OS,
   Java/Scala/Spark compiler/build/JAR identity and executed command. A planned
   requirements file is not an installed lock or a successful import check.
4. Source/raw/processed/split/canonical-registry hashes and permission records,
   with exact leakage-group, label, taxonomy and normalization versions.
5. Model/base/tokenizer/checkpoint/config/calibrator hashes, license/revision,
   serving decision, language scope and genuine training/evaluation reports.
6. Device/precision/batch/sequence/accumulation/loader settings, actual RAM/VRAM,
   elapsed/throughput scope, seeds and any nondeterminism or OOM recovery.
7. Scoring minimums/prior/shrinkage/weight/model/method versions; recommendation
   candidate/channel/normalization/diversity policies; stream event/checkpoint/
   sink versions and current review revisions.
8. Result fields and denominators, skipped/failed/unavailable cases, selection
   decisions, limitations and human review. Keep failures as well as successes.

## 4. Execute and register evidence deliberately

The generated `scripts/evaluate_all.ps1`/`validation.runner` expose a plan before
execution and separate unit, PostgreSQL, browser, benchmark, parity, grounding
and evidence groups. Inspect their current help/configuration for exact opt-in
switches. The runner does not make a model evaluation genuine by wrapping it;
actual approved component reports must already exist or be explicitly produced
through their own governed entrypoints.

`validation.evidence` registers actual reports with identity/hashes and review
metadata. `validation.reporting` consolidates measured claims; null/missing
metrics remain unavailable. `validation.parity` consumes genuine matched
exports, and `validation.grounding` consumes actual human judgments. Read the
current schema/config examples before supplying input; example false approvals
and null paths are intentional blockers, not data to fill with fictional values.

Store each run in a fresh path chosen by the tool/configuration and preserve the
printed manifest/report identity. Never overwrite an earlier report to make a
failure disappear. A human must verify that a report's claim is warranted,
not merely that its JSON parses or its file hash matches.

## 5. Reconcile integration snapshots

Stop changes to the evaluated review snapshot while making a parity claim.
Match canonical IDs, latest review revisions, deletion/consent status, approved
model/policy version, effective weighting, target type and event input before
comparing Python, Scala, database and streaming outputs. State numeric
rounding/tolerance and distinguish a methodological mismatch from a timing lag.
Different methods or in-flight revisions are not expected to agree by chance.

Rehearse duplicate requests, concurrent revision conflicts, worker crash/retry,
late/out-of-order/conflicting events, deletion and restart with new isolated
output/checkpoint paths. Preserve conflicting inputs/reports for review rather
than deleting raw records. Never claim end-to-end exactly-once without evidence
for the entire source-through-sink protocol.

## 6. Curated bundle and release review

Use `scripts/prepare_evaluation_bundle.ps1`/`validation.bundle` only with an
explicit reviewed allowlist and a new destination. Default selection must not
include `.env`, credentials, private review/audio text, DB dumps, raw datasets,
virtual environments, node_modules, caches, restricted artwork or unlicensed
weights. A small file is not automatically shareable. Metadata filenames/paths
can themselves disclose personal information and need review.

The intended shareable bundle comprises selected source/docs, reviewed license
notices, sanitized environment/version manifests, approved model/dataset cards,
genuine metric/test reports, source/config hashes and specifically permitted
screenshots. Keep weights/raw/private material in a separate access-controlled
local archive if their rights allow it. Hash/signature verification establishes
file identity, not the truth of a scientific claim or a right to redistribute.

Before sharing, check the exact bundle manifest against
[LICENSES_AND_ATTRIBUTION.md](../../LICENSES_AND_ATTRIBUTION.md), verify report
values/IDs against [RESULTS_TEMPLATE.md](RESULTS_TEMPLATE.md), and review all
selected logs/screenshots for secrets or copyrighted/private content. Do not
stage the entire workspace or historical deletions as a release checkpoint.

## 7. New-terminal reproduction and offline rehearsal

On the user's already prepared machine, reproduce from a fresh terminal using
the explicit root Python and selected Java/Spark/Node paths. Check current
headroom, required ports, exact artifacts and schema readiness. Start services
deliberately through the through-11 launch scripts; no validation command may
silently install dependencies or train a model to rescue missing prerequisites.

Rehearse the real movie journey with cached metadata/artwork/weights/tokenizers
and optional speech. Offline environment variables prevent some library fetches
but do not prove no network requests. The operator chooses and records the
actual network isolation/observation method; source generation never changes
Windows networking/firewall settings. API documentation CDN assets, browser
extensions and other non-core resources must be assessed separately from core
AI inference. Text input and honest asset/model-unavailable states remain useful
failure paths but do not replace a successful required journey.

Record startup, complete-journey and recovery durations only after measuring
them. A later source/model/config change invalidates the affected acceptance
claim until relevant checks are repeated. State remaining failures instead of
declaring a frozen source tree universally reproducible.
