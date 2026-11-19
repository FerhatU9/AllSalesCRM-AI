"""Calculate transparent historical metrics; not a fresh model evaluation."""
import csv
import statistics
from pathlib import Path

DEFAULT_FILE = Path(__file__).resolve().parents[1] / "data" / "baseline_17_results.csv"


def summarize(path=DEFAULT_FILE):
    with open(path, newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError("Empty baseline CSV")
    correct = sum(row.get("core_answer_correct", "").strip().lower() == "yes" for row in rows)
    def mean_col(field):
        values = [float(row[field]) for row in rows if row.get(field, "").strip()]
        return statistics.mean(values) if values else None
    return {"questions": len(rows), "core_correct": correct,
            "core_accuracy": correct / len(rows), "groundedness": mean_col("groundedness"),
            "context_relevance": mean_col("context_relevance")}


if __name__ == "__main__":
    r = summarize()
    print("HISTORICAL BASELINE — not post-improvement test results")
    print(f"Core correct: {r['core_correct']}/{r['questions']} ({r['core_accuracy']:.1%})")
    print(f"Groundedness: {r['groundedness']:.3f}")
    print(f"Context relevance: {r['context_relevance']:.3f}")
