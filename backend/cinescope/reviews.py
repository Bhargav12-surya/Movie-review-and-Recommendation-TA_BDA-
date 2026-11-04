"""
Review analysis engine — production-grade sentiment analysis.

Features:
- Multi-tier sentiment scoring (transformer → TF-IDF → lexicon)
- Intensity-weighted lexicon with 270+ sentiment words
- Bigram/trigram phrase detection (70+ positive, 50+ negative)
- Degree modifier handling (amplifiers + dampeners)
- Emoji & emoticon sentiment scoring
- Sarcasm marker detection with confidence penalty
- Advanced negation handling (up to 4-word window, contraction-aware)
- Clause-level mixed-sentiment decomposition
- Per-clause confidence with evidence quality weighting
- Aspect-Based Sentiment Analysis (ABSA) with fine-grained scoring
- Hardened authenticity screening (gibberish, templates, punctuation, length)
- Review quality metrics (helpfulness, detail, coherence)
"""
from __future__ import annotations
import html
import json
import math
import os
import re
import string
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Optional
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TAXONOMY = json.loads((ROOT / 'data/taxonomy.json').read_text(encoding='utf-8'))
ASPECTS = TAXONOMY['aspects']
POS = set(TAXONOMY['positive'])
NEG = set(TAXONOMY['negative'])
POS.update({'like', 'liked', 'recommend', 'fine', 'decent', 'okay', 'ok'})
NEG.update({'dislike', 'disliked'})
POS_INTENSITY = TAXONOMY.get('positive_intensity', {})
NEG_INTENSITY = TAXONOMY.get('negative_intensity', {})
DEGREE_MODS = TAXONOMY.get('degree_modifiers', {})
AMPLIFIERS = DEGREE_MODS.get('amplifiers', {})
DAMPENERS = DEGREE_MODS.get('dampeners', {})
POS_BIGRAMS = TAXONOMY.get('positive_bigrams', {})
NEG_BIGRAMS = TAXONOMY.get('negative_bigrams', {})
EMOJI_SENT = TAXONOMY.get('emoji_sentiment', {})
SARCASM_MARKERS = TAXONOMY.get('sarcasm_markers', [])
NEGATORS = set(TAXONOMY.get('negators', [
    'not', 'no', 'never', 'hardly', 'barely',
    "isn't", "wasn't", "didn't", "don't", "wasnt", "isnt"
]))
NEGATORS.update({'cannot', "can't", 'cant'})
BUT_CONJUNCTIONS = set(TAXONOMY.get('but_conjunctions', [
    'but', 'however', 'although', 'yet', 'though'
]))
SPAM_PATTERNS = TAXONOMY.get('spam_patterns', [])

# Pre-compile expensive regexes
_HTML_TAG_RE = re.compile(r'<[^>]+>')
_WHITESPACE_RE = re.compile(r'\s+')
_TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")
_WORD_BOUNDARY_CACHE = {}
_URL_RE = re.compile(r'https?://\S+|www\.\S+', re.I)
_EXCESSIVE_PUNCT_RE = re.compile(r'[!?]{3,}')
_ALL_CAPS_WORD_RE = re.compile(r'\b[A-Z]{3,}\b')
_CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "\U00002764"  # ❤
    "]+",
    flags=re.UNICODE
)

# Maximum text length to prevent regex backtracking attacks
MAX_REVIEW_LENGTH = 50000
POSITIVE_THRESHOLD = 58.0
NEGATIVE_THRESHOLD = 42.0
_SOFT_NEGATORS = {'hardly', 'barely'}
_NEUTRAL_CUE_RE = re.compile(
    r"\b(?:okay|ok|average|so[- ]so|neither good nor bad|indifferent)\b",
    re.I,
)
_BALANCED_NEUTRAL_RE = re.compile(r'\bneither good nor bad\b', re.I)
_EXPLICIT_MIXED_RE = re.compile(r'\b(?:mixed feelings|both good and bad)\b', re.I)
_POSITIVE_IDIOM_PATTERNS = (
    (
        re.compile(
            r"\b(?:can(?:not|'t)|could(?:\s+not|n't))\s+recommend\b.{0,60}\benough\b",
            re.I,
        ),
        'cannot recommend enough',
        2.5,
    ),
    (
        re.compile(r"\b(?:could(?:\s+not|n't))\s+recommend\b.{0,60}\bmore\b", re.I),
        'could not recommend more',
        2.5,
    ),
)
_NEGATIVE_IDIOM_PATTERNS = (
    (re.compile(r'\bcould have been better\b', re.I), 'could have been better', 1.3),
    (re.compile(r'\bexpected (?:much )?more\b', re.I), 'expected more', 1.3),
    (re.compile(r'\b(?:barely|hardly) watchable\b', re.I), 'barely watchable', 1.6),
    (re.compile(r'\bnot worth (?:it|watching|seeing)\b', re.I), 'not worth it', 1.8),
)


