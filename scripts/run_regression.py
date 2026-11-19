"""Live question-run collector. Does not automatically claim answers are correct.

Explicit --live flag is required: each question makes a real API call and uses quota.
"""
import argparse
import csv
import os
import time
import uuid
from pathlib import Path
from dotenv import load_dotenv
from allsales.dify_client import DifyClient, DifyError

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "data" / "golden_17_questions.csv"


def read_questions(path=GOLDEN):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser(description="Run a repeatable Dify regression batch")
    p.add_argument("--live", action="store_true", help="Send actual queries and consume API quota")
    p.add_argument("--limit", type=int, default=17)
    p.add_argument("--output", default="results/new_regression_run.csv")
    args = p.parse_args()
    questions = read_questions()[:max(0, args.limit)]
    if not args.live:
        print(f"Dry run: {len(questions)} question(s) selected. Pass --live to contact Dify.")
        return
    load_dotenv(ROOT / ".env")
    client = DifyClient(os.getenv("DIFY_GEMINI_API_KEY", "") or os.getenv("DIFY_API_KEY", ""),
                        os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1"))
    outfile = Path(args.output)
    outfile.parent.mkdir(parents=True, exist_ok=True)
    columns = ("question_id", "question", "expected_answer", "actual_answer",
               "source_documents", "latency_s", "tokens", "status", "error_code",
               "manual_verdict")
    with outfile.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for question in questions:
            entry = {"question_id": question["question_id"],
                     "question": question["question"],
                     "expected_answer": question["expected_answer"],
                     "manual_verdict": "NOT_REVIEWED"}
            started = time.perf_counter()
            try:
                # Separate users for independent questions; avoids chat-history leakage.
                reply = client.ask(question["question"], user_id=str(uuid.uuid4()))
                entry.update(actual_answer=reply.answer,
                             source_documents="; ".join(reply.source_documents),
                             tokens=reply.tokens, status="ok", error_code="")
            except DifyError as exc:
                entry.update(actual_answer="", source_documents="", tokens="",
                             status="api_error", error_code=exc.code)
            entry["latency_s"] = round(time.perf_counter() - started, 2)
            writer.writerow(entry)
            f.flush()
            print(f"{entry['question_id']}: {entry['status']}")
    print(f"Saved raw answers to {outfile}. Review the manual_verdict column yourself.")


if __name__ == "__main__":
    main()
