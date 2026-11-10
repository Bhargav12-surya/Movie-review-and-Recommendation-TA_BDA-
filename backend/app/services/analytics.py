from datetime import datetime,timezone
from sqlalchemy import select
from backend.app.models import Movie,Review,Prediction,ModelArtifact,MovieScore,MovieSummary
from backend.app.core.config import ROOT
from backend.app.core.errors import ServiceUnavailable
from backend.app.repositories.catalogue import movie_or_404
from ml.common.artifacts import safe_path

def refresh(session,movie_id,settings):
    movie=movie_or_404(session,movie_id,lock=True)
    reviews=session.scalars(select(Review).where(Review.movie_id==movie_id,Review.is_deleted.is_(False),
        Review.evidence_permitted.is_(True),Review.is_synthetic.is_(False),Review.moderation_status=='published').limit(10001)).all()
    if len(reviews)>10000: raise ServiceUnavailable('batch_snapshot_required')
    approved={(row.component,row.version) for row in session.scalars(select(ModelArtifact).where(ModelArtifact.approved.is_(True))).all()}
    evidence=[]
    for review in reviews:
        predictions=session.scalars(select(Prediction).where(Prediction.review_id==review.id,Prediction.review_revision==review.revision,Prediction.status=='analysed')).all()
        sentiment=next((row for row in predictions if row.component=='sentiment' and (row.payload.get('source_component'),row.model_version) in approved),None)
        aspects=next((row for row in predictions if row.component=='aspects'),None)
        targets=[]
        if aspects and ('aspect_sentiment',aspects.model_version) in approved and all(version in {value for _,value in approved} for version in aspects.payload.get('dependency_versions',[])):
            for item in aspects.payload.get('aspects',[]):
                targets.append({'target_type':'aspect','target_key':item['aspect'],'probabilities':item['probabilities'],
                    'prediction_approved':True,'calibrated':True,'model_version':aspects.model_version})
        evidence.append({'review_id':str(review.id),'review_revision':review.revision,'reviewer_id':str(review.user_id),'movie_id':str(movie_id),
            'review_text':review.text,'text_sha256':review.text_sha256,'language_code':review.language_code,'created_at':review.created_at.isoformat(),
            'is_deleted':False,'is_synthetic':False,'moderation_status':'published','consent_or_license_ref':review.consent_version,'evidence_permitted':True,
            'probabilities':sentiment.payload['probabilities'] if sentiment else None,'sentiment_label':sentiment.payload['label'] if sentiment else None,
            'calibrated':bool(sentiment),'prediction_approved':bool(sentiment),'model_version':sentiment.model_version if sentiment else None,
            'aspect_categories':list({item['target_key'] for item in targets}),'target_predictions':targets})
    from scoring.policy import load_policy
    from scoring.aggregate import aggregate,target_records
    try:
        policy=load_policy(safe_path(settings.scoring_config,ROOT),safe_path(settings.scoring_approval,ROOT))
        score=aggregate(evidence,str(movie_id),policy)
    except (ValueError,TypeError,OSError,KeyError):
        policy=None
        score={'score':None,'review_count':len(evidence),'message':'Audience methodology is awaiting validation.' if evidence else 'Not enough audience reviews yet.','status':'methodology_unavailable' if evidence else 'insufficient_evidence'}
    session.add(MovieScore(movie_id=movie_id,score_type='overall',evidence_version=movie.evidence_version,score=score['score'],payload=score,
        model_version=policy.model_version if policy else 'unavailable',method_version=policy.method_version if policy else 'unavailable'))
    for key,paths in settings.target_score_policies.items():
        target_policy=load_policy(safe_path(paths['config'],ROOT),safe_path(paths['approval'],ROOT))
        target=aggregate(target_records(evidence,'aspect',key),str(movie_id),target_policy,'aspect',key)
        session.add(MovieScore(movie_id=movie_id,score_type='aspect',target_key=key,evidence_version=movie.evidence_version,
            score=target['score'],payload=target,model_version=target_policy.model_version,method_version=target_policy.method_version))
    from ml.summarization.predict import summarize
    summary=summarize(evidence,str(movie_id),{'mode':'extractive','maximum_reviews':10000,'maximum_selected_reviews':12})
    session.add(MovieSummary(movie_id=movie_id,evidence_version=movie.evidence_version,payload=summary))
    session.commit()