def clean_text(text: str) -> str:
    """Sanitize HTML, normalize whitespace, and enforce length limit."""
    if not text:
        return ''
    text = unicodedata.normalize('NFKC', str(text))[:MAX_REVIEW_LENGTH]
    text = text.translate(str.maketrans({'‘': "'", '’': "'", '‛': "'"}))
    text = _CONTROL_RE.sub('', text)
    text = html.unescape(text).replace('<br />', ' ').replace('<br>', ' ')
    text = _HTML_TAG_RE.sub(' ', text)
    return _WHITESPACE_RE.sub(' ', text).strip()


def tokens(text: str) -> list[str]:
    """Extract lowercase word tokens from text."""
    return _TOKEN_RE.findall(text.lower())


def has_phrase(text: str, phrase: str) -> bool:
    """Check if a phrase appears as a whole-word match in text."""
    key = phrase.lower()
    if key not in _WORD_BOUNDARY_CACHE:
        _WORD_BOUNDARY_CACHE[key] = re.compile(
            r'(?<!\w)' + re.escape(key) + r'(?!\w)', re.I
        )
    return bool(_WORD_BOUNDARY_CACHE[key].search(text))


def clauses(text: str) -> list[str]:
    """Split text into clause-level segments for fine-grained analysis."""
    parts = re.split(
        r'[.!?;…\n]+|\b(?:' + '|'.join(re.escape(c) for c in BUT_CONJUNCTIONS) + r')\b',
        text, flags=re.I
    )
    return [s.strip(' ,\t\r\n') for s in parts if s and s.strip(' ,\t\r\n')]


def _extract_emojis(text: str) -> list[str]:
    """Extract all emoji/emoticon characters from text."""
    return _EMOJI_RE.findall(text)


def _emoji_score(text: str) -> tuple[float, int]:
    """Score emojis in text. Returns (total_score, count)."""
    emojis = _extract_emojis(text)
    if not emojis:
        return 0.0, 0
    total = 0.0
    count = 0
    for emoji_seq in emojis:
        for char in emoji_seq:
            if char in EMOJI_SENT:
                total += EMOJI_SENT[char]
                count += 1
    return total, count


def _bigram_score(text: str) -> tuple[float, int]:
    """Score bigram/trigram phrases. Returns (total_score, count)."""
    lower = text.lower()
    total = 0.0
    count = 0
    for phrase, weight in POS_BIGRAMS.items():
        if phrase in lower:
            total += weight
            count += 1
    for phrase, weight in NEG_BIGRAMS.items():
        if phrase in lower:
            total -= weight
            count += 1
    return total, count


def _detect_sarcasm(text: str) -> tuple[bool, float]:
    """Detect potential sarcasm markers. Returns (is_sarcastic, confidence_penalty)."""
    lower = text.lower()
    markers_found = sum(1 for m in SARCASM_MARKERS if m in lower)

    # Quoted sarcasm: positive words in quotes may indicate sarcasm
    quoted_positive = len(re.findall(r'"([^"]*)"', text))
    scare_quotes = 0
    for match in re.finditer(r'"([^"]*)"', text):
        quoted_text = match.group(1).lower()
        if any(w in POS for w in tokens(quoted_text)):
            scare_quotes += 1

    # Excessive exclamation after negative context
    exclamation_sarcasm = bool(re.search(r'(?:great|wonderful|amazing|brilliant)[\s]*[!]{2,}', lower))

    total_markers = markers_found + scare_quotes + (1 if exclamation_sarcasm else 0)
    if total_markers > 0:
        return True, min(0.4, total_markers * 0.15)
    return False, 0.0


def _get_modifier_weight(preceding_tokens: list[str]) -> float:
    """Check for degree modifiers in preceding tokens. Returns multiplier."""
    modifier = 1.0
    for token in preceding_tokens:
        if token in AMPLIFIERS:
            modifier *= AMPLIFIERS[token]
        elif token in DAMPENERS:
            modifier *= DAMPENERS[token]
    # Also check bigram modifiers like "a bit"
    if len(preceding_tokens) >= 2:
        bigram = ' '.join(preceding_tokens[-2:])
        if bigram in DAMPENERS:
            modifier *= DAMPENERS[bigram]
    return modifier


