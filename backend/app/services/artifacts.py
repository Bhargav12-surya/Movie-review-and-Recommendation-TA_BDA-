"""Promotion reads actual metadata; it never loads weights or invents evaluations."""
from ml.common.artifacts import safe_path,read_json,sha256
from backend.app.core.config import ROOT
from backend.app.core.errors import ServiceUnavailable
from backend.app.models import ModelArtifact
from sqlalchemy import select

def resolve(session,component,language=None):
    rows=session.scalars(select(ModelArtifact).where(ModelArtifact.component==component,ModelArtifact.approved.is_(True)).order_by(ModelArtifact.created_at.desc())).all()
    row=next((item for item in rows if language is None or language in item.language_scope),None)
    if row is None: raise ServiceUnavailable('approved_model_unavailable')
    run=safe_path(row.run_path,ROOT)
    manifest=run/'model_manifest.json'
    if sha256(manifest)!=row.manifest_sha256: raise ServiceUnavailable('model_manifest_changed')
    document=read_json(manifest)
    if document.get('config_sha256') and document['config_sha256']!=sha256(safe_path(row.config_path,ROOT)):
        raise ServiceUnavailable('approved_model_config_changed')
    return row

def promote(session,body):
    run=safe_path(body.run_path,ROOT,output=True)
    config=safe_path(body.config_path,ROOT)
    reference=safe_path(body.approval_reference,ROOT)
    decision=read_json(reference)
    manifest=read_json(run/'model_manifest.json')
    if manifest.get('component')!=body.component:raise ValueError('Artifact component differs from its manifest.')
    if decision.get('serving_approved') is not True or not decision.get('reviewed_by') or decision.get('manifest_sha256')!=sha256(run/'model_manifest.json'):
        raise ValueError('A genuine serving decision bound to the model manifest is required.')
    if body.component in {'sentiment_transformer','multilingual_sentiment'}:
        if manifest.get('task') not in {'three_class_movie','multilingual_movie'} or manifest.get('labels')!={'negative':0,'neutral':1,'positive':2}:
            raise ValueError('A real three-class domain model is required; binary IMDb cannot be promoted here.')
    report=read_json(safe_path(decision['evaluation_path'],ROOT))
    if report.get('split')!='test' or report.get('model_manifest_sha256')!=sha256(run/'model_manifest.json') or decision.get('evaluation_sha256')!=sha256(safe_path(decision['evaluation_path'],ROOT)):
        raise ValueError('A matching actual held-out evaluation is required.')
    if body.component=='embeddings' and manifest.get('pretrained') is True:
        from ml.common.local_assets import approved_assets
        from ml.common.records import load_config
        _,permission=approved_assets(load_config(config))
        if manifest.get('config_sha256')!=sha256(config) or manifest.get('model_revision')!=permission['model_revision']:
            raise ValueError('Pretrained retrieval artifact differs from the approved local config/revision.')
    elif manifest.get('trained') is not True:
        raise ValueError('Actual trained model artifacts are required.')
    if not set(body.language_scope)<=set(decision.get('validated_language_scope',[])):
        raise ValueError('Requested serving scope must have human-reviewed evaluation support.')
    row=ModelArtifact(component=body.component,version=body.version,config_path=str(config.relative_to(ROOT)),run_path=str(run.relative_to(ROOT)),
        manifest_sha256=sha256(run/'model_manifest.json'),approved=True,language_scope=body.language_scope,approval_reference=str(reference.relative_to(ROOT)))
    session.add(row);session.commit()
    return {'component':row.component,'version':row.version,'approved':True}
