# Language and informal-review annotation addendum v1

Status: generated specification,not human annotations or an approved label policy.
Prepared9 November2026,Asia/Calcutta.

Retain the Phase1 consent,canonical linkage,original text/hash,review revision,
annotator/adjudicator and split-group contracts. Add independently annotated
language_code,languages,script,code_mixed,slang_present,emoji_present,sarcasm,
sarcasm_confidence/missingness and cohort tags. Keep unknown/unresolved values
explicit; never guess Hinglish from Latin characters or neutral from uncertainty.

| Field | Meaning |
|---|---|
| language_code | en,hi,hi-Latn,mul or unknown under the reviewed protocol |
| languages | Human/source-supported languages,for example en and hi for code mixing |
| script | Latin,Devanagari,Mixed,Other or unknown; distinct from language |
| sarcasm | Independent not_sarcastic/sarcastic annotation or unresolved; not sentiment polarity |
| slang_present,emoji_present | Annotated context characteristics; no default positive/negative meaning |
| cohorts | Explicit human/source strata used for subgroup evaluation |
| group_id | Frozen duplicate/source/movie/reviewer cluster,not a guessed language label |

Required cohorts include English,Hindi Devanagari,Romanized Hindi,Hinglish,
slang-heavy English,emoji-heavy,sarcastic English,sarcastic Hinglish and
mixed-aspect reviews. Report overlap and actual supports; cohorts are not assumed
mutually exclusive. Preserve a dedicated human-labelled Hinglish movie test
subset. Social-media data,if later supplied,requires independent permission/domain
review; it does not establish movie-domain performance.

Overall negative/neutral/positive stays negative0,neutral1,positive2. Equally
mixed,ambiguous sarcasm,irrelevant and unsupported-language cases need adjudication
under the approved policy. Do not silently turn these into neutral. Sentiment
and sarcasm agreement are measured separately. Do not infer sarcasm labels from
emoji or punctuation. Use two annotators on an overlapping subset and document
support,agreement and adjudication rather than fabricating kappa values.

Aspect spans remain [start,end) Python Unicode code-point offsets into the original
unchanged text. Normalized/transliterated views require alignment and separate
hashes. Browser UTF16 positions need conversion. Target-specific aspect sentiment
must not copy the overall review label. Combining marks/ZWJ/variation selectors
need regression fixtures; an emoji glyph is not necessarily one code point.

Source/preprocessing/annotation/split versions and permissions follow every
derived artifact. A missing neutral,Hindi,Hinglish or sarcasm source blocks the
corresponding fit/evaluation. It does not authorize synthetic replacement data.
