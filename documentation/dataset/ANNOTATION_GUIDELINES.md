# Annotation contract and proposed guidelines

Status: schema/validation workflow implemented; human annotation and policy
approval pending. This document creates no labels.

Only permitted, consented reviews with a validated application movie ID may
enter the three-class or aspect/theme datasets. MovieLens ratings/tags and the
binary IMDb benchmark cannot supply invented neutral labels or linked audience
reviews. Synthetic fixtures remain in tests.

## Review and permission records

Retain review_id, review revision, original review_text, its SHA-256,
language_code, UTC timestamp, source and consent/terms provenance. The approved
canonical movie registry must explicitly identify valid application IDs;
movielens:<id> provisional keys are not approved application identities.

For first-party material, record the consent version and permission to use the
content for the relevant purpose. Third-party material needs a source/license
record covering the intended use. A source=user string is insufficient.
Review deletion or consent withdrawal invalidates affected derived datasets,
predictions, vectors, summaries and score snapshots according to policy.

## Overall sentiment proposal

The final label map is negative 0, neutral 1, positive 2. Positive expresses an
overall favourable evaluation; negative an unfavourable evaluation. Neutral
requires a defined factual/non-evaluative/balanced policy.

Do not force uncertain, irrelevant, unsupported-language or equally mixed
reviews into neutral automatically. Annotators flag these for adjudication.
The exact mixed-to-three-class policy must be approved before labels are
finalized. The separate IMDb task remains binary negative 0/positive 1.

## Aspects and evidence

The starting taxonomy is Acting, Story, Screenplay, Direction, Characters,
Cinematography, Visual effects, Editing, Pacing, Music, Sound design, Dialogue,
Worldbuilding, Emotional impact, Originality and Runtime.

Annotate only an aspect actually expressed in the review. Preserve original
Unicode character offsets using the half-open convention [start,end), so that
review_text[start:end] exactly equals the recorded evidence. Do not normalize
or strip text before validating offsets. Store the review text hash and revision
with each annotation.

Explicit aspect spans support BIO token classification. Record implicit
categories separately; they do not create fictional token spans. Different
aspects in one sentence can have different sentiments. Use target-specific
positive/negative/neutral labels; mixed aspect opinions require the explicitly
approved mixed policy. Do not copy overall sentiment onto all aspects.

## Themes and reception

Keep story-theme relevance, review-theme mentions and theme-specific audience
sentiment as separate fields. Metadata relevance is not evidence that audiences
liked a theme. Theme reception annotations require target-specific textual
evidence and an independently reviewed polarity label.

## Agreement and splits

At least two annotators independently label an overlapping subset. Compare
matching review revisions and annotation targets, report overlap/support,
observed agreement and Cohen's kappa where defined, then adjudicate conflicts.
Kappa is undefined when its denominator is zero; report null with a reason.
Do not claim that agreement proves ground-truth correctness.

Freeze duplicate/near-duplicate and appropriate movie/reviewer groups before
train/validation/test assignment. Related revisions share one group. Fit
vocabularies, feature transforms, calibration and thresholds on training or
validation data as appropriate, never on the final held-out test.

## Local workflow

Supply the original text, canonical registry and permitted review/annotation
exports under data/raw. The prepare_annotations.py and preprocess_reviews.py
commands validate them and write only explicitly requested fresh outputs.
Rejected metadata is retained separately without logging private review text.
Schemas in schemas/datasets describe the executable contract.
