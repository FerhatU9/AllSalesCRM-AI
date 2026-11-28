"""Synthetic CRM qualification preview with an explicit optional Dify explanation."""
from __future__ import annotations

import logging
import os
from typing import Literal, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context
from pydantic import BaseModel, ConfigDict, Field

from allsales.dify_client import DifyClient, DifyError
from allsales.lead_explanation import build_explanation_prompt
from allsales.lead_qualification import LeadDecision, LeadFacts, LeadInput, evaluate_lead


Provider = Literal["none", "gemini", "claude"]
ExplanationStatus = Literal["not_requested", "withheld_incomplete", "unavailable", "complete"]
ExplanationFailure = Literal[
    "missing_configuration", "invalid_configuration", "access_rejected", "rate_limited",
    "provider_busy", "request_rejected", "timeout", "network", "invalid_response",
    "empty_answer", "unknown"
]
logger = logging.getLogger(__name__)


class PreviewFacts(LeadFacts):
    model_config = ConfigDict(extra="forbid")


class QualificationPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    facts: PreviewFacts
    provider: Provider = "none"
    confirm_synthetic: Literal[True]


class QualificationPreview(BaseModel):
    stored_status: Literal["new", "qualified"]
    decision: LeadDecision
    provider: Provider
    explanation_status: ExplanationStatus
    explanation_failure: ExplanationFailure | None = None
    explanation: str | None = None
    source_documents: list[str] = Field(default_factory=list)
    # The policy engine's exception-review flag is not approval to execute.
    followup_approval_required: Literal[True] = True
    automated_actions_taken: Literal[0] = 0


class PreviewState(TypedDict, total=False):
    lead: LeadInput
    provider: Provider
    decision: LeadDecision
    explanation_status: ExplanationStatus
    explanation_failure: ExplanationFailure
    explanation: str | None
    source_documents: list[str]


def evaluate_facts(state: PreviewState) -> dict:
    decision = evaluate_lead(state["lead"])
    if state["provider"] == "none":
        status: ExplanationStatus = "not_requested"
    elif decision.qualification_status != "Qualified":
        status = "withheld_incomplete"
    else:
        status = "unavailable"  # Overridden only on a successful model response.
    return {"decision": decision, "explanation_status": status}


def route_explanation(state: PreviewState) -> Literal["explain_policy", "finish"]:
    if state["provider"] != "none" and state["decision"].qualification_status == "Qualified":
        return "explain_policy"
    return "finish"


def _failure(provider: Provider, reason: ExplanationFailure) -> dict:
    # Log and return only our finite reason codes. Never raw Dify errors, keys,
    # provider messages, prompts or contact data.
    logger.warning("Qualification explanation unavailable: provider=%s reason=%s", provider, reason)
    return {"explanation_status": "unavailable", "explanation_failure": reason}


def _classify_error(error: DifyError) -> ExplanationFailure:
    if error.status in (401, 403):
        return "access_rejected"
    if error.status == 429:
        return "rate_limited"
    if error.status is not None:
        if error.status >= 500 or (error.status == 400 and error.retryable):
            return "provider_busy"
        return "request_rejected"
    # These codes are assigned locally by DifyClient to errors without an HTTP status.
    if error.code == "timeout":
        return "timeout"
    if error.code == "network":
        return "network"
    if error.code == "invalid_response":
        return "invalid_response"
    return "unknown"


def explain_policy(state: PreviewState) -> dict:
    provider = state["provider"]
    if provider == "gemini":
        key = os.getenv("DIFY_GEMINI_API_KEY", "").strip() or os.getenv("DIFY_API_KEY", "").strip()
    elif provider == "claude":
        key = os.getenv("DIFY_CLAUDE_API_KEY", "").strip()
    else:
        return _failure(provider, "invalid_configuration")
    if not key:
        return _failure(provider, "missing_configuration")

    decision = state["decision"]
    # Only the rule engine's fixed categories, numeric score and policy actions
    # cross the provider boundary. Do not send lead text, IDs or tokens.
    prompt = build_explanation_prompt(decision.model_dump())
    prompt += (
        "\nMandatory policy actions (explain; never approve or execute):\n"
        + "\n".join(f"- {action.action} ({action.handbook_section})" for action in decision.actions)
        + "\nAll recommendations require a separate human decision. No action has been taken."
    )
    try:
        reply = DifyClient(
            api_key=key, base_url=os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")
        ).ask(prompt, user_id=str(uuid4()), conversation_id="")
    except DifyError as error:
        return _failure(provider, _classify_error(error))
    except ValueError:
        return _failure(provider, "invalid_configuration")
    answer = reply.answer.strip()
    if not answer:
        return _failure(provider, "empty_answer")
    return {
        "explanation_status": "complete",
        "explanation": answer[:4000],
        "source_documents": [name[:200] for name in reply.source_documents[:10]],
    }


def build_qualification_graph():
    graph = StateGraph(PreviewState)
    graph.add_node("evaluate_facts", evaluate_facts)
    graph.add_node("explain_policy", explain_policy)
    graph.add_edge(START, "evaluate_facts")
    graph.add_conditional_edges(
        "evaluate_facts", route_explanation,
        {"explain_policy": "explain_policy", "finish": END},
    )
    graph.add_edge("explain_policy", END)
    return graph.compile()


_graph = build_qualification_graph()


def preview_qualification(
    lead: LeadInput, stored_status: Literal["new", "qualified"], provider: Provider
) -> QualificationPreview:
    # The submitted fictional data remains local and transient. No checkpointer,
    # graph persistence or remote tracing is configured.
    with tracing_context(enabled=False):
        result = _graph.invoke({"lead": lead, "provider": provider})
    return QualificationPreview(
        stored_status=stored_status,
        decision=result["decision"],
        provider=provider,
        explanation_status=result["explanation_status"],
        explanation_failure=result.get("explanation_failure"),
        explanation=result.get("explanation"),
        source_documents=result.get("source_documents", []),
    )
