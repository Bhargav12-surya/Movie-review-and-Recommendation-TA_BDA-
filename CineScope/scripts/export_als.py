"""Convert Spark itemFactors Parquet to the runtime NPZ format. No user IDs exported."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('item_factors');p.add_argument('--out',default='models/als_factors.npz');p.add_argument('--reg-param',type=float,default=.1);a=p.parse_args()
 frame=pd.read_parquet(a.item_factors).sort_values('id');Path(a.out).parent.mkdir(parents=True,exist_ok=True)
 np.savez_compressed(a.out,movie_ids=frame.id.to_numpy(dtype=np.int64),factors=np.stack(frame.features.to_numpy()).astype(np.float32),reg_param=np.array(a.reg_param));print(a.out)
