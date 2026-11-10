# Current limitations and acceptance boundaries

Prepared 10 November 2026, Asia/Calcutta. These are limitations of the inspected
source and current evidence, not reasons to fill gaps with synthetic reviews,
guessed IDs or attractive metrics. The latest request authorizes Phase12/13
source generation; it does not authorize executing training, tests, migrations,
services, downloads or new runtime experiments.

| Area | Current limitation | Required closure evidence |
|---|---|---|
| Full phase acceptance | Source generation is ahead of executed acceptance in several earlier phases | Actual dependency-ordered acceptance; do not mark Phase1/2 complete from later files |
| Rights and canonical mapping | Local data audit/provisional maps do not approve review rights or external movie joins | Reviewed source permissions, conflict quarantine and approved internal registry |
| Genuine annotations | Neutral/aspect/theme/language/sarcasm studies require real adjudicated movie-linked labels | Frozen legitimate manifests, support, annotator agreement and split/leakage report |
| IMDb scope | Binary benchmark cannot provide neutral labels or reliable application movie IDs | Separate binary results and separate genuine domain three-class training/evaluation |
| Installed environment | Last observed backend distribution metadata was missing in the selected Python; a changed torch build needs fresh CUDA validation | Manual prerequisite preparation, native imports, actual driver/build/tensor/precision checks and current resources |
| Laptop fit | Nominal16GB RAM/8GB VRAM is not free capacity; older RAM/disk snapshots were low | Current headroom and measured peak usage, one heavy workload at a time |
| NLP quality | Source/config/model-card templates are not trained/evaluated artifacts | Approved actual training and final held-out reports bound to exact hashes |
| Multilingual/informal coverage | A configuration language list, script observation or tokenizer vocabulary does not prove coverage | Human-labelled subgroup supports and held-out metrics; unsupported cohorts stay unavailable |
| Sarcasm | Independent diagnostic does not implement validated learned sentiment fusion | Prespecified fusion/ablation with independent/out-of-fold signals, if pursued |
| Aspects | Explicit extraction and target polarity can fail/truncate or miss implicit aspects | Exact span/window/category and full-pipeline evaluation; separate scheme for implicit targets |
| Themes/genre reception | Movie metadata themes and review theme mentions do not establish target audience polarity | Actual target-specific sentiment evidence/model and reviewed score policies; absent reception stays null |
| Topic models | Exploratory clusters can be unstable; optional BERTopic is not assumed installed/fitted | Actual versioned fit, stability/curator review and clear exploratory labeling |
| Summary generation | Extractive evidence is the default; local novel candidates can invent or omit claims | Snapshot-bound human factuality approval and separate coverage/contradiction evaluation |
| Summary metrics | ROUGE/BERTScore require permitted references and locally prepared metric/model dependencies | Actual reference rights, metric version and scores; no proxy invented values |
| Risk analysis | Bounded consenting text corpus and available behavioral data cannot prove authenticity | Legitimate labeled evaluation, subgroup/false-positive review and human moderation; no sentiment extremity feature |
| Audience representativeness | Opt-in submitted reviews may not represent all viewers; review-bootstrap intervals omit model error and selection bias | Counts, inclusion policy, uncertainty assumptions and explicit observational scope |
| Model administration | Registry admission exists; full revocation/rebuild and affected-export reconciliation still need verification | Deliberate registry operations, current prediction/vector/snapshot/event invalidation and rehearsed rollback |
| Consent/deletion | Current application review deletion/invalidation is not automatic erasure from prior exports/backups/checkpoints | Owner-approved retention/export withdrawal/retraining or unlearning policy and executed reconciliation |
| Recommendation candidates | Online source caps catalogue work at5000; current Scala ranking samples users/negatives | Prepared strategy for larger catalogues and correctly labelled candidate/universe evaluation |
| Cold application users | MovieLens identities cannot be borrowed; optional factor fold-in is separately reviewed | Real user consent/profile handling, approved fold-in protocol if used and cold-cohort measurements |
| Hybrid policy | Example channel weights are null/unvalidated | Actual validation-selected weights/interaction policy and prespecified channel ablations |
| ALS fallback | Sampled Scala cold candidates use a disclosed train-popularity scale | Actual fallback normalization/quality analysis; do not interpret mixed raw scale as calibrated taste probability |
| Query NLU | Current analytical English rules cover specified forms, not arbitrary language/paraphrases | Human query/intent/entity/constraint tests and documented supported grammar |
| Mood/pace | Positive target reception is not objective pacing speed or a guarantee of emotional experience | Validated proxy/threshold and explanation, or explicit unavailable/clarification |
| Context | Bounded private context can still misinterpret unsupported follow-ups | Ownership, expiry/limit/reset, ambiguity and negation tests with actual data |
| Voice | Optional cached CPU model, codecs, permissions, duration/memory/latency and WER are untested | Actual permitted audio/ground truth, no-network run and text fallback tests |
| Streaming lag | DB invalidates edits immediately, while Spark may retain old evidence during pending/unavailable reanalysis | Matching final revisions/snapshots and explicit replay/deletion/reconciliation/lag tests |
| Delivery semantics | Atomic files/checkpoints/idempotent source logic are not an end-to-end exactly-once proof | Actual source-through-sink crash/replay/conflict/late-event evidence |
| RDD/DF parity | Inspected RDD tag tokenizer normalizes punctuation while a DF demonstration uses whitespace tokens | Match tokenization before asserting numerical equivalence; preserve user edits and report actual differences |
| SQL/vector performance | Static ORM-column parity does not execute migrations/constraints; exact vector search is not an optimized ANN claim | Disposable PostgreSQL migration/query tests and measured plans/recall/latency before adding indexes |
| UI behavior | Type checking does not render pages or prove responsive/accessibility/offline behavior | Real-service desktop/mobile/keyboard/browser tests, builds and failure states |
| Production security | Local opaque bearer sessions and loopback defaults do not constitute public production hardening | Separate public-deployment threat/credential/transport/operational review before any release |
| Syllabus completeness | Core source covers selected topics; POS/NER/HMM/CRF/graph/translation exercises are not all present | Exact inspected/executed coursework evidence, or honest not-implemented rows |
| Academic results | Report/slide/checklist templates have no measured model/runtime values | Evidence-linked numbers and truthful limitations after the user executes the approved studies |

No saved historical compile, CUDA check, data count, static parser report or
legacy metric should be represented as a current end-to-end result. Preserve
the historical artifact and its source/environment fingerprint. When a later
run fails, record it as failed and retain the failure's scope; do not silently
substitute a previous successful run.

For a final claim, state what was implemented, what was executed, the exact
support/snapshot, what failed or was unavailable, and how that limits the
conclusion. Use the validation/evidence tooling and human review rather than
an unqualified statement that every feature is complete.
