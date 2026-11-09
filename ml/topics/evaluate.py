def evaluate(assignments, human_judgments):
    if not human_judgments:
        return {"topic_relevance": None, "status": "human_topic_relevance_judgments_missing", "cluster_count": len(set(assignments))}
    if any(type(value) is not bool for value in human_judgments):
        raise ValueError("Actual binary human relevance judgments are required.")
    return {"judgments": len(human_judgments), "human_relevance_rate": sum(human_judgments) / len(human_judgments), "coherence": None,
            "note": "Coherence/stability require a prespecified corpus protocol; no score is invented."}
