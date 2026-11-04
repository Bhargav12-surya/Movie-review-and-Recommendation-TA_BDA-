"""Run: python app.py. Local teaching server; no pip install required."""
import json
import math
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from engine import analyze, recommend

ROOT = Path(__file__).resolve().parent
CATALOG_PATH = Path(os.environ.get('CINESCOPE_CATALOG', str(ROOT/'data/catalog.json')))
CATALOG = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
IDS = {m['id'] for m in CATALOG}
MODEL_PATH = ROOT/'data/sentiment.json'
MODEL = json.loads(MODEL_PATH.read_text()) if MODEL_PATH.exists() else None


def analyze_live(text):
    result = analyze(text)
    if MODEL and text.strip():
        from engine import clean, tokens
        from collections import Counter
        ts = tokens(clean(text))
        features = Counter(ts + [' '.join(ts[i:i+2]) for i in range(len(ts)-1)])
        pairs = [(i, features[t]*MODEL['idf'][i]) for t,i in MODEL['vocabulary'].items() if features[t]]
        norm = math.sqrt(sum(v*v for _,v in pairs)) or 1
        z = MODEL['intercept'] + sum(MODEL['weights'][i]*v/norm for i,v in pairs)
        p = 1/(1+math.exp(-max(-700,min(700,z))))
        result.update(score=round(100*p,1), label='positive' if p>=.5 else 'negative',
                      method='TF-IDF + Logistic Regression (overall only)')
    return result


class Handler(BaseHTTPRequestHandler):
    def reply(self, data, status=200):
        body = json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/catalog':
            return self.reply({'movies': CATALOG, 'dataset': 'MovieLens' if CATALOG and CATALOG[0]['id'].startswith('ml:') else 'authored demo',
                               'model': 'trained TF-IDF' if MODEL else 'rule-based baseline'})
        files = {'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
        if path not in files:
            return self.reply({'error':'Not found'},404)
        content = (ROOT/'web'/files[path]).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type',{'/':'text/html','/app.js':'text/javascript','/style.css':'text/css'}[path]+'; charset=utf-8')
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length',0))
            if not 0 < length <= 200000:
                raise ValueError('Request must be 1-200000 bytes.')
            data = json.loads(self.rfile.read(length))
            if self.path == '/api/analyze':
                value = data.get('text','')
                if not isinstance(value,str) or len(value)>10000:
                    raise ValueError('Review must be text with at most 10000 characters.')
                return self.reply(analyze_live(value))
            if self.path == '/api/recommend':
                raw = data.get('history',[])
                if not isinstance(raw,list) or len(raw)>200:
                    raise ValueError('History must contain at most 200 films.')
                history = {}
                for h in raw:
                    rating = float(h['rating'])
                    review = h.get('review','')
                    if not math.isfinite(rating) or not .5<=rating<=5 or rating*2!=int(rating*2):
                        raise ValueError('Rating must be 0.5-5 in half-star steps.')
                    if not isinstance(review,str) or len(review)>10000:
                        raise ValueError('Invalid review.')
                    if h['id'] in IDS: history[h['id']] = dict(id=h['id'],rating=rating,review=review)
                return self.reply(recommend(CATALOG,list(history.values())))
            return self.reply({'error':'Not found'},404)
        except (ValueError, KeyError, TypeError, AttributeError):
            return self.reply({'error':'Invalid input. Check review length and rating.'},400)

if __name__ == '__main__':
    port = int(os.environ.get('PORT','8000'))
    print(f'CineScope: http://127.0.0.1:{port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
