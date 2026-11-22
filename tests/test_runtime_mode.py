"""Fail-closed checks for the local-only development runtime."""
import pytest
from fastapi.testclient import TestClient

from backend import api


@pytest.mark.parametrize("mode", ["production", "staging", "prod", "test", "", "other"])
def test_non_local_modes_rejected(monkeypatch, mode):
    monkeypatch.setenv("ALLSALES_ENV", mode)
    with pytest.raises(RuntimeError, match="local-only"):
        with TestClient(api.app):
            pass


def test_local_mode_allows_health_check(monkeypatch):
    monkeypatch.setenv("ALLSALES_ENV", "local")
    with TestClient(api.app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_missing_mode_is_rejected(monkeypatch):
    monkeypatch.delenv("ALLSALES_ENV", raising=False)
    with pytest.raises(RuntimeError, match="local-only"):
        api.require_local_environment()
    with pytest.raises(RuntimeError, match="local-only"):
        with TestClient(api.app):
            pass
