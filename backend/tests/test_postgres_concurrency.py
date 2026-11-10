"""Actual two-connection PostgreSQL contention in a new owned test schema.

Requires both RUN_POSTGRES_TESTS=1 and RUN_POSTGRES_CONCURRENCY=1. These are
synthetic database contracts, not model-quality or real audience evidence.
"""
from concurrent.futures import ThreadPoolExecutor
import os
import unittest
from uuid import UUID
from backend.tests.fixtures import prepare_api, headers, submit
from backend.tests.postgres_support import CommittedPostgresSandbox


@unittest.skipUnless(os.environ.get('RUN_POSTGRES_TESTS') == '1' and os.environ.get('RUN_POSTGRES_CONCURRENCY') == '1',
                     'Explicit disposable two-connection test opt-in required.')
class PostgresConcurrencyTests(unittest.TestCase):
    def setUp(self):
        prepare_api(self, CommittedPostgresSandbox)

    headers = headers
    submit = submit

    def test_concurrent_identical_submissions_create_one_review(self):
        from sqlalchemy import select, func
        from backend.app.models import Review
        def request():return self.client.post(self.path, json=self.body, headers=self.headers())
        with ThreadPoolExecutor(max_workers=2) as executor:
            tasks = [executor.submit(request) for _ in range(2)]
            responses = [task.result(timeout=15) for task in tasks]
        self.assertEqual([response.status_code for response in responses], [201, 201])
        self.assertEqual(responses[0].json(), responses[1].json())
        with self.sandbox.factory() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Review)), 1)

    def test_competing_edits_accept_one_revision_and_reject_stale_owner_copy(self):
        from backend.app.models import Review, ReviewRevision
        from sqlalchemy import select, func
        saved = self.submit()
        path = '/api/v1/reviews/' + saved['review_id']
        def edit(index):return self.client.patch(path, json=self.body | {'text': f'Synthetic concurrent edit number {index}.', 'expected_revision': 1}, headers=self.headers())
        with ThreadPoolExecutor(max_workers=2) as executor:
            tasks = [executor.submit(edit, index) for index in range(2)]
            responses = [task.result(timeout=15) for task in tasks]
        self.assertEqual(sorted(response.status_code for response in responses), [200, 409])
        with self.sandbox.factory() as session:
            self.assertEqual(session.get(Review, UUID(saved['review_id'])).revision, 2)
            self.assertEqual(session.scalar(select(func.count()).select_from(ReviewRevision)), 2)

    def test_two_claimers_do_not_take_the_same_durable_job(self):
        from sqlalchemy import select
        from backend.app.models import Job
        from backend.app.repositories.jobs import claim
        with self.sandbox.factory() as session:
            for index in range(2):session.add(Job(kind='isolated-contract', dedupe_key=f'isolated-claim-{index}', payload={}))
            session.commit()
        def take(owner):
            with self.sandbox.factory() as session:
                row = claim(session, owner, 6)
                return str(row.id) if row else None
        with ThreadPoolExecutor(max_workers=2) as executor:
            tasks = [executor.submit(take, f'isolated-worker-{index}') for index in range(2)]
            identifiers = [task.result(timeout=15) for task in tasks]
        self.assertEqual(len(set(identifiers)), 2)
        self.assertNotIn(None, identifiers)
        with self.sandbox.factory() as session:
            rows = session.scalars(select(Job)).all()
            self.assertTrue(all(row.status == 'running' and row.attempts == 1 for row in rows))

    def test_advisory_worker_lease_is_exclusive_between_connections(self):
        from sqlalchemy import text
        from backend.app.workers.main import LOCK_KEY
        with self.sandbox.engine.connect() as first, self.sandbox.engine.connect() as second:
            self.assertTrue(first.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': LOCK_KEY}))
            try:self.assertFalse(second.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': LOCK_KEY}))
            finally:first.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': LOCK_KEY})
            self.assertTrue(second.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': LOCK_KEY}))
            second.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': LOCK_KEY})


if __name__ == '__main__':unittest.main()
