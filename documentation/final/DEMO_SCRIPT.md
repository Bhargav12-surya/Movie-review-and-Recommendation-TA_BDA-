# Academic demonstration script

Prepared 10 November 2026, Asia/Calcutta. This is an unexecuted rehearsal plan.
Do not mark it passed until the named journeys have been observed on the laptop
with the exact frozen source, data and model artifacts being submitted.

## Preparation before evaluation day

- [ ] Close the data rights, canonical mapping, genuine annotation and held-out
  evaluation requirements in the earlier phase runbooks.
- [ ] Record the final source revision/fingerprints, exact installed dependency
  versions and resolved lockfiles.
- [ ] Cache permitted metadata, artwork, model/tokenizer files and optional speech
  weights locally. Review required attribution for the actual assets in use.
- [ ] Preserve the original raw datasets. Back up the permitted database and
  selected model/evaluation artifacts without exposing private reviews/secrets.
- [ ] Run actual disposable-DB/API/browser tests and retain failures as well as
  successful reports. A historical test report does not validate changed source.
- [ ] Select real catalogue movies for a rich-evidence case, a no-evidence case,
  a semantic-neighbour case and an ambiguous-title case. Record their canonical
  IDs in the private rehearsal notes; do not invent example mappings.
- [ ] Freeze reviewed scoring thresholds, target policies, language scopes and
  hybrid weights. Confirm that those versions match the saved real results.
- [ ] Choose a permitted live review example. Consent and publication permission
  must be explicit. Strong sentiment is not evidence of a fake review.
- [ ] Stop training. Do not run a large Spark job alongside the complete stack.
- [ ] Rehearse with network access unavailable by the user's choice. Verify actual
  cached operation; do not claim that browser speech recognition is offline.
- [ ] Measure real startup time and RAM/VRAM headroom on this laptop.

## Demonstration sequence

The sequence is an outline, not a promise of a measured duration. Use the real
catalogue and exact supported phrases when rehearsing.

| Step | Demonstrate | Evidence to point to | Failure behavior to show honestly |
|---|---|---|---|
| 1 | Open localhost:3000 and search the imported catalogue | Actual movie title, source metadata and canonical ID through the API | Empty catalogue/error state if import or DB is missing |
| 2 | Open a detail page | Local poster if licensed/cached, synopsis, genres/runtime and independently labelled ratings | Poster fallback and nullable metadata |
| 3 | Explain audience intelligence | Review/effective counts, sentiment probabilities/distribution, model/method version and update time | Exact insufficient-review message instead of an invented prior score |
| 4 | Read the summary above individual reviews | Current snapshot and quoted review IDs/revisions | No summary or explicit unavailable state without evidence |
| 5 | Sign in and submit the permitted live review | Authenticated ownership, pending response, persisted ID/revision and worker state | Model absent becomes pending/partial/unavailable; never a fabricated class |
| 6 | Observe real trained sentiment and aspects | Actual probability triple and distinct aspect spans/target polarity | Unsupported language explicitly unavailable |
| 7 | Observe refresh | Current evidence version, new calculated timestamp and eligible count | A live new review may not meet minimum evidence or change the score |
| 8 | Change an explicit rating/genre/theme preference | Saved profile and separate personal recommendation explanations | Cold-start/missing-channel explanation without borrowing MovieLens identity |
| 9 | Open personalized recommendations/similar movies | Actual contributing model/content/preferences, seen-item exclusions and neighbours | Unavailable ranking or empty eligible set |
| 10 | Ask title, genre-intersection, similarity, aspect and comparison questions | Same catalogue/scores/evidence as detail pages | Unknown/ambiguous titles ask for clarification; absent opinions abstain |
| 11 | Ask a bounded follow-up, then clear the conversation | Preserved actual context and authenticated ownership | Unsupported phrasing requests a clearer title/filter |
| 12 | Select the microphone only on user action | Locally cached offline transcription and returned text, if configured | Permission-denied/model-absent state; text input always usable |
| 13 | Open the no-evidence movie | Metadata with null audience score | "Not enough audience reviews yet." |
| 14 | Edit/delete the submitted review or withdraw evidence permission | Revision conflict protection, stale-score/summary invalidation, removal from current evidence | No old prediction/snapshot revival |