def heuristic_score(text: str) -> tuple[float, int, dict]:
    """
    Enhanced lexicon-based sentiment scoring with intensity, modifiers,
    negation, bigrams, and emoji support.

    Returns:
        (sentiment_index, evidence_count, detail_dict)
    """
    values = []
    clause_sentiments = []
    evidence = []
    negation_hits = 0
    idiom_hits = []

    for clause_text in clauses(text):
        ts = tokens(clause_text)
        clause_vals = []
        clause_idioms = [
            (name, weight)
            for pattern, name, weight in _POSITIVE_IDIOM_PATTERNS
            if pattern.search(clause_text)
        ]
        clause_negative_idioms = [
            (name, weight)
            for pattern, name, weight in _NEGATIVE_IDIOM_PATTERNS
            if pattern.search(clause_text)
        ]

        for i, token in enumerate(ts):
            if token in POS:
                base = POS_INTENSITY.get(token, 1.0)
            elif token in NEG:
                base = -(NEG_INTENSITY.get(token, 1.0))
            else:
                continue

            preceding = ts[max(0, i - 4):i]
            negators = [
                t for t in preceding
                if t in NEGATORS or t.endswith("n't")
            ]
            # "not only good" is additive emphasis rather than negation.
            if len(preceding) >= 2 and preceding[-2:] == ['not', 'only']:
                negators = [t for t in negators if t != 'not']
            negated = len(negators) % 2 == 1
            if token == 'recommend' and negated and clause_idioms:
                # The positive idiom is recorded below; counting its surface
                # negation as separate criticism would create a false Mixed label.
                continue
            if negated:
                negation_hits += 1
                inversion = -0.35 if any(t in _SOFT_NEGATORS for t in negators) else -0.75
                base *= inversion

            base *= _get_modifier_weight(preceding)
            clause_vals.append(base)
            values.append(base)
            evidence.append({
                'term': token,
                'score': round(base, 3),
                'negated': negated,
            })

        for name, weight in clause_idioms:
            clause_vals.append(weight)
            values.append(weight)
            idiom_hits.append(name)
            evidence.append({'term': name, 'score': weight, 'negated': False})
        for name, weight in clause_negative_idioms:
            clause_vals.append(-weight)
            values.append(-weight)
            idiom_hits.append(name)
            evidence.append({'term': name, 'score': -weight, 'negated': False})

        if clause_vals:
            clause_mean = sum(clause_vals) / len(clause_vals)
            clause_positive = sum(v for v in clause_vals if v > 0)
            clause_negative = abs(sum(v for v in clause_vals if v < 0))
            clause_mixed = clause_positive >= .5 and clause_negative >= .5
            clause_sentiments.append({
                'text': clause_text,
                'score': clause_mean,
                'polarity': (
                    'mixed' if clause_mixed
                    else 'positive' if clause_mean > .1
                    else 'negative' if clause_mean < -.1
                    else 'neutral'
                ),
                'evidence_count': len(clause_vals)
            })

    bigram_total, bigram_count = _bigram_score(text)
    if bigram_count:
        values.append(bigram_total)

    emoji_total, emoji_count = _emoji_score(text)
    if emoji_count:
        values.append(emoji_total)

    is_sarcastic, sarcasm_penalty = _detect_sarcasm(text)
    evidence_count = len(values)
    positive_strength = sum(v for v in values if v > 0)
    negative_strength = abs(sum(v for v in values if v < 0))
    strength_max = max(positive_strength, negative_strength, 1e-9)
    mixed = (
        positive_strength >= .5
        and negative_strength >= .5
        and min(positive_strength, negative_strength) / strength_max >= .2
    )

    if evidence_count == 0:
        raw_index = 50.0
    else:
        normalized = sum(values) / max(1.0, math.sqrt(evidence_count))
        raw_index = 50 + 45 * math.tanh(normalized / 2.0)

    if is_sarcastic and evidence_count > 0:
        raw_index = 50 + (raw_index - 50) * (1 - sarcasm_penalty)

    detail = {
        'clause_sentiments': clause_sentiments,
        'bigram_hits': bigram_count,
        'emoji_hits': emoji_count,
        'sarcasm_detected': is_sarcastic,
        'sarcasm_penalty': round(sarcasm_penalty, 3) if is_sarcastic else 0,
        'evidence_words': evidence_count,
        'raw_sum': round(sum(values), 3) if values else 0,
        'positive_strength': round(positive_strength, 3),
        'negative_strength': round(negative_strength, 3),
        'negation_hits': negation_hits,
        'mixed_evidence': mixed,
        'idiom_hits': idiom_hits,
        'evidence': evidence[:20],
    }

    return round(raw_index, 1), evidence_count, detail


