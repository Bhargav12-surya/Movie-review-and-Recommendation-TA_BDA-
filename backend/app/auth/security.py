from datetime import datetime,timezone
from functools import lru_cache
import hashlib
import secrets
from pwdlib import PasswordHash

PASSWORDS=PasswordHash.recommended()

def digest(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def new_token():
    return secrets.token_urlsafe(32)

def now():
    return datetime.now(timezone.utc)

@lru_cache
def dummy_hash():
    return PASSWORDS.hash(secrets.token_urlsafe(32))

def verify_password(password,hashed):
    try:
        return PASSWORDS.verify(password,hashed)
    except Exception:
        return False
