"""Apply the same runtime analyzer to historical review JSONL. Stream input/output."""
import argparse,json
from pathlib import Path
from cinescope.reviews import ReviewAnalyzer

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--out',default='artifacts/analyzed_reviews.jsonl');a=p.parse_args()
 model=ReviewAnalyzer();Path(a.out).parent.mkdir(parents=True,exist_ok=True)
 with open(a.input) as src,open(a.out,'w') as dst:
  for line in src:
   if line.strip():
    r=json.loads(line);result=model.analyze(r['text']);dst.write(json.dumps({**r,**result})+'\n')
 print(a.out)
