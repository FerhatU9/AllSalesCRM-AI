from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from allsales.auth import VerifiedIdentity, get_verified_identity
from allsales.models import FollowupRequest, LeadRecord
from backend.lead_routes import (
    safe_session,
    scoped_membership,
    scoped_record,
)


router = APIRouter(
    prefix="/v1/organizations/{organization_id}/leads/{lead_id}/followups",
    tags=["Follow-ups"],
)


class FollowupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_key: UUID


class FollowupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lead_id: UUID
    request_key: UUID
    status: str
    created_at: datetime
    expires_at: datetime
    decided_at: datetime | None
    executed_at: datetime | None


@router.post("", response_model=FollowupOut, status_code=201)
def create_followup(
    organization_id: UUID,
    lead_id: UUID,
    payload: FollowupCreate,
    response: Response,
    identity: VerifiedIdentity = Depends(get_verified_identity),
    session=Depends(safe_session),
):
    membership = scoped_membership(
        session, identity, organization_id
    )

    if membership.role not in {
        "owner", "admin", "sales", "automation"
    }:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions",
        )

    lead = scoped_record(
        session, identity, organization_id, lead_id
    )

    requester_id = membership.identity_id

    def find_existing():
        return session.scalar(
            select(FollowupRequest).where(
                FollowupRequest.lead_id == lead_id,
                FollowupRequest.request_key == payload.request_key,
            )
        )

    def return_existing(existing):
        if existing.requested_by_identity_id != requester_id:
            raise HTTPException(
                status_code=409,
                detail="Request key already in use",
            )

        response.status_code = 200
        return existing

    existing = find_existing()

    if existing is not None:
        return return_existing(existing)

    if lead.status != "qualified":
        raise HTTPException(
            status_code=409,
            detail="Only qualified leads can request follow-ups",
        )

    followup = FollowupRequest(
        lead_id=lead_id,
        request_key=payload.request_key,
        requested_by_identity_id=requester_id,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    session.add(followup)

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = find_existing()

        if existing is not None:
            return return_existing(existing)

        raise

    session.refresh(followup)

    return followup


@router.get("", response_model=list[FollowupOut])
def list_followups(
    organization_id: UUID,
    lead_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    identity: VerifiedIdentity = Depends(get_verified_identity),
    session=Depends(safe_session),
):
    scoped_record(session, identity, organization_id, lead_id)

    return session.scalars(
        select(FollowupRequest)
        .where(FollowupRequest.lead_id == lead_id)
        .order_by(
            FollowupRequest.created_at.desc(),
            FollowupRequest.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()
class FollowupDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approved", "rejected"]


@router.post("/{followup_id}/decision", response_model=FollowupOut)
def decide_followup(
    organization_id: UUID,
    lead_id: UUID,
    followup_id: UUID,
    payload: FollowupDecision,
    identity: VerifiedIdentity = Depends(get_verified_identity),
    session=Depends(safe_session),
):
    membership = scoped_membership(
        session, identity, organization_id
    )

    if membership.role not in {"owner", "admin"}:
        raise HTTPException(
            status_code=403,
            detail="Only owners and administrators can decide follow-ups",
        )

    lead_status = session.scalar(
        select(LeadRecord.status)
        .where(
            LeadRecord.id == lead_id,
            LeadRecord.organization_id == organization_id,
        )
        .with_for_update()
    )

    if lead_status is None:
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )

    existing_id = session.scalar(
        select(FollowupRequest.id).where(
            FollowupRequest.id == followup_id,
            FollowupRequest.lead_id == lead_id,
        )
    )

    if existing_id is None:
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )

    if payload.decision == "approved" and lead_status != "qualified":
        raise HTTPException(
            status_code=409,
            detail="Only qualified leads can be approved for follow-up",
        )

    now = datetime.now(timezone.utc)

    statement = (
        update(FollowupRequest)
        .where(
            FollowupRequest.id == followup_id,
            FollowupRequest.lead_id == lead_id,
            FollowupRequest.status == "pending",
            FollowupRequest.expires_at > now,
        )
        .values(
            status=payload.decision,
            decided_by_identity_id=membership.identity_id,
            decided_at=now,
        )
        .returning(FollowupRequest)
    )

    followup = session.scalars(statement).one_or_none()

    if followup is None:
        raise HTTPException(
            status_code=409,
            detail="Follow-up has expired or has already been decided",
        )

    session.commit()
    session.refresh(followup)

    return followup


@router.post("/{followup_id}/execute", response_model=FollowupOut)
def execute_followup(
    organization_id: UUID,
    lead_id: UUID,
    followup_id: UUID,
    identity: VerifiedIdentity = Depends(get_verified_identity),
    session=Depends(safe_session),
):
    membership = scoped_membership(
        session, identity, organization_id
    )

    if (
        membership.role != "automation"
        or not identity.is_machine
        or "execute:followups" not in identity.scopes
    ):
        raise HTTPException(
            status_code=403,
            detail="Execution permission required",
        )

    lead_status = session.scalar(
        select(LeadRecord.status)
        .where(
            LeadRecord.id == lead_id,
            LeadRecord.organization_id == organization_id,
        )
        .with_for_update()
    )

    if lead_status is None:
        raise HTTPException(status_code=404, detail="Not found")

    followup = session.scalar(
        select(FollowupRequest).where(
            FollowupRequest.id == followup_id,
            FollowupRequest.lead_id == lead_id,
        )
    )

    if followup is None:
        raise HTTPException(status_code=404, detail="Not found")

    if followup.requested_by_identity_id != membership.identity_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot execute another identity's request",
        )

    if followup.status == "executed":
        return followup

    if lead_status != "qualified":
        raise HTTPException(
            status_code=409,
            detail="Lead is no longer qualified",
        )

    now = datetime.now(timezone.utc)

    executed_id = session.scalar(
        update(FollowupRequest)
        .where(
            FollowupRequest.id == followup_id,
            FollowupRequest.status == "approved",
            FollowupRequest.expires_at > now,
            FollowupRequest.decided_at.is_not(None),
            FollowupRequest.decided_by_identity_id.is_not(None),
        )
        .values(
            status="executed",
            executed_at=now,
        )
        .returning(FollowupRequest.id)
        .execution_options(synchronize_session=False)
    )

    if executed_id is None:
        raise HTTPException(
            status_code=409,
            detail="Follow-up is not approved or has expired",
        )

    session.commit()
    session.refresh(followup)

    return followup