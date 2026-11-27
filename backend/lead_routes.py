"""Authenticated organization-scoped synthetic lead endpoints.

Caller-supplied organization identifiers never determine authorization.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from allsales.auth import VerifiedIdentity, get_verified_identity
from allsales.models import Identity, LeadAuditEvent, LeadRecord, find_membership
from allsales.storage import session_factory


router = APIRouter(prefix="/v1/organizations/{organization_id}/leads", tags=["Leads"])

WRITE_ROLES = frozenset({"owner", "admin", "sales"})


class LeadCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=500)


class LeadUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=160)
    summary: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, pattern="^(new|qualified|archived)$")


class LeadView(BaseModel):
    id: UUID
    organization_id: UUID
    company_name: str
    summary: str
    status: str

    model_config = {"from_attributes": True}


def scoped_membership(session, identity: VerifiedIdentity, org_id: UUID, *, write=False):
    membership = find_membership(
        session,
        issuer=identity.issuer,
        subject=identity.subject,
        organization_id=org_id,
    )

    if membership is None:
        raise HTTPException(status_code=404, detail="Not found")

    if not identity.allows_role(membership.role):
        raise HTTPException(
            status_code=403,
            detail="Identity is not authorized for this role",
        )

    if write and membership.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions",
        )

    return membership


def safe_session():
    try:
        factory = session_factory()
        with factory() as session:
            yield session
    except (SQLAlchemyError, RuntimeError, ValueError) as exc:
        # No database internals in API responses.
        raise HTTPException(status_code=503, detail="Account database unavailable") from exc


@router.get("", response_model=list[LeadView])
def list_leads(
    organization_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    identity: VerifiedIdentity = Depends(get_verified_identity),
    session=Depends(safe_session),
):
    scoped_membership(session, identity, organization_id)
    records = session.scalars(
        select(LeadRecord)
        .where(LeadRecord.organization_id == organization_id)
        .order_by(LeadRecord.id)
        .limit(limit).offset(offset)
    ).all()
    return records


@router.post("", response_model=LeadView, status_code=201)
def create_lead(
    organization_id: UUID,
    payload: LeadCreate,
    identity: VerifiedIdentity = Depends(get_verified_identity),
    session=Depends(safe_session),
):
    scoped_membership(session, identity, organization_id, write=True)
    actor = session.scalar(
        select(Identity).where(Identity.issuer == identity.issuer, Identity.subject == identity.subject)
    )
    if actor is None:
        raise HTTPException(status_code=404, detail="Not found")
    record = LeadRecord(
        organization_id=organization_id, created_by_identity_id=actor.id,
        company_name=payload.company_name.strip(), summary=payload.summary,
        status="new",
    )
    if not record.company_name:
        raise HTTPException(status_code=422, detail="Company name must not be blank")
    session.add(record)
    session.flush()
    session.add(LeadAuditEvent(
        organization_id=organization_id,
        lead_id=record.id,
        actor_identity_id=actor.id,
        action="created",
        changed_fields=["company_name", "summary", "status"],
        previous_status=None,
        new_status="new",
    ))
    session.commit()
    session.refresh(record)
    return record


def scoped_record(session, identity, organization_id, lead_id, *, write=False):
    scoped_membership(session, identity, organization_id, write=write)
    record = session.scalar(
        select(LeadRecord).where(
            LeadRecord.id == lead_id,
            LeadRecord.organization_id == organization_id,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Not found")
    return record


@router.get("/{lead_id}", response_model=LeadView)
def get_lead(
    organization_id: UUID,
    lead_id: UUID,
    identity: VerifiedIdentity = Depends(get_verified_identity),
    session=Depends(safe_session),
):
    return scoped_record(session, identity, organization_id, lead_id)


@router.patch("/{lead_id}", response_model=LeadView)
def update_lead(
    organization_id: UUID,
    lead_id: UUID,
    payload: LeadUpdate,
    identity: VerifiedIdentity = Depends(get_verified_identity),
    session=Depends(safe_session),
):
    record = scoped_record(session, identity, organization_id, lead_id, write=True)
    fields = payload.model_dump(exclude_unset=True)
    if any(value is None for value in fields.values()):
        raise HTTPException(status_code=422, detail="Null updates are not supported")
    if "company_name" in fields:
        fields["company_name"] = fields["company_name"].strip()
        if not fields["company_name"]:
            raise HTTPException(status_code=422, detail="Company name must not be blank")
    changed = {key: value for key, value in fields.items() if getattr(record, key) != value}
    if changed:
        previous_status = record.status
        for key, value in changed.items():
            setattr(record, key, value)
        actor = session.scalar(select(Identity).where(
            Identity.issuer == identity.issuer,
            Identity.subject == identity.subject,
        ))
        if actor is None:
            raise HTTPException(status_code=404, detail="Not found")
        session.add(LeadAuditEvent(
            organization_id=organization_id,
            lead_id=record.id,
            actor_identity_id=actor.id,
            action="updated",
            changed_fields=sorted(changed),
            previous_status=previous_status if "status" in changed else None,
            new_status=record.status if "status" in changed else None,
        ))
        session.commit()
    session.refresh(record)
    return record


class AuditEventView(BaseModel):
    id: UUID
    lead_id: UUID
    organization_id: UUID
    actor_identity_id: UUID
    action: str
    changed_fields: list[str]
    previous_status: str | None
    new_status: str | None
    occurred_at: datetime

    model_config = {"from_attributes": True}


@router.get("/{lead_id}/activity", response_model=list[AuditEventView])
def lead_activity(
    organization_id: UUID,
    lead_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    identity: VerifiedIdentity = Depends(get_verified_identity),
    session=Depends(safe_session),
):
    """Return recorded lead changes to authorized organization admins only."""
    membership = scoped_membership(session, identity, organization_id)
    if membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    record = session.scalar(select(LeadRecord.id).where(
        LeadRecord.id == lead_id,
        LeadRecord.organization_id == organization_id,
    ))
    if record is None:
        raise HTTPException(status_code=404, detail="Not found")
    return session.scalars(
        select(LeadAuditEvent).where(
            LeadAuditEvent.organization_id == organization_id,
            LeadAuditEvent.lead_id == lead_id,
        ).order_by(LeadAuditEvent.sequence)
        .limit(limit).offset(offset)
    ).all()
