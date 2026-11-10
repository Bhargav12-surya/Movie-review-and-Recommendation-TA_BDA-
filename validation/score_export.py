"""Build paired Python/Spark comparison inputs from real approved predictions."""
from dataclasses import asdict
import hashlib
import json
from .io import ROOT,approved,digest,path,read,rows,run_directory,write


def prepare(config_path):
    config_hash=digest(config_path);config=read(config_path);approved(config)
    if config.get('source_permission_reviewed') is not True or config['source_sha256']!=digest(config['source_path']):raise ValueError('A reviewed genuine prediction snapshot and its exact hash are required.')
    from scoring.policy import load_policy
    from scoring.eligibility import eligible
    from scoring.aggregate import aggregate
    policy_hash=digest(config['policy_path']);approval_hash=digest(config['policy_approval_path'])
    policy=load_policy(path(config['policy_path']),path(config['policy_approval_path']))
    if digest(config['policy_path'])!=policy_hash or digest(config['policy_approval_path'])!=approval_hash:raise ValueError('Scoring policy changed while loading.')
    scope=config.get('movie_ids',[])
    if not scope or len(scope)>1000 or len(set(scope))!=len(scope) or any(not isinstance(value,str) or not value for value in scope):raise ValueError('Declare1..1000 genuine canonical movie IDs without duplicates.')
    source=list(rows(config['source_path']));directory=run_directory('phase12');eligible_rows=[];scope_rows=[];scores=[]
    for movie_id in scope:
        selected,_=eligible(source,movie_id,policy)
        lookup={(row['review_id'],row['review_revision']):row for row in source if str(row.get('movie_id'))==movie_id}
        values=[]
        for item in selected:
            original=lookup[item['review_id'],item['revision']];probabilities=original['probabilities']
            values.append({'movie_id':movie_id,'review_id':item['review_id'],'reviewer_id':item['reviewer_id'],
                'p_negative':probabilities['negative'],'p_neutral':probabilities['neutral'],'p_positive':probabilities['positive'],'weight':item['weight']})
        eligible_hash=hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        provenance={'movie_id':movie_id,'score_type':'overall','target_key':None,'model_version':policy.model_version,'method_version':policy.method_version,
            'policy_sha256':policy_hash,'eligible_evidence_sha256':eligible_hash}
        score=aggregate(source,movie_id,policy)
        scores.append({**provenance,**{name:score.get(name) for name in ('score','raw_score','review_count','distinct_reviewers','effective_review_count','message')}})
        scope_rows.append(provenance);eligible_rows.extend(values)
    for filename,values in [('eligible.jsonl',eligible_rows),('scope.jsonl',scope_rows),('python_scores.jsonl',scores)]:
        with (directory/filename).open('x',encoding='utf-8') as stream:
            for row in values:stream.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')
    if digest(config['source_path'])!=config['source_sha256'] or digest(config_path)!=config_hash:raise ValueError('Comparison source/config changed; no completion manifest is published.')
    if digest(config['policy_path'])!=policy_hash or digest(config['policy_approval_path'])!=approval_hash:raise ValueError('Scoring methodology changed; no completion manifest is published.')
    result={'kind':'approved_score_parity_inputs','status':'prepared','source_permission_reviewed':True,'config_sha256':config_hash,
        'source_sha256':config['source_sha256'],'policy':asdict(policy),'policy_path':config['policy_path'],'policy_sha256':policy_hash,
        'policy_approval_path':config['policy_approval_path'],'policy_approval_sha256':approval_hash,
        'files_sha256':{name:digest(directory/name) for name in ('eligible.jsonl','scope.jsonl','python_scores.jsonl')},'scope':scope_rows,
        'limitations':'Genuine probability snapshot eligibility is evaluated in Python first. Scala checks only the shared arithmetic on exactly these frozen selected rows. This does not independently validate source labels or scientific policy.'}
    write(directory/'score_export.json',result)
    return {**result,'report_path':str((directory/'score_export.json').relative_to(ROOT))}
