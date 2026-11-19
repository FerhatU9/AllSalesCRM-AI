from scripts.compare_models import (
    FIELDS, atomic_save, read_existing, run_one, safe_error_detail,
)
from allsales.dify_client import ChatReply, DifyError

class GoodClient:
    def ask(self, question, *, user_id, conversation_id=""):
        return ChatReply("good", "", ("policy.md",), 23)

class BadClient:
    def ask(self, question, *, user_id, conversation_id=""):
        raise DifyError("Generic error", status=400, code="invalid_param",
                        provider_message="Run failed: bad input")

ROW = {"question_id": "Q06", "question": "Score 80?", "expected_answer": "One business day"}


def test_run_one_saves_safe_error_detail():
    item = run_one(ROW, "gemini", BadClient())
    assert item["status"] == "api_error"
    assert item["error_code"] == "invalid_param"
    assert item["http_status"] == 400
    assert item["error_detail"] == "Run failed: bad input"


def test_existing_rows_read_with_old_schema(tmp_path):
    filename = tmp_path / "old.csv"
    filename.write_text("question_id,model_route,status,question,expected_answer\nQ01,gemini,ok,a,b\n", encoding="utf-8")
    rows = read_existing(filename)
    assert rows[("Q01", "gemini")]["status"] == "ok"
    assert rows[("Q01", "gemini")]["error_detail"] == ""
    atomic_save(filename, rows)
    reread = read_existing(filename)
    assert set(reread[("Q01", "gemini")]) == set(FIELDS)


def test_redaction_of_keys():
    err = DifyError("x", provider_message="Bearer sk-longsecret123456789 and app-secret123456789")
    assert "longsecret" not in safe_error_detail(err)
    assert "secret123456789" not in safe_error_detail(err)


def test_good_path_still_valid():
    result = run_one(ROW, "claude", GoodClient())
    assert result["status"] == "ok"
    assert result["actual_answer"] == "good"