def _sentiment_result(
    text: str,
    model_name: str,
    model_probability: float | None = None,
) -> dict:
    """Combine a binary model with contextual rules and expose four labels."""
    lexicon_index, evidence_count, detail = heuristic_score(text)
    word_count = len(tokens(text))
    neutral_cue = bool(_NEUTRAL_CUE_RE.search(text))
    balanced_neutral = bool(_BALANCED_NEUTRAL_RE.search(text))
    explicit_mixed = bool(_EXPLICIT_MIXED_RE.search(text))

    if model_probability is None:
        sentiment_index = lexicon_index
        method = model_name
    else:
        model_index = 100 * model_probability
        if evidence_count == 0 and word_count < 6:
            # Binary document models are unreliable on tiny factual fragments.
            sentiment_index = 50.0
        elif neutral_cue and max(detail['positive_strength'], detail['negative_strength']) <= .8:
            sentiment_index = lexicon_index
        else:
            lexicon_weight = min(.72, .28 + .11 * min(evidence_count, 4))
            if detail['negation_hits']:
                lexicon_weight = .9 if word_count <= 10 else max(.72, lexicon_weight)
            if detail['idiom_hits']:
                lexicon_weight = max(.85, lexicon_weight)
            sentiment_index = lexicon_weight * lexicon_index + (1 - lexicon_weight) * model_index
        method = f'hybrid:{model_name}+context-rules'

    if balanced_neutral or explicit_mixed:
        sentiment_index = 50.0
    sentiment_index = round(float(np.clip(sentiment_index, 0, 100)), 1)
    mixed = bool(detail['mixed_evidence'])
    if explicit_mixed:
        label = 'mixed'
        reason = 'The review explicitly describes both positive and negative feelings.'
    elif balanced_neutral:
        label = 'neutral'
        reason = 'The review explicitly balances positive and negative wording.'
    elif mixed:
        label = 'mixed'
        reason = 'Clear positive and negative language appears in the review.'
    elif neutral_cue and max(detail['positive_strength'], detail['negative_strength']) <= .8:
        label = 'neutral'
        reason = 'The review uses explicitly neutral or middling language.'
    elif evidence_count == 0 and word_count < 6:
        label = 'neutral'
        reason = 'No reliable sentiment evidence was found in this short text.'
    elif NEGATIVE_THRESHOLD <= sentiment_index <= POSITIVE_THRESHOLD:
        label = 'neutral'
        reason = 'The combined sentiment signals remain close to neutral.'
    elif sentiment_index > POSITIVE_THRESHOLD:
        label = 'positive'
        reason = (
            'Contextual negation reverses nearby negative wording.'
            if detail['negation_hits'] and detail['positive_strength'] > detail['negative_strength']
            else 'The combined language signals lean positive.'
        )
    else:
        label = 'negative'
        reason = (
            'Contextual negation reverses nearby positive wording.'
            if detail['negation_hits'] and detail['negative_strength'] > detail['positive_strength']
            else 'The combined language signals lean negative.'
        )

    if label == 'mixed':
        if explicit_mixed:
            confidence = .76
        else:
            balance = min(detail['positive_strength'], detail['negative_strength']) / max(
                detail['positive_strength'], detail['negative_strength'], 1e-9
            )
            confidence = min(.95, .58 + .25 * balance + .04 * min(evidence_count, 3))
    elif label == 'neutral':
        if balanced_neutral:
            confidence = .82
        elif neutral_cue:
            confidence = .78
        elif evidence_count == 0:
            confidence = .38
        else:
            confidence = max(.5, .72 - abs(sentiment_index - 50) / 100)
    else:
        confidence = min(.98, .5 + abs(sentiment_index - 50) / 100)
        if detail['negation_hits'] and word_count <= 10:
            confidence = max(confidence, .72)
        if detail['sarcasm_detected']:
            confidence = min(.55, confidence * (1 - detail['sarcasm_penalty']))

    confidence = round(float(np.clip(confidence, 0, 1)), 4)
    detail.update({
        'lexicon_index': lexicon_index,
        'model_index': round(100 * model_probability, 1) if model_probability is not None else None,
        'neutral_cue': neutral_cue,
        'explicit_mixed': explicit_mixed,
    })
    return {
        'label': label,
        'sentiment_index': sentiment_index,
        'positive_probability': round(model_probability, 4) if model_probability is not None else None,
        'confidence': confidence,
        'uncertain': confidence < .6,
        'method': method,
        'label_reason': reason,
        'detail': detail,
    }


