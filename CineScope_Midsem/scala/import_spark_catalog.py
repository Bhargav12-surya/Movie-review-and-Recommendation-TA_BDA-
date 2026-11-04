"""Convert Spark's bounded JSON-lines export to the app's JSON array."""
import json
import sys
from pathlib import Path
rows=[]
for file in Path(sys.argv[1]).glob('part-*.json'):
    for line in file.read_text(encoding='utf-8').splitlines():
        r=json.loads(line);r['reviews']=[];r['provenance']='MovieLens / Scala Spark batch'
        r['genres']=[g for g in r['genres'] if g!='(no genres listed)'];rows.append(r)
if not rows:raise ValueError('No part-*.json files found')
destination=Path(__file__).resolve().parents[1]/'data/movielens.json'
destination.write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8');print(destination)
