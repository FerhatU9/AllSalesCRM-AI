"""Local, read-only LangGraph workflow for reviewing a stored CRM lead.

The graph receives only a database-derived status and a context-presence flag.
It never receives raw lead text, tokens, identities, URLs, or a mutation tool.
It cannot calculate a qualification score from the smaller CRM record.
"""
from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context
from pydantic import BaseModel, ConfigDict


LeadStatus = Literal["new", "qualified", "archived"]
RecommendationAction = Literal[
    "review_followup", "complete_qualification", "review_missing_context", "no_action"
]


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lead_status: LeadStatus
    recommended_action: RecommendationAction
    title: str
    reason: str
    review_steps: list[str]
    human_review_required: Literal[True] = True
    automated_actions_taken: Literal[0] = 0
    mode: Literal["local_rules"] = "local_rules"


class RecommendationState(TypedDict, total=False):
    status: LeadStatus
    has_summary: bool
    action: RecommendationAction
    recommendation: Recommendation


def assess_lead(state: RecommendationState) -> dict:
    """Choose the route from stored facts, never from model instructions."""
    if state["status"] == "archived":
        action = "no_action"
    elif state["status"] == "new":
        action = "complete_qualification"
    elif not state["has_summary"]:
        action = "review_missing_context"
    else:
        action = "review_followup"
    return {"action": action}


def route_review(state: RecommendationState) -> Literal["draft_followup", "draft_hold"]:
    return "draft_followup" if state["action"] == "review_followup" else "draft_hold"


def draft_followup(state: RecommendationState) -> dict:
    return {"recommendation": Recommendation(
        lead_status=state["status"],
        recommended_action="review_followup",
        title="Review a follow-up opportunity",
        reason="The CRM marks this lead as qualified and a summary is present. "
               "This is not a recalculated qualification score or approval.",
        review_steps=[
            "Verify the summary, contact consent, decision-maker and timing.",
            "Confirm that a follow-up is appropriate using the sales policy.",
            "Use the existing human approval workflow if a follow-up is needed.",
        ],
    )}


def draft_hold(state: RecommendationState) -> dict:
    action = state["action"]
    if action == "no_action":
        title = "No follow-up recommended"
        reason = "The CRM marks this lead as archived."
        steps = ["Leave this lead archived unless an authorized human changes its status."]
    elif action == "complete_qualification":
        title = "Complete lead qualification"
        reason = "The stored status is new, not qualified."
        steps = ["Collect missing qualification facts.", "Have an authorized human review the lead."]
    else:
        title = "Review missing context"
        reason = "The lead is marked qualified but has no meaningful summary."
        steps = ["Add and verify a summary before considering a follow-up."]
    return {"recommendation": Recommendation(
        lead_status=state["status"], recommended_action=action,
        title=title, reason=reason, review_steps=steps,
    )}


def build_recommendation_graph():
    builder = StateGraph(RecommendationState)
    builder.add_node("assess_lead", assess_lead)
    builder.add_node("draft_followup", draft_followup)
    builder.add_node("draft_hold", draft_hold)
    builder.add_edge(START, "assess_lead")
    builder.add_conditional_edges(
        "assess_lead", route_review,
        {"draft_followup": "draft_followup", "draft_hold": "draft_hold"},
    )
    builder.add_edge("draft_followup", END)
    builder.add_edge("draft_hold", END)
    return builder.compile()


_graph = build_recommendation_graph()


def recommend_lead(status: LeadStatus, has_summary: bool) -> Recommendation:
    if status not in {"new", "qualified", "archived"}:
        raise ValueError("Unsupported lead status")
    # Keep this local even if LangSmith tracing is enabled elsewhere.
    with tracing_context(enabled=False):
        result = _graph.invoke({"status": status, "has_summary": has_summary})
    return Recommendation.model_validate(result["recommendation"])
