from uuid import UUID
from fastapi import APIRouter,Depends,Header,Response,HTTPException
from sqlalchemy.orm import Session
from backend.app.auth.dependencies import get_current_user
from backend.app.database.session import get_session
from backend.app.models import User,Review
from backend.app.core.config import get_settings
from backend.app.schemas.requests import ReviewInput,ReviewEdit
from backend.app.services import reviews as service

router=APIRouter(tags=['reviews'])

@router.post('/movies/{movie_id}/reviews',status_code=201)
def submit(movie_id:int,body:ReviewInput,idempotency_key:str=Header(alias='Idempotency-Key'),user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    return service.submit(session,user,movie_id,body,idempotency_key,get_settings())

@router.get('/reviews/{review_id}')
def get_review(review_id:UUID,user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    row,_=service.owned(session,user,review_id)
    return service.public_review(session,row)

@router.patch('/reviews/{review_id}')
def edit(review_id:UUID,body:ReviewEdit,user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    return service.edit(session,user,review_id,body,get_settings())

@router.delete('/reviews/{review_id}',status_code=204)
def delete_review(review_id:UUID,user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    service.remove(session,user,review_id,get_settings())
    return Response(status_code=204)

@router.post('/reviews/{review_id}/reanalyze')
def reanalyze(review_id:UUID,user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    row,_=service.owned(session,user,review_id)
    body=ReviewEdit(text=row.text,language_code=row.language_code,user_rating=float(row.user_rating) if row.user_rating else None,
        training_permitted=row.training_permitted,evidence_permitted=row.evidence_permitted,moderation_permitted=row.moderation_permitted,consent_version=row.consent_version,expected_revision=row.revision)
    return service.edit(session,user,review_id,body,get_settings())
