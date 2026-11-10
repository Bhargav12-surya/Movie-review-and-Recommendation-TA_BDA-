from sqlalchemy import select,func
from backend.app.models import Movie,MovieEmbedding,Preference,Rating,Review,ModelArtifact,Interaction
from backend.app.core.config import ROOT
from backend.app.repositories.catalogue import public_movie
from ml.common.artifacts import read_json,safe_path
from recommender.profile import build_profile
from recommender.hybrid import recommend
from recommender.factors import FactorStore

def for_user(session,user,settings,k=12,filters=None):
    preference=session.get(Preference,user.id)
    if preference is None or not preference.personalization_permitted:
        return {'status':'preferences_required','recommendations':[],'message':'Choose preferences and allow personalization to build your shelves.'}
    rows=session.scalars(select(Movie).where(Movie.canonical_mapping_approved.is_(True)).order_by(Movie.id).limit(5001)).all()
    if len(rows)>5000:
        from backend.app.core.errors import ServiceUnavailable
        raise ServiceUnavailable('catalogue_requires_prepared_candidate_snapshot')
    catalogue=[{'movie_id':str(row.id),'genres':row.genres,'themes':(row.features or {}).get('themes',[]),
        'runtime_minutes':row.runtime_minutes,'eligible':True} for row in rows]
    by_id={row['movie_id']:row for row in catalogue}
    vectors=session.scalars(select(MovieEmbedding).join(Movie,MovieEmbedding.movie_id==Movie.id)
        .where(MovieEmbedding.content_version==Movie.content_version,MovieEmbedding.model_version.in_(select(ModelArtifact.version)
            .where(ModelArtifact.component=='embeddings',ModelArtifact.approved.is_(True)))).order_by(MovieEmbedding.model_version)).all()
    # One selected model scope; never combine dimensions/revisions silently.
    version=vectors[-1].model_version if vectors else None
    for row in vectors:
        if row.model_version==version and str(row.movie_id) in by_id:
            by_id[str(row.movie_id)].update(embedding=row.embedding.tolist(),embedding_model_version=row.model_version)
    ratings=session.scalars(select(Rating).where(Rating.user_id==user.id)).all()
    history=[{'movie_id':str(row.movie_id),'event_type':'rating','rating':float(row.value),'personalization_permitted':True} for row in ratings]
    config=read_json(safe_path(settings.hybrid_config,ROOT))
    event_weights={'rating':1.0}
    if config.get('interaction_weights_validated') is True:
        event_weights=config['interaction_weights']
        events=session.scalars(select(Interaction).where(Interaction.user_id==user.id,Interaction.event_type.in_(['watched','watchlist']))
            .distinct(Interaction.movie_id,Interaction.event_type).order_by(Interaction.movie_id,Interaction.event_type,Interaction.created_at.desc()).limit(1000)).all()
        history += [{'movie_id':str(row.movie_id),'event_type':row.event_type,'personalization_permitted':True} for row in events]
    seen={str(value) for value in session.scalars(select(Review.movie_id).where(Review.user_id==user.id,Review.is_deleted.is_(False))).all()}
    explicit={'ratings':{str(row.movie_id):float(row.value) for row in ratings},'seen_movie_ids':list(seen)}
    if preference.genres:explicit['genre_preferences']=preference.genres
    if preference.themes:explicit['theme_preferences']=preference.themes
    profile=build_profile(explicit,history,catalogue,event_weights)
    config['filters']=filters or {}
    scores=None
    if settings.factor_directory and settings.factor_mapping:
        store=FactorStore.load(settings.factor_directory,settings.factor_mapping,ROOT)
        # App users stay cold to ALS unless separately approved fold-in is configured.
        if config.get('fold_in_method_approved') is True:
            vector=store.fold_in(profile['ratings'],config)
            if vector is not None: scores=store.scores(application_vector=vector)
    result=recommend(catalogue,profile,config,scores,k)
    metadata={str(row.id):public_movie(row) for row in rows}
    result['recommendations']=[{**row,'movie':metadata[row['movie_id']]} for row in result['recommendations']]
    result.update(status='available',candidate_protocol='all_current_canonical_catalogue_up_to_5000; larger_catalogues_require_prepared_snapshot')
    return result
