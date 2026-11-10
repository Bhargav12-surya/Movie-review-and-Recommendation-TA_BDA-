# Data purposes, consent and retention record

Prepared 10 November 2026, Asia/Calcutta. This describes the inspected local
source and the policy decisions the owner must complete. It is not a claim that
all export, account deletion, backup or model-unlearning workflows already
exist. Do not infer permission from local file presence or from `source=user`.

## Separate purposes

| Data/action | Purpose and current source behavior | Owner record / limit |
|---|---|---|
| Registration/sign-in | Local account email/display name and Argon2 password hash; random session token is hashed for storage | Local authentication is not verified real-world identity or consent authenticity; no default admin |
| Publishing a review | Authenticated owner submits original Unicode text linked to a validated canonical movie ID | Explain that published review text is visible; no consent to unrelated purposes is implied |
| Audience evidence | `evidence_permitted` controls inclusion in eligible score/summary evidence | Retain consent version, current revision, moderation/deletion state and reviewed score policy |
| Research training | `training_permitted`, separate and initially false | Manual dataset eligibility/annotation/rights review still required; no automatic training occurs on submission |
| Similarity moderation | `moderation_permitted`, separate and initially false | Current online risk compares a bounded consenting corpus; no unsupported behavioral identity or sentiment-extremity feature |
| Personalization | Preference permission controls use of rating/preference/history channels; withdrawal removes stored interactions in current source | Stored explicit ratings/watchlist are separate user records; disabling personalization must not be described as deleting them |
| Voice | User selects microphone, browser records bounded audio, authenticated local STT may return text | No continuous recording or application-level durable audio store is intended; multipart/browser/OS temporary handling is not a secure-erasure guarantee |
| Annotation/evaluation | Human labels, source identities, permission/provenance and fixed split/group records | Use genuine adjudicated data and purpose-specific permission; synthetic fixtures stay isolated |
| Sharing reports/screenshots | Curated evidence only after separate distribution review | Publication permission for a live review does not automatically permit redistribution in a dataset, screenshot or model-training bundle |

## Current revision and deletion behavior

Edits use authenticated ownership and an expected revision. New revisions
invalidate movie score/summary snapshots, remove old prediction/vector records
and enqueue current analysis. Withdrawing training permission marks retained
revision records ineligible for future training selection. Review deletion
scrubs current text and stored revision/prediction/vector rows and publishes a
text-free deletion event through the outbox. The worker must not revive an older
in-flight revision. Rehearse these behaviors against the exact source; a static
description is not a proof of correct concurrent execution.

Public live DB invalidation does not erase already-created private exports,
Spark sinks, backups, evaluation references, external copies or trained model
parameters. A review withdrawal must trigger an operator inventory of affected
artifacts and a documented retention/withdrawal/retraining decision. Do not
claim certified model unlearning or account erasure without an implemented and
executed process. Current account deletion/export policy and a complete
moderation appeal process remain owner/engineering decisions.

The streaming view may lag while an edited review's new analysis is pending or
unavailable. Check the final current revision/deletion flags in the DB,
published events, batch/stream outputs and any external evidence exports before
asserting that withdrawal is fully reflected. Risk corpus-derived signals may
also require refresh/review after source eligibility changes.

## Retention decisions to complete

Record an actual owner, policy version, purpose, retention period and deletion
method for account/session records, original reviews/revisions, predictions,
interactions, chat turns/context, annotations, audio references, logs, model
checkpoints, reports and backups. No retention duration is invented here.
Current chat source bounds context by40turns/24hours and supports clearing a
conversation; an expiry check is not automatic physical cleanup of every old
row. Keep that distinction visible in the user's privacy notice.

For each export list its included review IDs/revisions/hashes, permission
snapshot, destination/access control, who may use it, redistribution terms and
how a later withdrawal is handled. A data hash can reveal linkage and is not a
guarantee of anonymity. Minimize personally identifying metadata in shareable
reports; preserve private mapping records only where necessary and permitted.

## Secret-safe operation

Keep database credentials in private backend configuration and never in source,
frontend `NEXT_PUBLIC_` variables, command arguments, screenshots or result
files. Do not print full environment dumps or raw authenticated requests.
Opaque session tokens remain in browser memory in the current UI; refresh signs
the user out. Logs should retain only necessary job/status/error identities,
not password/token/review bodies. Review test failure output, browser captures
and SQL exceptions before sharing because they may contain private content.

The default local HTTP/loopback setup is intended for the laptop. A public
deployment needs a separately reviewed transport, account, credential,
authorization, upload, abuse and operational policy; no publication is performed
by this source handoff. The generated evidence bundle uses explicit permission
allowlists, not automatic collection of all data or environment files.

## Fair moderation and human review

A strong positive/negative opinion is not evidence of deception. Similarity,
anomaly or risk-index output is a signal with a disclosed corpus/model scope.
Do not label a user fake or automatically suppress a genuine review based on an
unvalidated index. If real moderation decisions are made, record the human
review, reason, source evidence, uncertainty and a way to correct/appeal the
decision. Evaluate false positives across legitimate language/source groups
when labels exist. Without those labels, accuracy/PR-AUC/FPR remains unavailable.

## Publication review record

For each shareable artifact record: artifact path/hash, data/model/software
license or consent reference, permitted purpose/audience, included personal or
copyrighted content, required attribution, exclusions/redactions, reviewer,
decision/date and expiry/withdrawal requirements. Blank examples do not grant
permission. Link the final decisions from the curated manifest and
[LICENSES_AND_ATTRIBUTION.md](../../LICENSES_AND_ATTRIBUTION.md).
