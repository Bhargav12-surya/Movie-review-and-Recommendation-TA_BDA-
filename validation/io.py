"""Bounded workspace inputs and fresh reports; no raw data writes or secrets."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import uuid

ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN={'.git','.venv','venv','node_modules','temp'}


def path(value,output=False):
    given=Path(value);resolved=(ROOT/given).resolve() if not given.is_absolute() else given.resolve()
    if resolved==ROOT or not resolved.is_relative_to(ROOT) or set(part.casefold() for part in resolved.relative_to(ROOT).parts)&FORBIDDEN:
        raise ValueError('Use a permitted path within the workspace.')
    if any(part.casefold().startswith('.env') and part.casefold()!='.env.example' for part in resolved.parts) or resolved.suffix.lower() in {'.key','.pem'}:
        raise ValueError('Credential files cannot be evaluation inputs or outputs.')
    if output and not resolved.is_relative_to(ROOT/'artifacts'):
        raise ValueError('Evaluation outputs belong under artifacts; raw datasets are immutable.')
    return resolved


def digest(value,maximum=256*1024**2):
    source=path(value)
    if not source.is_file() or source.stat().st_size>maximum:raise ValueError('Input missing or exceeds the declared hashing budget.')
    before=(source.stat().st_size,source.stat().st_mtime_ns);result=hashlib.sha256()
    with source.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):result.update(chunk)
    if (source.stat().st_size,source.stat().st_mtime_ns)!=before:raise ValueError('Input changed during hashing.')
    return result.hexdigest()


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate JSON key.')
        result[key]=value
    return result


def decode(value):
    def reject(_):raise ValueError('Nonfinite JSON number.')
    return json.loads(value,object_pairs_hook=unique,parse_constant=reject)


def read(value,maximum=8*1024**2):
    source=path(value)
    if not source.is_file() or source.stat().st_size>maximum:raise ValueError('Bounded JSON input required.')
    result=decode(source.read_text(encoding='utf-8-sig'))
    if not isinstance(result,dict):raise ValueError('Expected a JSON object.')
    return result


def rows(value,maximum_rows=100000,maximum_bytes=128*1024**2):
    source=path(value);total=0
    with source.open('r',encoding='utf-8-sig') as stream:
        for index,line in enumerate(stream):
            total+=len(line.encode('utf-8'))
            if index>=maximum_rows or total>maximum_bytes or len(line)>1024**2:raise ValueError('JSONL export budget exceeded.')
            item=decode(line)
            if not isinstance(item,dict):raise ValueError('Each JSONL row must be an object.')
            yield item


def write(value,payload):
    target=path(value,output=True);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(payload,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')


def run_directory(label):
    if label not in {'phase12','phase13','benchmark','rehearsal','bundle'}:raise ValueError('Unknown report purpose.')
    target=ROOT/'artifacts'/label/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:10])
    target.mkdir(parents=True,exist_ok=False)
    return target


def approved(config):
    if config.get('execution_approved') is not True or not config.get('reviewed_by'):
        raise ValueError('Supply a reviewed execution config; examples deliberately approve nothing.')


def pointer(document,value):
    if value=='':return document
    if not isinstance(value,str) or not value.startswith('/'):raise ValueError('Use a JSON pointer, not executable expressions.')
    for part in value[1:].split('/'):
        part=part.replace('~1','/').replace('~0','~')
        document=document[int(part)] if isinstance(document,list) else document[part]
    return document
