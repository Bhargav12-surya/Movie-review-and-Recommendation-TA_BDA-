/**
 * CineScope · Browser Demo Engine — Production Build
 *
 * Transparent browser-only demonstration engine with full parity
 * to the Python backend sentiment analysis capabilities.
 *
 * Features:
 * - Intensity-weighted lexicon sentiment analysis (270+ words)
 * - Bigram/trigram phrase detection (120+ phrases)
 * - Degree modifier handling (amplifiers + dampeners)
 * - Emoji & emoticon sentiment scoring
 * - Sarcasm marker detection with confidence penalty
 * - Advanced negation handling (4-word window, contraction-aware)
 * - Clause-level mixed-sentiment decomposition
 * - Aspect-level scoring with evidence extraction
 * - Hardened review authenticity screening
 * - Review quality metrics (detail, helpfulness, coherence)
 * - Content-based recommendation with taste profiling
 * - Multi-turn conversational movie discovery
 */

export let catalog = [];
export let seedReviews = [];
export let tax = {};


/* ── Initialization ── */

export async function initEngine() {
  [catalog, seedReviews, tax] = await Promise.all(
    ['catalog', 'reviews', 'taxonomy'].map((n) =>
      fetch(`/${n}.json`).then((r) => r.json())
    )
  );
}


/* ── Local Storage Helpers ── */

const read = (key, fallback) => {
  try {
    return JSON.parse(localStorage.getItem(key)) ?? fallback;
  } catch {
    return fallback;
  }
};

const write = (key, value) => localStorage.setItem(key, JSON.stringify(value));


/* ── User History ── */

export function history() {
  return read('cinescope.ratings', []);
}

export function rate(id, rating) {
  const rows = history().filter((r) => r.movie_id !== id);
  rows.push({
    movie_id: id,
    rating,
    updated_at: new Date().toISOString(),
  });
  write('cinescope.ratings', rows);
  return rows;
}

export function unrate(id) {
  const rows = history().filter((r) => r.movie_id !== id);
  write('cinescope.ratings', rows);
  return rows;
}


/* ── Review Storage ── */

export const reviews = (id) =>
  [...seedReviews, ...read('cinescope.reviews', [])].filter(
    (r) => r.movie_id === id
  );


/* ── Text Processing ── */

const words = (s) =>
  String(s).toLowerCase().replace(/[‘’‛]/g, "'").match(/[a-z]+(?:'[a-z]+)?/g) || [];

const split = (s) => {
  const conjunctions = (tax.but_conjunctions || [
    'but', 'however', 'although', 'yet', 'though',
    'nevertheless', 'nonetheless', 'despite',
    'unfortunately', 'sadly', 'except', 'while', 'whereas'
  ]).join('|');
  return s
    .split(new RegExp(`[.!?;…\\n]+|\\b(?:${conjunctions})\\b`, 'i'))
    .map((s) => s.trim().replace(/^,+|,+$/g, ''))
    .filter(Boolean);
};

const phrase = (s, w) =>
  new RegExp(
    '(?:^|\\W)' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?:$|\\W)',
    'i'
  ).test(s);


/* ── Emoji Extraction ── */

const EMOJI_RE = /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2702}-\u{27B0}\u{24C2}-\u{1F251}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{FE00}-\u{FE0F}\u{200D}\u{2764}]+/gu;

function extractEmojis(text) {
  return (text.match(EMOJI_RE) || []);
}

function emojiScore(text) {
  const emojiSent = tax.emoji_sentiment || {};
  const emojis = extractEmojis(text);
  let total = 0, count = 0;
  for (const seq of emojis) {
    for (const char of seq) {
      if (emojiSent[char] !== undefined) {
        total += emojiSent[char];
        count++;
      }
    }
  }
  return { total, count };
}


/* ── Bigram Scoring ── */

function bigramScore(text) {
  const lower = text.toLowerCase();
  const posBigrams = tax.positive_bigrams || {};
  const negBigrams = tax.negative_bigrams || {};
  let total = 0, count = 0;

  for (const [p, w] of Object.entries(posBigrams)) {
    if (lower.includes(p)) { total += w; count++; }
  }
  for (const [p, w] of Object.entries(negBigrams)) {
    if (lower.includes(p)) { total -= w; count++; }
  }
  return { total, count };
}


