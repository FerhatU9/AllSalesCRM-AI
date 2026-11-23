"""OIDC verification using locally generated RSA keys, no network requests."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from allsales import auth


@pytest.fixture
def oidc(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class LocalKey:
        def __init__(self, pub):
            self.key = pub

    class LocalJwks:
        def get_signing_key_from_jwt(self, _token):
            return LocalKey(key.public_key())

    monkeypatch.setattr(auth, "jwks_client", lambda _url: LocalJwks())
    monkeypatch.setenv("OIDC_ISSUER", "https://identity.example/")
    monkeypatch.setenv("OIDC_AUDIENCE", "allsales-api")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://identity.example/.well-known/jwks.json")

    def make_token(**overrides):
        now = datetime.now(timezone.utc)
        claims = dict(
            iss="https://identity.example/", aud="allsales-api", sub="test-user",
            iat=now, exp=now + timedelta(minutes=5)
        )
        claims.update(overrides)
        return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "local-test"})

    return make_token


def test_valid_signed_token_is_accepted(oidc):
    principal = auth.verify_access_token(oidc())
    assert (principal.issuer, principal.subject) == ("https://identity.example/", "test-user")


@pytest.mark.parametrize("changed", [
    {"iss": "https://evil.example/"},
    {"aud": "another-api"},
    {"exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
    {"sub": ""},
])
def test_invalid_claims_rejected(oidc, changed):
    with pytest.raises(HTTPException) as exc:
        auth.verify_access_token(oidc(**changed))
    assert exc.value.status_code == 401


def test_missing_provider_configuration_rejected(oidc, monkeypatch):
    monkeypatch.delenv("OIDC_AUDIENCE")
    with pytest.raises(HTTPException) as exc:
        auth.verify_access_token(oidc())
    assert exc.value.status_code == 503


def test_http_jwks_and_unrelated_host_rejected(oidc, monkeypatch):
    for url in ["http://identity.example/keys", "https://other.example/keys"]:
        monkeypatch.setenv("OIDC_JWKS_URL", url)
        with pytest.raises(HTTPException) as exc:
            auth.verify_access_token(oidc())
        assert exc.value.status_code == 503


def test_unsigned_token_rejected(oidc):
    token = jwt.encode(
        {"iss": "https://identity.example/", "aud": "allsales-api",
         "sub": "test-user", "iat": 100, "exp": 9999999999},
        key="", algorithm="none"
    )
    with pytest.raises(HTTPException) as exc:
        auth.verify_access_token(token)
    assert exc.value.status_code == 401


def test_no_empty_token():
    with pytest.raises(HTTPException) as exc:
        auth.verify_access_token("")
    assert exc.value.status_code == 401
