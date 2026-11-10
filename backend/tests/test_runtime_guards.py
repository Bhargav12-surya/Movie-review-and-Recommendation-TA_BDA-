"""Real PostgreSQL failure/revision/consent/vector contracts; never model metrics.

All accounts, movies, vectors and candidate strings are isolated synthetic test
fixtures. The actual ModelRuntime is used only with an empty registry, yielding
unavailable outputs; no fake positive/neutral/negative prediction is supplied.
"""
from datetime import datetime, timedelta, timezone
import os
from types import SimpleNamespace
import unittest
from uuid import UUID

from backend.tests.fixtures import prepare_api, headers, submit


@unittest.skipUnless(os.environ.get('RUN_POSTGRES_TESTS') == '1', 'Explicit disposable PostgreSQL opt-in required.')
class RuntimeGuardTests(unittest.TestCase):
    def setUp(self):
        prepare_api(self)

    headers = headers
    submit = submit

    def test_expired_and_revoked_sessions_cannot_reuse_account(self):
        from backend.app.models import AuthSession
        from backend.app.auth.security import digest
        from sqlalchemy import select
        with self.sandbox.factory() as session:
            token = session.scalar(select(AuthSession).where(AuthSession.token_hash == digest(self.tokens[0])))
            token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            session.commit()
        self.assertEqual(self.client.get('/api/v1/me', headers=self.headers()).status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/logout', headers=self.headers(1)).status_code, 204)
        self.assertEqual(self.client.get('/api/v1/me', headers=self.headers(1)).status_code, 401)

    def test_nonadministrator_cannot_read_registry_or_request_refresh(self):
        for method, path in [('get', '/api/v1/admin/pipeline-status'),
                             ('post', '/api/v1/admin/movies/987654321/refresh')]:
            self.assertEqual(getattr(self.client, method)(path, headers=self.headers()).status_code, 403)

    def test_missing_offline_speech_does_not_invent_transcription_or_require_a_microphone(self):
        response = self.client.post('/api/v1/chat/transcribe', headers=self.headers(),
            files={'file': ('isolated.wav', b'isolated-invalid-audio-fixture', 'audio/wav')})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'offline_speech_unavailable_use_text')
        self.assertNotIn('text', response.json())
        self.assertEqual(self.client.post('/api/v1/chat/query', json={'text': 'Drama'}, headers=self.headers()).status_code, 202)

    def test_model_registry_rejects_unapproved_and_unsupported_language_scopes(self):
        from backend.app.models import ModelArtifact
        from backend.app.services.artifacts import resolve
        from backend.app.core.errors import ServiceUnavailable
        with self.sandbox.factory() as session:
            session.add(ModelArtifact(component='sentiment_transformer', version='synthetic-unapproved-v1',
                config_path='no-test-weights', run_path='no-test-weights', manifest_sha256='0' * 64,
                approved=False, language_scope=['en'], approval_reference='isolated-unapproved-fixture'))
            session.commit()
            with self.assertRaises(ServiceUnavailable):resolve(session, 'sentiment_transformer', 'en')
            session.add(ModelArtifact(component='sentiment_transformer', version='synthetic-en-scope-only',
                config_path='no-test-weights', run_path='no-test-weights', manifest_sha256='0' * 64,
                approved=True, language_scope=['en'], approval_reference='synthetic-disposable-test-only'))
            session.commit()
            with self.assertRaises(ServiceUnavailable):resolve(session, 'sentiment_transformer', 'mul')

    def test_full_queue_rolls_back_review_and_movie_invalidation(self):
        from sqlalchemy import func, select
        from backend.app.models import Job, Movie, Review
        self.settings.maximum_pending_jobs = 1
        response = self.client.post(self.path, json=self.body, headers=self.headers())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error']['code'], 'analysis_queue_full_retry_later')
        with self.sandbox.factory() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Review)), 0)
            self.assertEqual(session.scalar(select(func.count()).select_from(Job)), 0)
            self.assertEqual(session.get(Movie, 987654321).evidence_version, 0)

    def test_withdrawing_personalization_removes_interactions_not_owned_ratings(self):
        from sqlalchemy import func, select
        from backend.app.models import Interaction, Rating
        preference = {'genres': {'Drama': 1}, 'themes': {}, 'personalization_permitted': True}
        self.assertEqual(self.client.put('/api/v1/me/preferences', json=preference, headers=self.headers()).status_code, 200)
        self.assertEqual(self.client.put('/api/v1/me/interactions/987654321', json={'event_type': 'watched'}, headers=self.headers()).status_code, 200)
        self.assertEqual(self.client.put('/api/v1/me/ratings/987654321', json={'value': 4}, headers=self.headers()).status_code, 200)
        self.assertEqual(self.client.put('/api/v1/me/preferences', json=preference | {'personalization_permitted': False}, headers=self.headers()).status_code, 200)
        with self.sandbox.factory() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Interaction)), 0)
            self.assertIsNotNone(session.get(Rating, (self.users[0], 987654321)))
        self.assertEqual(self.client.put('/api/v1/me/interactions/987654321', json={'event_type': 'watched'}, headers=self.headers()).status_code, 403)

    def test_training_withdrawal_clears_historical_training_permissions(self):
        from sqlalchemy import select
        from backend.app.models import ReviewRevision
        response = self.client.post(self.path, json=self.body | {'training_permitted': True}, headers=self.headers())
        self.assertEqual(response.status_code, 201)
        identifier = response.json()['review_id']
        changed = self.client.patch('/api/v1/reviews/' + identifier, json=self.body | {'expected_revision': 1}, headers=self.headers())
        self.assertEqual(changed.status_code, 200)
        with self.sandbox.factory() as session:
            revisions = session.scalars(select(ReviewRevision).where(ReviewRevision.review_id == UUID(identifier))).all()
            self.assertEqual(len(revisions), 2)
            self.assertTrue(all(not row.training_permitted for row in revisions))

    def test_summary_candidate_is_withheld_until_actual_factuality_approval(self):
        from backend.app.models import Movie, MovieSummary
        with self.sandbox.factory() as session:
            movie = session.get(Movie, 987654321)
            session.add(MovieSummary(movie_id=movie.id, evidence_version=movie.evidence_version,
                payload={'status': 'requires_factuality_review', 'summary': [],
                         'generated_candidate': 'Synthetic unapproved candidate; not audience evidence.', 'publication_approved': False}))
            session.commit()
        response = self.client.get('/api/v1/movies/987654321/summary')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('generated_candidate', response.json())
        self.assertEqual(response.json()['publication_approved'], False)

    def test_stale_version_snapshot_and_star_ratings_do_not_become_audience_sentiment(self):
        from backend.app.models import Movie, MovieScore, Rating
        with self.sandbox.factory() as session:
            movie = session.get(Movie, 987654321)
            movie.evidence_version = 2
            session.add(MovieScore(movie_id=movie.id, evidence_version=1, score_type='overall', score=None,
                                   payload={'score': None, 'message': 'Old isolated fixture'}, model_version='test-only', method_version='test-only'))
            session.add(Rating(user_id=self.users[0], movie_id=movie.id, value=4))
            session.commit()
        response = self.client.get('/api/v1/movies/987654321').json()
        self.assertIsNone(response['scores']['overall']['score'])
        self.assertEqual(response['scores']['overall']['message'], 'Not enough audience reviews yet.')
        self.assertEqual(response['audience_star_rating']['count'], 1)
        self.assertEqual(response['audience_star_rating']['mean'], 4)

    def test_pgvector_neighbours_exclude_other_models_dimensions_and_content_versions(self):
        from backend.app.models import Movie, MovieEmbedding, ModelArtifact
        from backend.app.repositories.catalogue import similar_movies
        with self.sandbox.factory() as session:
            session.add(ModelArtifact(component='embeddings', version='synthetic-vector-geometry-v1',
                config_path='isolated-placeholder', run_path='isolated-placeholder', manifest_sha256='0' * 64,
                approved=True, language_scope=['en'], approval_reference='synthetic-disposable-test-only'))
            # These are geometric test vectors, not generated or evaluated movie embeddings.
            session.add(MovieEmbedding(movie_id=987654321, model_version='synthetic-vector-geometry-v1', content_version=1, dimension=2, embedding=[1, 0]))
            for offset, version, dimension, content in [(1, 'synthetic-vector-geometry-v1', 2, 1),
                                                       (2, 'other-isolated-version', 2, 1),
                                                       (3, 'synthetic-vector-geometry-v1', 3, 1),
                                                       (4, 'synthetic-vector-geometry-v1', 2, 2)]:
                identifier = 987654321 + offset
                session.add(Movie(id=identifier, title='Synthetic geometry fixture', metadata_source='synthetic-test-only', canonical_mapping_approved=True))
                session.flush()
                session.add(MovieEmbedding(movie_id=identifier, model_version=version, content_version=content, dimension=dimension, embedding=[1] + [0] * (dimension - 1)))
            session.commit()
            result = similar_movies(session, session.get(Movie, 987654321))
            self.assertEqual([row['id'] for row in result['movies']], ['987654322'])

    def test_missing_models_produce_unavailable_rows_without_probabilities(self):
        from sqlalchemy import select
        from backend.app.models import Job, Prediction, Review
        from backend.app.services.inference import ModelRuntime
        from backend.app.workers.main import analyse
        saved = self.submit()
        with self.sandbox.factory() as session:
            job = session.scalar(select(Job).where(Job.kind == 'analyse_review'))
        status = analyse(self.sandbox.factory, job, ModelRuntime(self.settings), self.settings, lambda: None)
        self.assertEqual(status, 'unavailable')
        with self.sandbox.factory() as session:
            predictions = session.scalars(select(Prediction)).all()
            self.assertEqual(len(predictions), 3)
            self.assertTrue(all(row.status == 'unavailable' and 'probabilities' not in row.payload for row in predictions))
            self.assertEqual(session.get(Review, UUID(saved['review_id'])).analysis_status, 'unavailable')

    def test_worker_cannot_publish_if_lease_is_lost(self):
        from sqlalchemy import func, select
        from backend.app.models import Job, Prediction
        from backend.app.services.inference import ModelRuntime
        from backend.app.workers.main import analyse
        self.submit()
        with self.sandbox.factory() as session:
            job = session.scalar(select(Job).where(Job.kind == 'analyse_review'))
        def lost_lease():
            raise RuntimeError('isolated lease loss')
        with self.assertRaises(RuntimeError):
            analyse(self.sandbox.factory, job, ModelRuntime(self.settings), self.settings, lost_lease)
        with self.sandbox.factory() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Prediction)), 0)

    def test_edit_between_inference_and_publication_cancels_old_revision(self):
        from sqlalchemy import func, select
        from backend.app.models import Job, Prediction, Review
        from backend.app.services.inference import ModelRuntime
        from backend.app.workers.main import analyse
        saved = self.submit()
        with self.sandbox.factory() as session:
            job = session.scalar(select(Job).where(Job.kind == 'analyse_review'))
        def intervening_edit():
            response = self.client.patch('/api/v1/reviews/' + saved['review_id'], json=self.body | {'expected_revision': 1}, headers=self.headers())
            self.assertEqual(response.status_code, 200)
        status = analyse(self.sandbox.factory, job, ModelRuntime(self.settings), self.settings, intervening_edit)
        self.assertEqual(status, 'cancelled')
        with self.sandbox.factory() as session:
            self.assertEqual(session.get(Review, UUID(saved['review_id'])).revision, 2)
            self.assertEqual(session.scalar(select(func.count()).select_from(Prediction)), 0)

    def test_claim_obeys_attempt_limit_and_retry_availability(self):
        from sqlalchemy import delete
        from backend.app.models import Job
        from backend.app.repositories.jobs import claim
        with self.sandbox.factory() as session:
            session.execute(delete(Job))  # Own empty disposable test schema only.
            session.add(Job(kind='isolated-probe', dedupe_key='exhausted', attempts=6, status='unavailable', payload={}))
            session.add(Job(kind='isolated-probe', dedupe_key='future', available_at=datetime.now(timezone.utc) + timedelta(hours=1), payload={}))
            session.commit()
            self.assertIsNone(claim(session, 'isolated-worker', 6))
            session.add(Job(kind='isolated-probe', dedupe_key='ready', payload={}))
            session.commit()
            row = claim(session, 'isolated-worker', 6)
            self.assertEqual(row.dedupe_key, 'ready')
            self.assertEqual(row.attempts, 1)
            self.assertEqual(row.status, 'running')
            self.assertEqual(row.locked_by, 'isolated-worker')
            self.assertIsNotNone(row.locked_at)

    def test_deduplicated_job_retry_succeeds_even_when_external_capacity_is_full(self):
        from backend.app.repositories.jobs import enqueue
        from backend.app.models import Job
        from sqlalchemy import select, func
        with self.sandbox.factory() as session:
            enqueue(session, 'isolated-contract', 'stable-contract-key', {}, maximum=1)
            enqueue(session, 'isolated-contract', 'stable-contract-key', {}, maximum=1)
            session.commit()
            self.assertEqual(session.scalar(select(func.count()).select_from(Job)), 1)

    def test_internal_child_reserve_is_bounded_and_claimed_before_new_analysis(self):
        from backend.app.repositories.jobs import enqueue, claim
        from fastapi import HTTPException
        with self.sandbox.factory() as session:
            enqueue(session, 'analyse_review', 'parent-contract', {}, maximum=1)
            enqueue(session, 'publish_event', 'child-event-contract', {}, maximum=1, internal=True)
            enqueue(session, 'refresh_movie', 'child-refresh-contract', {}, maximum=1, internal=True)
            session.commit()
            with self.assertRaises(HTTPException):
                enqueue(session, 'publish_event', 'overflow-child-contract', {}, maximum=1, internal=True)
            session.rollback()
            first = claim(session, 'isolated-worker', 6)
            second = claim(session, 'isolated-worker', 6)
            third = claim(session, 'isolated-worker', 6)
            self.assertEqual([row.kind for row in (first, second, third)], ['publish_event', 'refresh_movie', 'analyse_review'])

    def test_conversation_expiry_and_turn_cap_prevent_unbounded_context(self):
        from backend.app.models import Conversation, ChatTurn
        first = self.client.post('/api/v1/chat/query', json={'text': 'Drama'}, headers=self.headers()).json()
        conversation_id = UUID(first['conversation_id'])
        with self.sandbox.factory() as session:
            conversation = session.get(Conversation, conversation_id)
            conversation.updated_at = datetime.now(timezone.utc) - timedelta(days=2)
            session.commit()
        response = self.client.post('/api/v1/chat/query', json={'text': 'Something shorter', 'conversation_id': str(conversation_id)}, headers=self.headers())
        self.assertEqual(response.status_code, 410)
        with self.sandbox.factory() as session:
            session.get(Conversation, conversation_id).updated_at = datetime.now(timezone.utc)
            for _ in range(39):session.add(ChatTurn(conversation_id=conversation_id, user_id=self.users[0], query='Isolated bounded turn', reply={}))
            session.commit()
        response = self.client.post('/api/v1/chat/query', json={'text': 'Drama', 'conversation_id': str(conversation_id)}, headers=self.headers())
        self.assertEqual(response.status_code, 409)


if __name__ == '__main__':
    unittest.main()
