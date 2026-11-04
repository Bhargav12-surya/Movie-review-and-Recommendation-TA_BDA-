"""Download official archives after you review the dataset terms in docs/DATASETS.md."""
import argparse
import hashlib
import json
import tarfile
import zipfile
from datetime import datetime,timezone
from pathlib import Path
import requests

SOURCES={
 'movielens-small':('https://files.grouplens.org/datasets/movielens/ml-latest-small.zip','ml-latest-small.zip'),
 'movielens-32m':('https://files.grouplens.org/datasets/movielens/ml-32m.zip','ml-32m.zip'),
 'imdb-reviews':('https://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz','aclImdb_v1.tar.gz'),
 'imdb-basics':('https://datasets.imdbws.com/title.basics.tsv.gz','title.basics.tsv.gz'),
 'imdb-ratings':('https://datasets.imdbws.com/title.ratings.tsv.gz','title.ratings.tsv.gz')}

def download(name,out):
 url,filename=SOURCES[name];out=Path(out);out.mkdir(parents=True,exist_ok=True);target=out/filename
 tmp=target.with_suffix(target.suffix+'.part')
 with requests.get(url,stream=True,timeout=(15,180)) as response:
  response.raise_for_status()
  with tmp.open('wb') as f:
   for chunk in response.iter_content(1024*1024): f.write(chunk)
 tmp.replace(target)
 digest=hashlib.sha256()
 with target.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): digest.update(chunk)
 (out/(filename+'.provenance.json')).write_text(json.dumps({'source':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'sha256':digest.hexdigest(),'bytes':target.stat().st_size},indent=2))
 def safe(name):
  if not (out/name).resolve().is_relative_to(out.resolve()): raise ValueError('Unsafe archive path')
 if filename.endswith('.zip'):
  with zipfile.ZipFile(target) as z:
   for info in z.infolist():
    safe(info.filename)
    if (info.external_attr >> 16)&0o170000==0o120000: raise ValueError('Archive symlink rejected')
   z.extractall(out)
 elif filename.endswith('.tar.gz'):
  with tarfile.open(target) as t:
   for member in t.getmembers():
    safe(member.name)
    if member.issym() or member.islnk() or not (member.isfile() or member.isdir()): raise ValueError('Unsupported archive entry')
   t.extractall(out)
 print(target)
 return target

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('dataset',choices=SOURCES);parser.add_argument('--out',default='data/raw');args=parser.parse_args();download(args.dataset,args.out)
