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
from allsales.models import Identity, LeadAuditEvent, LeadRecord, Membership, Organization, QualificationRecord
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
        assert {"organizations", "identities", "memberships", "leads", "lead_audit_events", "qualification_records"} <= set(inspect(engine).get_table_names())

        with Session(engine) as session:
            org_a = Organization(slug="integration-a", display_name="Synthetic A")
            org_b = Organization(slug="integration-b", display_name="Synthetic B")
            alice = Identity(issuer="https://idp.example/", subject="alice")
            bob = Identity(issuer="https://idp.example/", subject="bob")
            viewer = Identity(issuer="https://idp.example/", subject="viewer")
            session.add_all([org_a, org_b, alice, bob, viewer])
            session.flush()
            org_a_id, org_b_id, alice_id = org_a.id, org_b.id, alice.id
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

            facts = {
                "country": "Netherlands", "employee_count": 120, "industry": "SaaS",
                "contact_name": "Demo Buyer", "business_email": "buyer@example.test",
                "lead_source": "Website", "assigned_owner": "Demo Rep",
                "consent_status": "Opted In", "decision_days": 20,
                "decision_authority": "final", "engagement": "none",
            }
            lead_path = path(org_a_id, lead_id)
            history_path = lead_path + "/qualifications"
            dashboard_path = f"/v1/organizations/{org_a_id}/qualification-dashboard"
            preview = client.post(lead_path + "/qualification-preview", json={"facts": facts, "confirm_synthetic": True})
            assert preview.status_code == 200, preview.text
            payload = {"facts": facts, "confirm_synthetic": True, "request_key": str(uuid4()),
                       "review_digest": preview.json()["review_digest"]}
            assert client.get(history_path).json() == []
            saved = client.post(history_path, json=payload)
            assert saved.status_code == 201, saved.text
            assert saved.json()["decision"]["provisional_score"] == 85
            retry = client.post(history_path, json=payload)
            assert retry.status_code == 200 and retry.json() == saved.json()
            dashboard = client.get(dashboard_path)
            assert dashboard.status_code == 200, dashboard.text
            assert dashboard.json()["tier_a"] == 1
            assert dashboard.json()["evaluated"] == 1
            assert dashboard.json()["leads"][0]["latest"] == saved.json()
            assert client.get(path(org_a_id, lead_id) + "/activity").status_code == 403
            assert client.get(path(org_b_id)).status_code == 404
            assert client.get(path(org_b_id, lead_id)).status_code == 404
            assert client.patch(path(org_b_id, lead_id), json={"status": "archived"}).status_code == 404

            set_identity("alice")
            # Sales members cannot read audit trails, even though they can update leads.
            assert client.get(path(org_a_id, lead_id) + "/activity").status_code == 403

            set_identity("viewer")
            assert client.get(path(org_a_id)).status_code == 200
            assert client.post(path(org_a_id), json={"company_name": "Forbidden"}).status_code == 403
            assert client.patch(path(org_a_id, lead_id), json={"status": "archived"}).status_code == 403

            assert client.get(history_path).status_code == 200
            assert client.get(dashboard_path).status_code == 200
            assert client.post(history_path, json=payload).status_code == 403

            set_identity("bob")
            assert client.get(path(org_b_id)).json() == []
            assert client.get(path(org_a_id, lead_id)).status_code == 404
            assert client.get(path(org_a_id)).status_code == 404
            assert client.get(path(org_a_id, lead_id) + "/activity").status_code == 404

            assert client.get(history_path).status_code == 404
            assert client.get(dashboard_path).status_code == 404
            api.app.dependency_overrides.clear()
            assert client.get(path(org_a_id)).status_code == 401

        with Session(engine) as session:
            records = session.scalars(select(LeadRecord)).all()
            assert len(records) == 1
            assert records[0].organization_id == org_a_id
            assert records[0].status == "qualified"
            snapshot = session.scalars(select(QualificationRecord)).one()
            assert snapshot.lead_id == records[0].id
            assert snapshot.actor_identity_id == alice_id
            assert snapshot.decision["priority_tier"] == "A"
            events = session.scalars(select(LeadAuditEvent)).all()
            assert len(events) == 2
            assert events[0].organization_id == org_a_id
            assert events[0].action == "created"
            assert events[1].action == "updated"
            assert events[1].previous_status == "new"
            assert events[1].new_status == "qualified"
    finally:
        api.app.dependency_overrides.clear()
        engine.dispose()