Do not describe a predicted sentiment index as a user star rating, a theme
relevance score as audience reception, or a personalized match as public
consensus. Point out whether a summary is quoted extraction, pretrained model
inference or an actually fine-tuned model; those are different claims.

## Separate BDA segment

Stop or reduce the full stack if current free memory cannot support the small
approved Spark demonstration. Use [the BDA runbook](../bda/RUNBOOK.md), final
compiled Scala source and a fresh output/checkpoint directory. Start with the
synthetic isolated smoke fixture when explaining mechanics; explicitly label it
synthetic. Use the validated MovieLens inputs for the real data-processing
evidence. Never replace the real dataset evaluation with fixture counts.

- Show Scala ingestion schemas and the quarantine/quality reports.
- Show actual RDD operations and DataFrame joins/aggregations.
- Use `explain` and Spark UI to demonstrate laziness, actions, stages, partitioning,
  shuffles and caching; do not claim multi-machine speedup in local mode.
- Show genuinely saved MLlib ALS factors, exact configuration and temporal ranking
  evaluation. Do not retrain the full 32M model during the evaluation.
- Publish a valid new text-free review event and show an actual streaming
  micro-batch. Explain stable IDs, revision/deletion handling, checkpoint and sink.
- Show measured restart/replay evidence, including duplicates/conflicts/late events.
  A running query alone does not prove exactly-once delivery.
- Reconcile final application/batch/stream evidence snapshots before claiming
  numerical agreement.

## Academic evidence segment

Present the genuinely measured tables in [EVALUATION_REGISTER.md](EVALUATION_REGISTER.md).
Keep binary IMDb results separate from domain three-class results. Include neutral
support, language/Hinglish/sarcasm cohorts, exact-span and full aspect-pipeline
metrics, calibration, summary factuality, recommendation cold starts and actual
hardware measurements. If a cohort has no permitted ground truth, label its
metric unavailable and state the missing input.

Use [SYLLABUS_MAPPING.md](SYLLABUS_MAPPING.md) to connect each syllabus claim to
specific source plus executed evidence. Methods without measurements belong in
the limitations/future-work discussion.

## Recovery rehearsal

| Failure | Recovery procedure | Acceptance evidence |
|---|---|---|
| API stopped | Restart only the project API with the documented launcher; keep the database and worker state | Actual readiness plus persisted review lookup |
| Worker stopped | Restart the single leased worker; inspect queued/unavailable jobs and real revision-safe retry | No duplicate or stale publication |
| Database stopped | Restore the user-managed PostgreSQL service through its normal controls; recheck credentials privately | Readiness and read/write transaction recovery |
| Model or permission missing | Restore the exact approved local artifact or leave feature unavailable | Correct hash/scope and genuine later inference |
| Voice unavailable | Continue through permanent text input | Discovery query completes without microphone |
| Network unavailable | Use cached catalogue/artwork/checkpoints; show deliberate missing-asset fallback | No paid or external inference dependency |
| Spark memory pressure | Stop the Spark run through its owned process and use already saved genuine output; rerun later with measured headroom | Do not report the interrupted run as passed |

Do not delete raw data, reset Git, kill unrelated processes, disable security
controls or run automatic installers to rescue the demo. Record recovery time
only after actually measuring it.

## Rehearsal record

All fields below are **unmeasured / not executed** until filled from actual logs.

| Field | Current value |
|---|---|
| Rehearsal date/time and operator | Not recorded |
| Source/model/data/method/lock fingerprints | Not frozen for final execution |
| Startup and complete-journey duration | Unmeasured |
| Journey pass/fail and evidence paths | Not executed |
| Peak available/used RAM and VRAM | Unmeasured for the complete stack |
| Offline rehearsal and voice result | Not executed |
| Recovery result/time | Not executed / unmeasured |
| Reviewer and remaining issues | Pending |
