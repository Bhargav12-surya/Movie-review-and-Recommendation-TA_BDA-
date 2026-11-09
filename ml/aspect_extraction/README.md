# Explicit aspect extraction

Generated source; no trained checkpoint or measured capability. The BIO taxonomy uses O plus B/I for sixteen movie aspects. Fast-tokenizer offsets address unchanged Unicode originals. Special/pad tokens use -100; partial boundary spans are masked, and every gold span must fit a complete window. Inference repairs invalid I starts as B, discards uncertain window-edge spans and merges overlapping candidates deterministically. These policies need actual tokenizer/model tests.

Training, evaluation and prediction delegate to ml/aspect_common. No keyword extraction is used as a final prediction. Token confidence is uncalibrated; exact span F1 and end-to-end target/polarity F1 are required. Implicit aspects and overlapping gold spans remain unsupported under the current annotation scheme. See documentation/phase4/RUNBOOK.md.