/* ── Sarcasm Detection ── */

function detectSarcasm(text) {
  const lower = text.toLowerCase();
  const markers = tax.sarcasm_markers || [];
  const markersFound = markers.filter((m) => lower.includes(m)).length;

  // Quoted sarcasm: positive words in quotes
  let scareQuotes = 0;
  const quoted = text.match(/"([^"]*)"/g) || [];
  for (const q of quoted) {
    const inner = q.slice(1, -1).toLowerCase();
    if (words(inner).some((w) => tax.positive.includes(w))) {
      scareQuotes++;
    }
  }

  // Excessive exclamation after positive
  const exclSarcasm = /(?:great|wonderful|amazing|brilliant)\s*[!]{2,}/i.test(text);

  const totalMarkers = markersFound + scareQuotes + (exclSarcasm ? 1 : 0);
  if (totalMarkers > 0) {
    return { detected: true, penalty: Math.min(0.4, totalMarkers * 0.15) };
  }
  return { detected: false, penalty: 0 };
}


/* ── Degree Modifier Weight ── */

function getModifierWeight(precedingTokens) {
  const amplifiers = tax.degree_modifiers?.amplifiers || {};
  const dampeners = tax.degree_modifiers?.dampeners || {};
  let modifier = 1.0;

  for (const token of precedingTokens) {
    if (amplifiers[token]) modifier *= amplifiers[token];
    else if (dampeners[token]) modifier *= dampeners[token];
  }

  // Check bigram dampeners like "a bit"
  if (precedingTokens.length >= 2) {
    const bigram = precedingTokens.slice(-2).join(' ');
    if (dampeners[bigram]) modifier *= dampeners[bigram];
  }

  return modifier;
}


/* ── Negation Set ── */

function isNegator(token) {
  const negators = new Set([...(tax.negators || [
    'not', 'no', 'never', 'hardly', 'barely',
    "isn't", "wasn't", "didn't", "don't", "doesn't",
    "couldn't", "wouldn't", "shouldn't", "won't",
    "haven't", "hasn't", "hadn't", "weren't", "aren't",
    'without', 'lack', 'lacks', 'nothing', 'none',
    'wasnt', 'isnt', 'didnt', 'doesnt', 'dont',
    'couldnt', 'wouldnt', 'shouldnt', 'wont',
    'havent', 'hasnt', 'hadnt', 'werent', 'arent',
  ]), 'cannot', "can't", 'cant']);
  return negators.has(token) || token.endsWith("n't");
}


/* ── Enhanced Sentiment Analysis ── */

