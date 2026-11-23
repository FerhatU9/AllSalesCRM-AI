"""Database isolation, role constraints and migration smoke tests."""

from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from allsales.models import Base, Identity, Membership, Organization, find_membership, list_memberships
from allsales.storage import database_url


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def add_company(session, *, slug, issuer, subject, role):
    organization = Organization(slug=slug, display_name=slug.title())
    identity = Identity(issuer=issuer, subject=subject)
    session.add_all([organization, identity])
    session.flush()
    session.add(Membership(organization_id=organization.id, identity_id=identity.id, role=role))
    session.commit()
    return organization


def test_membership_is_scoped_to_verified_identity_and_organization(session):
    a = add_company(session, slug="company-a", issuer="https://idp.example/", subject="person-a", role="sales")
    b = add_company(session, slug="company-b", issuer="https://idp.example/", subject="person-b", role="owner")

    assert find_membership(session, issuer="https://idp.example/", subject="person-a", organization_id=a.id).role == "sales"
    assert find_membership(session, issuer="https://idp.example/", subject="person-a", organization_id=b.id) is None
    assert find_membership(session, issuer="https://other.example/", subject="person-a", organization_id=a.id) is None
    assert [(o.slug, r) for o, r in list_memberships(session, issuer="https://idp.example/", subject="person-b")] == [("company-b", "owner")]
    assert find_membership(session, issuer="https://idp.example/", subject="person-a", organization_id=uuid4()) is None


def test_memberships_do_not_accept_unknown_role(session):
    organization = Organization(slug="acme", display_name="Acme")
    identity = Identity(issuer="https://idp.example/", subject="a")
    session.add_all([organization, identity])
    session.flush()
    session.add(Membership(organization_id=organization.id, identity_id=identity.id, role="superuser"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_issuer_and_subject_pair_is_unique(session):
    session.add(Identity(issuer="https://idp.example/", subject="a"))
    session.commit()
    session.add(Identity(issuer="https://idp.example/", subject="a"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_database_url_is_explicit(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        database_url()


def test_initial_migration_builds_schema(monkeypatch, tmp_path):
    db_path = tmp_path / "schema.sqlite"
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///" + str(db_path))
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine("sqlite+pysqlite:///" + str(db_path))
    try:
        assert {"identities", "organizations", "memberships"} <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
