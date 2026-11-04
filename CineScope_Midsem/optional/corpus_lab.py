"""Real training corpus PMI and LDA. Run after IMDb preparation; no synthetic metrics."""
import json
import math
from collections import Counter
from train_baselines import ROOT,rows,clean,tokens

def run():
    from sklearn.feature_extraction.text import CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    texts=[r['text'] for r in rows() if r['split']=='train']
    bigrams=Counter();left=Counter();right=Counter()
    for text in texts:
        ts=tokens(clean(text))
        for a,b in zip(ts,ts[1:]):bigrams[a,b]+=1;left[a]+=1;right[b]+=1
    total=sum(bigrams.values())
    phrases=sorted([dict(phrase=a+' '+b,count=c,pmi=math.log2(c*total/(left[a]*right[b]))) for (a,b),c in bigrams.items() if c>=10],key=lambda r:-r['pmi'])[:50]
    vector=CountVectorizer(max_features=10000,min_df=5,max_df=.9,stop_words='english')
    matrix=vector.fit_transform(texts);lda=LatentDirichletAllocation(n_components=6,max_iter=10,random_state=42).fit(matrix)
    names=vector.get_feature_names_out();topics=[[names[i] for i in topic.argsort()[-10:][::-1]] for topic in lda.components_]
    out={'pmi_min_count':10,'phrases':phrases,'topics_unlabeled':topics,'train_reviews':len(texts)}
    (ROOT/'data/corpus_lab.json').write_text(json.dumps(out,indent=2));print(out)
if __name__=='__main__':run()
