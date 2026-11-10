"""Text-free genuine prediction outbox; atomic replay-safe file publication."""
from datetime import datetime,timezone
import hashlib
import json
import os
import uuid
from ml.common.artifacts import safe_path
from backend.app.core.config import ROOT
from backend.app.repositories.jobs import enqueue

def queue_event(session,review,movie,prediction,settings,internal=False):
    eligible=not review.is_deleted and review.evidence_permitted and review.moderation_status=='published' and prediction is not None
    event={'event_id':f'app:{review.id}:{review.revision}','review_id':f'app:{review.id}','review_revision':review.revision,
        'movie_id':str(movie.id),'operation':'upsert' if eligible else 'delete',
        'event_time':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'positive_probability':prediction['payload']['probabilities']['positive'] if eligible else None,
        'neutral_probability':prediction['payload']['probabilities']['neutral'] if eligible else None,
        'negative_probability':prediction['payload']['probabilities']['negative'] if eligible else None,
        'model_version':prediction['model_version'] if eligible else None,'canonical_movie_validated':movie.canonical_mapping_approved,
        'consent_eligible':bool(review.evidence_permitted),'moderation_eligible':review.moderation_status=='published','is_synthetic':False}
    enqueue(session,'publish_event',f'event:{review.id}:{review.revision}',{'event':event},settings.maximum_pending_jobs,internal=internal)

def publish(event,settings):
    from scripts.publish_review_events import validate_event
    validate_event(event,allow_synthetic=False)
    directory=safe_path(settings.review_event_directory,ROOT,output=True);directory.mkdir(parents=True,exist_ok=True)
    target=directory/(hashlib.sha256(event['event_id'].encode()).hexdigest()+'.jsonl')
    content=(json.dumps(event,sort_keys=True,separators=(',',':'))+'\n').encode()
    if target.exists():
        if target.read_bytes()!=content:raise ValueError('Event ID conflict; never overwrite a published event.')
        return
    temporary=directory/('.pending-'+uuid.uuid4().hex)
    with temporary.open('xb') as stream:stream.write(content);stream.flush();os.fsync(stream.fileno())
    try:os.link(temporary,target)
    except FileExistsError:
        if target.read_bytes()!=content:raise ValueError('Conflicting published event.')
    finally:temporary.unlink(missing_ok=True)
