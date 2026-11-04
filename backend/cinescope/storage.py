"""SQLite persistence for the local research app; idempotent review ingestion."""
from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4
from .reviews import ROOT


class Store:
    def __init__(self, directory, seed_reviews=True):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db = self.directory / 'cinescope.sqlite3'
        with self.connect() as c:
            c.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY, movie_id INTEGER NOT NULL,
                text TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS reviews_movie ON reviews(movie_id);
            CREATE TABLE IF NOT EXISTS ratings (
                user_id TEXT NOT NULL, movie_id INTEGER NOT NULL,
                rating REAL NOT NULL CHECK(rating BETWEEN 0.5 AND 5),
                updated_at TEXT NOT NULL, PRIMARY KEY(user_id,movie_id));
            ''')
            if seed_reviews:
                for r in json.loads((ROOT / 'data/demo/reviews.json').read_text()):
                    c.execute('INSERT OR IGNORE INTO reviews VALUES (?,?,?,?,?)', tuple(r[k] for k in ('review_id','movie_id','text','source','created_at')))

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA busy_timeout=30000')
        c.execute('PRAGMA foreign_keys=ON')
        try:
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def reviews(self, movie_id):
        with self.connect() as c:
            return [dict(x) for x in c.execute('SELECT * FROM reviews WHERE movie_id=? ORDER BY created_at,review_id', (movie_id,))]

    def review(self, review_id):
        with self.connect() as c:
            row = c.execute('SELECT * FROM reviews WHERE review_id=?', (review_id,)).fetchone()
            return dict(row) if row else None

    def add_review(self, movie_id, text, source='user', review_id=None, created_at=None):
        r = dict(review_id=review_id or str(uuid4()), movie_id=movie_id, text=text, source=source,
                 created_at=created_at or datetime.now(timezone.utc).isoformat())
        with self.connect() as c:
            result = c.execute(
                'INSERT OR IGNORE INTO reviews VALUES (?,?,?,?,?)',
                tuple(r[k] for k in ('review_id', 'movie_id', 'text', 'source', 'created_at')),
            )
            inserted = result.rowcount == 1
        # The database is the source of truth. Export its events for Spark with export_events.py.
        return {**r, 'inserted': inserted}

    def rate(self, user_id, movie_id, rating):
        with self.connect() as c:
            c.execute('INSERT INTO ratings VALUES (?,?,?,?) ON CONFLICT(user_id,movie_id) DO UPDATE SET rating=excluded.rating,updated_at=excluded.updated_at',
                      (user_id, movie_id, rating, datetime.now(timezone.utc).isoformat()))
        return self.history(user_id)

    def history(self, user_id):
        with self.connect() as c:
            return [dict(x) for x in c.execute('SELECT * FROM ratings WHERE user_id=? ORDER BY updated_at DESC', (user_id,))]

    def delete_rating(self, user_id, movie_id):
        with self.connect() as c:
            c.execute('DELETE FROM ratings WHERE user_id=? AND movie_id=?', (user_id, movie_id))
