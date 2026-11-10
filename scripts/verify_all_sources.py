"""Static verification of all active project source, never application execution.

Excluded: datasets,weights,artifacts,legacy temp copies,dependencies,Git and
caches. Those files must not be executed/deserialized or mistaken for active
source. Scala,PowerShell and TypeScript parser checks have separate reports.
"""
import ast
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote
import uuid
import tomllib

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','.venv','venv','node_modules','temp','data','models','artifacts','logs','.cache','.aws','.codex','.agents','.vscode','.next','__pycache__','.pytest_cache','.metals','.bloop','target','dist','build','.ipynb_checkpoints','test-results','playwright-report'}
EXTENSIONS={'.py','.json','.yaml','.yml','.ipynb','.scala','.sbt','.ts','.tsx','.mjs','.js','.ps1','.sql','.md','.txt','.ini','.css','.toml','.properties'}


def main():
    paths=[];errors=[];warnings=[];counts={'python':0,'authored_python_tests_not_executed':0,'json_or_yaml':0,'toml':0,'notebooks':0,'notebook_python_cells':0,'scala_recorded':0,'powershell_recorded':0,'typescript_recorded':0,'other_source':0};trees={}
    for parent,directories,files in os.walk(ROOT):
        directories[:]=[name for name in directories if name not in EXCLUDED]
        for name in files:
            item=Path(parent)/name
            if name.startswith('.env') or item.suffix not in EXTENSIONS:continue
            if item.stat().st_size>16*1024**2: warnings.append({'file':item.relative_to(ROOT).as_posix(),'reason':'oversized_source_not_read'});continue
            paths.append(item)
    for item in sorted(paths):
        relative=item.relative_to(ROOT).as_posix()
        try:
            value=item.read_text(encoding='utf-8-sig')
            if item.suffix=='.py':
                trees[item]=ast.parse(value,filename=relative);counts['python']+=1
                if 'tests' in item.relative_to(ROOT).parts:counts['authored_python_tests_not_executed']+=sum(isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test_') for node in ast.walk(trees[item]))
            elif item.suffix in {'.json','.yaml','.yml'}:
                if item.suffix=='.json':json.loads(value)
                else:
                    try:json.loads(value)
                    except ValueError:
                        import yaml
                        yaml.safe_load(value)
                counts['json_or_yaml']+=1
            elif item.suffix=='.toml':tomllib.loads(value);counts['toml']+=1
            elif item.suffix=='.ipynb':
                notebook=json.loads(value);counts['notebooks']+=1
                for index,cell in enumerate(notebook['cells']):
                    if cell['cell_type']=='code':
                        code=''.join(cell['source'])
                        if any(line.lstrip().startswith(('%','!')) for line in code.splitlines()):warnings.append({'file':relative,'cell':index,'reason':'notebook_magic_requires_kernel_validation'});continue
                        ast.parse(code,filename=relative+':cell'+str(index));counts['notebook_python_cells']+=1
                        if cell.get('execution_count') is not None or cell.get('outputs'):warnings.append({'file':relative,'cell':index,'reason':'historical_output_not_current_validation'})
            elif item.suffix=='.scala':counts['scala_recorded']+=1
            elif item.suffix=='.ps1':counts['powershell_recorded']+=1
            elif item.suffix in {'.ts','.tsx'}:counts['typescript_recorded']+=1
            else:counts['other_source']+=1
            if item.suffix=='.md':
                for target in re.findall(r'\]\(([^)]+)\)',value):
                    target=target.split('#',1)[0].strip('<>')
                    if not target or ':' in target or target.startswith('/'):continue
                    resolved=(item.parent/unquote(target)).resolve()
                    if not resolved.exists():warnings.append({'file':relative,'reason':'document_reference_missing_or_future','target':target})
        except Exception as error:errors.append({'file':relative,'error_type':type(error).__name__,'line':getattr(error,'lineno',None)})
    roots={'backend','discovery','ml','scoring','recommender','dataset_tools','validation','tests'}
    for item,tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom) and not node.level and node.module and node.module.split('.')[0] in roots:
                target=ROOT/Path(*node.module.split('.'))
                if not target.with_suffix('.py').is_file() and not (target/'__init__.py').is_file():errors.append({'file':item.relative_to(ROOT).as_posix(),'error_type':'local_module_missing','module':node.module})
    required=['validation/runner.py','validation/parity.py','validation/score_export.py','validation/state_export.py','validation/model_smoke.py','validation/grounding.py','validation/evidence.py','validation/rehearsal.py','validation/bundle.py',
        'scripts/evaluate_all.ps1','scripts/rehearse_demo.ps1','scripts/prepare_evaluation_bundle.ps1','notebooks/15_final_model_comparison.ipynb','documentation/phase12/RUNBOOK.md',
        'documentation/final/ACADEMIC_REPORT.md','documentation/final/PRESENTATION.md','documentation/final/SYLLABUS_MAPPING.md']
    for relative in required:
        if not (ROOT/relative).is_file():errors.append({'file':relative,'error_type':'required_phase12_13_file_missing'})
    report={'schema_version':1,'scope':'all_active_source_static_only','date_asia_calcutta':'2026-11-10','checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'passed':not errors,'counts':counts,'errors':errors,'warnings':warnings,'excluded_directories':sorted(EXCLUDED),
        'files_sha256':{item.relative_to(ROOT).as_posix():hashlib.sha256(item.read_bytes()).hexdigest() for item in sorted(paths)},
        'limits':'No imports of project modules,tests,model/data deserialization,DB/Spark/services/builds/installers/resolvers. Non-JSON YAML uses the already-installed safe YAML parser without executing tags. Recorded JVM/PS/TS sources need separate parser reports. Missing/future doc references are warnings,not runtime acceptance.'}
    output=ROOT/'artifacts/source_validation'/('all-active-'+uuid.uuid4().hex[:12]+'.json');output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps({'passed':report['passed'],'counts':counts,'errors':errors,'warnings_count':len(warnings),'report':str(output.relative_to(ROOT))}))
    return 0 if report['passed'] else 2

if __name__=='__main__':raise SystemExit(main())
