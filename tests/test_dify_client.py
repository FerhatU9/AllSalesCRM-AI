from allsales.dify_client import DifyClient, DifyError
import pytest


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self.body = body
    def json(self):
        return self.body


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.last_request = None
    def post(self, url, **kwargs):
        self.last_request = (url, kwargs)
        return self.response


def test_successful_answer_and_sources():
    fake = FakeSession(FakeResponse(200, {
        "answer": "Priority B: within three business days.",
        "conversation_id": "c42", "metadata": {"retriever_resources": [
            {"document_name": "policy.md"}, {"document_name": "policy.md"}],
            "usage": {"total_tokens": 310}}}))
    client = DifyClient("fake-test-key", session=fake)
    response = client.ask("Score 62?", user_id="user", conversation_id="old")
    assert response.answer.startswith("Priority B")
    assert response.conversation_id == "c42"
    assert response.source_documents == ("policy.md",)
    assert response.tokens == 310
    assert fake.last_request[1]["json"]["conversation_id"] == "old"
    assert fake.last_request[1]["json"]["response_mode"] == "blocking"


def test_invalid_key_is_clear():
    fake = FakeSession(FakeResponse(401, {"code":"unauthorized","message":"no"}))
    with pytest.raises(DifyError, match="API key"):
        DifyClient("fake-test-key", session=fake).ask("hello", user_id="x")


def test_high_demand_wrapped_as_400():
    fake = FakeSession(FakeResponse(400, {"code":"invalid_param",
        "message": "Run failed: model currently experiencing high demand. Please try again later"}))
    with pytest.raises(DifyError) as captured:
        DifyClient("fake-test-key", session=fake).ask("hello", user_id="x")
    assert captured.value.retryable
    assert "temporarily" in str(captured.value)


def test_missing_answer_caught():
    fake = FakeSession(FakeResponse(200, {"conversation_id":"c42"}))
    with pytest.raises(DifyError, match="missing an answer"):
        DifyClient("fake-test-key", session=fake).ask("hello", user_id="x")


def test_non_secure_external_endpoint_rejected():
    with pytest.raises(ValueError, match="HTTPS"):
        DifyClient("test", base_url="http://api.example.com/v1")


def test_http_localhost_prefix_attack_is_rejected():
    with pytest.raises(ValueError, match="HTTPS"):
        DifyClient("test", base_url="http://localhost.attacker.example/v1")


def test_http_loopback_is_allowed_for_local_dify():
    assert DifyClient("test", base_url="http://127.0.0.1:5001/v1").base_url.endswith("/v1")


def test_embedded_url_credentials_are_rejected():
    with pytest.raises(ValueError, match="HTTPS"):
        DifyClient("test", base_url="https://user:password@api.dify.ai/v1")
