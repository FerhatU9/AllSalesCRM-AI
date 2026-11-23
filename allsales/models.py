"""Identity and organization models. No customer data is stored here yet."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid, func, select
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



class LeadAuditEvent(Base):
    """Database-backed activity history for synthetic leads.

    Capture verified actor identity, affected fields and status changes.
    Do not store names, summaries, tokens or policy text in this table.
    """

    __tablename__ = "lead_audit_events"
    __table_args__ = (
        CheckConstraint("action IN ('created', 'updated')", name="ck_lead_audit_action"),
        Index("ix_lead_audit_org_lead", "organization_id", "lead_id", "sequence"),
    )

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), unique=True, nullable=False, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    lead_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("leads.id", ondelete="RESTRICT"), nullable=False
    )
    actor_identity_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("identities.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    changed_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(16))
    new_status: Mapped[str | None] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


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
