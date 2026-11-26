from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from allsales.auth import VerifiedIdentity, get_verified_identity
from allsales.models import (
    Base,
    FollowupRequest,
    Identity,
    LeadRecord,
    Membership,
    Organization,
)
from backend import api, lead_routes


def test_followup_approval_and_security(monkeypatch):
    monkeypatch.setenv("ALLSALES_ENV", "local")

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    issuer = "https://idp.example/"

    with Session(engine) as db:
        org = Organization(slug="org-a", display_name="A")
        other = Organization(slug="org-b", display_name="B")

        users = {
            name: Identity(issuer=issuer, subject=name)
            for name in ["owner", "admin", "sales", "viewer", "outsider"]
        }

        db.add_all([org, other, *users.values()])
        db.flush()

        for role in ["owner", "admin", "sales", "viewer"]:
            db.add(
                Membership(
                    organization_id=org.id,
                    identity_id=users[role].id,
                    role=role,
                )
            )

        db.add(
            Membership(
                organization_id=other.id,
                identity_id=users["outsider"].id,
                role="owner",
            )
        )

        lead = LeadRecord(
            organization_id=org.id,
            created_by_identity_id=users["sales"].id,
            company_name="Synthetic Company",
            summary="Test lead",
            status="new",
        )

        db.add(lead)
        db.flush()

        org_id = org.id
        other_id = other.id
        lead_id = lead.id
        owner_id = users["owner"].id
        admin_id = users["admin"].id

        db.commit()

    monkeypatch.setattr(
        lead_routes, "session_factory", lambda: factory
    )

    lead_url = f"/v1/organizations/{org_id}/leads/{lead_id}"
    url = f"{lead_url}/followups"

    def sign_in(subject):
        monkeypatch.setitem(
            api.app.dependency_overrides,
            get_verified_identity,
            lambda: VerifiedIdentity(
                issuer=issuer,
                subject=subject,
            ),
        )

    try:
        with TestClient(api.app) as client:

            # Authentication required
            assert client.get(url).status_code == 401

            sign_in("sales")

            key = {"request_key": str(uuid4())}

            # Unqualified lead must be rejected
            assert client.post(url, json=key).status_code == 409

            assert client.patch(
                lead_url,
                json={"status": "qualified"},
            ).status_code == 200

            # Create pending follow-up
            created = client.post(url, json=key)
            assert created.status_code == 201, created.text
            assert created.json()["status"] == "pending"

            followup_id = created.json()["id"]
            decision_url = f"{url}/{followup_id}/decision"

            # Retry must not create duplicates
            retry = client.post(url, json=key)
            assert retry.status_code == 200
            assert retry.json()["id"] == followup_id
            assert len(client.get(url).json()) == 1

            # Sales cannot approve
            assert client.post(
                decision_url,
                json={"decision": "approved"},
            ).status_code == 403

            # Caller cannot spoof approval status
            assert client.post(
                url,
                json={**key, "status": "approved"},
            ).status_code == 422

            sign_in("viewer")

            assert client.get(url).status_code == 200
            assert client.post(url, json=key).status_code == 403

            assert client.post(
                decision_url,
                json={"decision": "approved"},
            ).status_code == 403

            # Cross-organization isolation
            sign_in("outsider")

            assert client.get(url).status_code == 404

            assert client.post(
                decision_url,
                json={"decision": "approved"},
            ).status_code == 404

            wrong_url = (
                f"/v1/organizations/{other_id}"
                f"/leads/{lead_id}/followups"
            )

            assert client.get(wrong_url).status_code == 404

            # Owner can approve
            sign_in("owner")

            approved = client.post(
                decision_url,
                json={"decision": "approved"},
            )

            assert approved.status_code == 200, approved.text
            assert approved.json()["status"] == "approved"
            assert approved.json()["decided_at"] is not None

            # Decision cannot be changed afterward
            assert client.post(
                decision_url,
                json={"decision": "rejected"},
            ).status_code == 409

            # Administrator can reject
            sign_in("admin")

            second = client.post(
                url,
                json={"request_key": str(uuid4())},
            )

            assert second.status_code == 201

            second_id = second.json()["id"]

            rejected = client.post(
                f"{url}/{second_id}/decision",
                json={"decision": "rejected"},
            )

            assert rejected.status_code == 200
            assert rejected.json()["status"] == "rejected"

            # Expired requests cannot be approved
            third = client.post(
                url,
                json={"request_key": str(uuid4())},
            )

            assert third.status_code == 201

            expired_id = third.json()["id"]

            with Session(engine) as db:
                record = db.get(FollowupRequest, UUID(expired_id))
                record.expires_at = (
                    datetime.now(timezone.utc) - timedelta(hours=1)
                )
                db.commit()

            assert client.post(
                f"{url}/{expired_id}/decision",
                json={"decision": "approved"},
            ).status_code == 409

            # Verify saved identities and execution status
            with Session(engine) as db:
                approved_record = db.get(
                    FollowupRequest, UUID(followup_id)
                )

                rejected_record = db.get(
                    FollowupRequest, UUID(second_id)
                )

                assert approved_record.decided_by_identity_id == owner_id
                assert rejected_record.decided_by_identity_id == admin_id
                assert approved_record.executed_at is None

    finally:
        engine.dispose()