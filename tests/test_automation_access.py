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

    finally:
        engine.dispose()