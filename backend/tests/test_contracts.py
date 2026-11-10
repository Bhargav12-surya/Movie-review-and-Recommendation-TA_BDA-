"""Contract tests; no weights, database, or network are needed."""
import importlib.util
import unittest

BACKEND_PRESENT = all(importlib.util.find_spec(name) is not None for name in
                      ('fastapi', 'pydantic', 'pydantic_settings', 'pwdlib', 'sqlalchemy', 'pgvector'))


@unittest.skipUnless(BACKEND_PRESENT, 'Manually install the approved backend test dependencies first.')
class RequestContractTests(unittest.TestCase):
    def test_unicode_text_is_preserved_and_consent_is_separate(self):
        from backend.app.schemas.requests import ReviewInput
        text = 'Acting mast tha 😂 but pacing बहुत धीमी लगी.'
        row = ReviewInput(text=text, language_code='mul', evidence_permitted=True, consent_version='isolated-test-v1')
        self.assertEqual(row.text, text)
        self.assertTrue(row.evidence_permitted)
        self.assertFalse(row.training_permitted)
        self.assertFalse(row.moderation_permitted)

    def test_invalid_rating_and_unknown_privileged_fields_are_rejected(self):
        from backend.app.schemas.requests import ReviewInput
        from pydantic import ValidationError
        base = dict(text='An isolated contract test review.', language_code='en', evidence_permitted=False,
                    consent_version='isolated-test-v1')
        for changes in [{'user_rating': 4.2}, {'user_rating': float('nan')}, {'is_admin': True},
                        {'is_synthetic': False}, {'language_code': 'unsupported'}, {'text': ' ' * 15}]:
            with self.subTest(fields=tuple(changes)):
                with self.assertRaises(ValidationError):
                    ReviewInput(**(base | changes))

    def test_edit_requires_explicit_positive_revision(self):
        from backend.app.schemas.requests import ReviewEdit
        from pydantic import ValidationError
        base = dict(text='An isolated contract test review.', language_code='en', evidence_permitted=False,
                    consent_version='isolated-test-v1')
        for changes in [{}, {'expected_revision': 0}]:
            with self.assertRaises(ValidationError):
                ReviewEdit(**(base | changes))

    def test_preferences_cannot_invent_unbounded_weights(self):
        from backend.app.schemas.requests import Preferences
        from pydantic import ValidationError
        for weights in [{'Drama': float('inf')}, {'Drama': -1}, {'Drama': 1.1}, {'': 0.5}]:
            with self.assertRaises(ValidationError):
                Preferences(genres=weights)

    def test_password_hashing_and_opaque_token_storage(self):
        from backend.app.auth.security import PASSWORDS, new_token, digest, verify_password
        password = 'isolated-unit-test-passphrase'
        hashed = PASSWORDS.hash(password)
        self.assertNotEqual(hashed, password)
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password('different-passphrase', hashed))
        self.assertFalse(verify_password(password, 'malformed-hash'))
        first, second = new_token(), new_token()
        self.assertNotEqual(first, second)
        self.assertEqual(len(digest(first)), 64)
        self.assertNotEqual(digest(first), first)

    def test_public_account_schema_excludes_secrets(self):
        from backend.app.schemas.auth import PublicUser
        fields = set(PublicUser.model_fields)
        self.assertNotIn('password_hash', fields)
        self.assertNotIn('access_token', fields)


if __name__ == '__main__':
    unittest.main()
