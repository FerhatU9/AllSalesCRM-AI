# Security policy

AllSales CRM is a local synthetic-data development prototype, not a production service.

## Supported usage

- **Fictional leads and synthetic policy documents only.** Do not store real customer information or expose services to the internet.
- The Streamlit demo uses a shared local development token, not a user login or tenant security boundary.
- Authenticated account/lead APIs verify signed OIDC access tokens and enforce organization membership; development Auth0 browser login and local PostgreSQL were demonstrated. The separate demo endpoints are not migrated to user OIDC.
- `ALLSALES_ENV` modes other than `local` are deliberately rejected. Preserve loopback bindings, including Docker Compose ports.
- The [draft follow-up feature](https://github.com/FerhatU9/AllSalesCRM-AI/pull/32) adds a separate Auth0 machine application with minimum `request:followups` scope and a separately granted `execute:followups` scope and an `automation` membership. Machines cannot modify leads or approve/reject follow-ups. A live local machine approval attempt returned HTTP 403; only verified owners/admins decide requests.
- The draft LangGraph recommendation endpoint is human-only and read-only. Only stored status and summary presence enter the graph; no raw customer text, model call, remote tracing or mutation tool is used. The execution endpoint requires the automation role, machine identity and `execute:followups` scope. Only the original requester may execute its own approved, unexpired request while the lead remains qualified; retries return the persisted execution result. Execution is database-only and does not authorize external delivery. Grant these client scopes only to the dedicated automation application where needed; do not grant anonymous access. Keep n8n manual, synthetic and unpublished. Do not grant anonymous access or elevate machine identities merely to bypass a failed authorization test.

## Credentials

Keep Dify app keys, database credentials, OIDC configuration and local development tokens in ignored `.env` or `web/.env.local` files, and automation secrets in the dedicated local n8n credential manager. Keep provider keys in Dify itself. Do not commit bearer tokens, credentials, workflow execution logs, real identifiers or private configuration. The committed workflow template omits saved credentials, request identifiers and pinned data and is inactive by default. Review changes before committing. If a credential is exposed, revoke and rotate it immediately; inspect commit history as well as current files.

## Vulnerability reporting

For non-sensitive issues, use the repository issue tracker. **Do not publish vulnerabilities, credentials, customer data, or exploit details in public issues.** Contact the repository owner privately through an appropriate secure channel for sensitive disclosures.

## Before deployment

Require independently validated authentication and authorization, database-level tenant isolation, audit integrity, rate limits, monitoring, threat modeling, backup recovery, privacy/retention controls, secrets rotation, vulnerability remediation and security assessment. Passing CI and local demonstrations do not establish production readiness.

Read the [architecture](docs/COMMERCIAL_ARCHITECTURE.md), [project limitations](docs/PROJECT_STATUS.md), [automation guide](docs/FOLLOWUP_AUTOMATION.md) and [technical engineering report](docs/AllSales_CRM_Technical_Report.pdf).
