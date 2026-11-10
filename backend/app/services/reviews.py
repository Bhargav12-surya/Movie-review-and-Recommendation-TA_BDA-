import hashlib
import json
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select,update,delete,text
from backend.app.models import Review,ReviewRevision,Prediction,ReviewEmbedding,MovieScore,MovieSummary,Idempotency,ModelArtifact
from backend.app.repositories.catalogue import movie_or_404
from backend.app.repositories.jobs import enqueue

def checksum(value): return hashlib.sha256(value.encode('utf-8')).hexdigest()

def invalidate(session,movie):
    movie.evidence_version+=1
    session.execute(update(MovieScore).where(MovieScore.movie_id==movie.id).values(is_stale=True,payload={}))
    session.execute(update(MovieSummary).where(MovieSummary.movie_id==movie.id).values(is_stale=True,payload={}))

def revision_record(row):
    return ReviewRevision(review_id=row.id,revision=row.revision,text=row.text,text_sha256=row.text_sha256,
        language_code=row.language_code,training_permitted=row.training_permitted,evidence_permitted=row.evidence_permitted)

def enqueue_analysis(session,row,movie,settings):
    enqueue(session,'analyse_review',f'review:{row.id}:{row.revision}',{'review_id':str(row.id),'revision':row.revision},settings.maximum_pending_jobs)
    enqueue(session,'refresh_movie',f'movie:{movie.id}:{movie.evidence_version}',{'movie_id':movie.id,'evidence_version':movie.evidence_version},settings.maximum_pending_jobs)

def submit(session,user,movie_id,body,key,settings):
    if not key or not 8<=len(key)<=120: raise HTTPException(400,detail='idempotency_key_required_8_to_120_characters')
    movie=movie_or_404(session,movie_id,lock=True)
    hashed=checksum(key)
    scope=f'review:{movie_id}'
    session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),{'key':str(user.id)+scope+hashed})
    payload_hash=checksum(json.dumps(body.model_dump(mode='json'),sort_keys=True,separators=(',',':')))
    previous=session.get(Idempotency,(user.id,scope,hashed))
    if previous:
        if previous.payload_hash!=payload_hash: raise HTTPException(409,detail='idempotency_key_payload_conflict')
        return previous.response
    row=Review(user_id=user.id,movie_id=movie_id,revision=1,text_sha256=checksum(body.text),**body.model_dump())
    session.add(row);session.flush();session.add(revision_record(row));invalidate(session,movie)
    enqueue_analysis(session,row,movie,settings)
    response={'review_id':str(row.id),'movie_id':str(movie.id),'revision':row.revision,'analysis_status':'pending'}
    session.add(Idempotency(user_id=user.id,scope=scope,key_hash=hashed,payload_hash=payload_hash,response=response))
    session.commit()
    return response

def owned(session,user,identifier,lock=False):
    first=session.get(Review,identifier)
    if first is None or first.user_id!=user.id: raise HTTPException(404,detail='review_not_found')
    movie=movie_or_404(session,first.movie_id,lock=lock)
    row=session.scalar(select(Review).where(Review.id==identifier).with_for_update().execution_options(populate_existing=True)) if lock else first
    if row.is_deleted: raise HTTPException(410,detail='review_deleted')
    return row,movie

def edit(session,user,identifier,body,settings):
    row,movie=owned(session,user,identifier,True)
    if row.revision!=body.expected_revision: raise HTTPException(409,detail='review_revision_conflict')
    row.revision+=1
    for name,value in body.model_dump(exclude={'expected_revision'}).items(): setattr(row,name,value)
    row.text_sha256=checksum(row.text);row.analysis_status='pending'
    if not row.training_permitted:
        session.execute(update(ReviewRevision).where(ReviewRevision.review_id==row.id).values(training_permitted=False))
    session.execute(delete(Prediction).where(Prediction.review_id==row.id))
    session.execute(delete(ReviewEmbedding).where(ReviewEmbedding.review_id==row.id))
    session.add(revision_record(row));invalidate(session,movie);enqueue_analysis(session,row,movie,settings)
    if not row.evidence_permitted:
        from backend.app.services.events import queue_event
        queue_event(session,row,movie,None,settings)
    session.commit()
    return {'review_id':str(row.id),'revision':row.revision,'analysis_status':row.analysis_status}

def remove(session,user,identifier,settings):
    row,movie=owned(session,user,identifier,True)
    row.revision+=1;row.text='';row.text_sha256=checksum('');row.is_deleted=True;row.training_permitted=False;row.evidence_permitted=False;row.moderation_permitted=False;row.analysis_status='cancelled'
    for model in (ReviewRevision,Prediction,ReviewEmbedding): session.execute(delete(model).where(model.review_id==row.id))
    invalidate(session,movie)
    from backend.app.services.events import queue_event
    queue_event(session,row,movie,None,settings)
    enqueue(session,'refresh_movie',f'movie:{movie.id}:{movie.evidence_version}',{'movie_id':movie.id,'evidence_version':movie.evidence_version},settings.maximum_pending_jobs)
    session.commit()

def public_review(session,row):
    predictions=session.scalars(select(Prediction).where(Prediction.review_id==row.id,Prediction.review_revision==row.revision)).all()
    approved=set(session.scalars(select(ModelArtifact.version).where(ModelArtifact.approved.is_(True))).all())
    predictions=[item for item in predictions if item.component=='risk' or item.status!='analysed' or
        (item.model_version in approved and all(version in approved for version in item.payload.get('dependency_versions',[])))]
    return {'id':str(row.id),'movie_id':str(row.movie_id),'revision':row.revision,'text':row.text,'language_code':row.language_code,
        'created_at':row.created_at.isoformat(),'analysis_status':row.analysis_status,
        'predictions':{item.component:{'status':item.status,'model_version':item.model_version,**item.payload} for item in predictions}}
