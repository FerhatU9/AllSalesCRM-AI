from fastapi.testclient import TestClient
from allsales.dify_client import ChatReply, DifyError
from backend import api


def client(monkeypatch):
    monkeypatch.setenv("API_APP_TOKEN", "test-local-token")
    return TestClient(api.app)


def test_health_does_not_claim_upstream_health(monkeypatch):
    c = client(monkeypatch)
    assert c.get("/health").json() == {"status": "ok", "version": "0.8.0"}


def test_authentication_required_for_models(monkeypatch):
    c = client(monkeypatch)
    assert c.get("/v1/models").status_code == 401
    assert c.get("/v1/models", headers={"X-API-Key": "wrong"}).status_code == 401


def test_provider_config_reflected_without_keys(monkeypatch):
    c = client(monkeypatch)
    monkeypatch.setenv("DIFY_GEMINI_API_KEY", "fake-gemini")
    monkeypatch.delenv("DIFY_CLAUDE_API_KEY", raising=False)
    assert c.get("/v1/models", headers={"X-API-Key": "test-local-token"}).json() == {"models": ["gemini"]}


def test_unconfigured_claude_does_not_send_request(monkeypatch):
    c = client(monkeypatch)
    monkeypatch.delenv("DIFY_CLAUDE_API_KEY", raising=False)
    resp = c.post("/v1/chat", headers={"X-API-Key": "test-local-token"},
                  json={"question": "score 62?", "user_id": "session123", "model": "claude"})
    assert resp.status_code == 503
    assert "not configured" in resp.json()["detail"]


def test_gemini_chat_routes_via_client(monkeypatch):
    c = client(monkeypatch)
    monkeypatch.setenv("DIFY_GEMINI_API_KEY", "fake-gemini")
    seen = {}
    def fake_ask(self, question, *, user_id, conversation_id):
        seen.update(question=question, user_id=user_id, conversation_id=conversation_id)
        return ChatReply("Priority B; 3 business days", "conv123", ("handbook.md",), 200)
    monkeypatch.setattr(api.DifyClient, "ask", fake_ask)
    resp = c.post("/v1/chat", headers={"X-API-Key": "test-local-token"},
                  json={"question": "score 62?", "user_id": "session123",
                        "conversation_id": "earlier", "model": "gemini"})
    assert resp.status_code == 200
    assert resp.json() == {"answer": "Priority B; 3 business days",
                           "conversation_id": "conv123", "source_documents": ["handbook.md"],
                           "total_tokens": 200, "model": "gemini"}
    assert seen["conversation_id"] == "earlier"


def test_provider_error_is_sanitized(monkeypatch):
    c = client(monkeypatch)
    monkeypatch.setenv("DIFY_GEMINI_API_KEY", "secret-should-not-leak")
    def fake_ask(self, question, *, user_id, conversation_id):
        raise DifyError("The model service is temporarily unavailable", retryable=True)
    monkeypatch.setattr(api.DifyClient, "ask", fake_ask)
    resp = c.post("/v1/chat", headers={"X-API-Key": "test-local-token"},
                  json={"question": "score 48?", "user_id": "session123", "model": "gemini"})
    assert resp.status_code == 503
    assert "secret-should-not-leak" not in str(resp.json())


def test_blank_and_oversized_questions_rejected(monkeypatch):
    c = client(monkeypatch)
    h = {"X-API-Key": "test-local-token"}
    for q in ("", "x" * 1501):
        assert c.post("/v1/chat", headers=h, json={"question": q, "user_id": "session123"}).status_code == 422


def test_example_token_is_not_accepted(monkeypatch):
    monkeypatch.setenv("API_APP_TOKEN", "replace-with-a-random-32-byte-token")
    from fastapi.testclient import TestClient
    from backend.api import app
    response = TestClient(app).get(
        "/v1/models", headers={"X-API-Key": "replace-with-a-random-32-byte-token"}
    )
    assert response.status_code == 503
