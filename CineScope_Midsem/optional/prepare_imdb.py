"""Convert extracted aclImdb into a fixed shared split: python optional/prepare_imdb.py PATH."""
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import clean
ROOT=Path(__file__).resolve().parents[1]


def prepare(source, destination):
    buckets={}; conflicts=set(); total=0
    # Test seen first: retain official test membership when exact duplicates overlap.
    for split in ('test','train'):
        for label,name in [(0,'neg'),(1,'pos')]:
            urlfile=source/split/('urls_'+name+'.txt')
            urls=urlfile.read_text().splitlines() if urlfile.exists() else []
            for file in sorted((source/split/name).glob('*.txt')):
                total+=1; text=clean(file.read_text(encoding='utf-8'))
                fingerprint=hashlib.sha256(text.encode()).hexdigest()
                idx=int(file.name.split('_')[0]); match=re.search(r'tt\d+',urls[idx]) if idx<len(urls) else None
                group=match.group() if match else fingerprint
                fold='test' if split=='test' else ('validation' if int(hashlib.sha256(group.encode()).hexdigest()[:8],16)%5==0 else 'train')
                if fingerprint in buckets and buckets[fingerprint]['label']!=label: conflicts.add(fingerprint)
                buckets.setdefault(fingerprint,dict(id=fingerprint,text=text,label=label,split=fold,group=group))
    rows=[v for k,v in buckets.items() if k not in conflicts]
    if not rows: raise ValueError('No labeled files. Expected PATH/train/pos/*.txt etc.')
    with destination.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['id','text','label','split','group']);w.writeheader();w.writerows(rows)
    report={'raw':total,'kept':len(rows),'conflicting_texts_removed':len(conflicts),
            'counts':{s:sum(r['split']==s for r in rows) for s in ('train','validation','test')},
            'policy':'Official test, exact dedup, training movie-group hash validation when URL metadata exists. Test not grouped against train; inspect movie overlap separately.'}
    (destination.parent/'split_manifest.json').write_text(json.dumps(report,indent=2))
    print(report)

if __name__=='__main__':prepare(Path(sys.argv[1]),ROOT/'data/reviews.csv')
