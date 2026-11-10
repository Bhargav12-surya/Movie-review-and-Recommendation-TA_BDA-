from fastapi import APIRouter,Depends,Response,HTTPException
from sqlalchemy import select,delete,func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from backend.app.auth.dependencies import get_current_user
from backend.app.database.session import get_session
from backend.app.models import User,Preference,Rating,Watchlist,Movie,Review,Interaction
from backend.app.repositories.catalogue import movie_or_404,public_movie
from backend.app.services.reviews import public_review
from backend.app.schemas.requests import Preferences,RatingInput,InteractionInput

router=APIRouter(prefix='/me',tags=['profile'])

@router.get('/reviews')
def own_reviews(user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    rows=session.scalars(select(Review).where(Review.user_id==user.id,Review.is_deleted.is_(False)).order_by(Review.created_at.desc()).limit(200)).all()
    return {'reviews':[{**public_review(session,row),'training_permitted':row.training_permitted,
        'evidence_permitted':row.evidence_permitted,'moderation_permitted':row.moderation_permitted,'consent_version':row.consent_version} for row in rows]}

@router.get('')
def profile(user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    preference=session.get(Preference,user.id)
    ratings=session.scalars(select(Rating).where(Rating.user_id==user.id)).all()
    return {'user':{'id':str(user.id),'display_name':user.display_name},'preferences':{
        'genres':preference.genres if preference else {},'themes':preference.themes if preference else {},
        'personalization_permitted':preference.personalization_permitted if preference else False},
        'ratings':{str(row.movie_id):float(row.value) for row in ratings}}

@router.put('/preferences')
def preferences(body:Preferences,user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    session.execute(insert(Preference).values(user_id=user.id,**body.model_dump()).on_conflict_do_update(index_elements=['user_id'],set_={**body.model_dump(),'updated_at':func.now()}))
    if not body.personalization_permitted: session.execute(delete(Interaction).where(Interaction.user_id==user.id))
    session.commit()
    return body

@router.put('/ratings/{movie_id}')
def rate(movie_id:int,body:RatingInput,user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    movie_or_404(session,movie_id)
    session.execute(insert(Rating).values(user_id=user.id,movie_id=movie_id,value=body.value)
        .on_conflict_do_update(index_elements=['user_id','movie_id'],set_={'value':body.value,'updated_at':func.now()}))
    session.commit()
    return {'movie_id':str(movie_id),'rating':body.value}

@router.get('/watchlist')
def watchlist(user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    rows=session.scalars(select(Movie).join(Watchlist,Watchlist.movie_id==Movie.id).where(Watchlist.user_id==user.id).order_by(Watchlist.created_at.desc()).limit(500)).all()
    return {'movies':[public_movie(row) for row in rows]}

@router.put('/watchlist/{movie_id}')
def add_watchlist(movie_id:int,user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    movie_or_404(session,movie_id)
    session.execute(insert(Watchlist).values(user_id=user.id,movie_id=movie_id).on_conflict_do_nothing())
    preference=session.get(Preference,user.id)
    if preference and preference.personalization_permitted:
        exists=session.scalar(select(Interaction.id).where(Interaction.user_id==user.id,Interaction.movie_id==movie_id,Interaction.event_type=='watchlist').limit(1))
        if not exists:session.add(Interaction(user_id=user.id,movie_id=movie_id,event_type='watchlist',payload={'source':'explicit_save'}))
    session.commit()
    return {'movie_id':str(movie_id),'saved':True}

@router.put('/interactions/{movie_id}')
def interaction(movie_id:int,body:InteractionInput,user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    movie_or_404(session,movie_id)
    preference=session.get(Preference,user.id)
    if preference is None or not preference.personalization_permitted:raise HTTPException(403,detail='personalization_consent_required')
    exists=session.scalar(select(Interaction.id).where(Interaction.user_id==user.id,Interaction.movie_id==movie_id,Interaction.event_type==body.event_type).limit(1))
    if not exists:session.add(Interaction(user_id=user.id,movie_id=movie_id,event_type=body.event_type,payload={'source':'explicit_user_action'}))
    session.commit();return {'movie_id':str(movie_id),'event_type':body.event_type,'recorded':True}

@router.delete('/watchlist/{movie_id}',status_code=204)
def remove_watchlist(movie_id:int,user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    session.execute(delete(Watchlist).where(Watchlist.user_id==user.id,Watchlist.movie_id==movie_id))
    session.execute(delete(Interaction).where(Interaction.user_id==user.id,Interaction.movie_id==movie_id,Interaction.event_type=='watchlist'));session.commit()
    return Response(status_code=204)
