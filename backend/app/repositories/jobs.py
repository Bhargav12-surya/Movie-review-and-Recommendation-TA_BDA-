from datetime import datetime,timezone,timedelta
from fastapi import HTTPException
from sqlalchemy import select,func,text,case
from sqlalchemy.dialects.postgresql import insert
from backend.app.models import Job

def enqueue(session,kind,key,payload,maximum=1000,internal=False):
    session.execute(text('SELECT pg_advisory_xact_lock(70911340)'))
    if session.scalar(select(Job.id).where(Job.dedupe_key==key)) is not None:return
    # One leased worker may publish at most an event and a refresh child. Drain
    # children before another analysis so these reserved slots cannot grow freely.
    capacity=maximum+(2 if internal else 0)
    if session.scalar(select(func.count()).select_from(Job).where(Job.status.in_(['queued','running','unavailable'])))>=capacity:
        raise HTTPException(503,detail='analysis_queue_full_retry_later')
    session.execute(insert(Job).values(kind=kind,dedupe_key=key,payload=payload).on_conflict_do_nothing(index_elements=['dedupe_key']))

def claim(session,owner,maximum_attempts):
    now=datetime.now(timezone.utc)
    row=session.scalar(select(Job).where(Job.status.in_(['queued','unavailable']),Job.available_at<=now,Job.attempts<maximum_attempts)
        .order_by(case((Job.kind=='publish_event',0),(Job.kind=='refresh_movie',1),else_=2),Job.created_at,Job.id).with_for_update(skip_locked=True).limit(1))
    if row:
        row.status='running';row.locked_at=now;row.locked_by=owner;row.attempts+=1
    session.commit()
    return row
