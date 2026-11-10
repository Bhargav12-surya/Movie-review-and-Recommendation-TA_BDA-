"""Read-only local endpoint rehearsal plus independently reviewed operator evidence."""
from .benchmark import local_url,request
from .io import approved,digest,read

REQUIRED=('full_browser_journey','offline_cached_operation','worker_failure_recovery','database_failure_recovery',
    'missing_model_abstention','stream_restart_and_deletion','checkpoint_load','actual_spark_ui','attribution_and_consent','no_demo_training')


def evaluate(config_path):
    config=read(config_path);approved(config);checks=[]
    endpoints=config.get('endpoints',[])
    if not 1<=len(endpoints)<=5:raise ValueError('Declare1..5 read-only local endpoints.')
    for endpoint in endpoints:
        local_url(endpoint['url']);result=request(endpoint,5);checks.append({'id':'endpoint:'+endpoint['id'],'status':result['status'],'seconds':result['seconds']})
    evidence=config.get('operator_evidence',{})
    for identifier in REQUIRED:
        item=evidence.get(identifier,{})
        try:
            valid=item.get('passed') is True and bool(item.get('reviewed_by')) and item.get('artifact_sha256')==digest(item['artifact_path'])
        except (KeyError,ValueError,OSError):valid=False
        checks.append({'id':identifier,'status':'passed' if valid else 'incomplete','artifact_sha256':item.get('artifact_sha256') if valid else None})
    offline=config.get('network_disconnected_confirmed_by_operator') is True
    checks.append({'id':'operator_offline_confirmation','status':'passed' if offline else 'incomplete'})
    return {'kind':'demo_rehearsal','status':'passed' if all(row['status']=='passed' for row in checks) else 'incomplete','checks':checks,
        'config_sha256':digest(config_path),'limitations':'Endpoint checks prove reachability/status only. Operator evidence must document genuine observed journeys/fault recovery; this tool never changes adapters,stops services,trains or invents screenshots.'}
