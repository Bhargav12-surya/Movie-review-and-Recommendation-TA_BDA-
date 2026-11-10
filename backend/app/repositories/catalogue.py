from fastapi import HTTPException
from sqlalchemy import select,func
from backend.app.models import Movie,MovieScore,MovieSummary,MovieEmbedding,ModelArtifact

def movie_or_404(session,identifier,lock=False):
    query=select(Movie).where(Movie.id==identifier,Movie.canonical_mapping_approved.is_(True))
    row=session.scalar(query.with_for_update() if lock else query)
    if row is None: raise HTTPException(404,detail='movie_not_found')
    return row

def public_movie(row):
    return {'id':str(row.id),'title':row.title,'overview':row.overview,'release_date':row.release_date,
        'runtime_minutes':row.runtime_minutes,'original_language':row.original_language,
        'genres':row.genres,'keywords':row.keywords,'themes':(row.features or {}).get('themes',[]),
        'poster_url':f'/api/v1/movies/{row.id}/poster' if row.poster_path else None,'metadata_source':row.metadata_source}

def current_scores(session,movie):
    rows=session.scalars(select(MovieScore).where(MovieScore.movie_id==movie.id,MovieScore.evidence_version==movie.evidence_version,
        MovieScore.is_stale.is_(False)).order_by(MovieScore.created_at.desc())).all()
    result={}
    for row in rows:
        key=row.score_type+(':'+row.target_key if row.target_key else '')
        if key not in result: result[key]=row.payload
    if 'overall' not in result:
        result['overall']={'score':None,'review_count':0,'message':'Not enough audience reviews yet.','status':'pending_or_insufficient_evidence'}
    return result

def current_summary(session,movie):
    row=session.scalar(select(MovieSummary).where(MovieSummary.movie_id==movie.id,MovieSummary.evidence_version==movie.evidence_version,
        MovieSummary.is_stale.is_(False)).order_by(MovieSummary.created_at.desc()).limit(1))
    if row is None:return {'status':'no_evidence','summary':None}
    payload=dict(row.payload)
    if payload.get('publication_approved') is not True:payload.pop('generated_candidate',None)
    return payload

def similar_movies(session,movie,limit=12):
    approved=select(ModelArtifact.version).where(ModelArtifact.component=='embeddings',ModelArtifact.approved.is_(True))
    source=session.scalar(select(MovieEmbedding).where(MovieEmbedding.movie_id==movie.id,MovieEmbedding.content_version==movie.content_version)
        .where(MovieEmbedding.model_version.in_(approved))
        .order_by(MovieEmbedding.model_version).limit(1))
    if source is None: return {'status':'embeddings_unavailable','movies':[]}
    distance=MovieEmbedding.embedding.cosine_distance(source.embedding)
    rows=session.execute(select(Movie,distance.label('distance')).join(MovieEmbedding,MovieEmbedding.movie_id==Movie.id)
        .where(Movie.id!=movie.id,Movie.canonical_mapping_approved.is_(True),MovieEmbedding.model_version==source.model_version,
               MovieEmbedding.dimension==source.dimension,MovieEmbedding.content_version==Movie.content_version)
        .order_by(distance,Movie.id).limit(limit)).all()
    return {'status':'available','model_version':source.model_version,'movies':[{**public_movie(row), 'semantic_similarity':1-float(value)} for row,value in rows]}
