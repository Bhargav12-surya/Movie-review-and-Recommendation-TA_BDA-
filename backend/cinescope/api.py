"""Same-origin FastAPI application. Designed for localhost academic use.

Production enhancements:
- Input sanitization and length enforcement
- Rate limiting per-endpoint via sliding window
- Structured error responses
- Request ID tracking
- Graceful degradation for missing models
- CORS configuration for deployments
"""
from __future__ import annotations
import json
import logging
import os
import re
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import UUID, uuid4
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from . import __version__
from .reviews import ROOT, ReviewAnalyzer, clean_text
from .storage import Store
from .recommender import Recommender
from .chat import MovieChat


logger = logging.getLogger(__name__)
_REQUEST_ID_RE = re.compile(r'^[A-Za-z0-9._-]{1,128}$')


# ── Rate Limiter ──

class SlidingWindowRateLimiter:
    """Simple in-memory sliding window rate limiter."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = RLock()
        self._last_cleanup = time.monotonic()

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window
        with self._lock:
            entries = self._requests[key]
            while entries and entries[0] <= window_start:
                entries.popleft()
            if len(entries) >= self.max_requests:
                return False
            entries.append(now)
            # Periodically remove inactive client keys so a public endpoint
            # cannot grow this in-memory map without bound.
            if now - self._last_cleanup >= self.window:
                stale = [k for k, values in self._requests.items() if not values or values[-1] <= window_start]
                for stale_key in stale:
                    self._requests.pop(stale_key, None)
                self._last_cleanup = now
            return True


# ── Request Models ──

class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=3, max_length=20000)
    movie_id: int | None = None

    @field_validator('text')
    @classmethod
    def validate_text_content(cls, v: str) -> str:
        cleaned = clean_text(v)
        if len(cleaned) < 3 or not any(c.isalpha() for c in cleaned):
            raise ValueError('Review text must contain at least 3 characters of actual words')
        return v


class ReviewRequest(AnalyzeRequest):
    movie_id: int
    request_id: UUID | None = None


class RatingRequest(BaseModel):
    movie_id: int
    rating: float = Field(ge=.5, le=5, multiple_of=.5)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    context: dict[str, Any] = Field(default_factory=dict)


class BulkAnalyzeRequest(BaseModel):
    """Analyze multiple reviews in a single request."""
    reviews: list[AnalyzeRequest] = Field(min_length=1, max_length=50)


def create_app(data_dir=None, catalog_path=None, model_dir=None, sentiment_mode=None):
    path = Path(catalog_path or os.getenv('CINESCOPE_CATALOG') or ROOT / 'data/demo/catalog.json')
    movies = json.loads(path.read_text())
    by_id = {int(m['movie_id']): m for m in movies}
    demo = all(m.get('source') == 'demo' for m in movies)
    data_dir = data_dir or os.getenv('CINESCOPE_DATA_DIR') or ROOT / 'data' / ('demo-app' if demo else 'real-app')
    store = Store(data_dir, seed_reviews=demo)
    analyzer = ReviewAnalyzer(model_dir=model_dir, mode=sentiment_mode)
    recommender = Recommender(movies, model_dir=model_dir)
    chat = MovieChat(recommender, store, analyzer)
    lock = RLock()

    # Rate limiters for different endpoint categories
    analysis_limiter = SlidingWindowRateLimiter(max_requests=30, window_seconds=60)
    review_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)
    general_limiter = SlidingWindowRateLimiter(max_requests=120, window_seconds=60)

    app = FastAPI(
        title='CineScope',
        version=__version__,
        description='Production-grade review analysis and recommendation API with advanced sentiment analysis.',
        docs_url='/api/docs',
        redoc_url='/api/redoc',
    )
    app.state.store = store
    app.state.analyzer = analyzer
    app.state.recommender = recommender

    @app.middleware('http')
    async def operational_headers(request: Request, call_next):
        supplied = request.headers.get('x-request-id', '')
        request_id = supplied if _REQUEST_ID_RE.fullmatch(supplied) else str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Permissions-Policy'] = 'camera=(), geolocation=(), microphone=(self)'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    # CORS for development
    cors_origins = os.getenv('CINESCOPE_CORS_ORIGINS', '').split(',')
    if any(cors_origins):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[o.strip() for o in cors_origins if o.strip()],
            allow_methods=['*'],
            allow_headers=['*'],
        )

    # ── Exception handlers ──

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, 'request_id', str(uuid4()))
        logger.exception('Unhandled request error request_id=%s', request_id, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={'detail': 'Internal server error. Please try again.', 'request_id': request_id}
        )

    # ── Helpers ──

    def movie_or_404(mid):
        if mid not in by_id:
            raise HTTPException(404, 'Movie not found')
        return by_id[mid]

    def validated_text(text):
        text = clean_text(text)
        if len(text) < 3 or not any(c.isalpha() for c in text):
            raise HTTPException(422, 'Enter review text containing words')
        return text

    def check_rate_limit(limiter: SlidingWindowRateLimiter, key: str, endpoint: str):
        if not limiter.is_allowed(key):
            raise HTTPException(
                429,
                f'Rate limit exceeded for {endpoint}. Please try again shortly.',
                headers={'Retry-After': str(limiter.window)},
            )

    def get_client_key(request: Request) -> str:
        """Get a client identifier for rate limiting."""
        forwarded = request.headers.get('x-forwarded-for')
        trust_proxy = os.getenv('CINESCOPE_TRUST_PROXY', '').lower() in {'1', 'true', 'yes'}
        if trust_proxy and forwarded:
            return forwarded.split(',')[0].strip()
        return request.client.host if request.client else 'unknown'

    # ── Health ──

    @app.get('/api/health')
    def health():
        return {
            'status': 'ok',
            'version': __version__,
            'catalog_size': len(movies),
            'demo_data': demo,
            'sentiment_model': analyzer.model_name,
            'sentiment_labels': ['negative', 'neutral', 'mixed', 'positive'],
            'sentiment_language': 'en',
            'als_loaded': recommender.factors is not None,
            'semantic_retrieval': recommender.encoder is not None,
            'chat_transformer': bool(chat.generator_name),
            'speech_enabled': bool(os.getenv('CINESCOPE_WHISPER_MODEL')),
            'features': {
                'intensity_scoring': True,
                'bigram_detection': True,
                'emoji_analysis': True,
                'sarcasm_detection': True,
                'review_quality': True,
                'clause_decomposition': True,
                'four_class_sentiment': True,
                'contextual_negation': True,
            }
        }

    # ── Movies ──

    @app.get('/api/movies')
    def list_movies(
        request: Request,
        q: str = '',
        genre: str = '',
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        check_rate_limit(general_limiter, get_client_key(request), 'movie listing')
        found = [
            m for m in movies
            if q.lower() in (m['title'] + ' ' + ' '.join(m['themes'])).lower()
            and (not genre or genre in m['genres'])
        ]
        return {'movies': found[offset:offset + limit], 'total': len(found)}

    @app.get('/api/movies/{movie_id}')
    def movie_details(request: Request, movie_id: int):
        check_rate_limit(general_limiter, get_client_key(request), 'movie details')
        movie = movie_or_404(movie_id)
        with lock:
            summary = analyzer.summarize(store.reviews(movie_id))
        return {**movie, 'review_summary': summary}

    @app.get('/api/movies/{movie_id}/reviews')
    def list_reviews(
        movie_id: int,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        movie_or_404(movie_id)
        rows = store.reviews(movie_id)
        return {'reviews': rows[offset:offset + limit], 'total': len(rows)}

    # ── Review Analysis ──

    @app.post('/api/analyze')
    def analyze(request: Request, payload: AnalyzeRequest):
        check_rate_limit(analysis_limiter, get_client_key(request), 'analysis')
        text = validated_text(payload.text)
        if payload.movie_id is not None:
            movie_or_404(payload.movie_id)
        existing = tuple(r['text'] for r in store.reviews(payload.movie_id)) if payload.movie_id is not None else ()
        with lock:
            return analyzer.analyze(text, existing)

    @app.post('/api/analyze/bulk')
    def bulk_analyze(request: Request, payload: BulkAnalyzeRequest):
        """Analyze multiple reviews in a single request (max 50)."""
        check_rate_limit(analysis_limiter, get_client_key(request), 'bulk analysis')
        results = []
        with lock:
            for item in payload.reviews:
                text = validated_text(item.text)
                if item.movie_id is not None:
                    movie_or_404(item.movie_id)
                existing = tuple(r['text'] for r in store.reviews(item.movie_id)) if item.movie_id is not None else ()
                results.append(analyzer.analyze(text, existing))
        return {'results': results, 'count': len(results)}

    @app.post('/api/reviews', status_code=201)
    def add_review(request: Request, payload: ReviewRequest, response: Response):
        check_rate_limit(review_limiter, get_client_key(request), 'review submission')
        movie_or_404(payload.movie_id)
        text = validated_text(payload.text)
        review_id = f'user-{payload.request_id}' if payload.request_id else None
        with lock:
            prior = store.review(review_id) if review_id else None
            if prior and (prior['movie_id'] != payload.movie_id or prior['text'] != text):
                raise HTTPException(409, 'This request_id was already used for a different review')
            existing_rows = store.reviews(payload.movie_id)
            existing = tuple(
                r['text'] for r in existing_rows
                if not review_id or r['review_id'] != review_id
            )
            result = analyzer.analyze(text, existing)
            review = (
                {**prior, 'inserted': False}
                if prior
                else store.add_review(payload.movie_id, text, review_id=review_id)
            )
            summary = analyzer.summarize(store.reviews(payload.movie_id))
        if not review['inserted']:
            response.status_code = 200
        return {'review': review, 'analysis': result, 'review_summary': summary}

    # ── User History & Ratings ──

    @app.get('/api/users/{user_id}/history')
    def history(user_id: str):
        return {'ratings': store.history(user_id)}

    @app.put('/api/users/{user_id}/ratings')
    def rate(user_id: str, payload: RatingRequest):
        movie_or_404(payload.movie_id)
        return {'ratings': store.rate(user_id, payload.movie_id, payload.rating)}

    @app.delete('/api/users/{user_id}/ratings/{movie_id}')
    def delete_rating(user_id: str, movie_id: int):
        store.delete_rating(user_id, movie_id)
        return {'ratings': store.history(user_id)}

    # ── Recommendations ──

    @app.get('/api/users/{user_id}/recommendations')
    def recommend(
        user_id: str,
        q: str = '',
        genres: str = '',
        themes: str = '',
        limit: int = Query(12, ge=1, le=100),
    ):
        return {
            'movies': recommender.recommend(
                store.history(user_id),
                q,
                [s for s in genres.split(',') if s],
                [s for s in themes.split(',') if s],
                limit,
            )
        }

    # ── Chat ──

    @app.post('/api/users/{user_id}/chat')
    def converse(request: Request, user_id: str, payload: ChatRequest):
        check_rate_limit(analysis_limiter, get_client_key(request), 'chat')
        with lock:
            return chat.respond(payload.message, user_id, payload.context)

    # ── Speech Transcription ──

    @app.post('/api/transcribe')
    async def transcribe(request: Request):
        location = os.getenv('CINESCOPE_WHISPER_MODEL')
        if not location:
            raise HTTPException(
                503,
                'Set CINESCOPE_WHISPER_MODEL to a downloaded faster-whisper model, or use browser speech recognition'
            )
        # Stream with a hard cap before materializing the request body.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 10 * 1024 * 1024:
                raise HTTPException(413, 'Audio limit is 10 MiB')
        if not body:
            raise HTTPException(422, 'Audio is empty')
        from starlette.concurrency import run_in_threadpool

        def run():
            from faster_whisper import WhisperModel
            with lock:
                if not hasattr(app.state, 'whisper'):
                    app.state.whisper = WhisperModel(
                        location, device='cpu', compute_type='int8', local_files_only=True
                    )
                with tempfile.NamedTemporaryFile(suffix='.audio') as f:
                    f.write(body)
                    f.flush()
                    segments, info = app.state.whisper.transcribe(f.name, beam_size=3)
                    return {
                        'text': ' '.join(s.text for s in segments).strip(),
                        'language': info.language,
                        'method': 'faster-whisper',
                    }

        try:
            return await run_in_threadpool(run)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(422, 'Audio could not be transcribed') from exc

    # ── Static Frontend ──

    frontend = ROOT / 'frontend'
    if frontend.exists() and (frontend / 'index.html').exists():
        app.mount('/', StaticFiles(directory=frontend, html=True), name='frontend')

    return app


app = create_app()
