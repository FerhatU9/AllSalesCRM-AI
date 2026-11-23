"""Account API isolation tests: verified identity cannot list another company's membership."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from allsales.auth import VerifiedIdentity, get_verified_identity
from allsales.models import Base, Identity, Membership, Organization
from backend import api


def test_account_orgs_requires_bearer_token(monkeypatch):
    monkeypatch.delenv("OIDC_ISSUER", raising=False)
    with TestClient(api.app) as client:
        response = client.get("/v1/account/organizations")
    assert response.status_code == 401


def test_account_organizations_are_identity_scoped(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with Session(engine) as session:
        company_a = Organization(slug="a", display_name="Company A")
        company_b = Organization(slug="b", display_name="Company B")
        person_a = Identity(issuer="https://idp.example/", subject="alice")
        person_b = Identity(issuer="https://idp.example/", subject="bob")
        session.add_all([company_a, company_b, person_a, person_b])
        session.flush()
        session.add_all([
            Membership(organization_id=company_a.id, identity_id=person_a.id, role="sales"),
            Membership(organization_id=company_b.id, identity_id=person_b.id, role="owner"),
        ])
        session.commit()

    monkeypatch.setattr(api, "session_factory", lambda: factory)
    try:
        with TestClient(api.app) as client:
            api.app.dependency_overrides[get_verified_identity] = (
                lambda: VerifiedIdentity(issuer="https://idp.example/", subject="alice")
            )
            resp_a = client.get("/v1/account/organizations")
            assert resp_a.status_code == 200
            assert [(c["slug"], c["role"]) for c in resp_a.json()["organizations"]] == [("a", "sales")]

            api.app.dependency_overrides[get_verified_identity] = (
                lambda: VerifiedIdentity(issuer="https://idp.example/", subject="bob")
            )
            resp_b = client.get("/v1/account/organizations")
            assert resp_b.status_code == 200
            assert [(c["slug"], c["role"]) for c in resp_b.json()["organizations"]] == [("b", "owner")]
    finally:
        api.app.dependency_overrides.clear()
        engine.dispose()


def test_account_database_failure_is_sanitized(monkeypatch):
    """An unavailable database must not leak connection strings or raise an HTTP 500."""
    from sqlalchemy.exc import OperationalError

    monkeypatch.setenv("ALLSALES_ENV", "local")
    def unavailable_database():
        raise OperationalError(
            "SELECT identities.subject FROM identities",
            {},
            Exception("sensitive-test-database-host"),
        )

    monkeypatch.setattr(api, "session_factory", unavailable_database)
    api.app.dependency_overrides[get_verified_identity] = (
        lambda: VerifiedIdentity(issuer="https://idp.example/", subject="alice")
    )
    try:
        with TestClient(api.app) as client:
            response = client.get("/v1/account/organizations")
        assert response.status_code == 503
        assert response.json() == {"detail": "Account database is unavailable"}
        assert "sensitive-test-database-host" not in response.text
    finally:
        api.app.dependency_overrides.clear()
