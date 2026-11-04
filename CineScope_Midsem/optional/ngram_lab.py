"""A real count-based language model, separate from classifier n-gram features."""
import json
import math
from collections import Counter
from train_baselines import rows, ROOT, tokens, clean

class NGram:
    def __init__(self,n=2,alpha=1):self.n=n;self.alpha=alpha
    def fit(self,texts):
        sentences=[tokens(clean(t)) for t in texts]
        count=Counter(t for s in sentences for t in s)
        self.vocab={t for t,c in count.items() if c>=2}|{'<unk>','</s>'}
        self.count,self.context=Counter(),Counter()
        for s in sentences:
            seq=['<s>']*(self.n-1)+[t if t in self.vocab else '<unk>' for t in s]+['</s>']
            for i in range(self.n-1,len(seq)):
                context=tuple(seq[i-self.n+1:i]);self.count[context+(seq[i],)]+=1;self.context[context]+=1
        return self
    def probability(self,context,word):
        context=tuple(t if t in self.vocab or t=='<s>' else '<unk>' for t in context)
        word=word if word in self.vocab else '<unk>'
        return (self.count[context+(word,)]+self.alpha)/(self.context[context]+self.alpha*len(self.vocab))
    def perplexity(self,texts):
        loss=0;n=0
        for text in texts:
            seq=['<s>']*(self.n-1)+tokens(clean(text))+['</s>']
            for i in range(self.n-1,len(seq)):
                loss-=math.log(self.probability(seq[i-self.n+1:i],seq[i]));n+=1
        return math.exp(loss/n) if n else None
    def next_words(self,text,k=5):
        context=(['<s>']*(self.n-1)+tokens(clean(text)))[-(self.n-1):]
        return sorted(((w,self.probability(context,w)) for w in self.vocab),key=lambda x:(-x[1],x[0]))[:k]

if __name__=='__main__':
    data=rows();train=[r['text'] for r in data if r['split']=='train'];test=[r['text'] for r in data if r['split']=='test']
    output={}
    for n in (2,3):
        m=NGram(n).fit(train);output[str(n)]={'perplexity':m.perplexity(test),'after_the_movie':m.next_words('the movie'),'vocab':len(m.vocab),'alpha':m.alpha}
    (ROOT/'data/ngram_metrics.json').write_text(json.dumps(output,indent=2));print(output)
