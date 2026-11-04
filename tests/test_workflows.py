import json
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient
from cinescope.api import create_app
from cinescope.reviews import ROOT,ReviewAnalyzer,authenticity
from cinescope.recommender import Recommender
from cinescope.storage import Store
from cinescope.evaluation import ranking_metrics

@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(data_dir=tmp_path/'db',model_dir=tmp_path/'models',sentiment_mode='lexicon'))

@pytest.fixture
def analyzer(tmp_path):
    return ReviewAnalyzer(model_dir=tmp_path,mode='lexicon')

def test_clause_sentiment_and_missing_evidence(analyzer):
    r=analyzer.analyze('The acting is excellent, but the pacing is terrible.')
    assert r['aspects']['Acting']['score']>70
    assert r['aspects']['Pacing']['score']<30
    assert r['aspects']['Music']['score'] is None
    assert r['sentiment']['label']=='mixed'
    assert r['sentiment']['confidence']>=.6

def test_negation_and_uncertainty(analyzer):
    assert analyzer.score('The story is not good')['label']=='negative'
    assert analyzer.score('The ending is not terrible')['label']=='positive'
    assert analyzer.score('not bad')['label']=='positive'
    assert analyzer.score('It wasn’t bad')['label']=='positive'
    assert analyzer.score('I cannot recommend this movie')['label']=='negative'
    assert analyzer.score("I can't recommend this movie enough")['label']=='positive'
    assert analyzer.score('It is a film')['label']=='neutral'
    assert analyzer.score('It is a film')['uncertain']
    assert analyzer.score('It was okay')['label']=='neutral'
    assert analyzer.score('It was neither good nor bad')['label']=='neutral'
    assert analyzer.score('I have mixed feelings')['label']=='mixed'
    assert analyzer.score('It could have been better')['label']=='negative'
    assert analyzer.score('I expected more')['label']=='negative'
    assert analyzer.score('It was barely watchable')['label']=='negative'
    assert analyzer.score('Yeah right, what a masterpiece!!')['uncertain']
    assert analyzer.analyze('The music plays')['aspects']['Music']['score'] is None

def test_binary_model_cannot_override_clear_context(analyzer):
    class StronglyNegativeModel:
        classes_ = np.array([0, 1])
        @staticmethod
        def predict_proba(rows):
            return np.array([[.98, .02] for _ in rows])

    analyzer.vector_model = StronglyNegativeModel()
    analyzer.model_name = 'test-binary-model'
    result = analyzer.score('The movie was not bad')
    assert result['label']=='positive'
    assert result['positive_probability']==.02
    assert result['detail']['negation_hits']==1
    assert result['method'].startswith('hybrid:')

def test_integrity_is_screening_not_ground_truth():
    r=authenticity('A unique and excellent film',['A unique and excellent film'])
    assert r['duplicate'] and r['needs_review']
    assert 'fake' not in r or not r['fake']
    assert authenticity('An excellent film with brilliant performances')['risk_index']==0

def test_summary_uses_all_eligible_reviews_and_deduplicates(analyzer):
    reviews=[{'review_id':'one','text':'The story is excellent.','source':'test'},
             {'review_id':'two','text':'The story is awful and disappointing.','source':'test'}]
    first=analyzer.summarize(reviews[:1]);all_rows=analyzer.summarize(reviews)
    duplicate=analyzer.summarize(reviews+[dict(reviews[0],review_id='copy')])
    assert all_rows['aspects']['Story']['score']<first['aspects']['Story']['score']
    assert all_rows['eligible_reviews']==2
    assert duplicate['eligible_reviews']==2 and duplicate['duplicates_excluded']==1
    assert {e['polarity'] for e in all_rows['excerpts']}=={'positive','negative'}
    assert {'positive','negative','mixed','neutral','uncertain'}==set(all_rows['sentiment_counts'])
    assert analyzer.summarize([])['aspects']['Acting']['score'] is None

def test_recommendation_intersection_and_dislikes():
    movies=json.loads((ROOT/'data/demo/catalog.json').read_text());r=Recommender(movies)
    positive=r.recommend([{'movie_id':3,'rating':5}],genres=['Sci-Fi','Romance'])
    negative=r.recommend([{'movie_id':3,'rating':.5}],genres=['Sci-Fi','Romance'])
    assert all({'Sci-Fi','Romance'}.issubset(m['genres']) and m['movie_id']!=3 for m in positive)
    p={m['movie_id']:m['rank_score'] for m in positive};n={m['movie_id']:m['rank_score'] for m in negative}
    assert p[7]>n[7]
    assert any(m['movie_id']==13 for m in positive)

