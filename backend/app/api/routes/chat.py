from uuid import UUID
from datetime import datetime,timezone,timedelta
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File,Response
from sqlalchemy import select,delete,func
from sqlalchemy.orm import Session
from backend.app.models import User,Conversation,ChatTurn
from backend.app.auth.dependencies import get_current_user
from backend.app.database.session import get_session
from backend.app.core.config import get_settings,ROOT
from backend.app.schemas.requests import ChatInput
from backend.app.repositories.jobs import enqueue

router=APIRouter(prefix='/chat',tags=['grounded discovery'])

@router.post('/query',status_code=202)
def query(body:ChatInput,user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    conversation=session.scalar(select(Conversation).where(Conversation.id==body.conversation_id).with_for_update()) if body.conversation_id else None
    if body.conversation_id and (conversation is None or conversation.user_id!=user.id): raise HTTPException(404,detail='conversation_not_found')
    if conversation and conversation.updated_at<datetime.now(timezone.utc)-timedelta(hours=24):
        raise HTTPException(410,detail='conversation_expired_start_new')
    if conversation is None:
        conversation=Conversation(user_id=user.id,state={});session.add(conversation);session.flush()
    if session.scalar(select(func.count()).select_from(ChatTurn).where(ChatTurn.conversation_id==conversation.id))>=40:
        raise HTTPException(409,detail='conversation_limit_clear_or_start_new')
    turn=ChatTurn(conversation_id=conversation.id,user_id=user.id,query=body.text,reply={},status='pending')
    session.add(turn);session.flush()
    enqueue(session,'chat',f'chat:{turn.id}',{'turn_id':str(turn.id)},get_settings().maximum_pending_jobs)
    session.commit()
    return {'turn_id':str(turn.id),'conversation_id':str(conversation.id),'status':'pending'}

@router.get('/turns/{turn_id}')
def get_turn(turn_id:UUID,user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    turn=session.get(ChatTurn,turn_id)
    if turn is None or turn.user_id!=user.id: raise HTTPException(404,detail='turn_not_found')
    return {'turn_id':str(turn.id),'conversation_id':str(turn.conversation_id),'status':turn.status,'reply':turn.reply}

@router.delete('/conversations/{conversation_id}',status_code=204)
def clear(conversation_id:UUID,user:User=Depends(get_current_user),session:Session=Depends(get_session)):
    session.execute(delete(Conversation).where(Conversation.id==conversation_id,Conversation.user_id==user.id));session.commit()
    return Response(status_code=204)

@router.post('/transcribe')
def voice(file:UploadFile=File(...),user:User=Depends(get_current_user)):
    if file.content_type not in {'audio/webm','audio/wav','audio/ogg','audio/mp4','audio/mpeg'}: raise HTTPException(415,detail='unsupported_audio_format')
    try:
        from discovery.speech import transcribe
        return transcribe(file.file,get_settings(),ROOT)
    except (ValueError,ImportError,OSError): raise HTTPException(503,detail='offline_speech_unavailable_use_text') from None
