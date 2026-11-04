"""Join MovieLens to optional TMDB/IMDb metadata using stable IDs, not fuzzy titles."""
import argparse
import json
import re
from pathlib import Path
import pandas as pd
from cinescope.reviews import TAXONOMY,has_phrase


def build(movielens,tmdb=None,out='data/processed/catalog.json',imdb_basics=None):
 base=Path(movielens);movies=pd.read_csv(base/'movies.csv');links=pd.read_csv(base/'links.csv',dtype={'imdbId':'string'})
 frame=movies.merge(links,on='movieId',how='left',validate='one_to_one')
 extra={}
 if tmdb and Path(tmdb).exists():
  for line in Path(tmdb).read_text().splitlines():
   if line.strip():r=json.loads(line);extra[int(r['movie_id'])]=r
 imdb={}
 if imdb_basics:
  target={'tt'+str(x).zfill(7) for x in frame.imdbId.dropna()}
  for chunk in pd.read_csv(imdb_basics,sep='\t',dtype='string',na_values='\\N',chunksize=100000):
   for r in chunk[chunk.tconst.isin(target)].itertuples():imdb[r.tconst]=r
 records=[]
 for r in frame.itertuples():
  ex=extra.get(int(r.movieId),{});iid='tt'+str(r.imdbId).zfill(7) if pd.notna(r.imdbId) else None;ib=imdb.get(iid)
  year=re.search(r'\((\d{4})\)\s*$',r.title)
  keywords=ex.get('keywords',[])
  doc=ex.get('overview','')+' '+' '.join(keywords)
  themes=[label for label,aliases in TAXONOMY['themes'].items() if any(has_phrase(doc,a) for a in aliases)]
  genres=[g for g in str(r.genres).split('|') if g!='(no genres listed)']
  genres=['Sci-Fi' if g=='Science Fiction' else g for g in genres]
  runtime=ex.get('runtime') or (int(ib.runtimeMinutes) if ib is not None and pd.notna(ib.runtimeMinutes) else None)
  records.append({'movie_id':int(r.movieId),'title':ex.get('title') or re.sub(r'\s*\(\d{4}\)\s*$','',r.title),
   'year':int(year.group(1)) if year else None,'runtime':runtime,'genres':genres,'themes':themes,
   'overview':ex.get('overview',''),'imdb_id':iid,'tmdb_id':int(r.tmdbId) if pd.notna(r.tmdbId) else None,
   'poster':'https://image.tmdb.org/t/p/w500'+ex['poster_path'] if ex.get('poster_path') else '',
   'backdrop':'https://image.tmdb.org/t/p/w1280'+ex['backdrop_path'] if ex.get('backdrop_path') else '',
   'source':'movielens+tmdb' if ex else 'movielens','fictional':False})
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(records,indent=2));print(f'{len(records)} movies → {out}');return records

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--movielens',default='data/raw/ml-latest-small');p.add_argument('--tmdb',default='data/processed/tmdb_movies.jsonl');p.add_argument('--imdb-basics');p.add_argument('--out',default='data/processed/catalog.json');a=p.parse_args();build(a.movielens,a.tmdb,a.out,a.imdb_basics)
