"""Static source/config/schema verification for the through-Phase11 handoff.

No application imports, tests, package resolution, DB connections, model loads,
service startup or build commands. Writes a new bounded evidence report only.
"""
import argparse
import ast
from datetime import datetime,timezone,timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

ROOT=Path(__file__).resolve().parents[1]
PRUNED={'node_modules','.next','__pycache__','.git','.venv','venv'}


def collect(folder):
    if not folder.exists():return []
    result=[]
    for parent,directories,files in os.walk(folder):
        directories[:]=[name for name in directories if name not in PRUNED]
        result.extend(Path(parent)/name for name in files if Path(name).suffix in {'.py','.json','.ts','.tsx','.mjs','.css','.sql','.ini','.md','.ps1'})
    return result


def sql_columns(sql):
    tables={}
    for name,definition in re.findall(r'CREATE TABLE (\w+) \((.*?)\);',sql,re.S):
        parts=[];pending='';level=0;quoted=False
        for character in definition:
            if character=="'":quoted=not quoted
            if not quoted:
                if character=='(':level+=1
                if character==')':level-=1
            if character==',' and level==0 and not quoted:parts.append(pending);pending=''
            else:pending+=character
        parts.append(pending)
        names=[re.match(r'\s*(\w+)',part)[1] for part in parts]
        tables[name]={column for column in names if column.upper() not in {'PRIMARY','UNIQUE','CHECK','CONSTRAINT','FOREIGN'}}
    for name,column in re.findall(r'ALTER TABLE (\w+) ADD COLUMN (\w+)',sql):tables[name].add(column)
    return tables


def orm_columns(tree):
    result={}
    for cls in (node for node in tree.body if isinstance(node,ast.ClassDef)):
        name=None;columns=set()
        for node in cls.body:
            if not isinstance(node,ast.Assign):continue
            for target in node.targets:
                if not isinstance(target,ast.Name):continue
                if target.id=='__tablename__':name=ast.literal_eval(node.value)
                if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id in {'Column','uid','created','obj','arr'}:
                    columns.add(target.id)
        if name:result[name]=columns
    return result


def verify():
    errors=[];counts={'python':0,'json':0,'typescript_recorded':0,'sql_tables':0};trees={}
    paths=[]
    for folder in ('backend','frontend','discovery','documentation/phases9-11'):paths+=collect(ROOT/folder)
    for name in ('verify_application_sources.py','_local_services.ps1','start_all.ps1','stop_all.ps1','start_backend.ps1','start_worker.ps1','start_frontend.ps1','setup_database.ps1'):
        paths.append(ROOT/'scripts'/name)
    for path in sorted(set(paths)):
        try:
            if path.suffix=='.py':trees[path]=ast.parse(path.read_text(encoding='utf-8-sig'));counts['python']+=1
            elif path.suffix=='.json':json.loads(path.read_text(encoding='utf-8-sig'));counts['json']+=1
            elif path.suffix in {'.ts','.tsx'}:counts['typescript_recorded']+=1
        except (SyntaxError,ValueError,OSError,UnicodeError) as error:errors.append({'file':path.relative_to(ROOT).as_posix(),'error':type(error).__name__})
    project_roots={'backend','ml','recommender','scoring','discovery','dataset_tools','scripts'}
    for path,tree in trees.items():
        for node in ast.walk(tree):
            if not isinstance(node,ast.ImportFrom) or node.level or not node.module:continue
            if node.module.split('.')[0] not in project_roots:continue
            target=ROOT/Path(*node.module.split('.'))
            if not target.with_suffix('.py').is_file() and not (target/'__init__.py').is_file():
                errors.append({'file':path.relative_to(ROOT).as_posix(),'error':'local_module_missing','module':node.module})
    try:
        expected=orm_columns(trees[ROOT/'backend/app/models/entities.py'])
        actual=sql_columns((ROOT/'backend/alembic/schema_v1.sql').read_text(encoding='utf-8'))
        counts['sql_tables']=len(actual)
        if expected!=actual:errors.append({'error':'orm_frozen_sql_column_mismatch','tables':[name for name in set(expected)|set(actual) if expected.get(name)!=actual.get(name)]})
        package=json.loads((ROOT/'frontend/package.json').read_text(encoding='utf-8'))
        lock=json.loads((ROOT/'frontend/package-lock.json').read_text(encoding='utf-8'))
        for section in ('dependencies','devDependencies'):
            if package.get(section)!=lock['packages'][''].get(section):errors.append({'error':'manual_lock_root_manifest_mismatch','section':section})
            for name,version in package.get(section,{}).items():
                entry=ROOT/'frontend/node_modules'/name/'package.json'
                if entry.is_file() and json.loads(entry.read_text(encoding='utf-8'))['version']!=version:
                    errors.append({'error':'installed_direct_package_version_mismatch','name':name})
    except (ValueError,OSError,KeyError) as error:errors.append({'error':'static_contract_check_failed','kind':type(error).__name__})
    required=['backend/README.md','frontend/README.md','discovery/README.md','documentation/phases9-11/RUNBOOK.md',
        'backend/.env.example','frontend/.env.example','backend/app/workers/main.py','frontend/app/assistant/page.tsx','discovery/speech.py']
    for name in required:
        if not (ROOT/name).is_file():errors.append({'error':'required_source_missing','file':name})
    fingerprints={path.relative_to(ROOT).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(set(paths)) if path.is_file()}
    return {'schema_version':1,'date_asia_calcutta':datetime.now(timezone(timedelta(hours=5,minutes=30))).date().isoformat(),'checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'through_phase11_source_only','passed':not errors,'counts':counts,'errors':errors,'files_sha256':fingerprints,
        'not_executed':['unit_tests','database_connections_or_migrations','model_inference_or_training','Spark_jobs','build','browser','services','Phase12','Phase13'],
        'limitations':'AST/JSON/import-path/SQL-column checks are static. SQL constraints, libraries, races, actual model outputs and user journeys require execution. TypeScript and PowerShell parser reports are separate.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output');args=parser.parse_args()
    target=Path(args.output) if args.output else ROOT/'artifacts/source_validation'/('phases9-11-'+uuid.uuid4().hex[:10]+'.json')
    target=target.resolve()
    if not target.is_relative_to(ROOT/'artifacts/source_validation') or target.exists():raise ValueError('Use a new artifact report path only.')
    report=verify();target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({'passed':report['passed'],'counts':report['counts'],'errors':report['errors'],'report':str(target.relative_to(ROOT))}))
    return 0 if report['passed'] else 2

if __name__=='__main__':raise SystemExit(main())
