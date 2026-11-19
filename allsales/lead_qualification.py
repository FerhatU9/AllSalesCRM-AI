"""Deterministic decision support from the SYNTHETIC AllSales CRM handbook v1.0.

No LLM requests, outbound network calls, data persistence, or CRM mutations.
This is an educational demo, NOT a replacement for a real sales policy engine.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field


EU_COUNTRIES = (
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark",
    "Estonia", "Finland", "France", "Germany", "Greece", "Hungary", "Ireland",
    "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands",
    "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden",
)
UK_COUNTRIES = ("United Kingdom",)
# Explicitly recognized example non-EU/UK countries. Unknown names trigger review,
# not an automatic out-of-market determination.
OTHER_COUNTRIES = (
    "Australia", "Canada", "India", "Japan", "Norway", "Switzerland",
    "Türkiye", "United States",
)
COUNTRY_OPTIONS = ("Not provided",) + tuple(sorted(EU_COUNTRIES + UK_COUNTRIES + OTHER_COUNTRIES))


class LeadInput(BaseModel):
    company_name: str = Field(default="", max_length=120)
    country: str = Field(default="", max_length=80)
    employee_count: int | None = Field(default=None, ge=0, le=1000000)
    industry: str = Field(default="", max_length=120)
    contact_name: str = Field(default="", max_length=120)
    business_email: str = Field(default="", max_length=254)
    stated_use_case: str = Field(default="", max_length=600)
    lead_source: str = Field(default="", max_length=120)
    consent_status: Literal["Opted In", "Opted Out", "Unknown", "Missing"] = "Missing"
    assigned_owner: str = Field(default="", max_length=120)
    decision_days: int | None = Field(default=None, ge=0, le=3650)
    decision_authority: Literal["final", "influencer", "none", "unknown"] = "unknown"
    engagement: Literal["demo_booked", "email_replied", "none", "unknown"] = "unknown"
    proposed_discount_pct: float | None = Field(default=None, ge=0, le=100)
    custom_contract_terms: bool = False
    suspected_security_incident: bool = False
    urgent_service_outage: bool = False


class Action(BaseModel):
    action: str
    owner: str
    deadline: str | None = None
    handbook_section: str


class LeadDecision(BaseModel):
    qualification_status: Literal["Incomplete", "Needs clarification", "Qualified"]
    missing_fields: list[str]
    unclear_scoring_factors: list[str]
    market_region: Literal["EU", "UK", "Outside target regions", "Unverified"]
    score_components: dict[str, int | None]
    provisional_score: int | None
    priority_tier: Literal["A", "B", "C"] | None
    recommended_routing: str
    queue_status: str
    follow_up_target: str | None
    human_review_required: bool
    actions: list[Action]
    explanations: list[str]
    source_sections: list[str]
    policy_version: str = "Synthetic handbook v1.0"
    automated_actions_taken: int = 0


def _normal(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).casefold()
    return "".join(ch for ch in folded if not unicodedata.combining(ch)).strip()


_COUNTRIES_EU = {_normal(x) for x in EU_COUNTRIES} | {"czech republic"}
_COUNTRIES_UK = {_normal(x) for x in UK_COUNTRIES} | {"uk", "great britain"}
_COUNTRIES_OTHER = {_normal(x) for x in OTHER_COUNTRIES} | {"turkey", "usa", "united states of america"}


def market_region(country: str) -> Literal["EU", "UK", "Outside target regions", "Unverified"]:
    c = _normal(country)
    if c in _COUNTRIES_EU:
        return "EU"
    if c in _COUNTRIES_UK:
        return "UK"
    if c in _COUNTRIES_OTHER:
        return "Outside target regions"
    return "Unverified"


def _valid_business_email(email: str) -> bool:
    # Basic formatting check for this demo; NOT deliverability verification.
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()))


def _preferred(industry: str) -> bool:
    return _normal(industry) in {
        "saas", "software-as-a-service", "software as a service",
        "professional services", "retail"
    }


def evaluate_lead(lead: LeadInput) -> LeadDecision:
    """Evaluate one fictional lead. Never assign a tier to an incomplete record."""
    missing: list[str] = []
    required_strings = {
        "company_name": lead.company_name,
        "country": lead.country,
        "industry": lead.industry,
        "contact_name": lead.contact_name,
        "stated_use_case": lead.stated_use_case,
        "lead_source": lead.lead_source,
        "assigned_owner": lead.assigned_owner,
    }
    missing.extend(k for k, v in required_strings.items() if not v.strip())
    if lead.employee_count is None:
        missing.append("employee_count")
    if not _valid_business_email(lead.business_email):
        missing.append("business_email")
    if lead.consent_status == "Missing":
        missing.append("consent_status")

    region = market_region(lead.country)
    components: dict[str, int | None] = {
        "company_fit": None, "purchase_urgency": None,
        "decision_authority": None, "engagement": None,
    }
    if region != "Unverified" and lead.employee_count is not None and lead.industry.strip():
        fit_criteria = sum((
            10 <= lead.employee_count <= 500,
            region in ("EU", "UK"),
            _preferred(lead.industry),
        ))
        components["company_fit"] = 40 if fit_criteria == 3 else 20 if fit_criteria == 2 else 0
    if lead.decision_days is not None:
        components["purchase_urgency"] = 25 if lead.decision_days <= 30 else 10 if lead.decision_days <= 90 else 0
    components["decision_authority"] = {
        "final": 20, "influencer": 10, "none": 0, "unknown": None,
    }[lead.decision_authority]
    components["engagement"] = {
        "demo_booked": 15, "email_replied": 5, "none": 0, "unknown": None,
    }[lead.engagement]

    unclear = [key for key, value in components.items() if value is None]
    score = sum(v for v in components.values() if v is not None) if not unclear else None
    status: Literal["Incomplete", "Needs clarification", "Qualified"] = (
        "Incomplete" if missing else "Needs clarification" if unclear else "Qualified"
    )
    priority: Literal["A", "B", "C"] | None = None
    if status == "Qualified" and score is not None:
        priority = "A" if score >= 75 else "B" if score >= 50 else "C"

    explanations = [
        "Section 3: Company fit, urgency, authority and engagement are deterministic scoring factors."
    ]
    if missing:
        explanations.append("Section 2: Mandatory CRM fields must be completed before qualification; no priority tier is assigned.")
    if unclear:
        explanations.append("Sections 3 and 8: Unknown scoring inputs must be clarified; do not invent missing points.")
    if region == "Unverified" and lead.country.strip():
        explanations.append("Section 1: Country cannot be classified from the supported demo list; a sales manager must verify eligibility.")
    if region == "Outside target regions":
        explanations.append("Sections 1 and 5: Outside EU/UK requires a market-eligibility review regardless of score; not automatic rejection.")
    if lead.employee_count is not None and lead.employee_count > 500:
        explanations.append("Sections 1 and 5: More than 500 employees requires Enterprise Sales Manager special review.")
    if lead.employee_count is not None and lead.employee_count < 10:
        explanations.append("Section 1: Fewer than 10 employees normally belong in nurture rather than the active sales queue.")

    reviews: list[str] = []
    actions: list[Action] = []
    sections: set[str] = {"2", "3", "4", "5"}
    if missing:
        actions.append(Action(action="Complete missing CRM fields before qualification or active queue assignment.",
                              owner="Assigned owner", handbook_section="2"))
    if unclear:
        actions.append(Action(action="Clarify scoring inputs and ask the sales manager before treating the lead as Priority A.",
                              owner="Assigned owner / Sales Manager", handbook_section="8"))
        sections.add("8")
        reviews.append("Scoring clarification")
    if region == "Unverified" and lead.country.strip():
        reviews.append("Country and market eligibility verification")
        actions.append(Action(action="Verify country and market eligibility before assigning a sales territory.",
                              owner="Sales Manager", handbook_section="1"))
        sections.add("1")
    if region == "Outside target regions":
        reviews.append("Outside-market eligibility")
        actions.append(Action(action="Review market eligibility; do not automatically reject the lead.",
                              owner="Sales Manager", handbook_section="1"))
        sections.add("1")
    if lead.employee_count is not None and lead.employee_count > 500:
        reviews.append("Enterprise special review")
        actions.append(Action(action="Perform special review for organization above 500 employees.",
                              owner="Enterprise Sales Manager", handbook_section="5"))
        sections.add("1")

    if region == "Outside target regions":
        route = "Sales Manager — market-eligibility review"
    elif region == "Unverified":
        route = "Sales Manager — region verification" if lead.country.strip() else "Pending country"
    elif lead.employee_count is None:
        route = "Pending employee count"
    elif lead.employee_count > 500:
        route = "Enterprise Sales Manager — special review"
    elif lead.employee_count < 10:
        route = "Nurture queue"
    elif lead.employee_count <= 200:
        route = "SMB Sales Team"
    else:
        route = "Enterprise Sales Team"

    routing_reviews_needed = (bool(unclear) or region in ("Outside target regions", "Unverified")
                              or (lead.employee_count is not None and lead.employee_count > 500))
    if status != "Qualified":
        queue = "On hold — not qualified for active sales queue"
    elif routing_reviews_needed:
        queue = "On hold — human routing review required"
    elif lead.employee_count is not None and lead.employee_count < 10:
        queue = "Nurture queue"
    elif priority == "C":
        queue = "Nurture queue"
    else:
        queue = "Eligible for active sales queue (recommendation only)"

    target: str | None = None
    if priority == "A":
        target = "First personalized contact within 1 business day of qualification"
    elif priority == "B":
        target = "First personalized contact within 3 business days of qualification"
    elif priority == "C":
        target = "Nurture queue; review after 30 calendar days"

    if status == "Qualified" and target:
        actions.append(Action(action=target, owner="Assigned owner",
                              deadline=target.split(" within ")[-1] if priority in ("A", "B") else "30 calendar days",
                              handbook_section="4"))
        if priority == "C":
            explanations.append("Section 4: Priority C uses nurture and a 30-day review, not urgent outreach.")
    if lead.consent_status == "Opted Out":
        actions.append(Action(action="Do not send marketing campaigns to this contact.",
                              owner="Marketing / Sales", handbook_section="7"))
        sections.add("7")
    elif lead.consent_status == "Unknown":
        actions.append(Action(action="Do not treat Unknown consent as permission to send marketing.",
                              owner="Marketing / Sales", handbook_section="7"))
        sections.add("7")
    if lead.proposed_discount_pct is not None:
        sections.add("6")
        if lead.proposed_discount_pct > 10:
            reviews.append("Written discount approval")
            actions.append(Action(action=f"Obtain written sales manager approval BEFORE offering {lead.proposed_discount_pct:g}% discount.",
                                  owner="Sales Manager", handbook_section="6"))
        else:
            explanations.append("Section 6: Up to 10% discount can be proposed without manager approval.")
    if lead.custom_contract_terms:
        reviews.append("Custom contract terms")
        actions.append(Action(action="Refer requested custom contract terms to Sales Manager; make no unauthorized commitment.",
                              owner="Sales Manager", handbook_section="6"))
        sections.add("6")
    if lead.suspected_security_incident:
        actions.insert(0, Action(action="Escalate suspected security incident; this takes priority over routine follow-up.",
                                 owner="Security Team", deadline="Same business day", handbook_section="8"))
        sections.add("8")
    if lead.urgent_service_outage:
        actions.insert(0, Action(action="Escalate existing customer's urgent service outage; do not promise resolution time.",
                                 owner="Customer Support", deadline="Within 4 business hours", handbook_section="8"))
        sections.add("8")
    if lead.suspected_security_incident or lead.urgent_service_outage:
        explanations.append("Section 8: Internal escalation deadlines are not resolution guarantees; escalation precedes ordinary sales follow-up.")

    return LeadDecision(
        qualification_status=status,
        missing_fields=missing,
        unclear_scoring_factors=unclear,
        market_region=region,
        score_components=components,
        provisional_score=score,
        priority_tier=priority,
        recommended_routing=route,
        queue_status=queue,
        follow_up_target=target,
        human_review_required=bool(reviews),
        actions=actions,
        explanations=explanations,
        source_sections=[f"Section {s}" for s in sorted(sections, key=int)],
    )
