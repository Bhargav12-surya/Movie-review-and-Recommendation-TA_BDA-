# sarcasm model card

Status: **not trained; no performance measurements**.

- Task: sarcasm.
- Architecture/checkpoint/revision: user-supplied local licensed encoder; pending selection.
- Dataset/license/consent: pending approved human/source records and frozen hashes.
- Label policy: versioned fixed map; neutral/mixed/uncertain remain distinct policy questions.
- Splits: disjoint train,tuning,calibration,test with source/duplicate/movie/reviewer grouping.
- Training: configuration starts at length128, micro-batch2, accumulation8; no executed claim.
- Evaluation: accuracy, per-class and macro/weighted F1, confusion matrix,NLL,Brier,ECE;
  human-labelled language/slang/emoji/sarcasm/mixed-aspect cohorts and support counts.
- Hardware/latency/VRAM/checkpoint-resume measurements: not measured for this model.
- Limits: pretrained knowledge does not establish movie-domain,Hinglish or sarcasm accuracy;
  truncation may omit the end of a long review; subgroup and ablation tests are required.
- Deployment: no registered production artifact. Generated training artifacts remain experimental.
- Prohibited interpretation: metadata/rating/recommendation similarity is not audience sentiment;
  a sarcasm prediction does not justify flipping sentiment or assigning fake-review risk.

Populate this card from actual saved reports after authorized execution; retain limitations.
