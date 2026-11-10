from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.database.session import get_session
from backend.app.models import User,AuthSession
from .security import digest,now

bearer=HTTPBearer(auto_error=False)

def get_current_user(credentials:HTTPAuthorizationCredentials|None=Depends(bearer),session:Session=Depends(get_session)):
    if not credentials or credentials.scheme.lower()!='bearer' or not 20<=len(credentials.credentials)<=256:
        raise HTTPException(401,detail='authentication_required',headers={'WWW-Authenticate':'Bearer'})
    token=session.scalar(select(AuthSession).where(AuthSession.token_hash==digest(credentials.credentials),AuthSession.expires_at>now()))
    user=session.get(User,token.user_id) if token else None
    if user is None or not user.is_active:
        raise HTTPException(401,detail='session_invalid_or_expired',headers={'WWW-Authenticate':'Bearer'})
    return user

def require_admin(user:User=Depends(get_current_user)):
    if not user.is_admin: raise HTTPException(403,detail='administrator_required')
    return user
