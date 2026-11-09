# Informal and multilingual input handling

Status: source generated; no sentiment/language/sarcasm capability is claimed.

preprocess preserves an immutable original and code-point alignment for optional
feature views. Identity is the default. Symbol removal is a controlled ablation;
slang expansions require a reviewed supplied mapping. Original aspect offsets
must always refer to the original text. utf16_offset bridges browser indexing.

emoji_processing observes conservative Unicode symbol runs, not a complete
Unicode grapheme/emoji parser and never a universal polarity table. Flags,
combining characters,ZWJ sequences and presentation variants need corpus tests.
language_detection reports scripts separately; Latin text cannot distinguish
English,Romanized Hindi or Hinglish. Without a reviewed trained detector, language
status is unavailable. Caller/source language metadata must remain explicit.

slang_normalization locates expansions,repetitions and configured negation/contrast
cues. These are observations, not sentiment labels. transliteration requires an
explicit reviewed local adapter returning validated original-text alignment;
no translations or transliterations are fabricated by default.

evaluate compares actual held-out reports with identical tasks/manifests. The
notebooks define controlled emoji,transliteration and sarcasm experiments. There
are no populated results. Preserve this distinction when presenting the project.
