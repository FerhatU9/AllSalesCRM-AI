"""Authorization and transaction checks for synthetic lead activity history."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from allsales.auth import VerifiedIdentity, get_verified_identity
from allsales.models import Base, Identity, LeadAuditEvent, LeadRecord, Membership, Organization
from backend import api, lead_routes


@pytest.fixture
def setup_audit(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with Session(engine) as session:
        org_a = Organization(slug="audit-a", display_name="Synthetic A")
        org_b = Organization(slug="audit-b", display_name="Synthetic B")
        identities = {
            name: Identity(issuer="https://idp.example/", subject=name)
            for name in ("owner", "sales", "viewer", "outsider")
        }
        session.add_all([org_a, org_b, *identities.values()])
        session.flush()
        session.add_all([
            Membership(organization_id=org_a.id, identity_id=identities["owner"].id, role="owner"),
            Membership(organization_id=org_a.id, identity_id=identities["sales"].id, role="sales"),
            Membership(organization_id=org_a.id, identity_id=identities["viewer"].id, role="viewer"),
            Membership(organization_id=org_b.id, identity_id=identities["outsider"].id, role="owner"),
        ])
        session.commit()
        org_ids = (org_a.id, org_b.id)
        identity_ids = {name: x.id for name, x in identities.items()}
    monkeypatch.setattr(lead_routes, "session_factory", lambda: factory)
    try:
        with TestClient(api.app) as client:
            def sign_in(subject):
                api.app.dependency_overrides[get_verified_identity] = (
                    lambda: VerifiedIdentity(issuer="https://idp.example/", subject=subject)
                )
            yield client, factory, sign_in, org_ids, identity_ids
    finally:
        api.app.dependency_overrides.clear()
        engine.dispose()


def test_lead_changes_have_scoped_minimal_activity(setup_audit):
    client, factory, sign_in, (org_a, org_b), identities = setup_audit
    base_a = f"/v1/organizations/{org_a}/leads"
    base_b = f"/v1/organizations/{org_b}/leads"
    sign_in("sales")
    created = client.post(base_a, json={"company_name": "Fictional Inc", "summary": "Private synthetic notes"})
    assert created.status_code == 201, created.text
    lead_id = created.json()["id"]
    activity = base_a + f"/{lead_id}/activity"

    assert client.get(activity).status_code == 403
    updated = client.patch(base_a + f"/{lead_id}", json={"status": "qualified", "summary": "New synthetic notes"})
    assert updated.status_code == 200, updated.text
    assert client.patch(base_a + f"/{lead_id}", json={"status": "qualified"}).status_code == 200

    sign_in("viewer")
    assert client.get(activity).status_code == 403
    assert client.patch(base_a + f"/{lead_id}", json={"status": "archived"}).status_code == 403

    sign_in("outsider")
    assert client.get(activity).status_code == 404
    assert client.get(base_b + f"/{lead_id}/activity").status_code == 404

    sign_in("owner")
    events_response = client.get(activity)
    assert events_response.status_code == 200, events_response.text
    events = events_response.json()
    assert len(events) == 2
    assert events[0]["action"] == "created"
    assert events[0]["actor_identity_id"] == str(identities["sales"])
    assert events[0]["previous_status"] is None
    assert events[0]["new_status"] == "new"
    assert events[1]["action"] == "updated"
    assert events[1]["previous_status"] == "new"
    assert events[1]["new_status"] == "qualified"
    assert events[1]["changed_fields"] == ["status", "summary"]
    assert all(e["organization_id"] == str(org_a) for e in events)
    assert "Fictional Inc" not in str(events)
    assert "Private synthetic notes" not in str(events)
    assert client.get(activity, params={"limit": 1, "offset": 1}).json()[0]["action"] == "updated"
    assert client.get(activity, params={"limit": 101}).status_code == 422
    assert client.get(activity, params={"offset": -1}).status_code == 422

    with factory() as db:
        assert len(db.scalars(select(LeadAuditEvent)).all()) == 2
        assert db.scalar(select(LeadRecord).where(LeadRecord.id == uuid4())) is None


def test_audit_insert_failure_rolls_back_lead_creation(setup_audit):
    client, factory, sign_in, (org_a, _org_b), _ids = setup_audit
    sign_in("sales")
    engine = factory.kw["bind"]

    @event.listens_for(Session, "before_flush")
    def fail_if_audit_insert(session, context, instances):
        if any(isinstance(item, LeadAuditEvent) for item in session.new):
            raise RuntimeError("Simulated failure before audit persistence")

    try:
        with pytest.raises(RuntimeError, match="Simulated failure"):
            client.post(
                f"/v1/organizations/{org_a}/leads",
                json={"company_name": "Rollback Test", "summary": "Synthetic"},
            )
    finally:
        event.remove(Session, "before_flush", fail_if_audit_insert)

    with Session(engine) as db:
        assert db.scalars(select(LeadRecord)).all() == []
        assert db.scalars(select(LeadAuditEvent)).all() == []


def test_unauthenticated_activity_is_rejected(setup_audit):
    client, factory, sign_in, (org_a, _org_b), _ids = setup_audit
    api.app.dependency_overrides.clear()
    response = client.get(f"/v1/organizations/{org_a}/leads/{uuid4()}/activity")
    assert response.status_code == 401
