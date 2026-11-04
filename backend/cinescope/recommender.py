"""Signed, recency-weighted content + optional Spark ALS fold-in + diversity."""
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from .reviews import ROOT, TAXONOMY, has_phrase


def movie_document(movie):
    # Repeated structured tags make genre/theme interactions matter alongside synopsis.
    return ' '.join(movie.get('genres', [])*3 + movie.get('themes', [])*3 + [movie.get('overview', '')])


class Recommender:
    def __init__(self, movies, model_dir=None):
        self.movies = movies
        self.ids = {int(m['movie_id']): i for i, m in enumerate(movies)}
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english', sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform([movie_document(m) for m in movies])
        self.encoder = None
        embedding_path = os.getenv('CINESCOPE_EMBEDDING_MODEL')
        if embedding_path:
            from sentence_transformers import SentenceTransformer
            self.encoder = SentenceTransformer(embedding_path, local_files_only=True)
            self.embeddings = self.encoder.encode([movie_document(m) for m in movies], normalize_embeddings=True)
        self.factors = None
        location = Path(model_dir or os.getenv('CINESCOPE_MODEL_DIR') or ROOT / 'models') / 'als_factors.npz'
        # Demo IDs are deliberately a separate namespace from real MovieLens IDs.
        if location.exists() and not any(m.get('source') == 'demo' for m in movies):
            data = np.load(location, allow_pickle=False)
            self.factor_ids = {int(mid): i for i, mid in enumerate(data['movie_ids'])}
            self.factors = data['factors']
            self.reg = float(data['reg_param']) if 'reg_param' in data else .1

    def recommend(self, history=(), query='', genres=(), themes=(), limit=12):
        n = len(self.movies)
        if not n: return []
        signed = np.zeros(n)
        for row in history:
            idx = self.ids.get(int(row['movie_id']))
            if idx is None: continue
            age = 0
            try:
                age = max(0, (datetime.now(timezone.utc)-datetime.fromisoformat(row['updated_at'].replace('Z','+00:00'))).days)
            except (KeyError, ValueError, TypeError): pass
            signed[idx] = (float(row['rating'])-3) * np.exp(-age/365)
        seen = {int(r['movie_id']) for r in history}
        query_vec = self.vectorizer.transform([query])
        profile = np.asarray(signed @ self.matrix).reshape(1,-1)
        profile = normalize(profile)
        content = np.asarray(self.matrix @ profile.T).ravel()
        relevance = (self.matrix @ query_vec.T).toarray().ravel()
        if self.encoder is not None and query.strip():
            emb = self.encoder.encode([query], normalize_embeddings=True)[0]
            relevance = np.asarray(self.embeddings @ emb)
        # The signed profile penalizes disliked features rather than rewarding every watch.
        score = .6*content + (1.2*relevance if query.strip() else 0)
        als_mask = np.zeros(n, dtype=bool)
        if self.factors is not None:
            known = [(self.factor_ids[int(r['movie_id'])], float(r['rating'])) for r in history if int(r['movie_id']) in self.factor_ids]
            if known:
                y = self.factors[[i for i,_ in known]]
                values = np.array([v for _,v in known])
                x = np.linalg.solve(y.T@y + self.reg*len(known)*np.eye(y.shape[1]), y.T@values)
                for mid, idx in self.ids.items():
                    if mid in self.factor_ids:
                        pred = float(self.factors[self.factor_ids[mid]] @ x)
                        score[idx] += .55*(np.clip(pred, .5, 5)-3)/2
                        als_mask[idx] = True
        # Only a weak Bayesian rating prior; metadata-only titles receive the neutral mean.
        for i, movie in enumerate(self.movies):
            count = float(movie.get('rating_count', 0))
            mean = float(movie.get('rating_mean', 3))
            prior = (count*mean + 25*3)/(count+25)
            score[i] += .05*(prior-3)/2
        wanted_g = {x.casefold() for x in genres}
        wanted_t = {x.casefold() for x in themes}
        candidates = [i for i,m in enumerate(self.movies) if m['movie_id'] not in seen
                      and wanted_g.issubset({g.casefold() for g in m.get('genres',[])})
                      and wanted_t.issubset({t.casefold() for t in m.get('themes',[])})]
        candidates.sort(key=lambda i: (-float(score[i]), self.movies[i]['title']))
        # Bounded candidate set avoids a dense catalog-by-catalog similarity matrix.
        pool, selected = candidates[:200], []
        while pool and len(selected) < limit:
            def mmr(i):
                redundancy = max(((self.matrix[i] @ self.matrix[j].T)[0,0] for j in selected), default=0.)
                return .9*score[i] - .1*redundancy
            idx = max(pool, key=mmr); pool.remove(idx); selected.append(idx)
        positives = [self.movies[self.ids[int(r['movie_id'])]] for r in history if float(r['rating']) >= 3.5 and int(r['movie_id']) in self.ids]
        preferred = set(g for m in positives for g in m.get('genres',[]) + m.get('themes',[]))
        result=[]
        for i in selected:
            m = self.movies[i]
            overlap = [x for x in m.get('genres',[]) + m.get('themes',[]) if x in preferred]
            reasons = []
            if overlap: reasons.append('Matches your highly rated ' + ' + '.join(overlap[:3]) + ' films')
            if query: reasons.append('Retrieved for your description')
            if als_mask[i]: reasons.append('Also ranked by learned MovieLens factors')
            if not reasons: reasons.append('Explore this title; rate a few films to personalize')
            result.append({**m, 'rank_score': round(float(score[i]), 4), 'reasons': reasons,
                           'cold_start': not als_mask[i], 'rank_method': 'content + ALS' if als_mask[i] else 'content',
                           'score_note': 'Ranking score is not a predicted enjoyment percentage.'})
        return result
