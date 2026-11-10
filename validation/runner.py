"""Fixed local evaluation commands; plan by default, never trains or installs."""
import argparse
import json
import os
import subprocess
import sys
from .io import ROOT,digest,read,run_directory,write

GROUPS=('unit','postgres','browser','benchmark','parity','grounding','evidence')


def child(command,timeout,cwd=None):
    try:
        completed=subprocess.run(command,cwd=cwd or ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=False)
        if len(completed.stdout)>8*1024**2:raise ValueError('Structured runner output exceeded its budget.')
        # Only our curated reporters are accepted. Raw stderr is never persisted.
        report=json.loads(completed.stdout)
        if not isinstance(report,dict) or report.get('status') not in {'passed','failed','incomplete'}:raise ValueError('Structured reporter output required.')
        if completed.returncode and report['status']=='passed':report['status']='failed'
        return report
    except (OSError,ValueError,subprocess.TimeoutExpired):return {'status':'failed','reason':'local_runner_unavailable_or_timeout','details_redacted':True}


def run(config_path,groups,execute=False,allow_browser=False):
    config=read(config_path)
    if not groups or set(groups)-set(GROUPS):raise ValueError('Unknown evaluation group.')
    if not execute:return {'status':'planned','executed':False,'groups':groups,'restrictions':'No packages,services,training,DB or test commands started.'}
    directory=run_directory('phase12');results=[]
    for group in groups:
        try:
            if group in {'unit','postgres'}:
                modules=config[group+'_modules']
                if group=='postgres' and os.environ.get('RUN_POSTGRES_TESTS')!='1':report={'status':'incomplete','reason':'disposable_database_opt_in_required'}
                else:report=child([sys.executable,'-B','-m','validation.testing','--execute','--modules',*modules],config.get('test_timeout_seconds',300))
            elif group=='browser':
                node=config.get('node_executable','C:/Program Files/nodejs/node.exe');entry=ROOT/'frontend/node_modules/@playwright/test/cli.js'
                if not allow_browser or os.environ.get('RUN_LOCAL_E2E')!='1':report={'status':'incomplete','reason':'browser_and_local_stack_opt_in_required'}
                elif not entry.is_file():report={'status':'incomplete','reason':'manually_installed_playwright_required'}
                else:report=child([node,str(entry),'test','--reporter=./tests/reporter.ts'],config.get('browser_timeout_seconds',600),ROOT/'frontend')
            else:
                input_config=config[group+'_config']
                if not input_config:report={'status':'incomplete','reason':'reviewed_local_config_required'}
                elif group=='benchmark':
                    from .benchmark import measure
                    report=measure(input_config)
                elif group=='parity':
                    from .parity import evaluate
                    report=evaluate(input_config)
                elif group=='grounding':
                    from .grounding import evaluate
                    report=evaluate(input_config)
                else:
                    from .evidence import build
                    report=build(input_config)
            write(directory/(group+'.json'),report)
            results.append({'group':group,'status':report['status'],'report':str((directory/(group+'.json')).relative_to(ROOT))})
        except Exception as error:
            results.append({'group':group,'status':'incomplete','error_type':type(error).__name__,'reason':'valid_inputs_and_manual_prerequisites_required'})
    # Measured/recorded are intentionally not a passing acceptance verdict.
    status='failed' if any(row['status']=='failed' for row in results) else 'passed' if results and all(row['status']=='passed' for row in results) else 'incomplete'
    report={'kind':'phase12_selected_groups','status':status,'executed':True,'config_sha256':digest(config_path),'groups':results,
        'acceptance_scope':'Selected groups only. Scientific final tests,Spark jobs,restart/fault scenarios and academic acceptance are separate evidence requirements.'}
    report['report_path']=str((directory/'summary.json').relative_to(ROOT))
    write(directory/'summary.json',report);return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',default='configs/validation/suite.json');parser.add_argument('--groups',nargs='+',choices=GROUPS,default=['unit'])
    parser.add_argument('--execute',action='store_true');parser.add_argument('--allow-browser',action='store_true');args=parser.parse_args()
    try:result=run(args.config,args.groups,args.execute,args.allow_browser)
    except Exception as error:result={'status':'incomplete','error_type':type(error).__name__}
    print(json.dumps(result));return 0 if result['status'] in {'planned','passed'} else 2

if __name__=='__main__':raise SystemExit(main())
