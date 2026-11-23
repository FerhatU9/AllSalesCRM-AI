"""Provision a synthetic organization and its owner for local development only.

This is intentionally an OFFLINE administrator CLI, not an exposed API endpoint.
Never use this script with customer data or on a remote database.
"""
from __future__ import annotations

import argparse
import os
import re

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from allsales.models import Identity, Membership, Organization
from allsales.storage import database_url, session_factory


def require_local_database(url: str) -> None:
    """Prevent accidental writes to remote or production-like databases."""
    if os.getenv("ALLSALES_ENV") != "local":
        raise ValueError("Explicit ALLSALES_ENV=local is required")
    parsed = make_url(url)
    if parsed.drivername != "postgresql+psycopg":
        raise ValueError("Provisioning requires a local PostgreSQL database")
    if parsed.host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Remote database connections are not allowed for provisioning")
    if not parsed.database or not re.fullmatch(r"allsales(?:_[a-z0-9_]+)?", parsed.database):
        raise ValueError("Use a dedicated allsales development database")


def provision_demo_workspace(
    session: Session,
    *,
    issuer: str,
    subject: str,
    slug: str,
    display_name: str,
) -> tuple[Organization, bool]:
    """Idempotently create demo owner membership; never change existing roles."""
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,62}", slug):
        raise ValueError("Organization slug must be 3-63 lower-case URL-safe characters")
    if not (1 <= len(display_name.strip()) <= 160):
        raise ValueError("Organization name must contain 1-160 characters")
    if not issuer.startswith("https://") or not issuer.endswith("/") or len(issuer) > 255:
        raise ValueError("Issuer must be the exact HTTPS OIDC issuer ending with '/'")
    if not subject or len(subject) > 255 or any(c.isspace() for c in subject):
        raise ValueError("Enter an exact nonempty Auth0 subject without whitespace")

    org = session.scalar(select(Organization).where(Organization.slug == slug))
    if org is None:
        org = Organization(slug=slug, display_name=display_name.strip())
        session.add(org)
        session.flush()

    identity = session.scalar(
        select(Identity).where(Identity.issuer == issuer, Identity.subject == subject)
    )
    if identity is None:
        identity = Identity(issuer=issuer, subject=subject)
        session.add(identity)
        session.flush()

    membership = session.get(Membership, (org.id, identity.id))
    if membership is None:
        session.add(Membership(organization_id=org.id, identity_id=identity.id, role="owner"))
        session.flush()
        return org, True

    # A repeat run must not escalate an existing viewer/sales role to owner.
    return org, False


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Provision a synthetic local development workspace")
    parser.add_argument("--subject", required=True, help="Exact Auth0 subject (sub) from your own development user")
    parser.add_argument("--org-slug", default="allsales-demo")
    parser.add_argument("--org-name", default="AllSales Demo")
    parser.add_argument("--confirm-synthetic", action="store_true", help="Required acknowledgement: fictional data only")
    args = parser.parse_args(argv)

    if not args.confirm_synthetic:
        parser.error("--confirm-synthetic is required; only fictional company data is allowed")
    url = database_url()
    require_local_database(url)
    issuer = os.getenv("OIDC_ISSUER", "").strip()
    if not issuer:
        parser.error("OIDC_ISSUER must match the provider's exact issuer")
    factory = session_factory(url)
    with factory.begin() as session:
        org, created = provision_demo_workspace(
            session,
            issuer=issuer,
            subject=args.subject,
            slug=args.org_slug,
            display_name=args.org_name,
        )
        print(f"Development workspace: {org.slug}")
        print("Owner membership created" if created else "Existing membership preserved")
    print("Local setup only. Do not enter customer information.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
