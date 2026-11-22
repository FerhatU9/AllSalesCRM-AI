"""Identity and organization models. No customer data is stored here yet."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint, Uuid, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)


class Identity(Base):
    """External identity. The issuer+subject pair is globally unique."""

    __tablename__ = "identities"
    __table_args__ = (UniqueConstraint("issuer", "subject", name="uq_identity_issuer_subject"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)


class Membership(Base):
    """One user's role in one organization."""

    __tablename__ = "memberships"
    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'admin', 'sales', 'viewer')",
            name="ck_membership_role",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    identity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("identities.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)


class LeadRecord(Base):
    """Synthetic lead metadata with organization ownership.

    This schema is not approved to store actual customer information.
    """

    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("status IN ('new', 'qualified', 'archived')", name="ck_lead_status"),
        Index("ix_leads_org_id", "organization_id", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_identity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("identities.id", ondelete="RESTRICT"), nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="new")


def find_membership(
    session: Session, *, issuer: str, subject: str, organization_id: UUID
) -> Membership | None:
    """Look up membership from a *verified* issuer+subject, never a user-supplied identity."""

    statement = (
        select(Membership)
        .join(Identity, Membership.identity_id == Identity.id)
        .where(
            Identity.issuer == issuer,
            Identity.subject == subject,
            Membership.organization_id == organization_id,
        )
    )
    return session.scalar(statement)


def list_memberships(session: Session, *, issuer: str, subject: str) -> list[tuple[Organization, str]]:
    """Return organizations of an authenticated identity only."""

    statement = (
        select(Organization, Membership.role)
        .join(Membership, Membership.organization_id == Organization.id)
        .join(Identity, Membership.identity_id == Identity.id)
        .where(Identity.issuer == issuer, Identity.subject == subject)
        .order_by(Organization.slug)
    )
    return list(session.execute(statement).all())
