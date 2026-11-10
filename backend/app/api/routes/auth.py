from datetime import timedelta
from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy import select,delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.app.models import User,AuthSession
from backend.app.database.session import get_session
from backend.app.core.config import get_settings
from backend.app.auth.security import PASSWORDS,digest,new_token,now,verify_password,dummy_hash
from backend.app.auth.dependencies import get_current_user,bearer
from backend.app.schemas.auth import LoginInput,RegisterInput,PublicUser

router=APIRouter(prefix='/auth',tags=['authentication'])

def issue(session,user):
    token=new_token()
    session.add(AuthSession(user_id=user.id,token_hash=digest(token),expires_at=now()+timedelta(minutes=get_settings().auth_token_ttl_minutes)))
    session.commit()
    return {'access_token':token,'token_type':'bearer','user':PublicUser.model_validate(user).model_dump(mode='json')}

@router.post('/register',status_code=201)
def register(body:RegisterInput,session:Session=Depends(get_session)):
    if not get_settings().registration_enabled: raise HTTPException(403,detail='registration_disabled')
    user=User(email=body.email,display_name=body.display_name,password_hash=PASSWORDS.hash(body.password.get_secret_value()))
    session.add(user)
    try: session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409,detail='account_already_exists') from None
    return issue(session,user)

@router.post('/login')
def login(body:LoginInput,session:Session=Depends(get_session)):
    user=session.scalar(select(User).where(User.email==body.email))
    valid=verify_password(body.password.get_secret_value(),user.password_hash if user else dummy_hash())
    if not user or not valid or not user.is_active: raise HTTPException(401,detail='invalid_credentials')
    return issue(session,user)

@router.get('/me',response_model=PublicUser)
def me(user:User=Depends(get_current_user)):
    return user

@router.post('/logout',status_code=204)
def logout(user:User=Depends(get_current_user),credentials=Depends(bearer),session:Session=Depends(get_session)):
    session.execute(delete(AuthSession).where(AuthSession.user_id==user.id,AuthSession.token_hash==digest(credentials.credentials)))
    session.commit()
    return Response(status_code=204)
