# AllSales CRM AI — Production development plan

## Product vision
A real B2B sales-operations assistant: trustworthy internal policy Q&A, permission-aware document
search, lead qualification support, follow-up suggestions and supervisor-approved CRM actions.
Start as a **single-company private pilot** using synthetic information. Multi-tenant SaaS is later.

## Non-negotiable architecture
Streamlit (prototype) → FastAPI backend → a model-provider adapter → Dify Chatflow(s)
→ same versioned knowledge source and retrieval policy → Gemini or Claude → evidence-backed answer.
LangSmith observes development traces, model comparison and failures. Production observation must
use GDPR-conscious retention and redaction policies.

Claude and Gemini are BOTH core supported models. Gemini is not the only 'real' path.
We initially use two separate Dify Chatflows (one Gemini, one Claude) with identical RAG settings,
then abstract orchestration behind the FastAPI service. After the first comparative milestone,
add a hands-on direct Anthropic Python SDK exercise and a testable model adapter so we
understand both the low-code Dify integration and provider-level API engineering.

## Development milestones and verification gates

### Milestone 0 — Preserve and reproduce existing baseline
- Existing Dify Gemini workflow preserved and exported (workflow definition, KB recipe, model settings).
- Tests and local Streamlit→FastAPI→Dify calls pass for score 48 and 62.
- Development secrets in local .env only; do not push credentials.
**Exit gate:** clean-machine setup reproducible; no hidden manual configuration in README.

### Milestone 1 — CLAUDE INTEGRATION (not optional)
- Anthropic account/billing/controlled-spend setup; provider credentials stored in Dify.
- Official Anthropic provider installed; Claude Sonnet or available model selected.
- Dedicated Claude workflow published, same handbook/retrieval/prompt as Gemini.
- Separate Dify app API keys; FastAPI routes both; Streamlit lets users switch models.
**Exit gate:** 3 identical questions succeed with both models; failures are shown clearly; no secret disclosure.

### Milestone 2 — Fair dual-model RAG evaluation
- Versioned golden dataset expanded from 17 to include discount, abstention, jailbreak,
  ambiguous instructions, contradictory rules, and edge cases (goal: 50+ reviewed examples).
- Collect per-model correctness (human-reviewed), evidence hit quality, unsupported assertions,
  latency p50/p95, failures, and provider costs; compare apples to apples.
- Detect retrieval gaps (notably discount >10%), add source-span citations and policy version.
**Exit gate:** evaluation is repeatable with published before/after results and known remaining failures.

### Milestone 3 — Customer-facing core and permission-aware knowledge
- Versioned uploads with document owner approval; safe ingestion, parsing, indexing and deletion.
- Login with organizational identities; RBAC scopes documents per individual/role.
- Clear source links and uncertainty handling; do not invent policy or authorize discounts.
**Exit gate:** explicit deny tests ensure users cannot retrieve unapproved documents.

### Milestone 4 — Sales workflows (human-supervised)
- CRM sandbox read integration, lead summaries, deterministic priority-rule engine and recommended next actions.
- Human-approval workflow for edits, outreach, discount escalation and side effects;
  idempotency, activity logs and rollback where feasible.
**Exit gate:** tests prove no unauthorized CRM writes, duplicate emails or forbidden discounts.

### Milestone 5 — True production engineering
- Replace shared dev token with OIDC/SSO, per-user authorization, least privilege.
- Rate limiting, concurrency caps, quotas, provider circuit breakers, safe fallback & retries.
- Tenant isolation if pursuing SaaS; GDPR data mapping, vendor DPAs, deletion, retention,
  incident and security runbooks, logs without sensitive prompts by default.
- Docker, staging/prod environments, HTTPS, backup/restore tests, CI/CD, monitoring, alerts, SLOs.
**Exit gate:** threat modeling, penetration tests, load tests, recoverability and live telemetry verified.

### Milestone 6 — Commercial pilot / product validation
- Invite one consenting customer with authorized policies and representatives.
- Contract/terms/support/pricing, onboarding, user feedback and acceptance criteria.
- Conduct structured pilot and measure task resolution, failures, trust, and maintenance burden.
**Exit gate:** documented customer sign-off and sustainable operations before broader sales.

## Current implementation

The local Streamlit/FastAPI integration with Gemini and Claude through Dify was demonstrated, along with deterministic lead scoring and an optional policy explanation. Both sanitized Dify exports and the synthetic handbook are included, but fresh-workspace knowledge indexing has not been reproduced.

The earlier source package recorded 66 passing offline tests, 34 reviewed final model responses and five documented local UI scenarios. Further adversarial testing, passage-level citations, secure authentication, real CRM actions and production deployment remain incomplete.

## Scope boundaries
For the first pilot, avoid storing real customer private data and don't build autonomous high-impact actions.
Use source-grounded explanations and route approval decisions to human managers.
