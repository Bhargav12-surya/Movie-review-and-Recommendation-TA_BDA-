from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from backend.app.auth.dependencies import get_current_user
from backend.app.database.session import get_session
from backend.app.models import User
from backend.app.core.config import get_settings
from backend.app.services.recommendations import for_user

router=APIRouter(prefix='/recommendations',tags=['recommendations'])
@router.get('')
def recommendations(k:int=Query(12,ge=1,le=50),user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    return for_user(session,user,get_settings(),k)
