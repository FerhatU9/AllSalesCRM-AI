"""Stable review fingerprint for a server-computed synthetic decision.

This is a stale-preview guard, not a signature or authorization token.
"""
from hashlib import sha256
import json
from uuid import UUID


def review_digest(lead_id: UUID, stored_status: str, decision: dict) -> str:
    canonical = json.dumps(
        {"lead_id": str(lead_id), "stored_status": stored_status, "decision": decision},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()
