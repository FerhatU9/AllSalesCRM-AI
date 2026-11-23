"""Lead persistence and database migration, without any external services."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from allsales.models import Base, Identity, LeadRecord, Organization


def test_leads_belong_to_an_organization():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        person = Identity(issuer="https://identity.example/", subject="alice")
        a = Organization(slug="company-a", display_name="Company A")
        b = Organization(slug="company-b", display_name="Company B")
        db.add_all([a,b,person])
        db.flush()
        db.add_all([
            LeadRecord(organization_id=a.id, created_by_identity_id=person.id,
                       company_name="Demo A", summary="Example", status="new"),
            LeadRecord(organization_id=b.id, created_by_identity_id=person.id,
                       company_name="Demo B", summary="Example", status="archived"),
        ])
        db.commit()
        a_leads = db.scalars(select(LeadRecord).where(LeadRecord.organization_id == a.id)).all()
        assert [x.company_name for x in a_leads] == ["Demo A"]
        b_leads = db.scalars(select(LeadRecord).where(LeadRecord.organization_id == b.id)).all()
        assert [x.company_name for x in b_leads] == ["Demo B"]
        db.add(LeadRecord(organization_id=a.id, created_by_identity_id=person.id,
                          company_name="Invalid", summary="Example", status="invalid"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    engine.dispose()


def test_lead_migration_can_upgrade_and_downgrade(monkeypatch, tmp_path):
    db_path = tmp_path / "lead_schema.sqlite"
    url = "sqlite+pysqlite:///" + str(db_path)
    monkeypatch.setenv("DATABASE_URL", url)
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        assert "leads" in inspector.get_table_names()
        assert {"organization_id", "created_by_identity_id", "company_name", "summary", "status"} <= {
            col["name"] for col in inspector.get_columns("leads")
        }
    finally:
        engine.dispose()
    command.downgrade(cfg, "001_identity_schema")
    engine = create_engine(url)
    try:
        assert "leads" not in inspect(engine).get_table_names()
        assert "organizations" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