export function sentiment(text) {
  text = String(text).normalize('NFKC').replace(/[‘’‛]/g, "'");
  const posIntensity = tax.positive_intensity || {};
  const negIntensity = tax.negative_intensity || {};
  const positiveWords = new Set([
    ...(tax.positive || []),
    'like', 'liked', 'recommend', 'fine', 'decent', 'okay', 'ok',
  ]);
  const negativeWords = new Set([...(tax.negative || []), 'dislike', 'disliked']);
  const vals = [];
  const clauseSentiments = [];
  const evidence = [];
  let negationHits = 0;
  const idiomHits = [];
  const negativeIdiomPatterns = [
    [/\bcould have been better\b/i, 'could have been better', 1.3],
    [/\bexpected (?:much )?more\b/i, 'expected more', 1.3],
    [/\b(?:barely|hardly) watchable\b/i, 'barely watchable', 1.6],
    [/\bnot worth (?:it|watching|seeing)\b/i, 'not worth it', 1.8],
  ];

  for (const clause of split(text)) {
    const ts = words(clause);
    const clauseVals = [];
    const clausePositiveIdiom = /\b(?:can(?:not|'t)|could(?:\s+not|n't))\s+recommend\b.{0,60}\benough\b/i.test(clause)
      || /\b(?:could(?:\s+not|n't))\s+recommend\b.{0,60}\bmore\b/i.test(clause);
    const clauseNegativeIdioms = negativeIdiomPatterns.filter(([pattern]) => pattern.test(clause));

    ts.forEach((w, i) => {
      let base = 0;
      if (positiveWords.has(w)) {
        base = posIntensity[w] || 1.0;
      } else if (negativeWords.has(w)) {
        base = -(negIntensity[w] || 1.0);
      } else {
        return;
      }

      const preceding = ts.slice(Math.max(0, i - 4), i);
      let negators = preceding.filter(isNegator);
      if (preceding.slice(-2).join(' ') === 'not only') {
        negators = negators.filter((token) => token !== 'not');
      }
      const negated = negators.length % 2 === 1;
      if (w === 'recommend' && negated && clausePositiveIdiom) return;
      if (negated) {
        negationHits++;
        const soft = negators.some((token) => token === 'hardly' || token === 'barely');
        base *= soft ? -0.35 : -0.75;
      }

      base *= getModifierWeight(preceding);

      clauseVals.push(base);
      vals.push(base);
      evidence.push({ term: w, score: Math.round(base * 1000) / 1000, negated });
    });

    if (clausePositiveIdiom) {
      clauseVals.push(2.5);
      vals.push(2.5);
      idiomHits.push('cannot recommend enough');
      evidence.push({ term: 'cannot recommend enough', score: 2.5, negated: false });
    }
    for (const [, name, weight] of clauseNegativeIdioms) {
      clauseVals.push(-weight);
      vals.push(-weight);
      idiomHits.push(name);
      evidence.push({ term: name, score: -weight, negated: false });
    }

    if (clauseVals.length) {
      const mean = clauseVals.reduce((a, b) => a + b, 0) / clauseVals.length;
      const positive = clauseVals.filter((v) => v > 0).reduce((a, b) => a + b, 0);
      const negative = Math.abs(clauseVals.filter((v) => v < 0).reduce((a, b) => a + b, 0));
      clauseSentiments.push({
        text: clause,
        score: mean,
        polarity:
          positive >= 0.5 && negative >= 0.5
            ? 'mixed'
            : mean > 0.1
            ? 'positive'
            : mean < -0.1
            ? 'negative'
            : 'neutral',
        evidence_count: clauseVals.length,
      });
    }
  }

  // Add bigram scores
  const bg = bigramScore(text);
  if (bg.count) vals.push(bg.total);

  // Add emoji scores
  const em = emojiScore(text);
  if (em.count) vals.push(em.total);

  const sarcasm = detectSarcasm(text);
  const positiveStrength = vals.filter((v) => v > 0).reduce((a, b) => a + b, 0);
  const negativeStrength = Math.abs(vals.filter((v) => v < 0).reduce((a, b) => a + b, 0));
  const strengthMax = Math.max(positiveStrength, negativeStrength, Number.EPSILON);
  const mixed =
    positiveStrength >= 0.5
    && negativeStrength >= 0.5
    && Math.min(positiveStrength, negativeStrength) / strengthMax >= 0.2;

  let index;
  if (!vals.length) {
    index = 50;
  } else {
    const weightedSum = vals.reduce((a, b) => a + b, 0);
    const normalized = weightedSum / Math.max(1, Math.sqrt(vals.length));
    index = 50 + 45 * Math.tanh(normalized / 2.0);
  }

  if (sarcasm.detected && vals.length) {
    index = 50 + (index - 50) * (1 - sarcasm.penalty);
  }

  const neutralCue = /\b(?:okay|ok|average|so[- ]so|neither good nor bad|indifferent)\b/i.test(text);
  const balancedNeutral = /\bneither good nor bad\b/i.test(text);
  const explicitMixed = /\b(?:mixed feelings|both good and bad)\b/i.test(text);
  if (balancedNeutral || explicitMixed) index = 50;
  index = Math.round(index * 10) / 10;
  let label;
  let labelReason;
  if (explicitMixed) {
    label = 'mixed';
    labelReason = 'The review explicitly describes both positive and negative feelings.';
  } else if (balancedNeutral) {
    label = 'neutral';
    labelReason = 'The review explicitly balances positive and negative wording.';
  } else if (mixed) {
    label = 'mixed';
    labelReason = 'Clear positive and negative language appears in the review.';
  } else if (neutralCue && Math.max(positiveStrength, negativeStrength) <= 0.8) {
    label = 'neutral';
    labelReason = 'The review uses explicitly neutral or middling language.';
  } else if (!vals.length && words(text).length < 6) {
    label = 'neutral';
    labelReason = 'No reliable sentiment evidence was found in this short text.';
  } else if (index >= 42 && index <= 58) {
    label = 'neutral';
    labelReason = 'The sentiment signals remain close to neutral.';
  } else if (index > 58) {
    label = 'positive';
    labelReason = negationHits && positiveStrength > negativeStrength
      ? 'Contextual negation reverses nearby negative wording.'
      : 'The language signals lean positive.';
  } else {
    label = 'negative';
    labelReason = negationHits && negativeStrength > positiveStrength
      ? 'Contextual negation reverses nearby positive wording.'
      : 'The language signals lean negative.';
  }

  let confidence;
  if (label === 'mixed') {
    if (explicitMixed) {
      confidence = 0.76;
    } else {
      const balance = Math.min(positiveStrength, negativeStrength) / strengthMax;
      confidence = Math.min(0.95, 0.58 + 0.25 * balance + 0.04 * Math.min(vals.length, 3));
    }
  } else if (label === 'neutral') {
    confidence = balancedNeutral
      ? 0.82
      : neutralCue
      ? 0.78
      : !vals.length
      ? 0.38
      : Math.max(0.5, 0.72 - Math.abs(index - 50) / 100);
  } else {
    confidence = Math.min(0.98, 0.5 + Math.abs(index - 50) / 100);
    if (negationHits && words(text).length <= 10) confidence = Math.max(confidence, 0.72);
    if (sarcasm.detected) confidence = Math.min(0.55, confidence * (1 - sarcasm.penalty));
  }
  confidence = Math.max(0, Math.min(1, Math.round(confidence * 10000) / 10000));

  return {
    label,
    sentiment_index: index,
    positive_probability: null,
    confidence,
    uncertain: confidence < 0.6,
    method: 'lexicon-context-rules',
    label_reason: labelReason,
    detail: {
      clause_sentiments: clauseSentiments,
      bigram_hits: bg.count,
      emoji_hits: em.count,
      sarcasm_detected: sarcasm.detected,
      sarcasm_penalty: sarcasm.detected ? Math.round(sarcasm.penalty * 1000) / 1000 : 0,
      evidence_words: vals.length,
      raw_sum: Math.round(vals.reduce((a, b) => a + b, 0) * 1000) / 1000,
      positive_strength: Math.round(positiveStrength * 1000) / 1000,
      negative_strength: Math.round(negativeStrength * 1000) / 1000,
      negation_hits: negationHits,
      mixed_evidence: mixed,
      idiom_hits: idiomHits,
      evidence: evidence.slice(0, 20),
      lexicon_index: index,
      model_index: null,
      neutral_cue: neutralCue,
      explicit_mixed: explicitMixed,
    },
  };
}


/* ── Review Authenticity Screening ── */

export function authenticity(text, existing = []) {
  const ws = words(text);
  const normal = ws.join(' ');
  const signals = [];
  const signalCategories = {};
  let risk = 0;
  const wordCount = ws.length;

  // Duplicate detection
  const duplicate = !!normal && existing.some((t) => words(t).join(' ') === normal);
  if (duplicate) {
    risk = 0.9;
    signals.push('Duplicate text');
    signalCategories.duplicate = true;
  }

  // Near-duplicate detection
  if (!duplicate && normal.length > 80) {
    for (const prior of existing) {
      const other = words(prior).join(' ');
      // Simple character overlap check (approximation of SequenceMatcher)
      const shorter = Math.min(normal.length, other.length);
      const longer = Math.max(normal.length, other.length);
      if (shorter / longer > 0.85) {
        let matches = 0;
        const normalWords = normal.split(' ');
        const otherWords = other.split(' ');
        const otherSet = new Set(otherWords);
        for (const w of normalWords) {
          if (otherSet.has(w)) matches++;
        }
        if (matches / Math.max(normalWords.length, otherWords.length) > 0.9) {
          risk = Math.max(risk, 0.85);
          signals.push('Near-duplicate text detected');
          signalCategories.near_duplicate = true;
          break;
        }
      }
    }
  }

  // Spam / promotional content
  const spamPatterns = tax.spam_patterns || [
    'buy now', 'click here', 'promo code', 'discount code',
    'limited time', 'act now', 'free trial', 'subscribe',
    'follow me', 'check out my', 'visit my', 'link in',
    'use code', 'coupon', 'giveaway', 'dm me'
  ];
  const spamFound = spamPatterns.filter((p) => text.toLowerCase().includes(p));
  if (/https?:\/\/|www\./i.test(text)) spamFound.push('URL detected');
  if (spamFound.length) {
    risk += Math.min(0.6, spamFound.length * 0.2);
    signals.push(`Promotional content (${spamFound.slice(0, 3).join(', ')})`);
    signalCategories.spam = true;
  }

  // Repetitive wording
  if (wordCount >= 12) {
    const uniqueRatio = new Set(ws).size / wordCount;
    if (uniqueRatio < 0.3) {
      risk += 0.45;
      signals.push(`Unusually repetitive wording (unique ratio: ${Math.round(uniqueRatio * 100)}%)`);
      signalCategories.repetitive = true;
    } else if (uniqueRatio < 0.4) {
      risk += 0.15;
      signals.push(`Somewhat repetitive wording (unique ratio: ${Math.round(uniqueRatio * 100)}%)`);
    }
  }

  // Single word domination
  if (wordCount > 3) {
    const freq = {};
    for (const w of ws) freq[w] = (freq[w] || 0) + 1;
    const maxFreq = Math.max(...Object.values(freq));
    if (maxFreq / wordCount > 0.5) {
      const dominant = Object.entries(freq).sort((a, b) => b[1] - a[1])[0][0];
      risk += 0.25;
      signals.push(`One word dominates the review ("${dominant}")`);
      signalCategories.word_domination = true;
    }
  }

  // Excessive uppercase
  const letters = [...text].filter((c) => /[a-zA-Z]/.test(c));
  if (letters.length > 30) {
    const upperRatio = letters.filter((c) => c === c.toUpperCase() && c !== c.toLowerCase()).length / letters.length;
    if (upperRatio > 0.85) {
      risk += 0.20;
      signals.push('Mostly uppercase text (shouting)');
      signalCategories.excessive_caps = true;
    } else if (upperRatio > 0.60) {
      risk += 0.08;
      signals.push('Significant uppercase usage');
    }
  }

  // Excessive punctuation
  const exclCount = (text.match(/!/g) || []).length;
  if (exclCount > Math.max(10, wordCount * 0.3)) {
    risk += 0.15;
    signals.push(`Excessive exclamation marks (${exclCount})`);
    signalCategories.excessive_punctuation = true;
  }
  if (/[!?]{3,}/.test(text)) {
    risk += 0.10;
    signals.push('Repeated punctuation patterns (!!!/?????)')
  }

  // Gibberish detection
  if (wordCount >= 5) {
    const vowels = [...normal].filter((c) => 'aeiou'.includes(c)).length;
    const consonants = [...normal].filter((c) => /[a-z]/.test(c) && !'aeiou'.includes(c)).length;
    if (consonants > 0) {
      const vcRatio = vowels / consonants;
      if (vcRatio < 0.15 || vcRatio > 3.0) {
        risk += 0.35;
        signals.push('Text appears to be gibberish (unusual character distribution)');
        signalCategories.gibberish = true;
      }
    }
  }

  // Extremely short
  if (wordCount > 0 && wordCount < 3) {
    risk += 0.10;
    signals.push('Extremely short review (low effort)');
    signalCategories.too_short = true;
  }

  // Extremely long
  if (wordCount > 2000) {
    risk += 0.10;
    signals.push(`Unusually long review (${wordCount} words)`);
    signalCategories.too_long = true;
  }

  // Template detection
  const templatePhrases = [
    'i was paid', 'compensated for', 'free product',
    'in exchange for', 'honest review in exchange',
    'sponsored', 'gifted', '#ad', '#sponsored'
  ];
  const templateHits = templatePhrases.filter((p) => text.toLowerCase().includes(p)).length;
  if (templateHits) {
    risk += Math.min(0.3, templateHits * 0.15);
    signals.push('Potential template/compensated review language');
    signalCategories.template = true;
  }

  // All emoji / no substantive content
  const emojiChars = extractEmojis(text);
  const nonEmojiAlpha = [...text].filter((c) => /[a-zA-Z]/.test(c)).length;
  if (emojiChars.length > 3 && nonEmojiAlpha < 10) {
    risk += 0.20;
    signals.push('Review is mostly emojis with little substantive text');
    signalCategories.emoji_only = true;
  }

  return {
    risk_index: Math.min(100, Math.round(risk * 100)),
    needs_review: risk >= 0.7,
    duplicate,
    signals,
    signal_categories: signalCategories,
    method: 'heuristic-screening',
    note: 'These signals cannot establish whether a review is fake. Human review is required.',
  };
}


/* ── Review Quality Metrics ── */

export function reviewQuality(text) {
  const ws = words(text);
  const wordCount = ws.length;
  const clauseList = split(text);
  const clauseCount = clauseList.length;

  // Aspect mentions
  let aspectMentions = 0;
  for (const [, kws] of Object.entries(tax.aspects || {})) {
    for (const kw of kws) {
      if (phrase(text, kw)) { aspectMentions++; break; }
    }
  }

  // Detail score
  const detailScore = Math.min(100, Math.round(
    (Math.min(wordCount, 200) / 200 * 30) +
    (Math.min(aspectMentions, 6) / 6 * 40) +
    (Math.min(clauseCount, 8) / 8 * 30)
  ));

  // Helpfulness
  const hasComparison = /\b(compared to|better than|worse than|unlike|similar to|reminds me of)\b/i.test(text);
  const hasExamples = /\b(for example|for instance|such as|like when|scene where|moment when)\b/i.test(text);
  const hasReasoning = /\b(because|since|due to|the reason|what makes|this works|this fails)\b/i.test(text);

  const helpfulness = Math.min(100, Math.round(
    detailScore * 0.5 +
    (hasComparison ? 20 : 0) +
    (hasExamples ? 15 : 0) +
    (hasReasoning ? 15 : 0)
  ));

  // Coherence
  const uniqueRatio = new Set(ws).size / Math.max(1, wordCount);
  const avgClauseLen = wordCount / Math.max(1, clauseCount);
  const coherence = Math.min(100, Math.round(
    uniqueRatio * 60 +
    (avgClauseLen >= 8 && avgClauseLen <= 25 ? 40 : 20)
  ));

  return {
    word_count: wordCount,
    clause_count: clauseCount,
    aspect_mentions: aspectMentions,
    detail_score: detailScore,
    helpfulness,
    coherence,
    has_comparison: hasComparison,
    has_examples: hasExamples,
    has_reasoning: hasReasoning,
  };
}


/* ── Full Review Analysis ── */

export function analyze(text, id) {
  const cs = split(text);
  const aspects = {};

  for (const [name, aliases] of Object.entries(tax.aspects || {})) {
    const matches = cs.filter((c) => aliases.some((a) => phrase(c, a)));
    const scored = matches.filter((c) => !sentiment(c).uncertain);

    aspects[name] = {
      score: scored.length
        ? Math.round(
            scored.reduce((a, c) => a + sentiment(c).sentiment_index, 0) /
              scored.length
          )
        : null,
      mentions: matches.length,
      scored_mentions: scored.length,
      evidence: scored.slice(0, 3),
    };
  }

  const tags = (group) =>
    Object.entries(tax[group] || {})
      .map(([name, aliases]) => {
        const e = cs.filter((c) => aliases.some((a) => phrase(c, a)));
        return {
          name,
          relevance: Math.round((e.length / Math.max(cs.length, 1)) * 100),
          evidence: e,
        };
      })
      .filter((t) => t.evidence.length);

  const sentimentResult = sentiment(text);
  const qualityResult = reviewQuality(text);

  return {
    text,
    sentiment: sentimentResult,
    aspects,
    genres: tags('genres'),
    themes: tags('themes'),
    authenticity: authenticity(
      text,
      reviews(id).map((r) => r.text)
    ),
    quality: qualityResult,
  };
}


/* ── Review Summary ── */

export function summary(id) {
  const rows = reviews(id);
  const seen = [];
  const accepted = [];
  const flagged = [];
  let dup = 0;

  // Screen reviews
  for (const r of rows) {
    const q = authenticity(r.text, seen);
    seen.push(r.text);

    if (q.duplicate) {
      dup++;
      continue;
    }

    if (q.needs_review) {
      flagged.push(r.review_id);
      continue;
    }

    accepted.push(r);
  }

  // Aggregate aspects
  const aspects = {};
  const counts = { positive: 0, negative: 0, mixed: 0, neutral: 0, uncertain: 0 };
  const excerpts = [];

  accepted.forEach((r) => {
    const s = sentiment(r.text);
    if (s.uncertain) counts.uncertain++;
    else counts[s.label]++;
  });

  for (const a of Object.keys(tax.aspects || {})) {
    const found = accepted
      .map((r) => ({ r, a: analyze(r.text, id).aspects[a] }))
      .filter((x) => x.a.score !== null);

    aspects[a] = {
      score: found.length
        ? Math.round(
            found.reduce((s, x) => s + x.a.score, 0) / found.length
          )
        : null,
      review_count: found.length,
      evidence: found
        .slice(0, 3)
        .map((x) => ({ review_id: x.r.review_id, text: x.a.evidence[0] })),
    };
  }

  // Extract excerpts
  for (const polarity of ['positive', 'negative']) {
    const used = new Set();
    for (const r of accepted) {
      for (const c of split(r.text)) {
        const s = sentiment(c);
        if (!s.uncertain && s.label === polarity && !used.has(c) && used.size < 3) {
          excerpts.push({ review_id: r.review_id, text: c, polarity });
          used.add(c);
        }
      }
    }
  }

  // Build summary text
  const strong = Object.entries(aspects)
    .filter(([, v]) => v.score >= 65)
    .sort((a, b) => b[1].score - a[1].score)
    .slice(0, 3)
    .map(([k]) => k.toLowerCase());

  const weak = Object.entries(aspects)
    .filter(([, v]) => v.score !== null && v.score < 45)
    .map(([k]) => k.toLowerCase());

  let s = accepted.length
    ? `Across ${accepted.length} eligible reviews, ${counts.positive} lean positive, ${counts.negative} lean negative, ${counts.mixed} are mixed and ${counts.neutral} are neutral; ${counts.uncertain} are low-confidence.`
    : 'No eligible reviews yet. Discover this film through its genres, themes and synopsis.';

  if (strong.length) s += ' Praise centers on ' + strong.join(', ') + '.';
  if (weak.length) s += ' Criticism centers on ' + weak.join(', ') + '.';
  if (accepted.length && accepted.length < 5) s += ' This is a small sample.';

  // Compute sentiment distribution
  const sentimentDistribution = {};
  if (accepted.length) {
    const allScores = accepted.map((r) => sentiment(r.text).sentiment_index);
    sentimentDistribution.mean = Math.round(allScores.reduce((a, b) => a + b, 0) / allScores.length * 10) / 10;
    sentimentDistribution.min = Math.min(...allScores);
    sentimentDistribution.max = Math.max(...allScores);
  }

  return {
    summary: s,
    total_reviews: rows.length,
    eligible_reviews: accepted.length,
    duplicates_excluded: dup,
    flagged_review_ids: flagged,
    sentiment_counts: counts,
    sentiment_distribution: sentimentDistribution,
    aspects,
    excerpts,
    synthetic_demo: rows.some((r) => r.source === 'synthetic-demo'),
  };
}


/* ── Save User Review ── */

export function saveReview(id, text) {
  const r = {
    review_id: crypto.randomUUID(),
    movie_id: id,
    text,
    source: 'browser-user',
    created_at: new Date().toISOString(),
  };

  const analysis = analyze(text, id);
  write('cinescope.reviews', [...read('cinescope.reviews', []), r]);

  return {
    review: r,
    analysis,
    review_summary: summary(id),
  };
}


/* ── Recommendations Engine ── */

export function recommend(query = '', genres = [], themes = [], limit = 12) {
  const rows = history();
  const seen = new Set(rows.map((r) => r.movie_id));

  // Build preference profile from ratings
  const prefs = {};
  for (const r of rows) {
    const m = catalog.find((m) => m.movie_id === r.movie_id);
    if (m) {
      for (const t of [...m.genres, ...m.themes]) {
        prefs[t] = (prefs[t] || 0) + (r.rating - 3);
      }
    }
  }

  const qw = words(query).filter((w) => w.length > 2);

  return catalog
    .filter(
      (m) =>
        !seen.has(m.movie_id) &&
        genres.every((g) => m.genres.includes(g)) &&
        themes.every((t) => m.themes.includes(t))
    )
    .map((m) => {
      const tags = [...m.genres, ...m.themes];
      const doc = [m.title, m.overview, ...tags].join(' ').toLowerCase();

      // Score: taste affinity + query relevance
      const score =
        tags.reduce((s, t) => s + (prefs[t] || 0), 0) / Math.sqrt(tags.length) +
        qw.filter((w) => doc.includes(w)).length * 2;

      const matching = tags.filter((t) => (prefs[t] || 0) > 0);

      return {
        ...m,
        rank_score: score,
        reasons: [
          matching.length
            ? 'Because you enjoy ' + matching.slice(0, 3).join(' + ')
            : query
            ? 'Matches your description'
            : 'Rate a few films to personalize your picks',
        ],
        cold_start: true,
      };
    })
    .sort((a, b) => b.rank_score - a.rank_score || a.movie_id - b.movie_id)
    .slice(0, limit);
}


/* ── Conversational Chat Engine ── */

export function chat(message, context = {}) {
  const text = message.toLowerCase();
  context = { ...context };

  if (/reset|start over|clear filters/.test(text)) context = {};

  // Try to match a movie title
  const movie =
    [...catalog]
      .sort((a, b) => b.title.length - a.title.length)
      .find((m) => phrase(text, m.title)) ||
    catalog.find((m) => m.movie_id === context.movie_id);

  // Review summary queries
  if (/\b(review|reviews|summary|summari[sz]e|pacing|acting|ending)\b/.test(text)) {
    if (!movie) {
      return {
        answer: 'Which movie would you like a review summary for?',
        movies: [],
        context,
      };
    }

    const s = summary(movie.movie_id);
    context.movie_id = movie.movie_id;

    return {
      answer:
        movie.title +
        ': ' +
        s.summary +
        (s.synthetic_demo ? ' These are synthetic sample reviews.' : ''),
      movies: [movie],
      context,
      review_summary: s,
    };
  }

  // Build genre/theme filters from conversation
  const chatGenres = [...(context.genres || [])];
  const chatThemes = [...(context.themes || [])];
  const excluded = [...(context.excluded || [])];

  for (const [group, active] of [
    ['genres', chatGenres],
    ['themes', chatThemes],
  ]) {
    for (const [label, aliases] of Object.entries(tax[group] || {})) {
      if (!aliases.some((a) => phrase(text, a))) continue;

      const negative = aliases.some((a) =>
        new RegExp(
          '\\b(?:no|not|without|avoid|exclude)\\s+(?:any\\s+)?' + a + '\\b',
          'i'
        ).test(text)
      );

      if (negative) {
        const i = active.indexOf(label);
        if (i >= 0) active.splice(i, 1);
        if (!excluded.includes(label)) excluded.push(label);
      } else {
        if (!active.includes(label)) active.push(label);
        const i = excluded.indexOf(label);
        if (i >= 0) excluded.splice(i, 1);
      }
    }
  }

  // Runtime filters
  if (/shorter|under|less than/.test(text)) {
    context.max_runtime = Number(
      text.match(/(\d{2,3})\s*(?:min|minute)/)?.[1] || 120
    );
  }
  if (/any length|no time limit/.test(text)) {
    delete context.max_runtime;
  }

  // Build search query
  let query = message;
  if (movie) {
    context.movie_id = movie.movie_id;
    query += ' ' + [...movie.genres, ...movie.themes].join(' ');
  }

  // Get recommendations with filters applied
  let results = recommend(query, chatGenres, [], 40).filter(
    (m) =>
      !excluded.some((t) => [...m.genres, ...m.themes].includes(t)) &&
      (!context.max_runtime || m.runtime <= context.max_runtime) &&
      m.movie_id !== movie?.movie_id
  );

  // Re-sort by theme relevance if themes are specified
  if (chatThemes.length) {
    results.sort(
      (a, b) =>
        chatThemes.filter((t) => b.themes.includes(t)).length -
          chatThemes.filter((t) => a.themes.includes(t)).length ||
        b.rank_score - a.rank_score
    );
  }

  results = results.slice(0, 4);
  Object.assign(context, { genres: chatGenres, themes: chatThemes, excluded });

  return {
    answer: results.length
      ? `Here are ${results.length} films for ${chatGenres.join(' + ') || 'your mood'}. ` +
        results
          .map(
            (m) =>
              m.title +
              ' explores ' +
              m.themes.slice(0, 2).join(' and ').toLowerCase() +
              '.'
          )
          .join(' ')
      : 'No unseen films here match every filter. Try a broader request, or say "reset".',
    movies: results,
    context,
  };
}