class ReviewAnalyzer:
    """Production-grade review analyzer with multi-tier sentiment scoring."""

    def __init__(self, model_dir=None, mode=None):
        self.model_dir = Path(model_dir or os.getenv('CINESCOPE_MODEL_DIR') or ROOT / 'models')
        self.mode = mode or os.getenv('CINESCOPE_SENTIMENT', 'auto')
        self.vector_model = self.transformer = self.tokenizer = None
        self.aspect_model = self.aspect_tokenizer = None
        self.model_name = 'lexicon-context-rules'

        if self.mode in ('auto', 'transformer') and (self.model_dir / 'sentiment_transformer/config.json').exists():
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            location = self.model_dir / 'sentiment_transformer'
            self.tokenizer = AutoTokenizer.from_pretrained(location, local_files_only=True)
            self.transformer = AutoModelForSequenceClassification.from_pretrained(location, local_files_only=True).eval()
            self.model_name = 'fine-tuned-distilbert'
        elif self.mode in ('auto', 'tfidf') and (self.model_dir / 'sentiment_tfidf.joblib').exists():
            import joblib
            # Only load your own trusted training artifacts (pickle format).
            self.vector_model = joblib.load(self.model_dir / 'sentiment_tfidf.joblib')
            self.model_name = 'tfidf-logistic-regression'
        elif self.mode not in ('auto', 'lexicon'):
            raise FileNotFoundError(f'Requested {self.mode} model is missing in {self.model_dir}')

        if (self.model_dir / 'aspect_transformer/config.json').exists():
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            self.aspect_tokenizer = AutoTokenizer.from_pretrained(
                self.model_dir / 'aspect_transformer', local_files_only=True
            )
            self.aspect_model = AutoModelForSequenceClassification.from_pretrained(
                self.model_dir / 'aspect_transformer', local_files_only=True
            ).eval()

    @lru_cache(maxsize=4096)
    def score(self, text: str) -> dict:
        """Score sentiment of text using the best available model."""
        text = clean_text(text)
        if not text:
            return {
                'label': 'neutral', 'sentiment_index': 50.0,
                'positive_probability': None, 'confidence': None,
                'uncertain': True, 'method': self.model_name,
                'label_reason': 'No review text was provided.',
                'detail': {}
            }

        probability = None
        if self.transformer is not None:
            import torch
            ids = self.tokenizer.encode(text, add_special_tokens=False)
            probs, weights = [], []
            # Score every chunk instead of silently discarding the end of long reviews.
            with torch.inference_mode():
                for start in range(0, max(1, len(ids)), 384):
                    chunk = ids[start:start + 384]
                    batch = self.tokenizer.prepare_for_model(chunk, return_tensors='pt')
                    logits = self.transformer(**batch).logits.softmax(-1)[0]
                    probs.append(float(logits[1]))
                    weights.append(max(1, len(chunk)))
            probability = float(np.average(probs, weights=weights))
        elif self.vector_model is not None:
            probability = float(
                self.vector_model.predict_proba([text])[
                    0, list(self.vector_model.classes_).index(1)
                ]
            )

        return _sentiment_result(text, self.model_name, probability)

    def analyze(self, text: str, existing=()):
        """Full review analysis: sentiment, aspects, genres, themes, authenticity, quality."""
        text = clean_text(text)
        if not text:
            return self._empty_analysis(text)

        # Convert to tuple for hashability (existing may be a list)
        existing = tuple(existing) if not isinstance(existing, tuple) else existing

        aspects = {}
        clause_list = clauses(text)
        for name, words in ASPECTS.items():
            relevant = [s for s in clause_list if any(has_phrase(s, w) for w in words)]
            # Do not turn a mere mention without an opinion into a 50 score.
            scored = [(s, self.aspect_score(name, s)) for s in relevant]
            scored = [(s, r) for s, r in scored if not r['uncertain']]
            aspects[name] = {
                'score': round(float(np.mean([r['sentiment_index'] for _, r in scored])), 1) if scored else None,
                'mentions': len(relevant),
                'scored_mentions': len(scored),
                'evidence': [s for s, _ in scored[:3]],
                'method': 'fine-tuned-aspect-transformer' if self.aspect_model else 'clause-mention + ' + self.model_name
            }

        relevance = {}
        for group in ('genres', 'themes'):
            tags = []
            for label, aliases in TAXONOMY[group].items():
                evidence = [s for s in clause_list if any(has_phrase(s, w) for w in aliases)]
                if evidence:
                    tags.append({
                        'name': label,
                        'relevance': round(100 * len(evidence) / max(1, len(clause_list))),
                        'evidence': evidence[:2]
                    })
            relevance[group] = tags

        # Compute review quality metrics
        quality = review_quality(text)

        # Get full sentiment with clause detail
        sentiment_result = dict(self.score(text))

        return {
            'text': text,
            'sentiment': sentiment_result,
            'aspects': aspects,
            **relevance,
            'authenticity': authenticity(text, existing),
            'quality': quality,
            'score_note': '0–100 sentiment index, not an objective film quality score. Mixed means substantial evidence on both sides; decision confidence is not a calibrated probability. Genre/theme relevance is mention coverage.'
        }

    def _empty_analysis(self, text: str) -> dict:
        """Return a safe empty analysis result."""
        return {
            'text': text,
            'sentiment': {
                'label': 'neutral', 'sentiment_index': 50.0,
                'positive_probability': None, 'confidence': None,
                'uncertain': True, 'method': self.model_name,
                'label_reason': 'No review text was provided.', 'detail': {}
            },
            'aspects': {name: {'score': None, 'mentions': 0, 'scored_mentions': 0, 'evidence': [], 'method': self.model_name} for name in ASPECTS},
            'genres': [], 'themes': [],
            'authenticity': {'risk_index': 0, 'needs_review': False, 'duplicate': False, 'signals': [], 'method': 'heuristic-screening', 'note': 'Empty text.'},
            'quality': {'word_count': 0, 'detail_score': 0, 'helpfulness': 0, 'coherence': 0},
            'score_note': 'Empty text provided.'
        }

    @lru_cache(maxsize=4096)
    def aspect_score(self, aspect: str, sentence: str) -> dict:
        """Score a sentence for a specific aspect."""
        if self.aspect_model is None:
            return self.score(sentence)
        import torch
        batch = self.aspect_tokenizer(aspect, sentence, return_tensors='pt', truncation=True, max_length=256)
        with torch.inference_mode():
            probability = self.aspect_model(**batch).logits.softmax(-1)[0].tolist()
        return {
            'sentiment_index': round(100 * (probability[2] + .5 * probability[1]), 1),
            'uncertain': max(probability) < .5,
            'method': 'fine-tuned-aspect-transformer'
        }

    def summarize(self, reviews: list[dict]) -> dict:
        """All reviews contribute to aggregates; excerpts are extractive and cited by ID."""
        seen, accepted, flagged, deduped = [], [], [], 0
        for review in reviews:
            text = clean_text(review['text'])
            if not text:
                continue
            quality = authenticity(text, tuple(seen))
            seen.append(text)
            if quality['duplicate']:
                deduped += 1
                continue
            if quality['needs_review']:
                flagged.append(review['review_id'])
                continue
            accepted.append((review, self.analyze(text)))

        aspect_results = {}
        for a in ASPECTS:
            observations = [
                (r['review_id'], x['aspects'][a])
                for r, x in accepted
                if x['aspects'][a]['score'] is not None
            ]
            vals = [x['score'] for _, x in observations]
            aspect_results[a] = {
                'score': round(float(np.mean(vals)), 1) if vals else None,
                'review_count': len(vals),
                'support': 'limited' if len(vals) < 5 else 'available',
                'evidence': [{'review_id': rid, 'text': x['evidence'][0]} for rid, x in observations[:3] if x.get('evidence')]
            }

        # Mixed and neutral are first-class labels. Uncertainty remains an
        # orthogonal confidence flag and is not treated as another polarity.
        counts = Counter(
            x['sentiment']['label']
            for _, x in accepted
            if not x['sentiment']['uncertain']
        )
        uncertain_count = sum(1 for _, x in accepted if x['sentiment']['uncertain'])

        candidates = []
        for r, _ in accepted:
            for s in clauses(r['text']):
                score_result = self.score(s)
                if not score_result['uncertain']:
                    candidates.append({
                        'review_id': r['review_id'],
                        'text': s,
                        'polarity': score_result['label'],
                        'strength': abs(score_result['sentiment_index'] - 50)
                    })

        excerpts = []
        for polarity in ('positive', 'negative'):
            pool = sorted(
                (x for x in candidates if x['polarity'] == polarity),
                key=lambda x: -x['strength']
            )
            for item in pool:
                if any(
                    SequenceMatcher(None, item['text'].lower(), e['text'].lower()).ratio() > .7
                    for e in excerpts
                ):
                    continue
                excerpts.append({k: v for k, v in item.items() if k != 'strength'})
                if sum(e['polarity'] == polarity for e in excerpts) == 3:
                    break

        count = len(accepted)
        # Use .get() with default 0 to prevent KeyError on empty corpora
        positive_count = counts.get('positive', 0)
        negative_count = counts.get('negative', 0)
        mixed_count = counts.get('mixed', 0)
        neutral_count = counts.get('neutral', 0)

        if not count:
            summary = 'No eligible reviews yet. Recommendations can still use the movie\'s genres, themes and synopsis.'
        else:
            ordered = sorted(
                [(v['score'], k) for k, v in aspect_results.items() if v['score'] is not None],
                reverse=True
            )
            positives = [name.lower() for value, name in ordered if value >= 65]
            criticisms = [name.lower() for value, name in ordered if value < 45]
            summary = (
                f'Across {count} eligible reviews, {positive_count} lean positive, '
                f'{negative_count} lean negative, {mixed_count} are mixed and '
                f'{neutral_count} are neutral; {uncertain_count} are low-confidence.'
            )
            if positives:
                summary += ' Praise centers on ' + ', '.join(positives[:3]) + '.'
            if criticisms:
                summary += ' Criticism centers on ' + ', '.join(criticisms[:3]) + '.'
            if count < 5:
                summary += ' This is a small sample.'

        # Compute overall sentiment distribution for visualization
        sentiment_distribution = {}
        if count > 0:
            all_scores = [x['sentiment']['sentiment_index'] for _, x in accepted]
            sentiment_distribution = {
                'mean': round(float(np.mean(all_scores)), 1),
                'median': round(float(np.median(all_scores)), 1),
                'std': round(float(np.std(all_scores)), 1) if len(all_scores) > 1 else 0,
                'min': round(float(min(all_scores)), 1),
                'max': round(float(max(all_scores)), 1),
            }

        return {
            'summary': summary,
            'total_reviews': len(reviews),
            'eligible_reviews': count,
            'duplicates_excluded': deduped,
            'flagged_review_ids': flagged,
            'sentiment_counts': {
                'positive': positive_count,
                'negative': negative_count,
                'mixed': mixed_count,
                'neutral': neutral_count,
                'uncertain': uncertain_count
            },
            'sentiment_distribution': sentiment_distribution,
            'aspects': aspect_results,
            'excerpts': excerpts,
            'method': 'extractive + full-corpus aggregation',
            'synthetic_demo': any(r.get('source') == 'synthetic-demo' for r in reviews)
        }


