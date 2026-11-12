from pathlib import Path
from uuid import UUID
from fastapi import APIRouter,Depends,Query,HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from backend.app.database.session import get_session
from backend.app.models import Movie,Review,Rating
from backend.app.repositories.catalogue import movie_or_404,public_movie,current_scores,current_summary,similar_movies
from backend.app.services.reviews import public_review
from backend.app.core.config import ROOT,get_settings

router=APIRouter(prefix='/movies',tags=['catalogue'])

@router.get('')
def catalogue(q:str=Query('',max_length=200),genre:str|None=None,theme:str|None=None,page:int=Query(1,ge=1),page_size:int=Query(24,ge=1,le=60),session:Session=Depends(get_session)):
    conditions=[Movie.canonical_mapping_approved.is_(True)]
    if q:
        pattern = '%' + q.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'
        conditions.append(Movie.title.ilike(pattern, escape='!'))
    if genre: conditions.append(Movie.genres.contains([genre]))
    if theme: conditions.append(Movie.features['themes'].contains([theme]))
    total=session.scalar(select(func.count()).select_from(Movie).where(*conditions))
    rows=session.scalars(select(Movie).where(*conditions).order_by(Movie.poster_path.is_not(None).desc(),Movie.release_date.desc().nullslast(),Movie.id).offset((page-1)*page_size).limit(page_size)).all()
    return {'movies':[public_movie(row) for row in rows],'total':total,'page':page,'page_size':page_size}

@router.get('/{movie_id}')
def detail(movie_id:int,session:Session=Depends(get_session)):
    row=movie_or_404(session,movie_id)
    stars=session.execute(select(func.avg(Rating.value),func.count()).where(Rating.movie_id==movie_id)).one()
    return {**public_movie(row),'scores':current_scores(session,row),'summary':current_summary(session,row),
        'audience_star_rating':{'mean':float(stars[0]) if stars[0] is not None else None,'count':stars[1],'scale':'0.5..5; separate from review sentiment'}}

@router.get('/{movie_id}/scores')
def scores(movie_id:int,session:Session=Depends(get_session)):
    return current_scores(session,movie_or_404(session,movie_id))

@router.get('/{movie_id}/summary')
def summary(movie_id:int,session:Session=Depends(get_session)):
    return current_summary(session,movie_or_404(session,movie_id))

@router.get('/{movie_id}/reviews')
def reviews(movie_id:int,page:int=Query(1,ge=1),session:Session=Depends(get_session)):
    movie_or_404(session,movie_id)
    rows=session.scalars(select(Review).where(Review.movie_id==movie_id,Review.is_deleted.is_(False),Review.moderation_status=='published')
        .order_by(Review.created_at.desc()).offset((page-1)*20).limit(20)).all()
    return {'reviews':[public_review(session,row) for row in rows],'page':page}

@router.get('/{movie_id}/similar')
def similar(movie_id:int,session:Session=Depends(get_session)):
    return similar_movies(session,movie_or_404(session,movie_id))

def _serve_artwork(relative_path:str|None,error_code:str):
    if not relative_path: raise HTTPException(404,detail=error_code)
    folder=(ROOT/get_settings().poster_cache).resolve()
    if not folder.is_relative_to(ROOT): raise HTTPException(404,detail=error_code)
    path=(folder/relative_path).resolve()
    if not path.is_relative_to(folder) or path.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'} or not path.is_file():
        raise HTTPException(404,detail=error_code)
    return FileResponse(path,headers={'Cache-Control':'private,max-age=3600'})

@router.get('/{movie_id}/poster')
def poster(movie_id:int,session:Session=Depends(get_session)):
    row=movie_or_404(session,movie_id)
    return _serve_artwork(row.poster_path,'poster_unavailable')

@router.get('/{movie_id}/backdrop')
def backdrop(movie_id:int,session:Session=Depends(get_session)):
    row=movie_or_404(session,movie_id)
    return _serve_artwork(row.backdrop_path,'backdrop_unavailable')
