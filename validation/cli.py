"""Explicit manual entry points for evidence,parity,grounding,rehearsal and bundles."""
import argparse
import json
from .io import ROOT,run_directory,write


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('benchmark','parity','grounding','evidence','rehearsal','bundle','models','score-export','state-export'))
    parser.add_argument('--config',required=True);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if not args.execute:print(json.dumps({'status':'planned','executed':False,'action':args.action}));return 0
    try:
        if args.action=='benchmark':
            from .benchmark import measure
            result=measure(args.config)
        elif args.action=='bundle':
            from .bundle import prepare
            result=prepare(args.config)
        elif args.action=='score-export':
            from .score_export import prepare
            result=prepare(args.config)
        elif args.action=='state-export':
            from .state_export import prepare
            result=prepare(args.config)
        else:
            if args.action=='models':from .model_smoke import evaluate as function
            elif args.action=='parity':from .parity import evaluate as function
            elif args.action=='grounding':from .grounding import evaluate as function
            elif args.action=='rehearsal':from .rehearsal import evaluate as function
            else:from .evidence import build as function
            result=function(args.config);directory=run_directory('rehearsal' if args.action=='rehearsal' else 'phase13' if args.action=='evidence' else 'phase12')
            write(directory/(args.action+'.json'),result)
            if args.action=='evidence':
                from .reporting import markdown
                with (directory/'results.md').open('x',encoding='utf-8') as stream:stream.write(markdown(result))
        report_path=result.get('report_path') or result.get('directory') or str((directory/(args.action+'.json')).relative_to(ROOT))
        print(json.dumps({'status':result['status'],'kind':result.get('kind'),'executed':True,'report_path':report_path}))
        return 0 if result['status'] in {'passed','measured','recorded','prepared'} else 2
    except Exception as error:
        print(json.dumps({'status':'blocked_or_failed','error_type':type(error).__name__,'details_redacted':True}));return 2

if __name__=='__main__':raise SystemExit(main())
