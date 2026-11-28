"""Tenant-scoped synthetic qualification snapshots and active-lead dashboard."""

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID
import hmac

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError

from allsales.auth import VerifiedIdentity, get_verified_identity
from allsales.lead_qualification import LeadDecision, LeadInput, evaluate_lead
from allsales.models import LeadRecord, QualificationRecord
from allsales.qualification_graph import PreviewFacts
from allsales.qualification_snapshot import review_digest
from backend.lead_routes import safe_session, scoped_membership, scoped_record

router = APIRouter(prefix="/v1/organizations/{organization_id}", tags=["Qualification"])


class SaveQualification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    facts: PreviewFacts
    confirm_synthetic: Literal[True]
    request_key: UUID
    review_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class QualificationSnapshot(BaseModel):
    id: UUID
    lead_id: UUID
    stored_status: Literal["new", "qualified"]
    decision: LeadDecision
    created_at: datetime


def _view(record: QualificationRecord) -> QualificationSnapshot:
    timestamp = record.created_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return QualificationSnapshot(
        id=record.id, lead_id=record.lead_id, stored_status=record.stored_status,
        decision=LeadDecision.model_validate(record.decision), created_at=timestamp,
    )


def _human_member(session, identity, org_id, *, write=False):
    member = scoped_membership(session, identity, org_id, write=write)
    if identity.is_machine:
        raise HTTPException(status_code=403, detail="Human identity required")
    return member


@router.post("/leads/{lead_id}/qualifications", response_model=QualificationSnapshot, status_code=201)
def save_qualification(
    organization_id: UUID, lead_id: UUID, payload: SaveQualification, response: Response,
    identity: VerifiedIdentity = Depends(get_verified_identity), session=Depends(safe_session),
):
    member = _human_member(session, identity, organization_id, write=True)
    # PostgreSQL serializes concurrent saves for this lead; also reads its current
    # status under a row lock so a concurrent archive cannot race this decision.
    lead = session.scalar(select(LeadRecord).where(
        LeadRecord.id == lead_id, LeadRecord.organization_id == organization_id,
    ).with_for_update())
    if lead is None:
        raise HTTPException(status_code=404, detail="Not found")
    actor = member.identity_id

    def find_existing():
        return session.scalar(select(QualificationRecord).where(
            QualificationRecord.lead_id == lead_id,
            QualificationRecord.request_key == payload.request_key,
        ))

    def existing_view(existing):
        digest = review_digest(lead_id, existing.stored_status, existing.decision)
        if existing.actor_identity_id != actor or not hmac.compare_digest(digest, payload.review_digest):
            raise HTTPException(status_code=409, detail="Request key already in use")
        response.status_code = 200
        return _view(existing)

    response.headers["Cache-Control"] = "no-store"
    existing = find_existing()
    if existing is not None:
        return existing_view(existing)
    if lead.status not in {"new", "qualified"}:
        raise HTTPException(status_code=409, detail="Archived leads cannot be evaluated")
    # Recompute; browser cannot submit a score, tier, AI answer or actor identity.
    decision = evaluate_lead(LeadInput(
        company_name=lead.company_name, stated_use_case=lead.summary, **payload.facts.model_dump(),
    )).model_dump(mode="json")
    digest = review_digest(lead_id, lead.status, decision)
    if not hmac.compare_digest(digest, payload.review_digest):
        raise HTTPException(status_code=409, detail="Decision changed; preview again before saving")
    record = QualificationRecord(
        lead_id=lead_id, actor_identity_id=actor, request_key=payload.request_key,
        stored_status=lead.status, decision=decision,
    )
    session.add(record)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = find_existing()
        if existing is not None:
            return existing_view(existing)
        raise
    session.refresh(record)
    return _view(record)


@router.get("/leads/{lead_id}/qualifications", response_model=list[QualificationSnapshot])
def qualification_history(
    organization_id: UUID, lead_id: UUID, response: Response,
    limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
    identity: VerifiedIdentity = Depends(get_verified_identity), session=Depends(safe_session),
):
    _human_member(session, identity, organization_id)
    scoped_record(session, identity, organization_id, lead_id)
    response.headers["Cache-Control"] = "no-store"
    records = session.scalars(select(QualificationRecord).where(
        QualificationRecord.lead_id == lead_id,
    ).order_by(QualificationRecord.sequence.desc()).limit(limit).offset(offset))
    return [_view(row) for row in records]


class DashboardLead(BaseModel):
    id: UUID
    company_name: str
    status: Literal["new", "qualified"]
    latest: QualificationSnapshot | None


class QualificationDashboard(BaseModel):
    total_active: int
    evaluated: int
    not_evaluated: int
    needs_clarification: int
    tier_a: int
    tier_b: int
    tier_c: int
    leads: list[DashboardLead]


@router.get("/qualification-dashboard", response_model=QualificationDashboard)
def qualification_dashboard(
    organization_id: UUID, response: Response,
    limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
    identity: VerifiedIdentity = Depends(get_verified_identity), session=Depends(safe_session),
):
    _human_member(session, identity, organization_id)
    response.headers["Cache-Control"] = "no-store"
    active = (LeadRecord.organization_id == organization_id, LeadRecord.status.in_(("new", "qualified")))
    latest = (
        select(QualificationRecord.lead_id, func.max(QualificationRecord.sequence).label("sequence"))
        .join(LeadRecord, LeadRecord.id == QualificationRecord.lead_id)
        .where(*active).group_by(QualificationRecord.lead_id).subquery()
    )

    def scoped_latest(statement):
        return (
            statement.select_from(LeadRecord)
            .outerjoin(latest, latest.c.lead_id == LeadRecord.id)
            .outerjoin(QualificationRecord, QualificationRecord.sequence == latest.c.sequence)
            .where(*active)
        )

    tier = QualificationRecord.decision["priority_tier"].as_string()
    count_statement = scoped_latest(select(
        func.count(LeadRecord.id), func.count(QualificationRecord.sequence),
        *(func.coalesce(func.sum(case((tier == value, 1), else_=0)), 0) for value in ("A", "B", "C")),
    ))
    total, evaluated, a, b, c = session.execute(count_statement).one()
    rows = session.execute(scoped_latest(select(LeadRecord, QualificationRecord))
        .order_by(LeadRecord.company_name, LeadRecord.id).limit(limit).offset(offset)).all()
    return QualificationDashboard(
        total_active=total, evaluated=evaluated, not_evaluated=total - evaluated,
        needs_clarification=evaluated - a - b - c, tier_a=a, tier_b=b, tier_c=c,
        leads=[DashboardLead(
            id=lead.id, company_name=lead.company_name, status=lead.status,
            latest=_view(snapshot) if snapshot else None,
        ) for lead, snapshot in rows],
    )
