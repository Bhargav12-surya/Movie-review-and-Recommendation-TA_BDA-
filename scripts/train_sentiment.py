"""Train the real IMDb CPU baseline with the same routine used by notebook 02."""
import argparse,json
from cinescope.training import train_tfidf
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',default='data/processed/imdb_reviews.csv');p.add_argument('--models',default='models');p.add_argument('--out',default='artifacts');a=p.parse_args()
 _,report=train_tfidf(a.input,a.models,a.out);print(json.dumps(report,indent=2))
