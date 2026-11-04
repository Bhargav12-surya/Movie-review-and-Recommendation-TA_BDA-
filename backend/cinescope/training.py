"""Reproducible training routines used by the notebooks. No benchmark numbers are hardcoded."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit,train_test_split
from sklearn.metrics import accuracy_score,precision_recall_fscore_support,roc_auc_score,confusion_matrix
from .reviews import clean_text,authenticity


def metrics(y,pred,prob=None):
    precision,recall,f1,_=precision_recall_fscore_support(y,pred,average='macro',zero_division=0)
    result={'accuracy':float(accuracy_score(y,pred)),'macro_precision':float(precision),'macro_recall':float(recall),'macro_f1':float(f1),
            'confusion_matrix':confusion_matrix(y,pred).tolist(),'n':len(y)}
    if prob is not None and len(np.unique(y))==2:result['roc_auc']=float(roc_auc_score(y,prob))
    return result


def audit_reviews(frame):
    frame=frame.copy();frame['text']=frame.text.fillna('').map(clean_text)
    frame['text_hash']=frame.text.str.casefold().map(lambda t:hashlib.sha256(t.encode()).hexdigest())
    frame['duplicate']=frame.duplicated('text_hash',keep=False)
    frame['screening_risk']=frame.text.map(lambda text:authenticity(text)['risk_index'])
    # Flags are an audit queue, never ground-truth fake labels.
    return frame


def imdb_splits(csv):
    df=audit_reviews(pd.read_csv(csv)).query('text.str.len() > 0',engine='python')
    test=df[df.split=='test'].drop_duplicates('text_hash').copy()
    pool=df[(df.split=='train')&~df.text_hash.isin(test.text_hash)].drop_duplicates('text_hash').copy()
    if len(pool)<100 or len(test)<50:raise ValueError('Use the real prepared IMDb corpus, not demo reviews.')
    if 'imdb_id' in pool and pool.imdb_id.notna().all():
        train_idx,val_idx=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42).split(pool,groups=pool.imdb_id))
        train,val=pool.iloc[train_idx].copy(),pool.iloc[val_idx].copy()
    else:
        train,val=train_test_split(pool,test_size=.2,stratify=pool.label,random_state=42)
    for partition in (train,val,test):
        if partition.label.nunique()!=2:raise ValueError('A partition is missing a sentiment class.')
    return train,val,test


def train_tfidf(csv,model_dir='models',output='artifacts'):
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    import joblib,sklearn
    train,val,test=imdb_splits(csv);trials=[]
    for c in (.5,1.,2.):
        pipeline=Pipeline([('tfidf',TfidfVectorizer(ngram_range=(1,2),min_df=2,max_df=.98,max_features=100000,sublinear_tf=True)),
                           ('classifier',LogisticRegression(C=c,max_iter=600,random_state=42))])
        pipeline.fit(train.text,train.label)
        trial=metrics(val.label,pipeline.predict(val.text),pipeline.predict_proba(val.text)[:,1]);trials.append((trial['macro_f1'],c,pipeline,trial))
    _,selected_c,best,validation=max(trials,key=lambda t:t[0])
    # Test is touched once after model selection. Keep the selected train-only fit for comparison.
    test_metrics=metrics(test.label,best.predict(test.text),best.predict_proba(test.text)[:,1])
    Path(model_dir).mkdir(parents=True,exist_ok=True);Path(output).mkdir(parents=True,exist_ok=True)
    joblib.dump(best,Path(model_dir)/'sentiment_tfidf.joblib')
    report={'selected_C':selected_c,'validation':validation,'test':test_metrics,
            'train_rows':len(train),'seed':42,'sklearn_version':sklearn.__version__,
            'screened_high_risk_train':int((train.screening_risk>=70).sum()),
            'probability_note':'Logistic probabilities; evaluate calibration before treating them as confidence.'}
    (Path(output)/'sentiment_tfidf_metrics.json').write_text(json.dumps(report,indent=2))
    train[['review_id','screening_risk','duplicate']].to_csv(Path(output)/'training_review_audit.csv',index=False)
    return best,report


def train_transformer(csv,model_dir='models/sentiment_transformer',output='artifacts/transformer',epochs=2,batch_size=8,max_length=384):
    from datasets import Dataset
    from transformers import AutoTokenizer,AutoModelForSequenceClassification,DataCollatorWithPadding,TrainingArguments,Trainer,set_seed
    set_seed(42);train,val,test=imdb_splits(csv)
    tokenizer=AutoTokenizer.from_pretrained('distilbert/distilbert-base-uncased')
    def dataset(frame):
        ds=Dataset.from_dict({'text':frame.text.tolist(),'labels':frame.label.astype(int).tolist()})
        return ds.map(lambda b:tokenizer(b['text'],truncation=True,max_length=max_length),batched=True,remove_columns=['text'])
    train_ds,val_ds,test_ds=map(dataset,(train,val,test))
    model=AutoModelForSequenceClassification.from_pretrained('distilbert/distilbert-base-uncased',num_labels=2,id2label={0:'negative',1:'positive'},label2id={'negative':0,'positive':1})
    def compute(pred):return {k:v for k,v in metrics(pred.label_ids,np.argmax(pred.predictions,axis=1)).items() if isinstance(v,(int,float))}
    args=TrainingArguments(output_dir=output,learning_rate=2e-5,num_train_epochs=epochs,per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,eval_strategy='epoch',save_strategy='epoch',load_best_model_at_end=True,
        metric_for_best_model='macro_f1',save_total_limit=2,weight_decay=.01,seed=42,report_to='none',dataloader_num_workers=0)
    trainer=Trainer(model=model,args=args,train_dataset=train_ds,eval_dataset=val_ds,processing_class=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),compute_metrics=compute)
    trainer.train();result=trainer.predict(test_ds)
    from scipy.special import softmax
    report=metrics(result.label_ids,result.predictions.argmax(1),softmax(result.predictions,axis=1)[:,1])
    report['evaluation_note']='Test uses first 384 tokens. Runtime scores all chunks; separately validate this aggregation on long reviews.'
    trainer.save_model(model_dir);tokenizer.save_pretrained(model_dir)
    Path(output).mkdir(parents=True,exist_ok=True);(Path(output)/'test_metrics.json').write_text(json.dumps(report,indent=2))
    return trainer,report


def train_absa(csv,model_dir='models/aspect_transformer',output='artifacts/absa',epochs=3):
    """Needs human-annotated domain data: aspect,text,label,review_id,movie_id.
    Labels: negative=0, neutral=1, positive=2. Split by movie to avoid leakage.
    """
    from datasets import Dataset
    from transformers import AutoTokenizer,AutoModelForSequenceClassification,DataCollatorWithPadding,TrainingArguments,Trainer,set_seed
    set_seed(42);df=pd.read_csv(csv).dropna(subset=['aspect','text','label','movie_id']).drop_duplicates(['aspect','text'])
    if len(df)<100 or df.movie_id.nunique()<6:raise ValueError('Collect at least 100 aspect annotations across 6+ movies; substantially more is recommended.')
    if set(df.label.astype(int))!={0,1,2}:raise ValueError('ABSA requires negative=0, neutral=1, positive=2 labels.')
    rest_i,test_i=next(GroupShuffleSplit(test_size=.2,random_state=42).split(df,groups=df.movie_id));rest,test=df.iloc[rest_i],df.iloc[test_i]
    train_i,val_i=next(GroupShuffleSplit(test_size=.25,random_state=43).split(rest,groups=rest.movie_id));train,val=rest.iloc[train_i],rest.iloc[val_i]
    for part in (train,val,test):
        if part.label.nunique()!=3:raise ValueError('Annotate more data: every partition must contain all 3 classes.')
    tokenizer=AutoTokenizer.from_pretrained('distilbert/distilbert-base-uncased')
    def dataset(frame):
        ds=Dataset.from_dict({'aspect':frame.aspect.tolist(),'text':frame.text.tolist(),'labels':frame.label.astype(int).tolist()})
        return ds.map(lambda b:tokenizer(b['aspect'],b['text'],truncation=True,max_length=256),batched=True,remove_columns=['aspect','text'])
    model=AutoModelForSequenceClassification.from_pretrained('distilbert/distilbert-base-uncased',num_labels=3,id2label={0:'negative',1:'neutral',2:'positive'})
    def compute(p):return {'macro_f1':metrics(p.label_ids,p.predictions.argmax(1))['macro_f1']}
    args=TrainingArguments(output_dir=output,learning_rate=2e-5,num_train_epochs=epochs,per_device_train_batch_size=8,per_device_eval_batch_size=8,
        eval_strategy='epoch',save_strategy='epoch',load_best_model_at_end=True,metric_for_best_model='macro_f1',save_total_limit=2,seed=42,report_to='none')
    trainer=Trainer(model=model,args=args,train_dataset=dataset(train),eval_dataset=dataset(val),processing_class=tokenizer,
                    data_collator=DataCollatorWithPadding(tokenizer),compute_metrics=compute)
    trainer.train();pred=trainer.predict(dataset(test));report=metrics(pred.label_ids,pred.predictions.argmax(1))
    trainer.save_model(model_dir);tokenizer.save_pretrained(model_dir);Path(output).mkdir(parents=True,exist_ok=True)
    (Path(output)/'test_metrics.json').write_text(json.dumps(report,indent=2));return trainer,report
