"""python import_movielens.py path/to/ml-latest-small [--reviews linked.csv]
Optional linked.csv: movieId,review. No attempt to join IMDb review file indexes.
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def build(folder, reviews=None):
    sums, counts, texts = defaultdict(float), defaultdict(int), defaultdict(list)
    with (folder/'ratings.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            value=float(row['rating']); mid=row['movieId']
            if .5<=value<=5:
                sums[mid]+=value; counts[mid]+=1
    if reviews:
        with reviews.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                text=row['review'].strip()
                if text and text not in texts[row['movieId']] and len(texts[row['movieId']])<20:
                    texts[row['movieId']].append(text[:10000])
    with (folder/'movies.csv').open(encoding='utf-8-sig',newline='') as f:
        return [dict(id='ml:'+r['movieId'],title=r['title'],
                     genres=[g for g in r['genres'].split('|') if g!='(no genres listed)'],
                     rating_count=counts[r['movieId']],mean_rating=sums[r['movieId']]/counts[r['movieId']] if counts[r['movieId']] else 3,
                     reviews=texts[r['movieId']],provenance='MovieLens metadata; optional user-supplied linked reviews') for r in csv.DictReader(f)]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--reviews',type=Path);a=p.parse_args()
    destination=Path(__file__).resolve().parent/'data/movielens.json'
    destination.write_text(json.dumps(build(a.folder,a.reviews),ensure_ascii=False),encoding='utf-8')
    print('Wrote',destination,'\nSet CINESCOPE_CATALOG to this file, then restart app.py.')
