"""Actual PostgreSQL routes, ownership, revisions and durable-job contracts.

All records are invented fixtures in a transactionally isolated test schema.
No model outputs are mocked or written. No worker/inference job is executed.
"""
from datetime import timedelta
import os
import unittest
from unittest.mock import patch
from uuid import UUID

from backend.tests.postgres_support import PostgresSandbox, database_dependency


@unittest.skipUnless(os.environ.get('RUN_POSTGRES_TESTS') == '1', 'Disposable PostgreSQL tests require explicit opt-in.')
class PostgresAPITests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from backend.app.main import create_app
        from backend.app.core.config import BackendSettings
        from backend.app.database.session import get_session
        from backend.app.models import User, Movie, AuthSession
        from backend.app.auth.security import digest, new_token, now
        self.sandbox = self.enterContext(PostgresSandbox())
        settings = BackendSettings(_env_file=None, database_password='')
        with patch('backend.app.main.get_settings', return_value=settings):
            self.app = create_app()
        self.app.dependency_overrides[get_session] = database_dependency(self.sandbox.factory)
        self.client = self.enterContext(TestClient(self.app, raise_server_exceptions=True))
        self.tokens = []
        self.users = []
        with self.sandbox.factory() as session:
            for index in range(2):
                user = User(email=f'isolated-{index}@example.invalid', display_name='Synthetic API test account',
                            password_hash='unused-test-session-fixture')
                session.add(user); session.flush()
                token = new_token(); self.tokens.append(token); self.users.append(user.id)
                session.add(AuthSession(user_id=user.id, token_hash=digest(token), expires_at=now() + timedelta(minutes=5)))
            session.add(Movie(id=987654321, title='Synthetic isolation fixture', overview='Only for transactional tests.',
                              metadata_source='synthetic-test-only', canonical_mapping_approved=True, genres=['Drama']))
            session.commit()
        self.path = '/api/v1/movies/987654321/reviews'
        self.body = dict(text='Synthetic API test review, excluded from real audience evidence.', language_code='en',
                         evidence_permitted=False, training_permitted=False, moderation_permitted=False,
                         consent_version='isolated-test-only-v1')

    def headers(self, index=0, key='isolated-idempotency-key'):
        return {'Authorization': 'Bearer ' + self.tokens[index], 'Idempotency-Key': key}

    def submit(self):
        response = self.client.post(self.path, json=self.body, headers=self.headers())
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_submit_is_pending_and_replay_creates_no_second_review(self):
        from sqlalchemy import select, func
        from backend.app.models import Review, Job
        first, second = self.submit(), self.submit()
        self.assertEqual(first, second)
        self.assertEqual(first['analysis_status'], 'pending')
        with self.sandbox.factory() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Review)), 1)
            self.assertEqual(session.scalar(select(func.count()).select_from(Job)), 2)
        review = self.client.get('/api/v1/reviews/' + first['review_id'], headers=self.headers()).json()
        self.assertEqual(review['predictions'], {})

    def test_idempotency_payload_conflict_is_explicit(self):
        self.submit()
        response = self.client.post(self.path, json=self.body | {'text': 'Different isolated review text.'}, headers=self.headers())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error']['code'], 'idempotency_key_payload_conflict')

    def test_anonymous_and_other_owner_cannot_read_edit_delete(self):
        item = self.submit(); path = '/api/v1/reviews/' + item['review_id']
        self.assertEqual(self.client.get(path).status_code, 401)
        for method in ['get', 'patch', 'delete']:
            kwargs = {'json': self.body | {'expected_revision': 1}} if method == 'patch' else {}
            self.assertEqual(getattr(self.client, method)(path, headers=self.headers(1), **kwargs).status_code, 404)

    def test_edit_checks_revision_and_invalidates_existing_snapshot(self):
        from sqlalchemy import select
        from backend.app.models import Movie, MovieScore, MovieSummary, ReviewRevision
        item = self.submit(); path = '/api/v1/reviews/' + item['review_id']
        with self.sandbox.factory() as session:
            movie = session.get(Movie, 987654321)
            session.add(MovieScore(movie_id=movie.id, evidence_version=movie.evidence_version, score_type='overall',
                                   score=None, payload={'message': 'isolated-test-snapshot'}, model_version='test-only', method_version='test-only'))
            session.add(MovieSummary(movie_id=movie.id, evidence_version=movie.evidence_version, payload={'status': 'isolated-test'}))
            previous_version = movie.evidence_version
            session.commit()
        edited = self.client.patch(path, json=self.body | {'expected_revision': 1, 'text': 'Edited isolated API review text.'}, headers=self.headers())
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json()['revision'], 2)
        self.assertEqual(self.client.patch(path, json=self.body | {'expected_revision': 1}, headers=self.headers()).status_code, 409)
        with self.sandbox.factory() as session:
            self.assertEqual(session.get(Movie, 987654321).evidence_version, previous_version + 1)
            self.assertTrue(session.scalar(select(MovieScore)).is_stale)
            self.assertEqual(session.scalar(select(MovieSummary)).payload, {})
            self.assertEqual(session.get(ReviewRevision, (UUID(item['review_id']), 2)).text, 'Edited isolated API review text.')

    def test_delete_scrubs_text_and_queues_text_free_tombstone(self):
        from sqlalchemy import select, func
        from backend.app.models import Review, ReviewRevision, Job
        item = self.submit(); path = '/api/v1/reviews/' + item['review_id']
        self.assertEqual(self.client.delete(path, headers=self.headers()).status_code, 204)
        self.assertEqual(self.client.get(path, headers=self.headers()).status_code, 410)
        with self.sandbox.factory() as session:
            row = session.get(Review, UUID(item['review_id']))
            self.assertTrue(row.is_deleted)
            self.assertEqual(row.text, '')
            self.assertFalse(row.evidence_permitted)
            self.assertEqual(session.scalar(select(func.count()).select_from(ReviewRevision)), 0)
            event_job = session.scalar(select(Job).where(Job.kind == 'publish_event'))
            self.assertIsNotNone(event_job)
            self.assertNotIn('text', event_job.payload['event'])

    def test_database_constraints_reject_invalid_rating(self):
        from sqlalchemy.exc import IntegrityError
        from backend.app.models import Rating
        with self.sandbox.factory() as session:
            with self.assertRaises(IntegrityError):
                session.add(Rating(user_id=self.users[0], movie_id=987654321, value=6))
                session.flush()
            session.rollback()

    def test_private_conversation_ownership_and_pending_answer(self):
        response = self.client.post('/api/v1/chat/query', json={'text': 'Drama under 90 minutes'}, headers=self.headers())
        self.assertEqual(response.status_code, 202)
        data = response.json()
        wrong_owner = self.client.post('/api/v1/chat/query', json={'text': 'Something shorter', 'conversation_id': data['conversation_id']}, headers=self.headers(1))
        self.assertEqual(wrong_owner.status_code, 404)
        pending = self.client.get('/api/v1/chat/turns/' + data['turn_id'], headers=self.headers()).json()
        self.assertEqual(pending['status'], 'pending')
        self.assertEqual(pending['reply'], {})
        self.assertEqual(self.client.get('/api/v1/chat/turns/' + data['turn_id'], headers=self.headers(1)).status_code, 404)


if __name__ == '__main__':
    unittest.main()
