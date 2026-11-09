"""Human factuality/coverage measurements; overlap alone is not truth."""
def evaluate(judgments):
    if not judgments:
        raise ValueError("Actual human sentence judgments are required.")
    if any(type(row.get("supported")) is not bool or type(row.get("contradiction")) is not bool or not row.get("reviewer_id") for row in judgments):
        raise ValueError("Incomplete actual human judgments.")
    return {"sentences": len(judgments), "unsupported_claim_rate": sum(not row["supported"] for row in judgments) / len(judgments),
            "contradiction_rate": sum(row["contradiction"] for row in judgments) / len(judgments),
            "rouge": None, "bertscore": None, "overlap_metrics_status": "require_permitted_human_reference_summaries"}
