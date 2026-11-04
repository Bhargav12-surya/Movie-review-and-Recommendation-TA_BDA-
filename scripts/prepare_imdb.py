"""Keep official IMDb train/test partitions and map review URLs to IMDb title IDs."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import pandas as pd
from cinescope.reviews import clean_text


def prepare(path,out):
 path=Path(path);out=Path(out);out.mkdir(parents=True,exist_ok=True);rows=[]
 for split in ('train','test'):
  for label,name in ((0,'neg'),(1,'pos')):
   url_file=path/split/('urls_'+name+'.txt')
   urls=url_file.read_text().splitlines() if url_file.exists() else []
   for file in sorted((path/split/name).glob('*.txt')):
    idx=int(file.stem.split('_')[0]);url=urls[idx] if idx<len(urls) else ''
    match=re.search(r'(tt\d+)',url);text=clean_text(file.read_text(encoding='utf-8'))
    digest=hashlib.sha256(text.casefold().encode()).hexdigest()
    rows.append({'review_id':f'imdb-{split}-{name}-{file.stem}','text':text,'label':label,'split':split,
                 'imdb_id':match.group(1) if match else None,'source_url':url,'text_hash':digest})
 if not rows: raise FileNotFoundError('No reviews found. Pass the extracted aclImdb directory.')
 df=pd.DataFrame(rows)
 # Preserve the test benchmark, drop exact training duplicates also present in test.
 test_hash=set(df.loc[df.split.eq('test'),'text_hash']);leak=df.split.eq('train')&df.text_hash.isin(test_hash)
 removed=int(leak.sum());df=df.loc[~leak].drop_duplicates(['split','text_hash'])
 df.to_csv(out/'imdb_reviews.csv',index=False)
 with (out/'imdb_reviews.jsonl').open('w') as f:
  for r in df.to_dict('records'):f.write(json.dumps(r)+'\n')
 (out/'imdb_preparation.json').write_text(json.dumps({'rows':len(df),'train_test_duplicates_removed':removed,'split_counts':df.split.value_counts().to_dict()},indent=2))
 print(df.groupby(['split','label']).size())
 return df

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',default='data/raw/aclImdb');p.add_argument('--out',default='data/processed');a=p.parse_args();prepare(a.input,a.out)
