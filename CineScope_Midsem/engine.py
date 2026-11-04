"""Small, explainable English baseline. Scores are heuristic indices, not accuracy."""
import html
import math
import re
from collections import Counter

ASPECTS = {
    'Story': ['story', 'plot', 'script', 'writing'],
    'Acting': ['acting', 'actor', 'actors', 'cast', 'performance', 'performances'],
    'Visuals': ['visuals', 'visual', 'cinematography', 'effects', 'animation'],
    'Music': ['music', 'soundtrack', 'score', 'songs'],
    'Pacing': ['pacing', 'pace', 'slow', 'dragged', 'rushed'],
    'Ending': ['ending', 'climax', 'finale'],
}
THEMES = {'Friendship': ['friendship', 'friends'], 'Family': ['family', 'parent', 'father', 'mother'],
          'Love': ['love', 'romance', 'romantic'], 'Survival': ['survival', 'survive'],
          'Revenge': ['revenge'], 'Identity': ['identity', 'memory'],
          'Space': ['space', 'planet', 'astronaut'], 'Justice': ['justice', 'crime']}
GENRES = {'Action': ['action', 'fight', 'chase'], 'Comedy': ['comedy', 'funny', 'humor'],
          'Drama': ['drama', 'dramatic'], 'Horror': ['horror', 'scary'],
          'Romance': ['romance', 'romantic'], 'Sci-Fi': ['science fiction', 'sci-fi', 'scifi'],
          'Thriller': ['thriller', 'suspense'], 'Animation': ['animation', 'animated']}
POS = set('good great excellent amazing brilliant wonderful beautiful enjoyable entertaining powerful perfect fantastic loved love liked funny moving compelling stunning satisfying strong engaging fast'.split())
NEG = set('bad awful terrible boring weak poor dull disappointing hated hate predictable confusing rushed dragged ugly annoying slow worst pointless'.split())
NEGATORS = {'not', 'no', 'never', 'hardly', 'barely'}


def clean(text):
    text = html.unescape(text).replace('\u2019', "'")
    text = re.sub(r'<[^>]*>', ' ', text).lower()
    for a, b in {"can't": 'can not', "won't": 'will not', "n't": ' not',
                 '😍': ' loved ', '😊': ' good ', '😡': ' awful ', '👎': ' bad ',
                 'gr8': 'great', 'meh': 'dull', 'luv': 'love'}.items():
        text = text.replace(a, b) if a == "n't" or not a.isalpha() else re.sub(r'\b'+a+r'\b', b, text)
    return re.sub(r'\s+', ' ', text).strip()


def tokens(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())


def clauses(text):
    return [s.strip(' ,') for s in re.split(r'[.!?;]+|\b(?:but|however|although|yet)\b', text) if s.strip(' ,')]


def mention(text, words):
    return any(re.search(r'(?<!\w)'+re.escape(w)+r'(?!\w)', text) for w in words)


def opinions(ts):
    result = []
    for i, t in enumerate(ts):
        sign = 1 if t in POS else -1 if t in NEG else 0
        if sign:
            if sum(x in NEGATORS for x in ts[max(0, i-3):i]) % 2:
                sign *= -1
            result.append((i, sign))
    return result


def index(values):
    return round(50 + 50 * sum(values)/len(values), 1) if values else None


def analyze(text):
    normalized = clean(text)
    parts = clauses(normalized)
    values = [v for p in parts for _, v in opinions(tokens(p))]
    score = index(values)
    result = {'cleaned': normalized, 'method': 'lexicon + nearest-aspect rules',
              'score': score, 'label': 'no evidence' if score is None else
              'positive' if score > 60 else 'negative' if score < 40 else 'mixed / balanced',
              'opinion_count': len(values), 'aspects': {}, 'themes': {}, 'genres': {}}
    collected = {a: [] for a in ASPECTS}
    for part in parts:
        ts = tokens(part)
        anchors = [(i, a) for i, word in enumerate(ts) for a, ws in ASPECTS.items() if word in ws]
        for position, value in opinions(ts):
            if not anchors:
                continue
            distance = min(abs(position-i) for i, _ in anchors)
            # Ties are skipped: avoid assigning one opinion to two nearby aspects.
            names = {a for i, a in anchors if abs(position-i) == distance}
            if distance <= 4 and len(names) == 1:
                collected[names.pop()].append((value, part))
    for name, evidence in collected.items():
        result['aspects'][name] = {'score': index([v for v, _ in evidence]),
                                  'evidence': list(dict.fromkeys(p for _, p in evidence))}
    for group, taxonomy in [('themes', THEMES), ('genres', GENRES)]:
        for name, ws in taxonomy.items():
            matched = [p for p in parts if mention(p, ws)]
            if matched:
                vals = [v for p in matched for _, v in opinions(tokens(p))]
                result[group][name] = {'score': index(vals), 'mentions': len(matched),
                    'coverage': round(100*len(matched)/max(1,len(parts)),1), 'evidence': matched}
    return result


def recommend(catalog, history, limit=6):
    """Rating-driven genre affinity + review-derived themes/aspect preferences."""
    by_id = {m['id']: m for m in catalog}
    seen = {h['id'] for h in history}
    genre, theme, aspect = Counter(), Counter(), Counter()
    for h in history:
        movie = by_id.get(h['id'])
        if not movie:
            continue
        weight = (h['rating']-3)/2
        for g in movie['genres']:
            genre[g] += weight
        review = analyze(h.get('review', ''))
        for t, r in review['themes'].items():
            if r['score'] is not None:
                theme[t] += (r['score']-50)/50
        for a, r in review['aspects'].items():
            if r['score'] is not None and r['score'] > 50:
                aspect[a] += (r['score']-50)/50
    scale = max(1, sum(abs((h['rating']-3)/2) for h in history))
    ranked = []
    for movie in catalog:
        if movie['id'] in seen:
            continue
        profiles = [analyze(r) for r in movie.get('reviews', [])]
        g = sum(genre[x] for x in movie['genres']) / (scale*max(1,len(movie['genres'])))
        present = {t for p in profiles for t in p['themes']}
        t = sum(theme[x] for x in present)/max(1,sum(abs(x) for x in theme.values()))
        matches = []
        for a, weight in aspect.items():
            scores = [p['aspects'][a]['score'] for p in profiles if p['aspects'][a]['score'] is not None]
            if scores:
                matches.append(weight * (sum(scores)/len(scores)-50)/50)
        a = sum(matches)/max(1,sum(aspect.values()))
        # Damped rating prior. Demo films have no fabricated community ratings.
        n, mean = movie.get('rating_count',0), movie.get('mean_rating',3)
        prior = ((n*mean + 20*3)/(n+20)-3)/2
        value = .65*g + .15*t + .15*a + .05*prior
        reasons = []
        liked = [x for x in movie['genres'] if genre[x] > 0]
        if liked: reasons.append('Liked genres: '+', '.join(liked))
        if t > 0: reasons.append('Review theme match')
        if a > 0: reasons.append('Review aspect match')
        if not reasons: reasons.append('Catalog fallback' if not history else 'Available unseen option')
        ranked.append({**movie, 'match': round(value,4), 'reasons': reasons,
                       'components': {'genre': round(g,3),'theme':round(t,3),'aspect':round(a,3),'prior':round(prior,3)}})
    return sorted(ranked,key=lambda m:(-m['match'],m['title']))[:limit]
