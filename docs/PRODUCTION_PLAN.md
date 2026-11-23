# AllSales CRM — Product development roadmap

This is the working plan for developing AllSales CRM into a product that can be operated by a business. **Do not use real customer data or deploy publicly while the security and operational gates remain incomplete.**

## How we will work

The developer builds and operates the product in VS Code, with the assistant guiding implementation. At each task, the assistant will:

1. Explain **what** will change, **why** it matters, and **which technology** is involved in plain language.
2. Identify the actual files and provide precise commands or edits, without presenting already-written code as a completed hands-on learning experience.
3. Have the developer run the application, inspect real outputs, and share failures or results.
4. Verify the result with automated tests **and** a working user journey before marking the task complete.
5. Keep work focused on the product: no artificial exercises, repeated setup, inflated progress claims, or unnecessary technologies.

The assistant may handle explicitly requested repository maintenance. Product development should remain hands-on, with the developer implementing and understanding meaningful changes. Credentials must stay in local environment files or a proper secrets manager, never in chat or GitHub.

## Verified starting point

| Component | Current evidence | Limitation |
| --- | --- | --- |
| Streamlit policy and qualification demo | Implemented Python UI and FastAPI demo endpoints; recorded synthetic scenarios | Shared local development token; not a customer-facing application |
| Gemini and Claude | Separate Dify Chatflows and recorded evaluation results | Knowledge-index reproduction and live service reliability are not proven |
| Next.js application | Landing page, Auth0 SDK integration and organization/lead pages; CI checks TypeScript and builds | No verified sign-in to a real Auth0 development tenant |
| Identity and permissions | FastAPI checks signed OIDC tokens and organization memberships; offline tests | Live login, invitations, account administration and end-to-end controls remain incomplete |
| Lead records | SQLAlchemy models and Alembic migrations; synthetic PostgreSQL integration tests | No production deployment, real CRM integration or row-level security |
| Lead activity | Activity records and owner/admin API, backed by automated tests | Not tamper-proof or a complete operational audit service |
| Containers | Local-only Dockerfile and Compose configuration | No verified fresh-machine container startup |

Tests validate only what they actually exercise. The public repository and successful CI builds do not establish commercial readiness.

## Phase 1 — End-to-end local user journey

**Goal:** Reproduce a working application using a real development account and fictional data.

- On the developer's machine: verify Python, Node.js, Docker and repository state.
- Start a dedicated local PostgreSQL database, apply Alembic migrations and provision a fictional organization using the existing local-only script.
- Configure an Auth0 development tenant and API audience without exposing credentials.
- Start FastAPI and Next.js, sign in, display permitted organizations, create/update a synthetic lead and confirm persistence after restart.
- Fix actual integration failures as they arise; record the steps needed to reproduce the result.

**Exit gate:** A complete browser-to-FastAPI-to-PostgreSQL journey works with a real development identity, and unauthorized access is denied. A successful TypeScript build alone does not count.

## Phase 2 — Complete the core sales workspace

**Goal:** Make the authenticated interface usable without manually calling APIs.

- Improve the lead list with search, filters and status management; add clear error and empty states.
- Integrate existing activity history in the interface with role-based access.
- Add controlled invitations and membership administration with explicit authorization.
- Define business requirements and validation for lead records, lifecycle and organization boundaries.
- Write browser-level tests for representative authorized and unauthorized user journeys.

**Exit gate:** A user can complete the core sales workflow through the browser, and another organization cannot read or modify their records.

## Phase 3 — Integrate the AI policy assistant safely

**Goal:** Bring the existing Gemini/Claude Dify workflows into an authenticated product without leaking company data.

- Connect the policy assistant to the verified identity and company workspace.
- Provision approved company-specific knowledge; enforce access before retrieval.
- Add trustworthy passage-level source references, evidence checks and abstention behavior.
- Compare models on reviewed cases, including misleading documents, prompt injection, unsupported questions, failure handling, latency and cost.
- Keep deterministic scoring and human policy approvals separate from model text.

**Exit gate:** An authorized account receives supported answers only from permitted material. Cross-company retrieval attempts and unsafe model actions fail automated tests.

## Phase 4 — Approved business workflows

**Goal:** Implement useful automation while keeping people in control.

- Start with a CRM sandbox integration and read-only synchronization; validate data mapping and consent.
- Introduce explicit approval before CRM updates, outreach, discount-related decisions or other side effects.
- Add idempotency, retry behavior, permissions and activity records to external actions.
- Evaluate **LangGraph** for controlled multi-step agent decisions and **n8n** for approved integrations only if a concrete workflow justifies them.
- The developer builds and runs each workflow, inspects inputs/outputs and explains how the components connect.

**Exit gate:** Real side effects cannot occur without the required authenticated human approval. Duplicate actions and failures are tested.

## Phase 5 — Production reliability and security

**Goal:** Prepare a controlled staging environment, not immediately a public multi-company service.

- Make dependency installs reproducible; review and test security updates.
- Add browser and integration tests, rate limits, secure authorization, company data isolation and appropriate database safeguards.
- Implement structured logging and tracing with redaction; evaluate OpenTelemetry and operational alerting.
- Test secret rotation, backups, restore, incident handling, migrations and rollback.
- Threat-model authentication, policy retrieval, LLM output and external actions; obtain an appropriate independent security review.
- Review privacy needs, customer consent, data retention, deletion and processor arrangements before processing real information.

**Exit gate:** Staging operations, authorization boundaries, recoverability and security acceptance criteria are demonstrated with evidence.

## Phase 6 — Controlled business pilot

**Goal:** Verify that one consenting company can use the product responsibly and obtains measurable value.

- Agree on permitted data, use cases, acceptance criteria, support and incident ownership.
- Onboard users and approved knowledge, with monitoring and human-approval controls.
- Measure answer quality, task completion, availability, customer feedback, cost and maintenance effort.
- Fix pilot issues and secure customer acceptance before considering broad multi-company rollout and billing.

**Exit gate:** A functioning, securely operated pilot with documented acceptance—not just deployed code.

## Technology decisions

**Already in the codebase:** Python, FastAPI, Streamlit, Next.js, TypeScript, SQLAlchemy, Alembic, PostgreSQL tests, Auth0 SDK integration, Dify, Gemini/Claude workflows, Docker configuration and GitHub Actions.

**Candidates for later stages, not implemented merely by listing them:** Playwright for browser journeys; OpenTelemetry for tracing; database row-level security; a managed cloud platform; LangGraph for justified agent workflows; n8n for approved integrations; background workers when actual asynchronous needs appear.

No Kubernetes, additional model framework, message broker, billing service or external CRM integration should be added without a verified requirement.

## Next hands-on task

**Phase 1, first step:** Inspect the local VS Code project and installed tools, then bring up a dedicated PostgreSQL development database. Only after the developer verifies the database and migrations should the project proceed to real Auth0 sign-in.

Start with [local onboarding](LOCAL_ONBOARDING.md) and [customer web setup](CUSTOMER_WEB.md). Review [current project status](PROJECT_STATUS.md) after each completed milestone.
