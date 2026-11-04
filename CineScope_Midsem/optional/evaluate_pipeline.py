"""Score externally collected gold/predictions. No labels or results are fabricated.
Usage: python optional/evaluate_pipeline.py data/evaluation.json
Schema is in data/evaluation_template.json and the handbook.
"""
import json
import math
import sys
from collections import Counter

def label_metrics(rows):
    labels=sorted({r['gold'] for r in rows}|{r['pred'] for r in rows});per={};matrix=Counter((r['gold'],r['pred']) for r in rows)
    for label in labels:
        tp=matrix[label,label];fp=sum(v for (g,p),v in matrix.items() if p==label and g!=label);fn=sum(v for (g,p),v in matrix.items() if g==label and p!=label)
        precision=tp/(tp+fp) if tp+fp else 0;recall=tp/(tp+fn) if tp+fn else 0
        per[label]={'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0,'support':tp+fn}
    return {'n':len(rows),'accuracy':sum(r['gold']==r['pred'] for r in rows)/len(rows) if rows else None,'macro_f1':sum(x['f1'] for x in per.values())/len(per) if per else None,'per_class':per,'labels':labels,'confusion_matrix':[[matrix[g,p] for p in labels] for g in labels]}

def ranking(rows,k=10):
    scored=[]
    for r in rows:
        gold=set(r['relevant']);retrieved=list(dict.fromkeys(r['ranked']))[:k]
        if not gold:continue
        hits=[int(x in gold) for x in retrieved];dcg=sum(h/math.log2(i+2) for i,h in enumerate(hits));ideal=sum(1/math.log2(i+2) for i in range(min(k,len(gold))))
        scored.append({'precision_at_k':sum(hits)/k,'recall_at_k':sum(hits)/len(gold),'ndcg_at_k':dcg/ideal,'mrr':next((1/(i+1) for i,h in enumerate(hits) if h),0)})
    return {'total_queries':len(rows),'scored_queries':len(scored),'k':k,**{key:sum(r[key] for r in scored)/len(scored) if scored else None for key in ['precision_at_k','recall_at_k','ndcg_at_k','mrr']}}

def evaluate(data):
    out={'sentiment':label_metrics(data.get('sentiment',[])),'aspects':{}}
    for name,rows in data.get('aspects',{}).items():out['aspects'][name]=label_metrics(rows)
    tp=fp=fn=0
    for row in data.get('ner',[]):
        gold={tuple(x) for x in row['gold']};pred={tuple(x) for x in row['pred']};tp+=len(gold&pred);fp+=len(pred-gold);fn+=len(gold-pred)
    out['ner']={'tp':tp,'fp':fp,'fn':fn,'exact_span_type_f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}
    for task in ['retrieval','recommendations']:out[task]=ranking(data.get(task,[]),data.get('k',10))
    summaries=data.get('summaries',[])
    out['summaries']={'n':len(summaries)}
    for key in ['faithfulness','coverage','balance','readability']:
        vals=[r[key] for r in summaries if key in r]
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) or not 1<=v<=5 for v in vals):raise ValueError('Summary rubrics must be numeric 1-5')
        out['summaries'][key]={'n':len(vals),'mean':sum(vals)/len(vals) if vals else None}
    return out

if __name__=='__main__':
    from pathlib import Path
    path=Path(sys.argv[1]);output=path.with_name(path.stem+'_metrics.json')
    output.write_text(json.dumps(evaluate(json.loads(path.read_text())),indent=2));print(output)
