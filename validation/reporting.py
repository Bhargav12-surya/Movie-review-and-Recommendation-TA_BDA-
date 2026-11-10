"""Readable tables from genuine registered reports; never invent missing values."""
from .io import digest,read,write


def comparison(register,study_ids,metric):
    selected=[item for item in register.get('studies',[]) if item['id'] in set(study_ids)]
    if len(selected)!=len(set(study_ids)) or not selected:raise ValueError('Every requested actual study must exist.')
    if len({(item['task'],item['protocol_id'],item.get('evaluation_role')) for item in selected})!=1:raise ValueError('Compare only the same task,role and frozen split/candidate protocol.')
    return [{'study':item['id'],'value':item.get('metrics',{}).get(metric) if item['status']=='recorded' else None,
        'status':item['status'],'artifact_sha256':item.get('artifact_sha256')} for item in selected]


def markdown(register):
    def escaped(value):return str(value).replace('|','/').replace('\n',' ')
    lines=['# Actual evaluation evidence','',f"Register status: {escaped(register.get('status','incomplete'))}.",'',
        'Missing metrics remain unmeasured. Recorded evidence does not establish scientific acceptance.','',
        '| Study | Task/protocol | Status | Actual metrics |','|---|---|---|---|']
    for item in register.get('studies',[]):
        metrics=', '.join(f'{escaped(name)}={value:.6g}' for name,value in item.get('metrics',{}).items()) or 'Unmeasured'
        lines.append(f"| {escaped(item['id'])} | {escaped(item['task'])} / {escaped(item['protocol_id'])} / {escaped(item.get('evaluation_role'))} | {escaped(item['status'])} | {metrics} |")
    return '\n'.join(lines)+'\n'
