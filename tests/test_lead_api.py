"""Cross-organization and role-based access tests for synthetic lead endpoints."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from allsales.auth import VerifiedIdentity, get_verified_identity
from allsales.models import Base, Identity, LeadRecord, Membership, Organization
from backend import api
from backend import lead_routes


def test_secure_lead_crud_and_isolation(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with Session(engine) as db:
        a = Organization(slug="org-a", display_name="A")
        b = Organization(slug="org-b", display_name="B")
        alice = Identity(issuer="https://idp.example/", subject="alice")
        bob = Identity(issuer="https://idp.example/", subject="bob")
        viewer = Identity(issuer="https://idp.example/", subject="viewer")
        db.add_all([a, b, alice, bob, viewer])
        db.flush()
        ids = (a.id, b.id)
        db.add_all([
            Membership(organization_id=a.id, identity_id=alice.id, role="sales"),
            Membership(organization_id=b.id, identity_id=bob.id, role="owner"),
            Membership(organization_id=a.id, identity_id=viewer.id, role="viewer"),
        ])
        db.commit()

    monkeypatch.setattr(lead_routes, "session_factory", lambda: factory)
    root = "/v1/organizations"
    def path(org, suffix=""):
        return f"{root}/{org}/leads{suffix}"

    try:
        with TestClient(api.app) as client:
            api.app.dependency_overrides[get_verified_identity] = lambda: VerifiedIdentity(
                issuer="https://idp.example/", subject="alice"
            )
            created = client.post(path(ids[0]), json={"company_name":"Synthetic A", "summary":"Demo"})
            assert created.status_code == 201, created.text
            lead_id = created.json()["id"]
            assert created.json()["organization_id"] == str(ids[0])
            assert client.get(path(ids[0])).json()[0]["company_name"] == "Synthetic A"
            assert client.get(path(ids[0], f"/{lead_id}")).status_code == 200
            assert client.patch(path(ids[0], f"/{lead_id}"), json={"status":"qualified"}).json()["status"] == "qualified"
            assert client.post(path(ids[0]), json={"company_name":"  "}).status_code == 422
            assert client.patch(path(ids[0], f"/{lead_id}"), json={"status":"invalid"}).status_code == 422
            assert client.patch(path(ids[0], f"/{lead_id}"), json={"summary":None}).status_code == 422
            assert client.get(path(ids[1])).status_code == 404
            assert client.get(path(ids[1], f"/{lead_id}")).status_code == 404
            assert client.post(path(ids[1]), json={"company_name":"Forbidden"}).status_code == 404
            assert client.patch(path(ids[1], f"/{lead_id}"), json={"status":"archived"}).status_code == 404

            api.app.dependency_overrides[get_verified_identity] = lambda: VerifiedIdentity(
                issuer="https://idp.example/", subject="viewer"
            )
            assert client.get(path(ids[0])).status_code == 200
            assert client.post(path(ids[0]), json={"company_name":"Blocked"}).status_code == 403
            assert client.patch(path(ids[0], f"/{lead_id}"), json={"status":"archived"}).status_code == 403

            api.app.dependency_overrides[get_verified_identity] = lambda: VerifiedIdentity(
                issuer="https://idp.example/", subject="bob"
            )
            assert client.get(path(ids[0])).status_code == 404
            assert client.get(path(ids[1])).json() == []
            assert client.get(path(ids[1], f"/{lead_id}")).status_code == 404
            assert client.get(path(ids[0], f"/{uuid4()}")).status_code == 404
    finally:
        api.app.dependency_overrides.clear()
        engine.dispose()


def test_bearer_required_for_lead_endpoints():
    with TestClient(api.app) as client:
        response = client.get(f"/v1/organizations/{uuid4()}/leads")
    assert response.status_code == 401
