from uuid import UUID
from sqlalchemy import select,func,or_
from backend.app.models import ChatTurn,Conversation,Movie,MovieEmbedding,Review,Prediction,MovieScore,ModelArtifact
from backend.app.repositories.catalogue import public_movie,current_scores,current_summary,similar_movies
from backend.app.core.errors import ServiceUnavailable
from discovery.parser import parse_query

def resolve_title(session,title):
    return session.scalars(select(Movie).where(Movie.canonical_mapping_approved.is_(True),
        or_(func.lower(Movie.title)==title.casefold(),func.lower(func.regexp_replace(Movie.title,r' \([0-9]{4}\)$',''))==title.casefold())).limit(6)).all()

def evidence_profile(session,movie):
    return {**public_movie(movie),'scores':current_scores(session,movie),'summary':current_summary(session,movie)}

def answer(session,query,context,settings,user_id):
    parsed=parse_query(query,context)
    resolved=[]
    for title in parsed['titles']:
        choices=resolve_title(session,title)
        if len(choices)!=1:
            return {'status':'clarification','text':'Choose the exact catalogue title/year.' if choices else 'I could not resolve that movie in the local catalogue.',
                    'movies':[public_movie(row) for row in choices]},context
        resolved.append(choices[0])
    if not resolved and parsed['intent']=='aspect' and context.get('last_movie_id'):
        row=session.get(Movie,context['last_movie_id'])
        if row: resolved=[row]
    if parsed['intent'] in {'movie','compare','aspect'} and resolved:
        profiles=[evidence_profile(session,row) for row in resolved]
        if parsed['intent']=='aspect':
            key=parsed['aspect'];quotes=[]
            rows=session.execute(select(Review,Prediction).join(Prediction,Prediction.review_id==Review.id).where(Review.movie_id==resolved[0].id,
                Review.is_deleted.is_(False),Review.evidence_permitted.is_(True),Review.moderation_status=='published',
                Prediction.review_revision==Review.revision,Prediction.component=='aspects',Prediction.status=='analysed').limit(200)).all()
            for review,prediction in rows:
                approved=set(session.scalars(select(ModelArtifact.version).where(ModelArtifact.approved.is_(True))).all())
                if prediction.model_version not in approved or any(version not in approved for version in prediction.payload.get('dependency_versions',[])): continue
                for item in prediction.payload.get('aspects',[]):
                    if item.get('aspect')==key and len(quotes)<12:
                        quotes.append({'review_id':str(review.id),'revision':review.revision,'quote':review.text[max(0,item['start']-70):min(len(review.text),item['end']+100)],'label':item.get('label')})
            reply={'status':'grounded','text':f'Here is the available {key} evidence.' if quotes else 'Not enough audience reviews yet.',
                   'movies':profiles,'evidence':quotes,'aspect':key}
        else:
            reply={'status':'grounded','text':'Catalogue facts and available audience evidence are shown below. Missing audience scores remain unavailable.', 'movies':profiles}
        context={**context,'last_movie_id':resolved[0].id if len(resolved)==1 else None}
        return reply,context
    if parsed['intent']=='similar' and resolved:
        result=similar_movies(session,resolved[0])
        return {'status':result['status'],'text':'Semantic neighbours from the local catalogue.' if result['movies'] else 'Local semantic embeddings are unavailable.',
                'movies':result['movies']},{**context,'last_movie_id':resolved[0].id}
    targets=(['pacing'] if parsed['needs_pacing_evidence'] else [])+(['emotional_impact'] if parsed['needs_emotional_evidence'] else [])
    if targets and settings.discovery_minimum_aspect_score is None:
        return {'status':'constraint_unavailable','text':'That request needs validated pacing or emotional-impact audience evidence. Choose genre/theme filters until those aspect scores are available.','movies':[]},context
    conditions=[Movie.canonical_mapping_approved.is_(True)]
    genres=parsed['genres'] or context.get('genres',[])
    if genres: conditions.append(Movie.genres.contains(genres))
    for genre in parsed['excluded_genres']: conditions.append(~Movie.genres.contains([genre]))
    themes=parsed['themes']
    if themes: conditions.append(Movie.features['themes'].contains(themes))
    maximum=parsed['maximum_runtime']
    if parsed['shorter_followup']:
        base=session.get(Movie,context.get('last_movie_id')) if context.get('last_movie_id') else None
        if not base or not base.runtime_minutes: return {'status':'clarification','text':'Shorter than which movie? Include a title or a minute limit.','movies':[]},context
        maximum=base.runtime_minutes-1
    if maximum: conditions.append(Movie.runtime_minutes<=maximum)
    for target in targets:
        conditions.append(select(MovieScore.id).where(MovieScore.movie_id==Movie.id,MovieScore.evidence_version==Movie.evidence_version,
            MovieScore.is_stale.is_(False),MovieScore.score_type=='aspect',MovieScore.target_key==target,
            MovieScore.score>=settings.discovery_minimum_aspect_score).exists())
    rows=session.scalars(select(Movie).where(*conditions).order_by(Movie.release_date.desc().nullslast(),Movie.id).limit(12)).all()
    if not genres and not themes and not targets:
        try:
            from backend.app.services.artifacts import resolve
            from backend.app.core.config import ROOT
            from ml.common.records import load_config
            from ml.embeddings.predict import encode
            artifact=resolve(session,'embeddings')
            encoded=encode([query],load_config(ROOT/artifact.config_path))
            vector=encoded['vectors'][0].tolist()
            distance=MovieEmbedding.embedding.cosine_distance(vector)
            rows=session.scalars(select(Movie).join(MovieEmbedding,MovieEmbedding.movie_id==Movie.id).where(*conditions,
                MovieEmbedding.model_version==artifact.version,MovieEmbedding.dimension==encoded['dimension'],MovieEmbedding.content_version==Movie.content_version)
                .order_by(distance,Movie.id).limit(12)).all()
            return {'status':'semantic','text':'Semantic matches from the actual locally indexed catalogue.',
                    'movies':[public_movie(row) for row in rows]},context
        except (ServiceUnavailable,OSError,ValueError,ImportError):
            if query.casefold().strip() not in {'recommend movies','show movies','recommend something'}:
                return {'status':'semantic_unavailable','text':'Semantic discovery is unavailable until a validated local embedding model and catalogue index are prepared. Genre and title searches remain available.','movies':[]},context
    # Prefer the real hybrid service when a permitted profile exists. Its filters
    # retain the same explicit constraints; unavailable models never fabricate ranks.
    from backend.app.services.recommendations import for_user
    from backend.app.models import User
    try:
        if targets: raise ServiceUnavailable('target_filtered_catalogue_results')
        result=for_user(session,session.get(User,user_id),settings,12,{'required_genres':genres,'excluded_genres':parsed['excluded_genres'],
            'required_themes':themes,**({'maximum_runtime':maximum} if maximum else {})})
        if result['status']=='available':
            return {'status':'personalized','text':'Results ranked from your actual preferences and available model inputs.',
                'movies':[row['movie'] for row in result['recommendations']],'recommendations':result['recommendations']},{**context,'genres':genres}
    except (ValueError,OSError,ServiceUnavailable): pass
    return {'status':'catalogue_filter','text':'Catalogue matches for your constraints; personalized ranking is unavailable.',
            'movies':[public_movie(row) for row in rows]}, {**context,'genres':genres,'maximum_runtime':maximum}

def process_turn(session,turn_id,settings):
    turn=session.get(ChatTurn,UUID(turn_id))
    if turn is None or turn.status=='complete': return
    conversation=session.scalar(select(Conversation).where(Conversation.id==turn.conversation_id).with_for_update())
    reply,state=answer(session,turn.query,conversation.state or {},settings,turn.user_id)
    conversation.state=state;turn.reply=reply;turn.status='complete';session.commit()
