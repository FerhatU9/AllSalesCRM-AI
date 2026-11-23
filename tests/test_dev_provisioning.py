"""Local-only, repeatable development workspace provisioning."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from allsales.models import Base, Identity, Membership, Organization
from scripts.provision_demo_workspace import provision_demo_workspace, require_local_database


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_provisioner_is_idempotent_and_does_not_upgrade_existing_roles(session):
    data = dict(
        issuer="https://example.eu.auth0.com/",
        subject="auth0|test-subject",
        slug="allsales-demo",
        display_name="AllSales Demo",
    )
    org, created = provision_demo_workspace(session, **data)
    session.commit()
    assert created
    assert session.scalar(select(Organization).where(Organization.slug == "allsales-demo")).id == org.id
    identity = session.scalar(select(Identity))
    membership = session.get(Membership, (org.id, identity.id))
    assert membership.role == "owner"

    membership.role = "viewer"
    session.commit()
    same_org, created = provision_demo_workspace(session, **data)
    session.commit()
    assert same_org.id == org.id
    assert not created
    assert session.get(Membership, (org.id, identity.id)).role == "viewer"
    assert len(session.scalars(select(Organization)).all()) == 1


@pytest.mark.parametrize("slug", ["UPPER", "a", "-wrong", "bad slug", "a" * 64])
def test_reject_invalid_slug(session, slug):
    with pytest.raises(ValueError, match="slug"):
        provision_demo_workspace(
            session, issuer="https://idp.example/", subject="auth0|test",
            slug=slug, display_name="Synthetic",
        )


def test_remote_db_and_nonlocal_mode_are_rejected(monkeypatch):
    monkeypatch.setenv("ALLSALES_ENV", "local")
    for url in [
        "postgresql+psycopg://user:pw@db.prod.example/allsales",
        "postgresql+psycopg://user:pw@localhost/sales_prod",
        "sqlite+pysqlite:///:memory:",
    ]:
        with pytest.raises(ValueError):
            require_local_database(url)
    require_local_database("postgresql+psycopg://user:pw@127.0.0.1/allsales_dev")
    monkeypatch.setenv("ALLSALES_ENV", "production")
    with pytest.raises(ValueError, match="ALLSALES_ENV"):
        require_local_database("postgresql+psycopg://user:pw@localhost/allsales_dev")


def test_forged_or_empty_identity_is_rejected(session):
    for issuer, subject in [
        ("http://identity.example/", "auth0|a"),
        ("https://identity.example/", ""),
        ("https://identity.example/", "subject with spaces"),
    ]:
        with pytest.raises(ValueError):
            provision_demo_workspace(
                session, issuer=issuer, subject=subject,
                slug="allsales-demo", display_name="Demo"
            )
