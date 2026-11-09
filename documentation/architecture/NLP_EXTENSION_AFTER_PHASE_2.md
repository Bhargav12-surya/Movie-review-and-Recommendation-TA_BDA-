# Mandatory NLP extension — scheduled after Phase 2

Accepted instruction: the user requested integration after Phase 2 and supplied
the extension on 9 November 2026, Asia/Calcutta. It is part of the existing
project, not a separate product. Current Phase 1 work continues first; no model
weights, datasets or language services are fetched by recording this plan.

## Timing and specification updates

After Phase 2 passes its execution/evidence gate, update ARCHITECTURE.md,
IMPLEMENTATION_PLAN.md and AGENTS.md with this extension and a versioned Phase 1
language/annotation addendum. Preserve completed work and original audit
snapshots. Record actual progress in IMPLEMENTATION_STATUS.md.

Do not skip missing-data, environment, license or training-approval gates.
The present English binary benchmark remains a separate baseline.

## Required language behaviour

Support English, Hindi Devanagari, Romanized Hindi and Hinglish/code-switching
only to the extent demonstrated by legitimate training and subgroup evaluation.
Preserve slang, emojis, emoticons, expressive punctuation, negation, contrast,
spelling variants and repetitions as contextual signals. Do not assign universal
word/emoji polarity. Do not reverse sentiment mechanically when sarcasm is
predicted.

Preserve original Unicode text separately from normalized/transliterated views.
Original aspect spans use Python Unicode code-point [start,end) offsets;
frontend UTF-16 indexing requires an explicit conversion when implemented.
Hindi combining characters, variation selectors and emoji sequences make
untracked normalization unsafe. Any optional transliteration/translation must
retain alignment and be evaluated rather than applied to every review.

Mixed overall polarity requires the approved three-class policy. Target-specific
acting/story/aspect opinions remain separate even in one code-mixed sentence.
Ambiguous sarcasm and uncertain language need explicit uncertainty/unsupported
states, not fabricated confident labels.

## Phase integration

| Phase | Required extension |
|---|---|
| 1 addendum | Version language/script/mixedness annotations, consent/provenance, slang/emoji/sarcasm tags, duplicate groups and dedicated held-out Hinglish movie reviews; never fabricate labels/translations |
| 3 | Compare English DistilBERT, multilingual baseline and fine-tuned multilingual model, emoji-aware processing and independently validated sarcasm/multitask signal |
| 4 | Train/evaluate multilingual aspect spans and target-conditioned sentiment; maintain original offsets |
| 5 | Evaluate multilingual embeddings and grounded summaries; abstain where checkpoint/language support is unvalidated |
| 7 | Use validated calibrated probabilities; retain minimum evidence and separate language uncertainty |
| 9 | Version language/model/sarcasm/uncertainty metadata in real inference APIs |
| 10 | Unicode-aware input/display, supported-language notices and appropriate uncertainty states |
| 12 | Cross-language, slang, emoji, negation, sarcasm and mixed-aspect integration tests |
| 13 | Held-out subgroup metrics, model comparisons, ablations and honest limitations |

Candidate multilingual families include XLM-RoBERTa and MuRIL. License,
tokenizer/script support, actual memory, local runtime and held-out performance
must be checked after Phase 2 before selection or weight-download approval.
Prefer one validated deployed multilingual model over unnecessary simultaneous
large models. Keep the English baseline for comparison.

## Required modular source and experiments

Create ml/informal_language/{preprocess,emoji_processing,slang_normalization,
transliteration,language_detection,evaluate}.py,config.yaml,README.md;
ml/multilingual_sentiment and ml/sarcasm each get train.py,evaluate.py,
predict.py,config.yaml,README.md and model_card.md.

Create notebooks informal_language_analysis,hinglish_sentiment_analysis,
sarcasm_detection,emoji_sentiment_analysis and multilingual_model_comparison.
Reuse shared data, calibration, checkpoint/resume and resource utilities.
Artifacts stay separate from source code.

## Data and evaluation gates

The user supplies all data manually. Require genuine three-class English/Hindi/
Hinglish labels, movie-domain aspect spans/polarity, sarcasm/irony annotations,
emoji-bearing examples and a human-labelled Hinglish movie test subset.
Social-media resources, if later considered under the user's instruction,
need license/domain/label audits; they do not substitute for movie-domain
evaluation. Do not invent neutral, sarcasm or translated labels.

Report actual supports and accuracy,macro-F1,per-class precision/recall,
confusion matrices,calibration,span/aspect F1,sarcasm precision/recall/F1,
latency and RAM/VRAM for English,Hindi,Romanized Hindi,Hinglish,slang-heavy,
emoji-heavy,sarcastic English/Hinglish and mixed-aspect cohorts. Evaluate
optional transliteration,emoji processing and sarcasm signals through ablation.
The supplied examples are candidate test prompts requiring human validation,
not benchmark measurements or a keyword lookup specification.

Train one substantial Transformer at a time on the 8 GB GPU. Use validated mixed
precision,small batches,accumulation,dynamic padding,early stopping,resume and
memory monitoring. Downloads and substantial training need separate approval.

## Current status

Requirement accepted and queued. No multilingual/sarcasm model is trained,
selected,downloaded or integrated yet. Existing Phase 1 validators already retain
original Unicode text and code-point span offsets; this does not establish
Hindi/Hinglish sentiment capability.
