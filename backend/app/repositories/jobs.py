from datetime import datetime,timezone,timedelta
from fastapi import HTTPException
from sqlalchemy import select,func,text
from sqlalchemy.dialects.postgresql import insert
from backend.app.models import Job

def enqueue(session,kind,key,payload,maximum=1000):
    session.execute(text('SELECT pg_advisory_xact_lock(70911340)'))
    if session.scalar(select(func.count()).select_from(Job).where(Job.status.in_(['queued','running','unavailable'])))>=maximum:
        raise HTTPException(503,detail='analysis_queue_full_retry_later')
    session.execute(insert(Job).values(kind=kind,dedupe_key=key,payload=payload).on_conflict_do_nothing(index_elements=['dedupe_key']))

def claim(session,owner,maximum_attempts):
    now=datetime.now(timezone.utc)
    row=session.scalar(select(Job).where(Job.status.in_(['queued','unavailable']),Job.available_at<=now,Job.attempts<maximum_attempts)
        .order_by(Job.created_at).with_for_update(skip_locked=True).limit(1))
    if row:
        row.status='running';row.locked_at=now;row.locked_by=owner;row.attempts+=1
    session.commit()
    return row
