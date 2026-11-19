from scripts.summarize_baseline import summarize


def test_saved_baseline_matches_recorded_metrics():
    metrics = summarize()
    assert metrics["questions"] == 17
    assert metrics["core_correct"] == 15
    assert round(metrics["groundedness"], 3) == 0.941
    assert round(metrics["context_relevance"], 3) == 0.853
