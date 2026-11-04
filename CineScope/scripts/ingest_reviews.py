"""Idempotently ingest linked historical review JSONL. IMDb filename IDs are NOT movie IDs."""
import argparse
import json
from pathlib import Path
from cinescope.storage import Store
from cinescope.reviews import clean_text


def ingest(path,catalog,data_dir):
 movies=json.loads(Path(catalog).read_text());ids={m['movie_id'] for m in movies};store=Store(data_dir,seed_reviews=False)
 inserted=skipped=0
 with Path(path).open() as f:
  for line in f:
   if not line.strip():continue
   r=json.loads(line)
   if r.get('movie_id') not in ids or not r.get('text','').strip():skipped+=1;continue
   result=store.add_review(r['movie_id'],clean_text(r['text']),r.get('source','imported'),r.get('review_id'),r.get('created_at'))
   inserted+=result['inserted']
 print(json.dumps({'inserted':inserted,'skipped_unknown_or_empty':skipped}))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--catalog',default='data/processed/catalog.json');p.add_argument('--data-dir',default='data/real-app');a=p.parse_args();ingest(a.input,a.catalog,a.data_dir)
