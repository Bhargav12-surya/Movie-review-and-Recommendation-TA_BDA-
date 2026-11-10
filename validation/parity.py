"""Compare genuine normalized score/state exports; do not run Spark or infer."""
import math
from .io import approved,digest,read,rows


def key(row):
    return (str(row['movie_id']),row.get('score_type','overall'),row.get('target_key'))


def close(left,right,tolerance):
    if left is None or right is None:return left is right
    return type(left) in (int,float) and type(right) in (int,float) and math.isfinite(left) and math.isfinite(right) and math.isclose(left,right,rel_tol=tolerance,abs_tol=tolerance)


def score_parity(left,right,scope,tolerance=1e-7):
    """Each export must describe the same already eligible evidence and policy.

    Scala exports wrap ReviewAnalytics outputs with externally frozen provenance;
    they must never manufacture a new audience score or synthesize absent rows.
    """
    if not scope or not 0<tolerance<=1e-3:raise ValueError('Declare a nonempty movie scope and bounded numerical tolerance.')
    def indexed(values):
        result={}
        for row in values:
            identifier=key(row)
            if identifier in result:raise ValueError('Duplicate score identity in an export.')
            for field in ('model_version','method_version','policy_sha256','eligible_evidence_sha256'):
                if not row.get(field):raise ValueError('Both exports need model/method/policy/evidence provenance.')
            for field in ('review_count','distinct_reviewers'):
                if type(row.get(field)) is not int or row[field]<0:raise ValueError('Explicit nonnegative integer evidence counts required.')
            if 'score' not in row or 'raw_score' not in row or 'effective_review_count' not in row:raise ValueError('Explicit normalized score/null/support fields required.')
            for field in ('score','raw_score'):
                if row[field] is not None and (type(row[field]) not in (float,int) or not math.isfinite(row[field]) or not 0<=row[field]<=100):raise ValueError('Score must be null or within0..100.')
            result[identifier]=row
        return result
    first,second=indexed(left),indexed(right);failures=[];compared=0
    expected={(str(item['movie_id']),item.get('score_type','overall'),item.get('target_key')) for item in scope}
    for identifier in sorted(expected,key=str):
        if identifier not in first or identifier not in second:failures.append({'identity':list(identifier),'field':'missing_export_row'});continue
        a,b=first[identifier],second[identifier];compared+=1
        for field in ('model_version','method_version','policy_sha256','eligible_evidence_sha256','review_count','distinct_reviewers'):
            if field not in a or field not in b or a[field]!=b[field]:failures.append({'identity':list(identifier),'field':field})
        for field in ('score','raw_score','effective_review_count'):
            # raw_score is deliberately absent/null below the minimum in both normalized exports.
            if not close(a.get(field),b.get(field),tolerance):failures.append({'identity':list(identifier),'field':field})
        if a.get('score') is None:
            if a.get('message')!='Not enough audience reviews yet.' or b.get('message')!='Not enough audience reviews yet.':failures.append({'identity':list(identifier),'field':'minimum_evidence_message'})
        # ReviewAnalytics has no bootstrap interval. Record uncertainty as not
        # comparable rather than pretending matching nulls proves calibration.
    if set(first)!=expected or set(second)!=expected:failures.append({'field':'export_scope_differs'})
    return {'kind':'score_parity','status':'passed' if compared and not failures else 'failed','compared_rows':compared,'failures':failures,
        'tolerance':tolerance,'uncertainty_parity':'not_implemented_in_scala; assess_python_bootstrap_separately'}


def state_parity(batch,stream,declared_pending=()):
    """Compare finalized current-review exports, including tombstones/late edits.

    Export review_id,review_revision,movie_id,operation,model_version,
    consent_eligible,moderation_eligible,is_synthetic and semantic_hash. A retained
    disputed revision must be quarantined, never downgraded to an older upsert.
    """
    def indexed(values):
        result={}
        for row in values:
            identifier=row['review_id']
            if identifier in result:raise ValueError('Current-state exports need exactly one row per review.')
            if type(row.get('review_revision')) is not int or row['review_revision']<1 or not row.get('semantic_hash'):
                raise ValueError('Current revision and validated semantic hash required.')
            if row.get('operation') not in {'upsert','delete'} or any(type(row.get(field)) is not bool for field in ('consent_eligible','moderation_eligible','is_synthetic')):
                raise ValueError('Validated operation and explicit eligibility booleans required.')
            result[identifier]=row
        return result
    first,second=indexed(batch),indexed(stream);pending=set(declared_pending);failures=[]
    fields=('movie_id','review_revision','operation','model_version','consent_eligible','moderation_eligible','is_synthetic','semantic_hash')
    for identifier in set(first)|set(second):
        if identifier in pending:continue
        if identifier not in first or identifier not in second:failures.append({'review_id':identifier,'field':'missing_current_revision'});continue
        for field in fields:
            if field not in first[identifier] or field not in second[identifier] or first[identifier][field]!=second[identifier][field]:failures.append({'review_id':identifier,'field':field})
    status='failed' if failures else 'incomplete' if pending or not first else 'passed'
    return {'kind':'state_parity','status':status,'batch_rows':len(first),'stream_rows':len(second),'pending_count':len(pending),
        'failures':failures,'limitations':'Declared pending IDs keep acceptance incomplete. This compares supplied snapshots; it does not execute restart/replay/conflict scenarios or prove exactly-once.'}


def evaluate(config_path):
    config=read(config_path);approved(config);kind=config.get('kind')
    first,second=config['left'],config['right']
    for item in (first,second):
        if item.get('sha256')!=digest(item['path']):raise ValueError('Export hash differs from the frozen comparison input.')
    a,b=list(rows(first['path'])),list(rows(second['path']))
    if kind=='score':result=score_parity(a,b,config.get('scope',[]),config.get('tolerance',1e-7))
    elif kind=='state':result=state_parity(a,b,config.get('declared_pending_review_ids',[]))
    else:raise ValueError('Choose score or state parity.')
    result['input_sha256']={'left':first['sha256'],'right':second['sha256'],'config':digest(config_path)}
    return result
