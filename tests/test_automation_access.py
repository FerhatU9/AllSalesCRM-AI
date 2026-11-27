from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from allsales import auth
from allsales.models import Identity, Membership, Organization, LeadRecord
from backend import api, lead_routes


def test_automation_access(monkeypatch, tmp_path):
    issuer = "https://identity.example/"
    audience = "allsales-api"
    url = "sqlite+pysqlite:///" + str(tmp_path / "automation.sqlite")

    monkeypatch.setenv("ALLSALES_ENV", "local")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("OIDC_ISSUER", issuer)
    monkeypatch.setenv("OIDC_AUDIENCE", audience)
    monkeypatch.setenv(
        "OIDC_JWKS_URL", issuer + ".well-known/jwks.json"
    )

    command.upgrade(Config("alembic.ini"), "head")

    engine = create_engine(url)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    monkeypatch.setattr(api, "session_factory", lambda: factory)
    monkeypatch.setattr(lead_routes, "session_factory", lambda: factory)

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    monkeypatch.setattr(
        auth,
        "jwks_client",
        lambda _: SimpleNamespace(
            get_signing_key_from_jwt=lambda _: SimpleNamespace(
                key=key.public_key()
            )
        ),
    )

    def headers(subject, scope="", machine=False):
        now = datetime.now(timezone.utc)

        claims = {
            "iss": issuer,
            "aud": audience,
            "sub": subject,
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "scope": scope,
        }

        if machine:
            claims["gty"] = "client-credentials"

        token = jwt.encode(claims, key, algorithm="RS256")

        return {"Authorization": f"Bearer {token}"}

    try:
        with factory.begin() as db:
            org = Organization(slug="demo", display_name="Demo")
            other = Organization(slug="other", display_name="Other")

            bot = Identity(
                issuer=issuer,
                subject="n8n-test@clients",
            )

            owner = Identity(
                issuer=issuer,
                subject="owner-user",
            )

            db.add_all([org, other, bot, owner])
            db.flush()

            db.add_all([
                Membership(
                    organization_id=org.id,
                    identity_id=bot.id,
                    role="automation",
                ),
                Membership(
                    organization_id=org.id,
                    identity_id=owner.id,
                    role="owner",
                ),
            ])

            lead = LeadRecord(
                organization_id=org.id,
                created_by_identity_id=owner.id,
                company_name="Synthetic Company",
                summary="Automation test",
                status="qualified",
            )

            db.add(lead)
            db.flush()

            lead_url = f"/v1/organizations/{org.id}/leads/{lead.id}"
            other_url = f"/v1/organizations/{other.id}/leads"
            followup_url = lead_url + "/followups"

        bot_headers = headers(
            "n8n-test@clients",
            "request:followups",
            machine=True,
        )

        with TestClient(api.app) as client:

            # Automation can view its assigned organization.
            organizations = client.get(
                "/v1/account/organizations",
                headers=bot_headers,
            )

            assert organizations.status_code == 200
            assert organizations.json()["organizations"][0]["role"] == "automation"

            # Automation can create a pending request.
            payload = {"request_key": str(uuid4())}

            created = client.post(
                followup_url,
                json=payload,
                headers=bot_headers,
            )

            assert created.status_code == 201
            assert created.json()["status"] == "pending"

            decision_url = (
                followup_url
                + "/"
                + created.json()["id"]
                + "/decision"
            )

            # Automation cannot edit leads.
            assert client.patch(
                lead_url,
                json={"status": "archived"},
                headers=bot_headers,
            ).status_code == 403

            # Automation cannot approve its own request.
            assert client.post(
                decision_url,
                json={"decision": "approved"},
                headers=bot_headers,
            ).status_code == 403

            # Automation cannot access another organization.
            assert client.get(
                other_url,
                headers=bot_headers,
            ).status_code == 404

            # A machine token without the required scope is rejected.
            assert client.post(
                followup_url,
                json=payload,
                headers=headers("n8n-test@clients", machine=True),
            ).status_code == 403

            # A human owner can approve the request.
            approved = client.post(
                decision_url,
                json={"decision": "approved"},
                headers=headers("owner-user"),
            )

            assert approved.status_code == 200
            assert approved.json()["status"] == "approved"

            # Execution security tests
            executor_headers = headers(
                "n8n-test@clients",
                "request:followups execute:followups",
                machine=True,
            )

            execute_url = decision_url.replace(
                "/decision", "/execute"
            )

            # Request permission alone is insufficient.
            assert client.post(
                execute_url, headers=bot_headers
            ).status_code == 403

            # Human owners cannot use the automation endpoint.
            assert client.post(
                execute_url, headers=headers("owner-user")
            ).status_code == 403

            # Approved execution succeeds.
            executed = client.post(
                execute_url, headers=executor_headers
            )

            assert executed.status_code == 200, executed.text
            assert executed.json()["status"] == "executed"
            assert executed.json()["executed_at"] is not None

            # Retrying returns the same execution timestamp.
            retry = client.post(
                execute_url, headers=executor_headers
            )

            assert retry.status_code == 200
            assert retry.json() == executed.json()

            # Pending requests cannot execute.
            pending = client.post(
                followup_url,
                json={"request_key": str(uuid4())},
                headers=bot_headers,
            )

            assert pending.status_code == 201

            pending_url = (
                followup_url + "/" + pending.json()["id"]
            )

            assert client.post(
                pending_url + "/execute",
                headers=executor_headers,
            ).status_code == 409

            # Rejected requests cannot execute.
            rejected = client.post(
                pending_url + "/decision",
                json={"decision": "rejected"},
                headers=headers("owner-user"),
            )

            assert rejected.status_code == 200

            assert client.post(
                pending_url + "/execute",
                headers=executor_headers,
            ).status_code == 409

            # Expired approved requests cannot execute.
            from uuid import UUID
            from allsales.models import FollowupRequest

            expired = client.post(
                followup_url,
                json={"request_key": str(uuid4())},
                headers=bot_headers,
            )

            assert expired.status_code == 201

            expired_id = expired.json()["id"]
            expired_url = followup_url + "/" + expired_id

            assert client.post(
                expired_url + "/decision",
                json={"decision": "approved"},
                headers=headers("owner-user"),
            ).status_code == 200

            with factory.begin() as db:
                record = db.get(FollowupRequest, UUID(expired_id))
                record.expires_at = (
                    datetime.now(timezone.utc) - timedelta(hours=1)
                )

            assert client.post(
                expired_url + "/execute",
                headers=executor_headers,
            ).status_code == 409


    finally:
        engine.dispose()