def test_als_artifact_loaded_and_demo_namespace_blocked(tmp_path):
    np.savez(tmp_path/'als_factors.npz',movie_ids=np.array([1,2,3]),factors=np.array([[1.,0.],[.9,.1],[0.,1.]]),reg_param=np.array(.1))
    movies=[{'movie_id':i,'title':f'Film {i}','genres':['Drama'],'themes':['Love'],'overview':'A relationship story','source':'test'} for i in (1,2,3)]
    r=Recommender(movies,tmp_path)
    assert r.factors is not None
    picks=r.recommend([{'movie_id':1,'rating':5}])
    assert picks[0]['movie_id']==2 and picks[0]['rank_method']=='content + ALS'
    demo=Recommender([dict(m,source='demo') for m in movies],tmp_path)
    assert demo.factors is None

def test_api_end_to_end_history_reviews_and_cold_start(client):
    assert client.get('/api/health').status_code==200
    assert client.get('/').status_code==200
    empty=client.get('/api/movies/13').json()['review_summary']
    assert empty['total_reviews']==0
    before=client.get('/api/movies/1').json()['review_summary']['total_reviews']
    payload={'movie_id':1,'text':'The soundtrack is awful and the acting is disappointing.'}
    response=client.post('/api/reviews',json=payload)
    assert response.status_code==201
    assert response.json()['review_summary']['total_reviews']==before+1
    client.put('/api/users/tester/ratings',json={'movie_id':3,'rating':5})
    picks=client.get('/api/users/tester/recommendations',params={'genres':'Sci-Fi,Romance'}).json()['movies']
    assert picks and all(m['movie_id']!=3 for m in picks)
    assert len(client.get('/api/users/tester/history').json()['ratings'])==1
    client.delete('/api/users/tester/ratings/3')
    assert not client.get('/api/users/tester/history').json()['ratings']

def test_api_validation_and_unknown_movie(client):
    assert client.post('/api/analyze',json={'movie_id':99999,'text':'Very good'}).status_code==404
    assert client.post('/api/analyze',json={'text':'<br>    <br>'}).status_code==422
    assert client.put('/api/users/a/ratings',json={'movie_id':1,'rating':5.5}).status_code==422
    assert client.put('/api/users/a/ratings',json={'movie_id':1,'rating':3.2}).status_code==422
    assert client.get('/api/movies/99999').status_code==404
    assert client.post('/api/transcribe',content=b'audio').status_code==503

def test_review_submission_is_idempotent_and_responses_are_hardened(client):
    request_id='4ad86fe3-7e3a-47dc-a531-bf9224026de8'
    payload={'movie_id':1,'text':'Not bad at all; the acting was good.','request_id':request_id}
    first=client.post('/api/reviews',json=payload,headers={'x-request-id':'test-request'})
    replay=client.post('/api/reviews',json=payload)
    assert first.status_code==201 and replay.status_code==200
    assert first.json()['review']['review_id']==replay.json()['review']['review_id']
    assert first.json()['review_summary']['total_reviews']==replay.json()['review_summary']['total_reviews']
    assert first.headers['x-request-id']=='test-request'
    assert first.headers['x-content-type-options']=='nosniff'
    conflict=client.post('/api/reviews',json={**payload,'text':'A different review.'})
    assert conflict.status_code==409

def test_browser_and_backend_taxonomies_stay_in_sync():
    assert json.loads((ROOT/'data/taxonomy.json').read_text(encoding='utf-8')) == json.loads(
        (ROOT/'frontend/taxonomy.json').read_text(encoding='utf-8')
    )

def test_chat_context_and_explicit_exclusion(client):
    first=client.post('/api/users/a/chat',json={'message':'Sci-fi with romance'}).json()
    assert first['movies'] and all({'Sci-Fi','Romance'}.issubset(m['genres']) for m in first['movies'])
    second=client.post('/api/users/a/chat',json={'message':'Under 120 minutes','context':first['context']}).json()
    assert second['movies'] and all(m['runtime']<=120 for m in second['movies'])
    summary=client.post('/api/users/a/chat',json={'message':'Summarize the reviews for Arrival'}).json()
    assert summary['review_summary']['eligible_reviews']==3
    follow=client.post('/api/users/a/chat',json={'message':'What about its pacing?','context':summary['context']}).json()
    assert follow['movies'][0]['title']=='Arrival'
    avoid=client.post('/api/users/a/chat',json={'message':'reset sci-fi without romance'}).json()
    assert all('Romance' not in m['genres'] for m in avoid['movies'])

def test_idempotent_import_and_persistence(tmp_path):
    store=Store(tmp_path,seed_reviews=False)
    assert store.add_review(1,'Good film',review_id='tmdb-a')['inserted']
    assert not store.add_review(1,'Good film',review_id='tmdb-a')['inserted']
    assert len(Store(tmp_path,seed_reviews=False).reviews(1))==1

def test_ranking_denominator_includes_unserved_users():
    result=ranking_metrics({'a':[1,2]},{'a':{1},'b':{3},'empty':set()},k=2)
    assert result['eligible_users']==2
    assert result['recall_at_k']==.5
    assert result['precision_at_k']==.25
