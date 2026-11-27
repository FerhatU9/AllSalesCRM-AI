import argparse
import re

from dotenv import load_dotenv
from sqlalchemy import select

from allsales.auth import oidc_settings
from allsales.models import Identity, Membership, Organization
from allsales.storage import database_url, session_factory
from scripts.provision_demo_workspace import require_local_database


def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-synthetic", action="store_true")
    args = parser.parse_args()

    if not args.confirm_synthetic:
        parser.error("--confirm-synthetic is required")

    url = database_url()
    require_local_database(url)

    issuer, _, _ = oidc_settings()

    client_id = input("Enter Automation Client ID: ").strip()

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", client_id):
        raise ValueError("Invalid Client ID")

    subject = client_id + "@clients"

    factory = session_factory(url)

    with factory.begin() as session:
        org = session.scalar(
            select(Organization).where(
                Organization.slug == "allsales-demo"
            )
        )

        if org is None:
            raise ValueError("Demo organization not found")

        identity = session.scalar(
            select(Identity).where(
                Identity.issuer == issuer,
                Identity.subject == subject,
            )
        )

        if identity is None:
            identity = Identity(issuer=issuer, subject=subject)
            session.add(identity)
            session.flush()

        memberships = session.scalars(
            select(Membership).where(
                Membership.identity_id == identity.id
            )
        ).all()

        for membership in memberships:
            if (
                membership.organization_id != org.id
                or membership.role != "automation"
            ):
                raise ValueError("Conflicting membership found")

        if not memberships:
            session.add(
                Membership(
                    organization_id=org.id,
                    identity_id=identity.id,
                    role="automation",
                )
            )

    print("Automation identity registered successfully.")
    print("Organization: allsales-demo")
    print("Role: automation")


if __name__ == "__main__":
    main()