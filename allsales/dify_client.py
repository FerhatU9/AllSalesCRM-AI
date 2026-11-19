"""Minimal Dify Chatflow API client with testable error handling.

Designed to keep network code separate from Streamlit. No credentials are logged.
"""
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit
import requests


@dataclass(frozen=True)
class ChatReply:
    answer: str
    conversation_id: str
    source_documents: tuple[str, ...]
    tokens: Optional[int] = None


class DifyError(Exception):
    def __init__(self, message: str, *, status: int | None = None,
                 code: str = "unknown", retryable: bool = False,
                 provider_message: str = ""):
        self.status = status
        self.code = code
        self.retryable = retryable
        # Diagnostic detail for local evaluation only; never show this in the public UI.
        self.provider_message = provider_message
        super().__init__(message)


def _read_error(response):
    try:
        body = response.json()
    except (ValueError, TypeError):
        body = {}
    if not isinstance(body, dict):
        body = {}
    code = str(body.get("code", "unknown"))[:80]
    raw_message = str(body.get("message", ""))
    raw = raw_message.lower()
    status = response.status_code
    # Dify sometimes wraps upstream Gemini overload errors as HTTP 400.
    overloaded = status == 400 and any(
        token in raw for token in ("high demand", "temporarily unavailable", "try again later")
    )
    if status in (401, 403):
        msg = "Dify authentication or access was rejected. Check the Dify app API key."
    elif status == 429:
        msg = "The service has reached a rate or usage limit. Check provider quota."
    elif overloaded or status in (502, 503, 504):
        msg = "The model service is temporarily unavailable or busy. Try again later."
    elif status >= 500:
        msg = "Dify experienced a server error."
    else:
        msg = f"Dify rejected the request (HTTP {status}, code: {code})."
    return DifyError(msg, status=status, code=code,
                     retryable=overloaded or status in (429, 502, 503, 504),
                     provider_message=raw_message)


class DifyClient:
    def __init__(self, api_key: str, base_url: str = "https://api.dify.ai/v1", session=None):
        if not api_key or not api_key.strip():
            raise ValueError("DIFY_API_KEY is missing")
        # Reject deceptive hosts such as http://localhost.attacker.example and
        # credentials embedded in URLs. Plain HTTP is allowed only for local testing.
        try:
            parsed = urlsplit(base_url)
            hostname = (parsed.hostname or "").lower()
            port = parsed.port  # Force validation of malformed ports.
            del port
        except ValueError as exc:
            raise ValueError("Invalid Dify base URL") from exc
        if (not hostname or parsed.username or parsed.password or parsed.query or
                parsed.fragment or any(c.isspace() for c in base_url) or
                (parsed.scheme != "https" and not (
                    parsed.scheme == "http" and hostname in {"localhost", "127.0.0.1", "::1"}
                ))):
            raise ValueError("Dify base URL must use HTTPS (except exact loopback hosts)")
        self._api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def ask(self, question: str, *, user_id: str, conversation_id: str = "") -> ChatReply:
        if not question.strip():
            raise ValueError("Question cannot be empty")
        try:
            response = self.session.post(
                f"{self.base_url}/chat-messages",
                headers={"Authorization": f"Bearer {self._api_key}",
                         "Content-Type": "application/json"},
                json={"inputs": {}, "query": question, "response_mode": "blocking",
                      "conversation_id": conversation_id, "user": user_id},
                timeout=(10, 90),
            )
        except requests.Timeout as exc:
            raise DifyError("The request timed out. Please try again later.", retryable=True) from exc
        except requests.RequestException as exc:
            raise DifyError("Could not contact Dify. Check your connection and service URL.") from exc

        if response.status_code >= 400:
            raise _read_error(response)
        try:
            payload = response.json()
        except (ValueError, TypeError) as exc:
            raise DifyError("Dify returned unreadable JSON.") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("answer"), str):
            raise DifyError("Dify response is missing an answer field.")
        metadata = payload.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        resources = metadata.get("retriever_resources") or []
        source_names = sorted({
            resource["document_name"]
            for resource in resources
            if isinstance(resource, dict) and isinstance(resource.get("document_name"), str)
            and resource["document_name"].strip()
        }) if isinstance(resources, list) else []
        usage = metadata.get("usage") or {}
        total_tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
        if not isinstance(total_tokens, int):
            total_tokens = None
        return ChatReply(
            answer=payload["answer"],
            conversation_id=str(payload.get("conversation_id") or conversation_id),
            source_documents=tuple(source_names),
            tokens=total_tokens,
        )
