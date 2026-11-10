"""Trace actual metrics/checks to reviewed frozen files; absent evidence stays open."""
import math
from .io import approved,digest,pointer,read


def build(config_path):
    config=read(config_path);approved(config);studies=config.get('studies',[]);records=[];seen=set()
    for study in studies:
        identifier=study['id']
        if identifier in seen:raise ValueError('Duplicate study identifier.')
        seen.add(identifier);record={'id':identifier,'task':study['task'],'protocol_id':study['protocol_id'],'evaluation_role':study.get('evaluation_role'),'status':'unavailable','metrics':{},'checks':{}}
        try:
            checksum=digest(study['artifact_path'])
            if checksum!=study['artifact_sha256']:raise ValueError('Artifact hash differs.')
            source=read(study['artifact_path'])
            role=study.get('evaluation_role')
            if role not in {'held_out_test','validation','calibration_diagnostic','runtime_acceptance','exploratory'}:raise ValueError('Declare the actual evaluation role.')
            if role=='held_out_test' and source.get('split')!='test':raise ValueError('Held-out claims require an actual test report; tuning/calibration cannot substitute.')
            if not study.get('reviewed_by') or study.get('provenance_reviewed') is not True:raise ValueError('Actual execution/provenance must be reviewed.')
            bindings=study.get('expected_fields',{})
            if not bindings:raise ValueError('Bind evidence to its task/split/input/model or executed source snapshot.')
            for location,expected in bindings.items():
                if pointer(source,location)!=expected:raise ValueError('Artifact provenance binding differs.')
            for name,location in study.get('metric_pointers',{}).items():
                value=pointer(source,location)
                if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Requested metric is absent/nonfinite/non-numeric.')
                record['metrics'][name]=value
            for name,check in study.get('check_pointers',{}).items():record['checks'][name]=pointer(source,check['pointer'])==check['expected']
            if not record['metrics'] and not record['checks']:raise ValueError('Study contains no measured metric or executed acceptance check.')
            record.update(status='recorded' if all(record['checks'].values()) else 'failed',artifact_path=study['artifact_path'],artifact_sha256=checksum,
                expected_fields=bindings,reviewed_by=study['reviewed_by'])
        except (OSError,ValueError,KeyError,IndexError,TypeError):record.update(status='unavailable',reason='reviewed_matching_artifact_required',metrics={},checks={})
        records.append(record)
    criteria=[]
    for requirement in config.get('requirements',[]):
        needed=set(requirement.get('study_ids',[]));matching=[item for item in records if item['id'] in needed]
        complete=bool(needed) and len(matching)==len(needed) and all(item['status']=='recorded' for item in matching)
        criteria.append({'id':requirement['id'],'satisfied':complete,'study_ids':sorted(needed)})
    # A fully recorded register is evidence availability, not a blanket quality
    # approval: scientific thresholds/claims need separate human decisions.
    return {'kind':'evidence_register','status':'recorded' if criteria and all(row['satisfied'] for row in criteria) else 'incomplete',
        'config_sha256':digest(config_path),'studies':records,'requirements':criteria,
        'acceptance':'No automatic academic/model-quality approval; review criterion coverage,protocols,supports and limitations.'}
