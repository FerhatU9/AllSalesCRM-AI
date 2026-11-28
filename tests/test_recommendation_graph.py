"""Graph routing, data minimization, tenant authorization and no-write checks."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from allsales.auth import VerifiedIdentity, get_verified_identity
from allsales.models import (
    Base, FollowupRequest, Identity, LeadAuditEvent, LeadRecord, Membership,
    Organization,
)
from allsales.recommendation_graph import recommend_lead
from backend import api, lead_routes


@pytest.mark.parametrize(("status", "summary", "action"), [
    ("new", False, "complete_qualification"),
    ("new", True, "complete_qualification"),
    ("qualified", True, "review_followup"),
    ("qualified", False, "review_missing_context"),
    ("archived", True, "no_action"),
    ("archived", False, "no_action"),
])
def test_graph_routes(status, summary, action):
    result = recommend_lead(status, summary)
    assert result.recommended_action == action
    assert result.lead_status == status
    assert result.mode == "local_rules"
    assert result.human_review_required is True
    assert result.automated_actions_taken == 0
    assert result.review_steps
    # Repeated invocation with the same facts is deterministic.
    assert recommend_lead(status, summary) == result


def test_graph_rejects_unrecognized_status():
    with pytest.raises(ValueError, match="Unsupported lead status"):
        recommend_lead("unknown", True)


def test_recommendation_api_scope_and_read_only(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    issuer = "https://idp.example/"
    with Session(engine) as db:
        a = Organization(slug="org-a", display_name="Synthetic A")
        b = Organization(slug="org-b", display_name="Synthetic B")
        identities = {
            subject: Identity(issuer=issuer, subject=subject)
            for subject in ("owner", "sales", "viewer", "other", "robot@clients")
        }
        db.add_all([a, b, *identities.values()])
        db.flush()
        for subject, org, role in [
            ("owner", a, "owner"), ("sales", a, "sales"),
            ("viewer", a, "viewer"), ("other", b, "owner"),
            ("robot@clients", a, "automation"),
        ]:
            db.add(Membership(
                organization_id=org.id, identity_id=identities[subject].id, role=role
            ))
        lead = LeadRecord(
            organization_id=a.id, created_by_identity_id=identities["owner"].id,
            company_name="Synthetic company", summary="Private test sentinel",
            status="qualified",
        )
        blank = LeadRecord(
            organization_id=a.id, created_by_identity_id=identities["owner"].id,
            company_name="Synthetic blank", summary="   ", status="qualified",
        )
        db.add_all([lead, blank])
        db.flush()
        org_a, org_b, lead_id, blank_id = a.id, b.id, lead.id, blank.id
        db.commit()

    monkeypatch.setattr(lead_routes, "session_factory", lambda: factory)
    monkeypatch.setenv("ALLSALES_ENV", "local")
    calls = []

    def spy(status, has_summary):
        calls.append((status, has_summary))
        return recommend_lead(status, has_summary)

    monkeypatch.setattr(lead_routes, "recommend_lead", spy)

    def path(org=org_a, lid=lead_id):
        return f"/v1/organizations/{org}/leads/{lid}/recommendation"

    def login(subject, scopes=frozenset()):
        api.app.dependency_overrides[get_verified_identity] = lambda: VerifiedIdentity(
            issuer=issuer, subject=subject, scopes=scopes
        )

    try:
        with TestClient(api.app) as client:
            assert client.get(path()).status_code == 401
            for subject in ("owner", "sales", "viewer"):
                login(subject)
                response = client.get(path())
                assert response.status_code == 200, response.text
                assert response.headers["Cache-Control"] == "no-store"
                assert response.json()["recommended_action"] == "review_followup"
                assert "Private test sentinel" not in response.text
            login("owner")
            assert client.get(path(lid=blank_id)).json()["recommended_action"] == "review_missing_context"
            assert client.get(path(lid=uuid4())).status_code == 404
            assert client.get(path(org=org_b)).status_code == 404
            login("other")
            assert client.get(path()).status_code == 404
            assert client.get(path(org=org_b)).status_code == 404
            login("unassigned")
            assert client.get(path()).status_code == 404
            login("robot@clients", frozenset({"request:followups", "execute:followups"}))
            assert client.get(path()).status_code == 403
            assert calls == [("qualified", True)] * 3 + [("qualified", False)]

        with Session(engine) as db:
            unchanged = db.get(LeadRecord, lead_id)
            assert unchanged.status == "qualified"
            assert unchanged.summary == "Private test sentinel"
            assert db.scalar(select(func.count()).select_from(LeadRecord)) == 2
            assert db.scalar(select(func.count()).select_from(FollowupRequest)) == 0
            assert db.scalar(select(func.count()).select_from(LeadAuditEvent)) == 0
    finally:
        api.app.dependency_overrides.clear()
        engine.dispose()
