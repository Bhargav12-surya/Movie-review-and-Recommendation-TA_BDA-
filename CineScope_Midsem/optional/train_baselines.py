"""Controlled BoW vs TF-IDF. Run after prepare_imdb.py; no test-driven selection."""
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import clean, tokens
ROOT=Path(__file__).resolve().parents[1]


def rows(path=ROOT/'data/reviews.csv'):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def run():
    from sklearn.feature_extraction.text import CountVectorizer,TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score,f1_score,confusion_matrix
    from sklearn.pipeline import Pipeline
    data=rows();groups={s:[r for r in data if r['split']==s] for s in ('train','validation','test')}
    if any(not r for r in groups.values()):raise ValueError('Need nonempty train/validation/test splits.')
    reports={}; winner=None
    for name,vectorizer in [('bow',CountVectorizer),('tfidf',TfidfVectorizer)]:
        candidates=[]
        for c in (.5,2.):
            model=Pipeline([('vector',vectorizer(preprocessor=clean,tokenizer=tokens,token_pattern=None,lowercase=False,ngram_range=(1,2),max_features=30000,min_df=2)),('classifier',LogisticRegression(C=c,max_iter=1000,random_state=42))])
            model.fit([r['text'] for r in groups['train']],[int(r['label']) for r in groups['train']])
            pred=model.predict([r['text'] for r in groups['validation']])
            candidates.append((f1_score([int(r['label']) for r in groups['validation']],pred,average='macro'),c,model))
        validation,c,model=max(candidates,key=lambda x:x[0])
        test=groups['test']; gold=[int(r['label']) for r in test]; pred=model.predict([r['text'] for r in test])
        reports[name]={'C':c,'validation_macro_f1':validation,'test_accuracy':accuracy_score(gold,pred),'test_macro_f1':f1_score(gold,pred,average='macro'),'confusion_matrix_labels':[0,1],'confusion_matrix':confusion_matrix(gold,pred,labels=[0,1]).tolist(),'test_n':len(test)}
        (ROOT/'data'/f'{name}_predictions.json').write_text(json.dumps([dict(id=r['id'],gold=y,pred=int(p)) for r,y,p in zip(test,gold,pred)]))
        if name=='tfidf':winner=model
    v=winner.named_steps['vector'];lr=winner.named_steps['classifier']
    artifact={'vocabulary':v.vocabulary_,'idf':v.idf_.tolist(),'weights':lr.coef_[0].tolist(),'intercept':float(lr.intercept_[0]),'classes':lr.classes_.tolist(),'model':'tfidf-logistic-regression','split':'data/split_manifest.json'}
    artifact['vocabulary']={k:int(v) for k,v in artifact['vocabulary'].items()}
    (ROOT/'data/sentiment.json').write_text(json.dumps(artifact))
    (ROOT/'data/baseline_metrics.json').write_text(json.dumps(reports,indent=2)); print(json.dumps(reports,indent=2))

if __name__=='__main__':run()
