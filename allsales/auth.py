"""Verify OIDC access tokens with a configured HTTPS JWKS endpoint.

This module does not create users, issue tokens, or accept unsigned/dev tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from urllib.error import URLError
from urllib.parse import urlsplit

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str


def oidc_settings() -> tuple[str, str, str]:
    """Only permit explicit, same-host HTTPS identity-provider configuration."""

    issuer = os.environ.get("OIDC_ISSUER", "").strip()
    audience = os.environ.get("OIDC_AUDIENCE", "").strip()
    jwks_url = os.environ.get("OIDC_JWKS_URL", "").strip()
    if not issuer or not audience or not jwks_url:
        raise HTTPException(status_code=503, detail="OIDC provider is not configured")
    parsed_issuer, parsed_jwks = urlsplit(issuer), urlsplit(jwks_url)
    if (parsed_issuer.scheme != "https" or parsed_jwks.scheme != "https" or
            not parsed_issuer.hostname or not parsed_jwks.hostname or
            parsed_issuer.hostname != parsed_jwks.hostname or
            parsed_issuer.username or parsed_jwks.username or
            parsed_issuer.password or parsed_jwks.password or
            parsed_issuer.query or parsed_issuer.fragment or
            parsed_jwks.query or parsed_jwks.fragment):
        raise HTTPException(status_code=503, detail="OIDC provider configuration is invalid")
    return issuer, audience, jwks_url


@lru_cache(maxsize=8)
def jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300, timeout=5)


def verify_access_token(token: str) -> VerifiedIdentity:
    """Validate signature, expiry, issued-at, issuer and audience, never token-controlled algorithms."""

    if not token or len(token) > 8192:
        raise HTTPException(status_code=401, detail="Invalid access token")
    issuer, audience, url = oidc_settings()
    try:
        key = jwks_client(url).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=["RS256"],
            issuer=issuer, audience=audience,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            leeway=30,
        )
    except (jwt.PyJWKClientConnectionError, URLError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=503, detail="Identity provider is unavailable") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(status_code=401, detail="Invalid access token")
    return VerifiedIdentity(issuer=issuer, subject=subject)


def get_verified_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> VerifiedIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required")
    return verify_access_token(credentials.credentials)
