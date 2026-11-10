"""Freeze a real pretrained retrieval experiment for later manual promotion.

This command performs metadata validation and ranking evaluation, not encoding,
training, model fetching or database writes. All inputs must already be local.
"""
import argparse
from ml.common.artifacts import safe_path,read_json,sha256,write_json
from ml.common.records import load_config
from ml.common.local_assets import approved_assets
from ml.embeddings.evaluate import evaluate
from backend.app.core.config import ROOT


def prepare(config_path,rankings_path,judgments_path,study_path,output):
    config_path=safe_path(config_path,ROOT);config=load_config(config_path)
    _,permission=approved_assets(config)
    rankings_path=safe_path(rankings_path,ROOT);judgments_path=safe_path(judgments_path,ROOT)
    study=read_json(safe_path(study_path,ROOT));rankings=read_json(rankings_path);judgments=read_json(judgments_path)
    if (study.get('split')!='test' or study.get('selection_frozen_before_test') is not True or not study.get('reviewed_by') or
        study.get('rankings_sha256')!=sha256(rankings_path) or study.get('judgments_sha256')!=sha256(judgments_path) or
        study.get('model_revision')!=permission['model_revision'] or not study.get('catalogue_sha256') or
        study.get('genuine_human_judgments') is not True or study.get('rankings_generated_by_actual_model') is not True):
        raise ValueError('A reviewed held-out retrieval study bound to actual model rankings and human judgments is required.')
    scope=study.get('validated_language_scope',[])
    if not scope or not set(scope)<=set(config['language_scope']):raise ValueError('Human-validated scope must be within the configured model scope.')
    metrics=evaluate(rankings,judgments,k=study.get('k',10))
    run=safe_path(output,ROOT,output=True);run.mkdir(parents=True,exist_ok=False)
    manifest={'schema_version':1,'component':'embeddings','task':'embeddings','pretrained':True,'trained':False,
        'locally_fine_tuned':False,'model_revision':permission['model_revision'],'language_scope':scope,
        'config_sha256':sha256(config_path),'permission_sha256':sha256(safe_path(config['model']['permission_path'],ROOT)),
        'retrieval_study_sha256':sha256(safe_path(study_path,ROOT))}
    write_json(run/'model_manifest.json',manifest)
    write_json(run/'evaluation-test.json',{'split':'test','metrics':metrics,'model_manifest_sha256':sha256(run/'model_manifest.json'),
        'rankings_sha256':sha256(rankings_path),'judgments_sha256':sha256(judgments_path),'study':study})
    return {'status':'metadata_frozen_not_serving_approved','run_path':str(run.relative_to(ROOT))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('config','rankings','judgments','study','output'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    import json
    print(json.dumps(prepare(args.config,args.rankings,args.judgments,args.study,args.output)))

if __name__=='__main__':main()
