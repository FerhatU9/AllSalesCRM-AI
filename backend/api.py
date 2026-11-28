"""Development-only FastAPI boundary for Dify-backed CRM policy answers.

IMPORTANT: Single shared API_APP_TOKEN is intentionally a local-development
mechanism; it is NOT a production user authentication solution.
"""
from contextlib import asynccontextmanager
import hmac
import logging
import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from allsales.dify_client import DifyClient, DifyError
from allsales.auth import VerifiedIdentity, get_verified_identity
from allsales.models import list_memberships
from allsales.storage import session_factory
from backend.lead_routes import router as leads_router
from backend.followup_routes import router as followups_router
from backend.qualification_routes import router as qualification_router
from allsales.lead_qualification import LeadInput, LeadDecision, evaluate_lead

load_dotenv()


def require_local_environment() -> None:
    """Reject staging or public deployment while using shared development credentials."""
    mode = os.getenv("ALLSALES_ENV", "").strip().lower()
    if mode != "local":
        raise RuntimeError(
            "AllSales CRM is local-only until user authentication, access control, "
            "and tenant isolation are implemented."
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    require_local_environment()
    yield


app = FastAPI(title="AllSales CRM Development API", version="0.8.0",
              docs_url="/docs", lifespan=lifespan)
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1500)
    # Local development identity only. Never use caller-supplied IDs as production tenant IDs.
    user_id: str = Field(min_length=8, max_length=120)
    conversation_id: str = Field(default="", max_length=120)
    model: Literal["gemini", "claude"] = "gemini"
    # Opt-in per request. Do not silently route user content to a second provider.
    allow_fallback: bool = False


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    source_documents: list[str]
    total_tokens: int | None = None
    model: Literal["gemini", "claude"]
    # Only included in JSON when fallback occurs; preserves existing response structure.
    requested_model: Literal["gemini", "claude"] | None = None
    fallback_used: bool | None = None


def require_dev_token(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("API_APP_TOKEN", "").strip()
    if not expected or expected == "replace-with-a-random-32-byte-token":
        raise HTTPException(status_code=503, detail="Development API token not configured")
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def provider_key(model: str) -> str:
    if model == "gemini":
        return (os.getenv("DIFY_GEMINI_API_KEY") or os.getenv("DIFY_API_KEY") or "").strip()
    if model == "claude":
        return os.getenv("DIFY_CLAUDE_API_KEY", "").strip()
    return ""


@app.get("/health")
def health():
    # Process health only; a good result is NOT proof that Dify or Gemini is healthy.
    return {"status": "ok", "version": "0.8.0"}


@app.get("/v1/models", dependencies=[Depends(require_dev_token)])
def models():
    return {"models": [name for name in ("gemini", "claude") if provider_key(name)]}


def alternate_model(model: Literal["gemini", "claude"]) -> Literal["gemini", "claude"]:
    return "claude" if model == "gemini" else "gemini"


def fallback_permitted(error: DifyError) -> bool:
    # Only transient service overloads: not bad keys, quota 429, timeouts,
    # retrieval errors, or invalid requests. An ambiguous POST timeout may
    # already have generated an answer, so don't repeat or switch automatically.
    return error.retryable and error.status in (400, 502, 503, 504)


@app.post("/v1/chat", response_model=ChatResponse, response_model_exclude_unset=True,
          dependencies=[Depends(require_dev_token)])
def chat(request: ChatRequest):
    key = provider_key(request.model)
    if not key:
        raise HTTPException(status_code=503, detail=f"{request.model} Dify app is not configured")
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question cannot be blank")
    base_url = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")
    actual_model = request.model
    switched = False
    try:
        response = DifyClient(api_key=key, base_url=base_url).ask(
            request.question, user_id=request.user_id, conversation_id=request.conversation_id
        )
    except DifyError as exc:
        backup_model = alternate_model(request.model)
        backup_key = provider_key(backup_model)
        if not (request.allow_fallback and fallback_permitted(exc) and backup_key):
            # Avoid returning secrets/provider payloads in the public error.
            raise HTTPException(status_code=503 if exc.retryable else 502, detail=str(exc)) from exc
        logger.warning("Transient model failure; opt-in fallback activated: %s -> %s, upstream status %s",
                       request.model, backup_model, exc.status)
        try:
            # CRITICAL: Always start a NEW Dify conversation in the other app.
            # A conversation ID from Gemini cannot be reused for Claude.
            response = DifyClient(api_key=backup_key, base_url=base_url).ask(
                request.question, user_id=request.user_id, conversation_id=""
            )
        except (DifyError, ValueError) as backup_exc:
            logger.warning("Backup provider did not complete request: %s", type(backup_exc).__name__)
            raise HTTPException(status_code=503,
                                detail="The selected model and backup are unavailable. Try later.") from backup_exc
        actual_model = backup_model
        switched = True
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Invalid backend Dify configuration") from exc
    fields = dict(
        answer=response.answer, conversation_id=response.conversation_id,
        source_documents=list(response.source_documents),
        total_tokens=response.tokens, model=actual_model,
    )
    if switched:
        fields.update(requested_model=request.model, fallback_used=True)
    return ChatResponse(**fields)


@app.post("/v1/leads/evaluate", response_model=LeadDecision,
          dependencies=[Depends(require_dev_token)], tags=["Lead decision workflow"])
def evaluate_sales_lead(lead: LeadInput):
    """Evaluate fictional input locally; no Dify calls, database writes or CRM actions."""
    return evaluate_lead(lead)


@app.get("/v1/account/organizations", tags=["Account"])
def account_organizations(identity: VerifiedIdentity = Depends(get_verified_identity)):
    """Return only organizations belonging to the cryptographically verified identity."""

    try:
        with session_factory()() as session:
            memberships = list_memberships(
                session, issuer=identity.issuer, subject=identity.subject
            )
            return {
                "organizations": [
                    {"id": str(organization.id), "name": organization.display_name,
                     "slug": organization.slug, "role": role}
                    for organization, role in memberships
                    if identity.allows_role(role)
                ]
            }
    except (SQLAlchemyError, RuntimeError, ValueError) as exc:
        logger.error("Account database is unavailable: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Account database is unavailable") from exc


# These endpoints require a verified OIDC identity; legacy demo routes remain separate.
app.include_router(leads_router)
app.include_router(followups_router)
app.include_router(qualification_router)