"""Qualification preview uses deterministic scores and opt-in, minimized AI calls."""
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from allsales.auth import VerifiedIdentity, get_verified_identity
from allsales.dify_client import ChatReply, DifyClient, DifyError
from allsales.lead_qualification import LeadInput
from allsales.models import Base, FollowupRequest, Identity, LeadAuditEvent, LeadRecord, Membership, Organization
from allsales.qualification_graph import preview_qualification
from backend import api, lead_routes


FACTS = {
    "country": "Netherlands", "employee_count": 120, "industry": "SaaS",
    "contact_name": "Demo Contact Sentinel", "business_email": "demo@example.test",
    "lead_source": "Demo Source Sentinel", "consent_status": "Opted In",
    "assigned_owner": "Demo Owner Sentinel", "decision_days": 20,
    "decision_authority": "final", "engagement": "none",
}


def sample(**changes):
    return LeadInput(**{
        "company_name": "Demo Company Sentinel", "stated_use_case": "Demo Summary Sentinel",
        **FACTS, **changes,
    })


def test_local_score_is_authoritative_and_no_provider_call(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("No provider call permitted")
    monkeypatch.setattr(DifyClient, "ask", forbidden)
    result = preview_qualification(sample(), "new", "none")
    assert result.decision.provisional_score == 85
    assert result.decision.priority_tier == "A"
    assert result.stored_status == "new"
    assert result.explanation_status == "not_requested" and result.explanation is None
    assert result.followup_approval_required and result.automated_actions_taken == 0
    incomplete = preview_qualification(sample(country=""), "qualified", "gemini")
    assert incomplete.decision.priority_tier is None
    assert incomplete.explanation_status == "withheld_incomplete"
    unknown = preview_qualification(sample(engagement="unknown"), "qualified", "claude")
    assert unknown.decision.provisional_score is None
    assert unknown.explanation_status == "withheld_incomplete"


@pytest.mark.parametrize("provider", ["gemini", "claude"])
def test_provider_receives_only_derived_facts(monkeypatch, provider):
    monkeypatch.setenv("DIFY_GEMINI_API_KEY", "gemini-test-key")
    monkeypatch.setenv("DIFY_CLAUDE_API_KEY", "claude-test-key")
    calls = []

    def fake_ask(self, question, *, user_id, conversation_id):
        assert self._api_key == provider + "-test-key"
        UUID(user_id)
        assert conversation_id == ""
        assert "Score: 85" in question
        assert "written sales manager approval" in question
        assert "Do not send marketing" in question
        for value in ["Demo Company Sentinel", "Demo Summary Sentinel", "Demo Contact Sentinel",
                      "demo@example.test", "Demo Source Sentinel", "Demo Owner Sentinel",
                      "Netherlands", "SaaS"]:
            assert value not in question
        calls.append(question)
        return ChatReply("Review the discount; the score is 85.", "", ("Synthetic handbook",))

    monkeypatch.setattr(DifyClient, "ask", fake_ask)
    result = preview_qualification(
        sample(proposed_discount_pct=15, consent_status="Opted Out"),
        "qualified", provider,
    )
    assert len(calls) == 1
    assert result.explanation_status == "complete"
    assert result.provider == provider
    assert result.decision.provisional_score == 85 and result.decision.priority_tier == "A"
    assert result.decision.human_review_required
    assert result.followup_approval_required and result.automated_actions_taken == 0
    assert result.source_documents == ["Synthetic handbook"]


def test_provider_failure_and_missing_key_keep_score(monkeypatch):
    monkeypatch.delenv("DIFY_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("DIFY_API_KEY", raising=False)
    calls = []

    def unavailable(self, *args, **kwargs):
        calls.append(self._api_key)
        raise DifyError("secret error details must not be returned")

    monkeypatch.setattr(DifyClient, "ask", unavailable)
    result = preview_qualification(sample(), "qualified", "gemini")
    assert not calls and result.explanation_status == "unavailable"
    monkeypatch.setenv("DIFY_GEMINI_API_KEY", "gemini-test-key")
    monkeypatch.setenv("DIFY_CLAUDE_API_KEY", "claude-test-key")
    result = preview_qualification(sample(), "qualified", "gemini")
    assert calls == ["gemini-test-key"]  # No retries or provider switching.
    assert result.decision.provisional_score == 85
    assert result.explanation_status == "unavailable" and result.explanation is None
    assert "secret error" not in result.model_dump_json()


def test_preview_api_roles_scope_and_no_writes(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:",
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    issuer = "https://idp.example/"
    with Session(engine) as db:
        a, b = Organization(slug="a", display_name="A"), Organization(slug="b", display_name="B")
        actors = {s: Identity(issuer=issuer, subject=s) for s in ("owner", "sales", "viewer", "outsider", "robot@clients")}
        db.add_all([a, b, *actors.values()])
        db.flush()
        for subject, org, role in [("owner", a, "owner"), ("sales", a, "sales"),
                                   ("viewer", a, "viewer"), ("outsider", b, "owner"),
                                   ("robot@clients", a, "automation")]:
            db.add(Membership(organization_id=org.id, identity_id=actors[subject].id, role=role))
        record = LeadRecord(organization_id=a.id, created_by_identity_id=actors["owner"].id,
                            company_name="Stored Company", summary="Stored summary", status="new")
        archived = LeadRecord(organization_id=a.id, created_by_identity_id=actors["owner"].id,
                              company_name="Archived Company", summary="Stored summary", status="archived")
        db.add_all([record, archived])
        db.flush()
        org, other, lead, archive = a.id, b.id, record.id, archived.id
        db.commit()

    monkeypatch.setenv("ALLSALES_ENV", "local")
    monkeypatch.setattr(lead_routes, "session_factory", lambda: factory)
    calls = []

    def spy(lead_input, status, provider):
        calls.append((lead_input.company_name, lead_input.stated_use_case, status, provider))
        return preview_qualification(lead_input, status, "none")

    monkeypatch.setattr(lead_routes, "preview_qualification", spy)

    def path(org_id=org, lead_id=lead):
        return f"/v1/organizations/{org_id}/leads/{lead_id}/qualification-preview"

    def login(subject, scopes=frozenset()):
        api.app.dependency_overrides[get_verified_identity] = lambda: VerifiedIdentity(
            issuer=issuer, subject=subject, scopes=scopes)

    payload = {"facts": FACTS, "provider": "none", "confirm_synthetic": True}
    try:
        with TestClient(api.app) as client:
            assert client.post(path(), json=payload).status_code == 401
            for subject in ("owner", "sales"):
                login(subject)
                r = client.post(path(), json=payload)
                assert r.status_code == 200, r.text
                assert r.headers["Cache-Control"] == "no-store"
                assert r.json()["stored_status"] == "new"
                assert r.json()["decision"]["provisional_score"] == 85
            login("owner")
            assert client.post(path(), json={**payload, "confirm_synthetic": False}).status_code == 422
            assert client.post(path(), json={**payload, "facts": {**FACTS, "company_name": "Spoof"}}).status_code == 422
            assert client.post(path(lead_id=archive), json=payload).status_code == 409
            assert client.post(path(org_id=other), json=payload).status_code == 404
            login("outsider")
            assert client.post(path(), json=payload).status_code == 404
            assert client.post(path(org_id=other), json=payload).status_code == 404
            login("viewer")
            assert client.post(path(), json=payload).status_code == 403
            login("robot@clients", frozenset({"request:followups", "execute:followups"}))
            assert client.post(path(), json=payload).status_code == 403
            assert calls == [("Stored Company", "Stored summary", "new", "none")] * 2
        with Session(engine) as db:
            assert db.get(LeadRecord, lead).status == "new"
            assert db.scalar(select(func.count()).select_from(LeadRecord)) == 2
            assert db.scalar(select(func.count()).select_from(FollowupRequest)) == 0
            assert db.scalar(select(func.count()).select_from(LeadAuditEvent)) == 0
    finally:
        api.app.dependency_overrides.clear()
        engine.dispose()
