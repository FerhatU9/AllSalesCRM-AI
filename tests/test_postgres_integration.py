"""PostgreSQL-backed API isolation test; runs only against disposable CI database.

Requires TEST_POSTGRES_URL and DATABASE_URL to point to the same test service.
Never run with real customer data.
"""
from __future__ import annotations

import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from allsales.auth import VerifiedIdentity, get_verified_identity
from allsales.models import Identity, LeadRecord, Membership, Organization
from backend import api, lead_routes


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="Disposable PostgreSQL CI service required")
def test_postgres_migrations_and_tenant_isolation(monkeypatch):
    url = os.environ["TEST_POSTGRES_URL"]
    assert url.startswith("postgresql+psycopg://"), "Integration test requires PostgreSQL"
    assert os.environ.get("CI") == "true", "Never point integration tests at a non-CI database"
    assert "127.0.0.1" in url or "localhost" in url, "Use a local disposable service"
    assert "/allsales_test" in url.split("?")[0], "Use the dedicated allsales_test database"
    monkeypatch.setenv("DATABASE_URL", url)

    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(url, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        assert {"organizations", "identities", "memberships", "leads"} <= set(inspect(engine).get_table_names())

        with Session(engine) as session:
            org_a = Organization(slug="integration-a", display_name="Synthetic A")
            org_b = Organization(slug="integration-b", display_name="Synthetic B")
            alice = Identity(issuer="https://idp.example/", subject="alice")
            bob = Identity(issuer="https://idp.example/", subject="bob")
            viewer = Identity(issuer="https://idp.example/", subject="viewer")
            session.add_all([org_a, org_b, alice, bob, viewer])
            session.flush()
            org_a_id, org_b_id = org_a.id, org_b.id
            session.add_all([
                Membership(organization_id=org_a.id, identity_id=alice.id, role="sales"),
                Membership(organization_id=org_b.id, identity_id=bob.id, role="owner"),
                Membership(organization_id=org_a.id, identity_id=viewer.id, role="viewer"),
            ])
            session.commit()

        monkeypatch.setattr(lead_routes, "session_factory", lambda: factory)
        monkeypatch.setattr(api, "session_factory", lambda: factory)

        def set_identity(subject):
            api.app.dependency_overrides[get_verified_identity] = (
                lambda: VerifiedIdentity(issuer="https://idp.example/", subject=subject)
            )

        def path(org_id, lead_id=""):
            return "/v1/organizations/" + str(org_id) + "/leads" + (
                "/" + str(lead_id) if lead_id else ""
            )

        with TestClient(api.app) as client:
            set_identity("alice")
            my_orgs = client.get("/v1/account/organizations")
            assert my_orgs.status_code == 200
            assert [o["slug"] for o in my_orgs.json()["organizations"]] == ["integration-a"]
            created = client.post(path(org_a_id), json={"company_name": "Example Synthetic", "summary": "No real customer data"})
            assert created.status_code == 201, created.text
            lead_id = created.json()["id"]
            assert client.get(path(org_a_id, lead_id)).status_code == 200
            assert client.patch(path(org_a_id, lead_id), json={"status": "qualified"}).status_code == 200
            assert client.get(path(org_b_id)).status_code == 404
            assert client.get(path(org_b_id, lead_id)).status_code == 404
            assert client.patch(path(org_b_id, lead_id), json={"status": "archived"}).status_code == 404

            set_identity("viewer")
            assert client.get(path(org_a_id)).status_code == 200
            assert client.post(path(org_a_id), json={"company_name": "Forbidden"}).status_code == 403
            assert client.patch(path(org_a_id, lead_id), json={"status": "archived"}).status_code == 403

            set_identity("bob")
            assert client.get(path(org_b_id)).json() == []
            assert client.get(path(org_a_id, lead_id)).status_code == 404
            assert client.get(path(org_a_id)).status_code == 404

            api.app.dependency_overrides.clear()
            assert client.get(path(org_a_id)).status_code == 401

        with Session(engine) as session:
            records = session.scalars(select(LeadRecord)).all()
            assert len(records) == 1
            assert records[0].organization_id == org_a_id
            assert records[0].status == "qualified"
    finally:
        api.app.dependency_overrides.clear()
        engine.dispose()
