"""Optional GPU experiment. Same review IDs as the baseline. Not loaded by the demo."""
import argparse
import json
import random
from train_baselines import rows, ROOT

def run(epochs):
    import numpy as np
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    from sklearn.metrics import f1_score,accuracy_score,confusion_matrix
    from torch.utils.data import DataLoader
    random.seed(42);np.random.seed(42);torch.manual_seed(42)
    device='cuda' if torch.cuda.is_available() else 'cpu'
    data=rows();splits={s:[r for r in data if r['split']==s] for s in ('train','validation','test')}
    tokenizer=AutoTokenizer.from_pretrained('distilbert/distilbert-base-uncased')
    model=AutoModelForSequenceClassification.from_pretrained('distilbert/distilbert-base-uncased',num_labels=2).to(device)
    def collate(batch):
        encoded=tokenizer([r['text'] for r in batch],padding=True,truncation=True,max_length=256,return_tensors='pt')
        encoded['labels']=torch.tensor([int(r['label']) for r in batch]);return {k:v.to(device) for k,v in encoded.items()}
    loaders={s:DataLoader(r,batch_size=8,shuffle=s=='train',collate_fn=collate) for s,r in splits.items()}
    optimizer=torch.optim.AdamW(model.parameters(),lr=2e-5)
    def evaluate(loader):
        model.eval();gold=[];pred=[]
        with torch.no_grad():
            for batch in loader:
                gold.extend(batch['labels'].cpu().tolist());pred.extend(model(**batch).logits.argmax(-1).cpu().tolist())
        return {'accuracy':accuracy_score(gold,pred),'macro_f1':f1_score(gold,pred,average='macro'),'confusion_matrix':confusion_matrix(gold,pred,labels=[0,1]).tolist()},gold,pred
    best=-1;destination=ROOT/'data/distilbert'
    for epoch in range(epochs):
        model.train()
        for batch in loaders['train']:
            optimizer.zero_grad();loss=model(**batch).loss;loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
        report,_,_=evaluate(loaders['validation']);print(epoch+1,report)
        if report['macro_f1']>best:
            best=report['macro_f1'];model.save_pretrained(destination);tokenizer.save_pretrained(destination)
    model=AutoModelForSequenceClassification.from_pretrained(destination).to(device)
    report,gold,pred=evaluate(loaders['test']);report.update(validation_macro_f1=best,test_n=len(gold),max_tokens=256,device=device,epochs=epochs)
    (ROOT/'data/distilbert_metrics.json').write_text(json.dumps(report,indent=2))
    (ROOT/'data/distilbert_predictions.json').write_text(json.dumps([dict(id=r['id'],gold=y,pred=p) for r,y,p in zip(splits['test'],gold,pred)]));print(report)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--epochs',type=int,default=2);a=p.parse_args()
    if a.epochs<1:p.error('epochs must be positive')
    run(a.epochs)
