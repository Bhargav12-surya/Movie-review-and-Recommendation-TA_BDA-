"""One database-leased local worker, durable jobs, revision-safe publication."""
from datetime import datetime,timezone,timedelta
import json
import hashlib
import time
import uuid
from sqlalchemy import select,update,text
from sqlalchemy.dialects.postgresql import insert
from backend.app.core.config import get_settings
from backend.app.core.errors import ServiceUnavailable
from backend.app.database.session import make_engine,get_session_factory
from backend.app.models import Job,Review,Prediction,ChatTurn,ModelArtifact
from backend.app.repositories.catalogue import movie_or_404
from backend.app.repositories.jobs import claim,enqueue
from backend.app.services.reviews import invalidate
from backend.app.services.inference import ModelRuntime

LOCK_KEY=70911339

def analyse(factory,job,runtime,settings,lease_check):
    with factory() as session:
        review=session.get(Review,uuid.UUID(job.payload['review_id']))
        if review is None or review.is_deleted or review.revision!=job.payload['revision']: return 'cancelled'
        data={'id':review.id,'movie_id':review.movie_id,'revision':review.revision,'text':review.text,'language':review.language_code}
        results=[]
        for component,method in [('sentiment',runtime.sentiment),('aspects',runtime.aspects),('themes',runtime.themes)]:
            try:
                results.append(method(session,data['text'],data['language']))
            except ServiceUnavailable as error:
                results.append({'component':component,'model_version':'unavailable','status':'unavailable','payload':{'reason':error.code}})
            except (OSError,ValueError,ImportError,RuntimeError) as error:
                results.append({'component':component,'model_version':'unavailable','status':'unavailable','payload':{'reason':'local_model_execution_unavailable','error_type':type(error).__name__}})
            finally: runtime.release()
        if review.moderation_permitted:
            from ml.review_risk.predict import predict as risk
            history=session.scalars(select(Review).where(Review.id!=review.id,Review.moderation_permitted.is_(True),
                Review.is_deleted.is_(False),Review.moderation_status=='published').order_by(Review.created_at.desc(),Review.id).limit(1000)).all()
            payload=risk(review.text,[row.text for row in history])
            payload['corpus_snapshot_sha256']=hashlib.sha256(json.dumps([(str(row.id),row.revision,row.text_sha256) for row in history]).encode()).hexdigest()
            payload['corpus_review_count']=len(history)
            results.append({'component':'risk','model_version':payload['method_version'],'status':'analysed','payload':payload})
    lease_check()
    with factory() as session:
        movie=movie_or_404(session,data['movie_id'],True)
        review=session.scalar(select(Review).where(Review.id==data['id']).with_for_update())
        if review is None or review.is_deleted or review.revision!=data['revision']: return 'cancelled'
        approved=set(session.scalars(select(ModelArtifact.version).where(ModelArtifact.approved.is_(True))).all())
        for result in results:
            if result['status']=='analysed' and result['component']!='risk' and (result['model_version'] not in approved or
                any(version not in approved for version in result['payload'].get('dependency_versions',[]))):
                result.update(status='unavailable',payload={'reason':'model_approval_withdrawn'})
        for result in results:
            session.execute(insert(Prediction).values(review_id=review.id,review_revision=review.revision,**result)
                .on_conflict_do_update(index_elements=['review_id','review_revision','component','model_version'],set_={'status':result['status'],'payload':result['payload']}))
        complete=sum(row['status']=='analysed' for row in results)
        review.analysis_status='complete' if complete==len(results) else 'partial' if complete else 'unavailable'
        invalidate(session,movie)
        from backend.app.services.events import queue_event
        sentiment=next((result for result in results if result['component']=='sentiment' and result['status']=='analysed'),None)
        if sentiment is not None or not review.evidence_permitted:queue_event(session,review,movie,sentiment,settings,internal=True)
        enqueue(session,'refresh_movie',f'movie:{movie.id}:{movie.evidence_version}',{'movie_id':movie.id,'evidence_version':movie.evidence_version},settings.maximum_pending_jobs,internal=True)
        session.commit()
        return 'succeeded' if complete==len(results) else 'unavailable'

def main():
    settings=get_settings();engine=make_engine(settings);factory=get_session_factory(engine)
    owner=str(uuid.uuid4());runtime=ModelRuntime(settings)
    with engine.connect() as lease:
        if not lease.scalar(text('SELECT pg_try_advisory_lock(:key)'),{'key':LOCK_KEY}):
            raise RuntimeError('Another local inference worker already owns the GPU/service lease.')
        expected_pid=lease.scalar(text('SELECT pg_backend_pid()'));lease.commit()
        def lease_check():
            if lease.scalar(text('SELECT pg_backend_pid()'))!=expected_pid: raise ServiceUnavailable('worker_lease_lost')
            lease.commit()
        with factory() as session:
            session.execute(update(Job).where(Job.status=='running').values(status='queued',locked_at=None,locked_by=None))
            session.commit()
        try:
            while True:
                lease_check()
                with factory() as session: job=claim(session,owner,settings.maximum_job_attempts)
                if job is None: time.sleep(.5);continue
                error_code=None
                try:
                    if job.kind=='analyse_review': status=analyse(factory,job,runtime,settings,lease_check)
                    elif job.kind=='refresh_movie':
                        from backend.app.services.analytics import refresh
                        with factory() as session: refresh(session,job.payload['movie_id'],settings,lease_check)
                        status='succeeded'
                    elif job.kind=='chat':
                        from backend.app.services.chat import process_turn
                        with factory() as session: process_turn(session,job.payload['turn_id'],settings,lease_check)
                        status='succeeded'
                    elif job.kind=='publish_event':
                        from backend.app.services.events import publish
                        publish(job.payload['event'],settings);status='succeeded'
                    else: raise ServiceUnavailable('unknown_job_kind')
                except Exception as error:
                    status='unavailable';error_code=error.code if isinstance(error,ServiceUnavailable) else type(error).__name__
                    if job.kind=='analyse_review':
                        with factory() as session:
                            session.execute(update(Review).where(Review.id==uuid.UUID(job.payload['review_id']),Review.revision==job.payload['revision'],
                                Review.analysis_status.in_(['pending','running'])).values(analysis_status='unavailable'))
                            session.commit()
                    elif job.kind=='chat':
                        with factory() as session:
                            turn=session.get(ChatTurn,uuid.UUID(job.payload['turn_id']))
                            if turn:
                                turn.status='failed';turn.reply={'status':'unavailable','text':'Discovery could not complete. Check the local worker,approved artifacts and catalogue,or try text with a title/genre.','movies':[]};session.commit()
                with factory() as session:
                    current=session.scalar(select(Job).where(Job.id==job.id).with_for_update())
                    if current.status=='running' and current.locked_by==owner:
                        current.status='failed' if status=='unavailable' and current.attempts>=settings.maximum_job_attempts else status
                        current.last_error=error_code
                        current.available_at=datetime.now(timezone.utc)+timedelta(seconds=min(3600,30*2**current.attempts))
                        current.locked_at=None;current.locked_by=None;session.commit()
                print(json.dumps({'job_id':str(job.id),'status':status,'error_code':error_code}),flush=True)
        finally:
            runtime.release()
            lease.execute(text('SELECT pg_advisory_unlock(:key)'),{'key':LOCK_KEY});lease.commit()
            engine.dispose()

if __name__=='__main__': main()
