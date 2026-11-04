"""Ranking and annotation metrics with explicit denominators and empty-user policy."""
import numpy as np


def ranking_metrics(predictions,relevance,k=10,catalog_size=None):
    # predictions/relevance: {user_id: list or set of movie_id}. Macro average over users with >=1 relevant heldout item.
    users=[u for u,items in relevance.items() if len(items)]
    if not users:return {'eligible_users':0,'recall_at_k':None,'ndcg_at_k':None,'precision_at_k':None,'coverage':None}
    recalls=[];ndcgs=[];precisions=[];catalog=set()
    for u in users:
        recommended=list(dict.fromkeys(predictions.get(u,[])))[:k]
        truth=set(relevance[u]);hits=np.array([int(i in truth) for i in recommended])
        recalls.append(float(hits.sum()/len(truth)))
        precisions.append(float(hits.sum()/k))
        dcg=float((hits/np.log2(np.arange(len(hits))+2)).sum())
        ideal=float((1/np.log2(np.arange(min(k,len(truth)))+2)).sum())
        ndcgs.append(dcg/ideal if ideal else 0.)
        catalog.update(recommended)
    return {'eligible_users':len(users),'recall_at_k':float(np.mean(recalls)),'ndcg_at_k':float(np.mean(ndcgs)),
            'precision_at_k':float(np.mean(precisions)),'coverage':len(catalog)/catalog_size if catalog_size else None,
            'note':'Users with no heldout relevant items excluded; no-recommendation users with relevant items count as zero.'}


def expected_calibration_error(y,prob,bins=10):
    y=np.asarray(y);p=np.asarray(prob);total=len(y);ece=0.
    for i in range(bins):
        mask=(p>=i/bins)&(p<(i+1)/bins if i<bins-1 else p<=1)
        if mask.any():ece+=mask.sum()/total*abs(p[mask].mean()-y[mask].mean())
    return float(ece)
