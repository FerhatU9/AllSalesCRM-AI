from scripts.compare_models import configured_routes, collect, FIELDS, select_questions, QUESTIONS
from allsales.dify_client import ChatReply, DifyError

class FakeClient:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def ask(self, question, *, user_id, conversation_id=""):
        self.calls.append((question, user_id, conversation_id))
        return ChatReply(self.answer, "conv", ("synthetic.md",), 42)

class FailingClient:
    def ask(self, question, *, user_id, conversation_id=""):
        raise DifyError("Transient failure", code="rate_limit", retryable=True)


def test_no_config_when_missing():
    assert configured_routes({}) == {}


def test_two_independent_clients_same_question():
    a, b = FakeClient("Gemini answer"), FakeClient("Claude answer")
    q = [{"question_id": "Q01", "question": "test?", "expected_answer": "expected"}]
    rows = list(collect(q, {"gemini": a, "claude": b}))
    assert len(rows) == 2 and set(r["model_route"] for r in rows) == {"gemini", "claude"}
    assert rows[0]["manual_correctness"] == "NOT_REVIEWED"
    assert a.calls[0][1] != b.calls[0][1]
    assert set(FIELDS) == set(rows[0])


def test_failed_provider_is_separate_result():
    q = [{"question_id": "Q05", "question": "rule?", "expected_answer": "expected"}]
    rows = list(collect(q, {"gemini": FakeClient("answer"), "claude": FailingClient()}))
    assert rows[0]["status"] == "ok"
    assert rows[1]["status"] == "api_error"
    assert rows[1]["actual_answer"] == ""


def test_17_existing_questions_found():
    assert len(select_questions(QUESTIONS, 17)) == 17
