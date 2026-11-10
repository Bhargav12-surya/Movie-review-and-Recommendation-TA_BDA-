from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from backend.app.auth.dependencies import require_admin
from backend.app.database.session import get_session
from backend.app.models import User,Job,ModelArtifact
from backend.app.schemas.requests import ArtifactInput
from backend.app.services.artifacts import promote
from backend.app.repositories.catalogue import movie_or_404
from backend.app.repositories.jobs import enqueue
from backend.app.core.config import get_settings

router=APIRouter(prefix='/admin',tags=['administration'])
@router.get('/pipeline-status')
def status(user:User=Depends(require_admin),session:Session=Depends(get_session)):
    return {'jobs':[{'status':status,'count':count} for status,count in session.execute(select(Job.status,func.count()).group_by(Job.status))],
            'models':[{'component':row.component,'version':row.version,'approved':row.approved} for row in session.scalars(select(ModelArtifact)).all()]}

@router.post('/models',status_code=201)
def register(body:ArtifactInput,user:User=Depends(require_admin),session:Session=Depends(get_session)):
    try: return promote(session,body)
    except (ValueError,OSError,KeyError,TypeError): raise HTTPException(422,detail='model_promotion_evidence_invalid') from None

@router.post('/movies/{movie_id}/refresh',status_code=202)
def refresh(movie_id:int,user:User=Depends(require_admin),session:Session=Depends(get_session)):
    movie=movie_or_404(session,movie_id,True)
    enqueue(session,'refresh_movie',f'movie:{movie.id}:{movie.evidence_version}:admin:{__import__("uuid").uuid4()}',{'movie_id':movie.id},get_settings().maximum_pending_jobs)
    session.commit();return {'status':'queued'}
