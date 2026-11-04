"""Human annotations only: review_id,text,aspect,label,split. Six small classifiers.
Labels: positive,negative,neutral,mixed,not_mentioned. No artificial gold labels.
This research script saves reports/models; the small frontend continues to use rules.
"""
import csv
import json
from pathlib import Path
from train_baselines import ROOT,clean,tokens

def run(path):
    import joblib
    from sklearn.pipeline import make_pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report
    from engine import ASPECTS
    with open(path,encoding='utf-8',newline='') as f:data=list(csv.DictReader(f))
    labels=['positive','negative','neutral','mixed','not_mentioned'];seen={};result={}
    for r in data:
        if r['aspect'] not in ASPECTS or r['label'] not in labels or r['split'] not in ('train','validation','test'):raise ValueError('Invalid annotation value')
        for key in (r['review_id'],clean(r['text'])):
            if key in seen and seen[key]!=r['split']:raise ValueError('Review leaks across splits')
            seen[key]=r['split']
    for aspect in ASPECTS:
        train=[r for r in data if r['aspect']==aspect and r['split']=='train']
        test=[r for r in data if r['aspect']==aspect and r['split']=='test']
        if len({r['label'] for r in train})<2 or not test:
            result[aspect]={'status':'insufficient annotations'};continue
        model=make_pipeline(TfidfVectorizer(preprocessor=clean,tokenizer=tokens,token_pattern=None,ngram_range=(1,2)),LogisticRegression(max_iter=1000,class_weight='balanced',random_state=42))
        model.fit([r['text'] for r in train],[r['label'] for r in train]);pred=model.predict([r['text'] for r in test])
        result[aspect]={'train_n':len(train),'test_n':len(test),'metrics':classification_report([r['label'] for r in test],pred,labels=labels,output_dict=True,zero_division=0)}
        joblib.dump(model,ROOT/'data'/f'aspect_{aspect.lower()}.joblib')
    (ROOT/'data/aspect_metrics.json').write_text(json.dumps(result,indent=2));print(result)
if __name__=='__main__':
    import sys
    run(sys.argv[1])
