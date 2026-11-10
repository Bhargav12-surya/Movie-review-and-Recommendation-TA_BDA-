"""Explicitly opted-in PostgreSQL harness, with transactional test-only schema.

The caller supplies an existing, disposable local *_test or *_tests database.
pgvector must already be installed in public by its owner. This helper installs
nothing, migrates no existing schema, and removes its own schema by rolling back
the transaction that created it. Application commits release savepoints only.
"""
from pathlib import Path
import os
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]


class PostgresSandbox:
    def __enter__(self):
        if os.environ.get('RUN_POSTGRES_TESTS') != '1':
            raise unittest.SkipTest('Opt in with RUN_POSTGRES_TESTS=1 after manually preparing a disposable database.')
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine import make_url
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import NullPool
        value = os.environ.get('MOVIE_TEST_DATABASE_URL', '')
        if not value:
            raise unittest.SkipTest('MOVIE_TEST_DATABASE_URL must identify a disposable local *_test or *_tests database.')
        try:
            url = make_url(value)
        except Exception:
            raise RuntimeError('The private test database URL is invalid; its contents are redacted.') from None
        if (url.drivername != 'postgresql+psycopg' or url.host not in {'localhost', '127.0.0.1', '::1'}
                or not url.database or not url.database.endswith(('_test', '_tests'))):
            raise RuntimeError('Tests require postgresql+psycopg, a loopback host and a *_test or *_tests database.')
        self.schema = 'movie_test_' + uuid.uuid4().hex
        self.engine = create_engine(url, poolclass=NullPool, hide_parameters=True, echo=False,
                                    connect_args={'connect_timeout': 5, 'options': '-c statement_timeout=10000 -c lock_timeout=3000'})
        self.connection = None
        self.transaction = None
        try:
            self.connection = self.engine.connect()
            self.transaction = self.connection.begin()
            installed = self.connection.scalar(text("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'"))
            if installed != 'public':
                raise RuntimeError('Manually enable pgvector in public in the disposable database before testing.')
            self.connection.execute(text(f'CREATE SCHEMA "{self.schema}"'))
            self.connection.execute(text(f'SET LOCAL search_path TO "{self.schema}", public'))
            ddl = (ROOT / 'backend/alembic/schema_v1.sql').read_text(encoding='utf-8-sig')
            for raw in ddl.split(';'):
                statement = '\n'.join(line for line in raw.splitlines() if not line.lstrip().startswith('--')).strip()
                if statement and not statement.upper().startswith('CREATE EXTENSION'):
                    self.connection.execute(text(statement))
            self.factory = sessionmaker(bind=self.connection, expire_on_commit=False,
                                        join_transaction_mode='create_savepoint')
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise RuntimeError('Disposable PostgreSQL setup failed; check prerequisites and permissions. Connection details are redacted.') from None

    def __exit__(self, exc_type, exc, tb):
        if self.transaction is not None and self.transaction.is_active:
            self.transaction.rollback()
        if self.connection is not None:
            self.connection.close()
        self.engine.dispose()


def database_dependency(factory):
    def session():
        with factory() as value:
            try:
                yield value
            except Exception:
                value.rollback()
                raise
    return session
