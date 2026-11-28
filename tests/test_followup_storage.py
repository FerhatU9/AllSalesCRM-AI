from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from allsales.models import (
    FollowupRequest,
    Identity,
    LeadRecord,
    Organization,
)


def test_followup_storage(monkeypatch, tmp_path):
    url = "sqlite+pysqlite:///" + str(
        tmp_path / "followup_test.sqlite"
    )

    monkeypatch.setenv("DATABASE_URL", url)

    config = Config("alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(url)

    try:
        assert "followup_requests" in inspect(
            engine
        ).get_table_names()

        with Session(engine) as session:
            org = Organization(
                slug="test-company",
                display_name="Test Company",
            )

            identity = Identity(
                issuer="https://identity.example/",
                subject="test-user",
            )

            session.add_all([org, identity])
            session.flush()

            lead = LeadRecord(
                organization_id=org.id,
                created_by_identity_id=identity.id,
                company_name="Nordvale Technologies",
                summary="Fictional test lead",
                status="qualified",
            )

            session.add(lead)
            session.flush()

            lead_id = lead.id
            identity_id = identity.id
            request_key = uuid4()

            def make_request(key, status="pending"):
                return FollowupRequest(
                    lead_id=lead_id,
                    requested_by_identity_id=identity_id,
                    request_key=key,
                    status=status,
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(hours=24),
                )

            request = make_request(request_key)
            session.add(request)
            session.flush()

            request_id = request.id
            session.commit()

            saved = session.get(
                FollowupRequest, request_id
            )

            assert saved.status == "pending"

            # Reject duplicate request keys.
            session.add(make_request(request_key))

            with pytest.raises(IntegrityError):
                session.commit()

            session.rollback()

            # Reject invalid approval statuses.
            session.add(
                make_request(uuid4(), "invalid")
            )

            with pytest.raises(IntegrityError):
                session.commit()

            session.rollback()

    finally:
        engine.dispose()

    command.downgrade(config, "003_lead_audit")

    engine = create_engine(url)

    try:
        tables = inspect(engine).get_table_names()

        assert "followup_requests" not in tables
        assert "leads" in tables

    finally:
        engine.dispose()