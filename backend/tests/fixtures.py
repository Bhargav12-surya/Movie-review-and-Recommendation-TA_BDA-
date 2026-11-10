"""Isolated API fixtures. These invented records are never scientific evidence."""
from datetime import timedelta
from unittest.mock import patch

from backend.tests.postgres_support import PostgresSandbox, database_dependency


def prepare_api(test, sandbox_type=PostgresSandbox):
    from fastapi.testclient import TestClient
    from backend.app.main import create_app
    from backend.app.core.config import BackendSettings
    from backend.app.database.session import get_session
    from backend.app.models import User, Movie, AuthSession
    from backend.app.auth.security import PASSWORDS, digest, new_token, now
    test.sandbox = test.enterContext(sandbox_type())
    test.settings = BackendSettings(_env_file=None, database_password='', inference_device='cpu',
        speech_model_path=None, speech_permission_path=None, factor_directory=None, factor_mapping=None,
        scoring_config='scoring/config.example.json', scoring_approval='scoring/approval.example.json',
        hybrid_config='configs/recommendation/hybrid.json', target_score_policies={}, summarization_config=None)
    # No test reads the application's private .env or configured artifact paths.
    for module in ('backend.app.main', 'backend.app.api.routes.auth', 'backend.app.api.routes.reviews',
                   'backend.app.api.routes.chat', 'backend.app.api.routes.admin',
                   'backend.app.api.routes.recommendations', 'backend.app.api.routes.movies'):
        test.enterContext(patch(module + '.get_settings', return_value=test.settings))
    test.app = create_app()
    test.app.dependency_overrides[get_session] = database_dependency(test.sandbox.factory)
    test.client = test.enterContext(TestClient(test.app, raise_server_exceptions=True))
    test.tokens, test.users = [], []
    test.password = 'isolated-contract-passphrase'
    with test.sandbox.factory() as session:
        for index in range(2):
            user = User(email=f'isolated-{index}@example.invalid', display_name='Synthetic API test account',
                        password_hash=PASSWORDS.hash(test.password))
            session.add(user); session.flush()
            token = new_token(); test.tokens.append(token); test.users.append(user.id)
            session.add(AuthSession(user_id=user.id, token_hash=digest(token), expires_at=now() + timedelta(minutes=5)))
        session.add(Movie(id=987654321, title='Synthetic isolation fixture', overview='Only for disposable tests.',
                          metadata_source='synthetic-test-only', canonical_mapping_approved=True, genres=['Drama']))
        session.commit()
    test.path = '/api/v1/movies/987654321/reviews'
    test.body = dict(text='Synthetic API test review, excluded from real audience evidence.', language_code='en',
                     evidence_permitted=False, training_permitted=False, moderation_permitted=False,
                     consent_version='isolated-test-only-v1')


def headers(test, index=0, key='isolated-idempotency-key'):
    return {'Authorization': 'Bearer ' + test.tokens[index], 'Idempotency-Key': key}


def submit(test):
    response = test.client.post(test.path, json=test.body, headers=headers(test))
    test.assertEqual(response.status_code, 201)
    return response.json()
