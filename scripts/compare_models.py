"""Safe, resumable Gemini/Claude evaluation collection.

Does not judge accuracy. Only --live can call the Dify API.
--resume preserves successful answers and reviewer notes, and retries failures only.
--max-new-calls 1 is designed for low-cost error diagnosis.
"""
import argparse
import csv
import os
import re
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from allsales.dify_client import DifyClient, DifyError

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = ROOT / "data" / "golden_17_questions.csv"
FIELDS = ["timestamp_utc", "question_id", "model_route", "question", "expected_answer",
          "actual_answer", "source_documents", "latency_seconds", "reported_tokens",
          "status", "error_code", "manual_correctness", "reviewer_notes",
          "http_status", "error_detail"]


def select_questions(path, limit):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))[:limit]


def configured_routes(env):
    return {k: env.get(v, "").strip() for k, v in (
        ("gemini", "DIFY_GEMINI_API_KEY"), ("claude", "DIFY_CLAUDE_API_KEY")
    ) if env.get(v, "").strip()}


def safe_error_detail(exc):
    """Local diagnostic, with common API credential patterns redacted."""
    detail = (getattr(exc, "provider_message", "") or str(exc))
    detail = re.sub(r"(?i)\bBearer\s+[^\s,;]+", "Bearer [REDACTED]", detail)
    detail = re.sub(r"(?i)\b(?:app|sk|key)-[a-zA-Z0-9_-]{8,}", "[REDACTED]", detail)
    detail = re.sub(r"(?i)\b(?:api_key|api-key|authorization)\s*[:=]\s*[^\s,;]+",
                    "credential=[REDACTED]", detail)
    return detail.replace("\n", " ").replace("\r", " ")[:350]


def collect(questions, clients, clock=time.perf_counter):
    """One result per question/model, with an isolated Dify conversation."""
    for row in questions:
        for model, client in clients.items():
            yield run_one(row, model, client, clock=clock)


def run_one(row, model, client, clock=time.perf_counter):
    entry = {key: "" for key in FIELDS}
    entry.update(timestamp_utc=datetime.now(timezone.utc).isoformat(),
                 question_id=row["question_id"], model_route=model,
                 question=row["question"], expected_answer=row["expected_answer"],
                 manual_correctness="NOT_REVIEWED")
    start = clock()
    try:
        reply = client.ask(row["question"], user_id=str(uuid.uuid4()))
        entry.update(actual_answer=reply.answer, status="ok",
                     source_documents="; ".join(reply.source_documents),
                     reported_tokens="" if reply.tokens is None else reply.tokens)
    except DifyError as exc:
        entry.update(status="api_error", error_code=exc.code,
                     http_status=exc.status if exc.status is not None else "",
                     error_detail=safe_error_detail(exc))
    entry["latency_seconds"] = round(clock() - start, 3)
    return entry


def read_existing(path):
    if not path.exists():
        raise FileNotFoundError(f"No previous results found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        entries = list(csv.DictReader(handle))
    results = {}
    for entry in entries:
        key = (entry.get("question_id", ""), entry.get("model_route", ""))
        if key in results:
            raise ValueError(f"Duplicate row in existing CSV: {key}")
        results[key] = {field: entry.get(field, "") for field in FIELDS}
    return results


def atomic_save(path, results):
    """Write full output in one replacement, avoiding partially written CSVs."""
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="",
                                         delete=False, dir=str(path.parent), suffix=".tmp") as handle:
            tmp_name = handle.name
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for result in results.values():
                writer.writerow({k: result.get(k, "") for k in FIELDS})
        os.replace(tmp_name, path)
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.remove(tmp_name)


def main():
    parser = argparse.ArgumentParser(description="Resumable Gemini vs Claude RAG evaluation")
    parser.add_argument("--live", action="store_true", help="Actually use both Dify apps (may consume credits)")
    parser.add_argument("--resume", action="store_true", help="Preserve existing OK rows; retry only failures")
    parser.add_argument("--limit", type=int, default=3, help="Question count, 1-17")
    parser.add_argument("--output", default="results/dual_model_answers.csv")
    parser.add_argument("--max-new-calls", type=int, default=0,
                        help="Limit new paid calls (0=unlimited); use 1 for diagnosis")
    parser.add_argument("--max-errors", type=int, default=2,
                        help="Stop after this many consecutive API errors (default 2)")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between NEW calls (default 2)")
    args = parser.parse_args()
    if not 1 <= args.limit <= 17:
        parser.error("--limit must be between 1 and 17")
    if args.max_new_calls < 0 or args.max_errors < 1 or args.delay < 0:
        parser.error("--max-new-calls must be >=0, --max-errors >=1, and --delay >=0")
    load_dotenv(ROOT / ".env")
    questions = select_questions(QUESTIONS, args.limit)
    routes = configured_routes(os.environ)
    print(f"Selected {len(questions)} questions x 2 model routes = {len(questions) * 2} possible calls")
    if not args.live:
        print("DRY RUN: no API requests sent. Pass --live explicitly to call Dify.")
        print(f"Routes configured: Gemini={bool(routes.get('gemini'))}, Claude={bool(routes.get('claude'))}")
        return
    if set(routes) != {"gemini", "claude"}:
        parser.error("Both DIFY_GEMINI_API_KEY and DIFY_CLAUDE_API_KEY must be configured")
    clients = {name: DifyClient(key, os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1"))
               for name, key in routes.items()}
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.resume:
        try:
            previous = read_existing(output)
        except (FileNotFoundError, ValueError) as exc:
            parser.error(str(exc))
        # Keep historical records for question IDs outside --limit as well.
        results = dict(previous)
    else:
        results = {}
    plan = [(row, model) for row in questions for model in ("gemini", "claude")]
    for row, model in plan:
        key = (row["question_id"], model)
        if key in results and (results[key]["question"] != row["question"] or
                               results[key]["expected_answer"] != row["expected_answer"]):
            parser.error(f"Dataset differs from stored result for {key}; refusing unsafe resume")
    completed = 0
    skipped = 0
    consecutive_errors = 0
    for row, model in plan:
        key = (row["question_id"], model)
        if args.resume and key in results and results[key]["status"] == "ok":
            skipped += 1
            continue
        if args.max_new_calls and completed >= args.max_new_calls:
            break
        if completed and args.delay:
            time.sleep(args.delay)
        result = run_one(row, model, clients[model])
        results[key] = result
        atomic_save(output, results)
        completed += 1
        print(f"{row['question_id']} {model}: {result['status']}")
        if result["status"] != "ok":
            consecutive_errors += 1
            print(f"  HTTP={result['http_status']} code={result['error_code']}")
            if result["error_detail"]:
                print(f"  Dify detail: {result['error_detail']}")
            if consecutive_errors >= args.max_errors:
                print("STOP: repeated API errors. Resolve cause before attempting remaining calls.")
                break
        else:
            consecutive_errors = 0
    print(f"Saved: {output}")
    print(f"New calls: {completed}; preserved successful existing answers: {skipped}")
    print("Accuracy is NOT assessed automatically. Review answers against the handbook.")


if __name__ == "__main__":
    main()
