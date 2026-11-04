"""Train CBOW and Skip-gram on the shared training reviews; optional local GloVe txt."""
import argparse
import json
from train_baselines import rows, ROOT, tokens, clean

def run(glove=None):
    from gensim.models import Word2Vec, KeyedVectors
    sentences=[tokens(clean(r['text'])) for r in rows() if r['split']=='train']
    report={};queries=['story','acting','excellent','boring','music']
    for name,sg in [('cbow',0),('skipgram',1)]:
        m=Word2Vec(sentences=sentences,vector_size=100,window=5,min_count=5,sg=sg,workers=1,seed=42,epochs=5)
        m.wv.save(str(ROOT/'data'/f'{name}.kv'))
        report[name]={q:m.wv.most_similar(q,topn=5) if q in m.wv else [] for q in queries}
    if glove:
        g=KeyedVectors.load_word2vec_format(glove,binary=False,no_header=True)
        report['glove']={q:g.most_similar(q,topn=5) if q in g else [] for q in queries}
    (ROOT/'data/word_vectors.json').write_text(json.dumps(report,indent=2));print(report)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--glove');a=p.parse_args();run(a.glove)