def authenticity(text: str, existing=()) -> dict:
    """
    Comprehensive review screening with multiple signal categories.

    Signals are for flagging only — no claim about genuine/fake authorship.
    """
    normalized = ' '.join(tokens(text))
    reasons = []
    risk = 0.0
    duplicate = False
    signal_categories = {}

    # Convert existing to tuple for consistency
    if not isinstance(existing, tuple):
        existing = tuple(existing)

    # ── Duplicate / near-duplicate detection ──
    if normalized:
        for prior in existing:
            other = ' '.join(tokens(prior))
            exact = normalized == other
            near = len(normalized) > 80 and SequenceMatcher(
                None, normalized, other, autojunk=True
            ).ratio() > .94
            if exact or near:
                duplicate = True
                risk = max(risk, .9)
                reasons.append('Duplicate or near-duplicate text')
                signal_categories['duplicate'] = True
                break

    words_list = tokens(text)
    word_count = len(words_list)

    # ── Promotional content / spam ──
    spam_found = []
    for pattern in SPAM_PATTERNS:
        if pattern.lower() in text.lower():
            spam_found.append(pattern)
    if _URL_RE.search(text):
        spam_found.append('URL detected')
    if spam_found:
        risk += min(0.6, len(spam_found) * 0.2)
        reasons.append(f'Promotional content ({", ".join(spam_found[:3])})')
        signal_categories['spam'] = True

    # ── Repetitive wording ──
    if word_count >= 12:
        unique_ratio = len(set(words_list)) / word_count
        if unique_ratio < 0.3:
            risk += .45
            reasons.append(f'Unusually repetitive wording (unique ratio: {unique_ratio:.0%})')
            signal_categories['repetitive'] = True
        elif unique_ratio < 0.4:
            risk += .15
            reasons.append(f'Somewhat repetitive wording (unique ratio: {unique_ratio:.0%})')

    # ── Single word domination ──
    if word_count > 3:
        word_freq = Counter(words_list)
        max_freq = max(word_freq.values(), default=0)
        if max_freq / word_count > 0.5:
            risk += .25
            dominant_word = word_freq.most_common(1)[0][0]
            reasons.append(f'One word dominates the review ("{dominant_word}")')
            signal_categories['word_domination'] = True

    # ── Excessive uppercase ──
    letters = [c for c in text if c.isalpha()]
    if len(letters) > 30:
        upper_ratio = sum(c.isupper() for c in letters) / len(letters)
        if upper_ratio > .85:
            risk += .20
            reasons.append('Mostly uppercase text (shouting)')
            signal_categories['excessive_caps'] = True
        elif upper_ratio > .60:
            risk += .08
            reasons.append('Significant uppercase usage')

    # ── Excessive punctuation ──
    exclamation_count = text.count('!')
    question_count = text.count('?')
    if exclamation_count > max(10, word_count * 0.3):
        risk += .15
        reasons.append(f'Excessive exclamation marks ({exclamation_count})')
        signal_categories['excessive_punctuation'] = True
    if _EXCESSIVE_PUNCT_RE.search(text):
        risk += .10
        reasons.append('Repeated punctuation patterns (!!!/?????)')

    # ── Gibberish detection (vowel/consonant ratio) ──
    if word_count >= 5:
        vowels = sum(c in 'aeiou' for c in normalized)
        consonants = sum(c.isalpha() and c not in 'aeiou' for c in normalized)
        if consonants > 0:
            vc_ratio = vowels / consonants
            if vc_ratio < 0.15 or vc_ratio > 3.0:
                risk += .35
                reasons.append('Text appears to be gibberish (unusual character distribution)')
                signal_categories['gibberish'] = True

    # ── Extremely short reviews (low effort) ──
    if 0 < word_count < 3:
        risk += .10
        reasons.append('Extremely short review (low effort)')
        signal_categories['too_short'] = True

    # ── Extremely long reviews (potential copypasta) ──
    if word_count > 2000:
        risk += .10
        reasons.append(f'Unusually long review ({word_count} words)')
        signal_categories['too_long'] = True

    # ── Template / copypasta detection ──
    # Common review spam templates
    template_phrases = [
        'i was paid', 'compensated for', 'free product',
        'in exchange for', 'honest review in exchange',
        'sponsored', 'gifted', '#ad', '#sponsored'
    ]
    template_hits = sum(1 for p in template_phrases if p in text.lower())
    if template_hits:
        risk += min(0.3, template_hits * 0.15)
        reasons.append('Potential template/compensated review language')
        signal_categories['template'] = True

    # ── All emoji / no substantive content ──
    emoji_chars = _extract_emojis(text)
    non_emoji_alpha = sum(c.isalpha() for c in text)
    if len(emoji_chars) > 3 and non_emoji_alpha < 10:
        risk += .20
        reasons.append('Review is mostly emojis with little substantive text')
        signal_categories['emoji_only'] = True

    return {
        'risk_index': round(min(risk, 1) * 100),
        'needs_review': risk >= .7,
        'duplicate': duplicate,
        'signals': reasons,
        'signal_categories': signal_categories,
        'method': 'heuristic-screening',
        'note': 'These signals cannot establish whether a review is fake. Human review is required.'
    }


