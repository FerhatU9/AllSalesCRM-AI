# Commercial architecture and delivery plan

## Product goal

AllSales CRM AI is intended to help a sales team search approved policies, qualify leads, understand next actions, and prepare human-reviewed CRM updates. The first commercial target is a **private pilot for one consenting company**, not an immediately public multi-company SaaS.

Today the application is a local development prototype using synthetic policies and records. The security features below are **proposals, not current capabilities**.

## Recommended architecture

| Layer | Current implementation | Commercial target |
| --- | --- | --- |
| Web experience | Local Streamlit | Authenticated Next.js/React application; keep Streamlit only for internal admin demonstrations |
| API | FastAPI with one shared development key | FastAPI with OIDC login validation, role/organization checks and per-user authorization |
| Business logic | Deterministic Python scoring and routing | Versioned rules, explicit approvals and policy ownership; keep LLM output advisory |
| AI orchestration | Dify Chatflows for Gemini and Claude | Keep Dify initially; introduce LangGraph only if controlled multi-step workflows justify it |
| Knowledge | One synthetic Dify knowledge base | Per-organization approved document ingestion, deletion, access checks, provenance and source-span citations |
| Data | No persistent CRM/customer records | PostgreSQL for tenant data, audit records and lead decisions; encrypted backup/recovery |
| Asynchronous work | Synchronous requests only | Background worker and queue (Redis + task worker), with idempotency and limits |
| Identity | Shared development API token | Managed OIDC identity provider, short-lived validated tokens, RBAC and least privilege |
| Deployment | Local process / loopback-only Docker Compose | Separate staging and production on managed EU cloud infrastructure, HTTPS, secrets manager, CI/CD |
| Telemetry | Developer-oriented tests and logs | Structured metrics/traces with redaction and retention controls, error tracking, alerts |
| Security | Local-only guardrails | Tenant isolation, dependency/code scanning, threat model, rate limits and external security review |
| Operations | Manual instructions | Health/readiness checks, migrations, incident response, backups, rollback and runbooks |

Technology choices are provisional. A managed cloud (Azure or AWS), PostgreSQL, OpenTelemetry and a hosted identity provider are credible starting options. Choose based on pilot customer requirements, data residency, cost and team capacity. Avoid deploying Kubernetes or an elaborate agent framework until operational complexity justifies them.

## Workstreams and acceptance criteria

### 1. Local reliability and reproducibility

- Development mode fails closed when a nonlocal deployment mode is requested.
- Application starts using documented local Docker Compose with ports bound to loopback.
- Unit tests and syntax validation pass on supported Python versions.
- Reproduction instructions and known external Dify dependencies are explicit.

**Gate:** fresh developer machine runs the synthetic app and local tests without undisclosed setup; do not call this production.

### 2. Identity, authorization and data protection

- Select an OIDC identity provider and validate issuer, audience, signature and token expiry.
- Assign each user a real identity and organization; derive tenant from verified identity, never from request text.
- Authorize every sensitive endpoint and knowledge retrieval by organization and role.
- Add unauthorized cross-tenant access tests and audit records with sensitive-field redaction.

**Gate:** no cross-company information exposure in automated integration and negative tests.

### 3. Persistent sales workflows

- Add PostgreSQL with migrations and defined entities for organizations, users, leads, decisions, approvals and audit events.
- Build lead create/read/update flows with validated permissions and an explicitly approved CRM sandbox adapter.
- Make external actions idempotent, record who approved them and support cancellation/rollback where feasible.
- Keep AI suggestions separate from business-rule decisions and approved actions.

**Gate:** negative tests prove a model response cannot silently update a CRM or authorize a discount.

### 4. Evidence-backed AI and evaluation

- Version customer knowledge, track consent and deletions, enforce document-level access before retrieval.
- Provide source-span references (not only document names); abstain when evidence is inadequate.
- Expand the evaluation set beyond 17 synthetic questions to include unsupported answers, retrieval attacks, prompt injection, consent and routing edge cases.
- Measure answer accuracy, citation quality, latency, provider outages and costs; require opt-in for cross-provider fallback.

**Gate:** reproducible evaluation and an agreed minimum quality threshold on customer-approved test scenarios.

### 5. Controlled deployment

- Deploy staging separately from production using HTTPS, secrets management, encryption, rate limits, network controls and a security review.
- Document data inventory, retention/deletion requests, processor agreements and applicable privacy/compliance obligations with professional legal review.
- Test backup restoration, incident response, key rotation and production rollback.

**Gate:** an accountable pilot owner signs off on the risks and live customer access.

### 6. Commercial pilot and scaling

- Recruit one authorized business, agree its acceptable uses, pricing and a paid pilot scope.
- Measure user adoption, error rates, supported-answer rates, time saved and actual value.
- Only after the pilot validates security and usefulness, add multi-tenant onboarding, billing and subscription management (for example, Stripe) where justified.

**Gate:** documented customer acceptance and sustainable service operations.

## GitHub practice

Use small pull requests with distinct outcomes. One tested feature or engineering improvement per commit is better than many cosmetic commits. Suggested commit progression:

1. `Enforce local-only runtime safeguards`
2. `Add reproducible local containers`
3. `Document commercial architecture and security boundaries`
4. `Implement authenticated user identity`
5. `Introduce database migrations and organization models`
6. `Enforce tenant-scoped lead access`
7. `Add audit logs and approval controls`
8. `Introduce secure CRM sandbox integration`

Only mark future work completed after implementation and validation. **Never rewrite history just to inflate the commit count.**

## Current limitations

- No real account login or per-user identity.
- No verified tenant-aware permission controls.
- No real CRM integration or persistent lead history.
- Dify configuration and model availability remain external dependencies.
- No real-company data processing has been approved or audited.
- No independent operational security, load or penetration testing.

A deployable application is not automatically commercial-ready. A paid pilot requires explicit product, security, privacy and operational acceptance criteria.
