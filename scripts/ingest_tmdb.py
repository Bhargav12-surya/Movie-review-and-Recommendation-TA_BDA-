"""Rate-limited TMDB metadata/review ingestion. Never place the bearer token in the UI."""
import argparse
import json
import os
import time
from pathlib import Path
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def ingest(movielens,out,limit=100,pages=3,start=0):
 token=os.getenv('TMDB_BEARER_TOKEN')
 if not token: raise SystemExit('Set TMDB_BEARER_TOKEN from your TMDB API account before ingestion.')
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 links=pd.read_csv(Path(movielens)/'links.csv',dtype={'imdbId':'string'}).dropna(subset=['tmdbId'])
 session=requests.Session();session.headers.update(Authorization='Bearer '+token)
 retry=Retry(total=4,backoff_factor=.8,status_forcelist=[429,500,502,503,504],respect_retry_after_header=True)
 session.mount('https://',HTTPAdapter(max_retries=retry))
 def get(route,params=None):
  response=session.get('https://api.themoviedb.org/3/'+route,params=params,timeout=(10,45));response.raise_for_status();time.sleep(.12);return response.json()
 # Append-only, resumable per movie; downstream ingestion deduplicates by source review ID.
 with (out/'tmdb_movies.jsonl').open('a') as mf,(out/'tmdb_reviews.jsonl').open('a') as rf:
  for row in links.iloc[start:start+limit].itertuples():
   mid=int(row.movieId);tid=int(row.tmdbId)
   try:
    m=get(f'movie/{tid}',{'append_to_response':'keywords'})
    mf.write(json.dumps({'movie_id':mid,'tmdb_id':tid,'imdb_id':m.get('imdb_id'),'title':m.get('title'),
     'runtime':m.get('runtime'),'overview':m.get('overview',''),'release_date':m.get('release_date'),
     'tmdb_genres':[g['name'] for g in m.get('genres',[])],'keywords':[k['name'] for k in m.get('keywords',{}).get('keywords',[])],
     'poster_path':m.get('poster_path'),'backdrop_path':m.get('backdrop_path'),'source':'tmdb'})+'\n');mf.flush()
    for page in range(1,pages+1):
     batch=get(f'movie/{tid}/reviews',{'page':page,'language':'en-US'})
     for r in batch.get('results',[]):
      rf.write(json.dumps({'review_id':'tmdb-'+r['id'],'movie_id':mid,'text':r['content'],'source':'tmdb',
       'created_at':r['created_at'],'source_url':r.get('url'),'rating':r.get('author_details',{}).get('rating')})+'\n')
     rf.flush()
     if page>=batch.get('total_pages',0):break
   except requests.HTTPError as exc:
    status=exc.response.status_code if exc.response is not None else None
    if status in (401,403):raise SystemExit('TMDB rejected the credential; verify access before retrying.')
    print(f'Skipped movie {mid}: HTTP {status}')
 print('Metadata and review JSONL saved. Review coverage is limited to available pages/language.')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--movielens',default='data/raw/ml-latest-small');p.add_argument('--out',default='data/processed');p.add_argument('--limit',type=int,default=100);p.add_argument('--pages',type=int,default=3);p.add_argument('--start',type=int,default=0);a=p.parse_args();ingest(a.movielens,a.out,a.limit,a.pages,a.start)