def review_quality(text: str) -> dict:
    """
    Assess review quality/helpfulness with heuristic metrics.

    Returns scores for word count, detail, helpfulness, and coherence.
    """
    words_list = tokens(text)
    word_count = len(words_list)
    clause_list = clauses(text)
    clause_count = len(clause_list)

    # Detail score: rewards specific aspect mentions, evidence, examples
    aspect_mentions = sum(
        1 for name, kws in ASPECTS.items()
        for kw in kws
        if has_phrase(text, kw)
    )
    detail_score = min(100, int(
        (min(word_count, 200) / 200 * 30) +  # Length contribution (up to 30)
        (min(aspect_mentions, 6) / 6 * 40) +  # Aspect coverage (up to 40)
        (min(clause_count, 8) / 8 * 30)       # Multi-clause structure (up to 30)
    ))

    # Helpfulness: combination of length, specificity, and structure
    has_comparison = bool(re.search(r'\b(compared to|better than|worse than|unlike|similar to|reminds me of)\b', text, re.I))
    has_examples = bool(re.search(r'\b(for example|for instance|such as|like when|scene where|moment when)\b', text, re.I))
    has_reasoning = bool(re.search(r'\b(because|since|due to|the reason|what makes|this works|this fails)\b', text, re.I))

    helpfulness = min(100, int(
        detail_score * 0.5 +
        (20 if has_comparison else 0) +
        (15 if has_examples else 0) +
        (15 if has_reasoning else 0)
    ))

    # Coherence: sentence diversity and vocabulary richness
    unique_ratio = len(set(words_list)) / max(1, word_count)
    avg_clause_len = word_count / max(1, clause_count)
    coherence = min(100, int(
        unique_ratio * 60 +
        (40 if 8 <= avg_clause_len <= 25 else 20)
    ))

    return {
        'word_count': word_count,
        'clause_count': clause_count,
        'aspect_mentions': aspect_mentions,
        'detail_score': detail_score,
        'helpfulness': helpfulness,
        'coherence': coherence,
        'has_comparison': has_comparison,
        'has_examples': has_examples,
        'has_reasoning': has_reasoning,
    }
