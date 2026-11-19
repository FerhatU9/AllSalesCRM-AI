from fastapi.testclient import TestClient
from allsales.dify_client import ChatReply, DifyError
from backend import api

HEADERS = {"X-API-Key": "test-local-token"}
PAYLOAD = {"question": "score 62?", "user_id": "session123", "model": "gemini",
           "conversation_id": "gemini-session-12"}


def configured_client(monkeypatch):
    monkeypatch.setenv("API_APP_TOKEN", "test-local-token")
    monkeypatch.setenv("DIFY_GEMINI_API_KEY", "fake-gemini")
    monkeypatch.setenv("DIFY_CLAUDE_API_KEY", "fake-claude")
    return TestClient(api.app)


def test_opt_in_overload_falls_back_once_and_starts_new_conversation(monkeypatch):
    c = configured_client(monkeypatch)
    seen = []
    def fake_ask(self, question, *, user_id, conversation_id):
        seen.append((self._api_key, conversation_id, question))
        if self._api_key == "fake-gemini":
            raise DifyError("Model overloaded", status=503, retryable=True)
        return ChatReply("Priority B: three business days", "claude-new-22", ("policy.md",), 100)
    monkeypatch.setattr(api.DifyClient, "ask", fake_ask)
    resp = c.post("/v1/chat", headers=HEADERS, json={**PAYLOAD, "allow_fallback": True})
    assert resp.status_code == 200
    assert resp.json()["model"] == "claude"
    assert resp.json()["requested_model"] == "gemini"
    assert resp.json()["fallback_used"] is True
    assert seen == [("fake-gemini", "gemini-session-12", "score 62?"),
                    ("fake-claude", "", "score 62?")]


def test_fallback_off_does_not_attempt_backup(monkeypatch):
    c = configured_client(monkeypatch)
    seen = []
    def fake_ask(self, question, *, user_id, conversation_id):
        seen.append(self._api_key)
        raise DifyError("Model overloaded", status=503, retryable=True)
    monkeypatch.setattr(api.DifyClient, "ask", fake_ask)
    resp = c.post("/v1/chat", headers=HEADERS, json=PAYLOAD)
    assert resp.status_code == 503
    assert seen == ["fake-gemini"]


def test_401_does_not_fallback_even_opted_in(monkeypatch):
    c = configured_client(monkeypatch)
    seen = []
    def fake_ask(self, question, *, user_id, conversation_id):
        seen.append(self._api_key)
        raise DifyError("Dify authentication rejected", status=401, retryable=False)
    monkeypatch.setattr(api.DifyClient, "ask", fake_ask)
    resp = c.post("/v1/chat", headers=HEADERS, json={**PAYLOAD, "allow_fallback": True})
    assert resp.status_code == 502
    assert seen == ["fake-gemini"]


def test_quota_429_does_not_fallback(monkeypatch):
    c = configured_client(monkeypatch)
    seen = []
    def fake_ask(self, question, *, user_id, conversation_id):
        seen.append(self._api_key)
        raise DifyError("Provider quota exceeded", status=429, retryable=True)
    monkeypatch.setattr(api.DifyClient, "ask", fake_ask)
    resp = c.post("/v1/chat", headers=HEADERS, json={**PAYLOAD, "allow_fallback": True})
    assert resp.status_code == 503
    assert seen == ["fake-gemini"]


def test_timeout_does_not_fallback(monkeypatch):
    c = configured_client(monkeypatch)
    seen=[]
    def fake_ask(self, question, *, user_id, conversation_id):
        seen.append(self._api_key)
        raise DifyError("Timeout", status=None, retryable=True)
    monkeypatch.setattr(api.DifyClient, "ask", fake_ask)
    resp = c.post("/v1/chat", headers=HEADERS, json={**PAYLOAD, "allow_fallback": True})
    assert resp.status_code == 503
    assert seen == ["fake-gemini"]


def test_healthy_model_not_switched(monkeypatch):
    c = configured_client(monkeypatch)
    def fake_ask(self, question, *, user_id, conversation_id):
        return ChatReply("Gemini answer", "original-gemini-id", (), 13)
    monkeypatch.setattr(api.DifyClient, "ask", fake_ask)
    resp = c.post("/v1/chat", headers=HEADERS, json={**PAYLOAD, "allow_fallback": True})
    assert resp.status_code == 200
    assert resp.json()["model"] == "gemini"
    assert "fallback_used" not in resp.json()


def test_backup_failure_returns_generic_error(monkeypatch):
    c = configured_client(monkeypatch)
    seen=[]
    def fake_ask(self, question, *, user_id, conversation_id):
        seen.append(self._api_key)
        if self._api_key == "fake-gemini":
            raise DifyError("Model overloaded", status=503, retryable=True)
        raise DifyError("secret-internal-provider-debug-string", status=503, retryable=True)
    monkeypatch.setattr(api.DifyClient, "ask", fake_ask)
    resp = c.post("/v1/chat", headers=HEADERS, json={**PAYLOAD, "allow_fallback": True})
    assert resp.status_code == 503
    assert "secret-internal" not in str(resp.json())
    assert len(seen)==2
