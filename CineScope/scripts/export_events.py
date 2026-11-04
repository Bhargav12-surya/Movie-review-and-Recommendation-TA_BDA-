"""Poll durable SQLite reviews and atomically publish JSON files for Spark streaming.
Run repeatedly or with --watch. State advances only after an event file is committed.
This decouples synchronous review inference from distributed analytics.
"""
import argparse,json,time,sqlite3
from pathlib import Path


def export(db,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);state=out/'.last_rowid';last=int(state.read_text()) if state.exists() else 0
 with sqlite3.connect(db) as conn:
  conn.row_factory=sqlite3.Row;rows=[dict(r) for r in conn.execute('SELECT rowid AS sequence,* FROM reviews WHERE rowid>? ORDER BY rowid LIMIT 1000',(last,))]
 if not rows:return 0
 end=rows[-1]['sequence'];target=out/f'events-{last+1:012}-{end:012}.json';tmp=out/f'.{target.name}.tmp'
 tmp.write_text('\n'.join(json.dumps(r) for r in rows)+'\n');tmp.replace(target)
 marker=out/'.last_rowid.tmp';marker.write_text(str(end));marker.replace(state)
 return len(rows)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',default='data/demo-app/cinescope.sqlite3');p.add_argument('--out',default='data/events');p.add_argument('--watch',action='store_true');a=p.parse_args()
 while True:
  count=export(a.db,a.out)
  if count:print(f'Published {count} events',flush=True)
  if not a.watch:break
  time.sleep(2)
