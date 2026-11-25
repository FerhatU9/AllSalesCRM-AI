# AllSales CRM — Product development roadmap

This roadmap guides AllSales CRM from its **local, synthetic-data prototype** to a secure, usable B2B sales application. The first commercial goal is a controlled pilot with one consenting organization, not a premature public SaaS launch.

**Current safety boundary:** Use fictional leads and synthetic company policies only. Do not expose the development FastAPI/Streamlit services publicly, upload customer data, enable unattended outreach, or remove `ALLSALES_ENV=local` safeguards until the security and operational requirements are demonstrated.

## Development approach

The developer performs the product implementation in VS Code with guided explanations of **what the technology does, why it is used and how to validate it**. Repository maintenance may be done through reviewed commits. For each milestone, record real output, run automated tests and demonstrate the working user journey. Do not label a milestone complete solely because code was committed or CI passed.

## Starting state — implemented vs. demonstrated

| Capability | Current evidence | What remains |
| --- | --- | --- |
| Policy assistant and lead qualification | Streamlit, FastAPI, deterministic rules, Dify Gemini/Claude workflows, synthetic evaluations | Integrate safely into the authenticated customer workspace |
| Web interface | Next.js/TypeScript workspace, Auth0 SDK, lead screens, passing build | Authenticated browser automation and independent security validation |
| Security and permissions | Signed OIDC token checks, organization membership validation, regression tests | Live viewer-token write rejection, account administration and defense in depth |
| Data storage | SQLAlchemy, Alembic, lead activity and disposable PostgreSQL integration tests | Database restart/restore validation and production data protection |
| Developer operations | Docker configuration, CI, reproducible npm lockfile, Playwright unauthenticated smoke tests, CodeQL | Fresh-machine onboarding, authenticated browser tests, backups and monitoring |
| n8n, LangGraph, Azure hosting | Selected for future features | **Not yet integrated into this product** |

## Milestone 1 — End-to-end CRM foundation (local demonstration complete)

Developer-observed login/logout, organization membership, lead creation/update, persistence across sessions, unassigned user restriction and viewer UI checks are recorded in [project status](PROJECT_STATUS.md). Offline tests passed. Direct live-token negative writes and confirmation of the dedicated PostgreSQL CI check remain follow-up security evidence before deployment.

**Technology:** Next.js, Auth0, FastAPI, SQLAlchemy, Alembic, PostgreSQL and Docker.

**Business goal:** An authorized person can create and manage fictional company leads through one usable browser interface.

Implementation order:

1. Inspect the developer's current Git branch, local changes and installed Python, Node.js and Docker tools. Do not reset or overwrite local changes.
2. Run a dedicated **loopback-only** PostgreSQL development database. Use existing migrations and verify schema creation and connectivity.
3. Set up an Auth0 development **Regular Web Application** and API audience. Keep all credentials in ignored local environment files.
4. Provision one fictional organization for the exact verified identity, using the existing development-only provisioning script.
5. Start FastAPI and Next.js; sign in using a real development account. Create a synthetic lead, update it, sign out/in and restart the services to verify persistence.
6. Verify an unassigned identity and a viewer cannot perform prohibited actions. Record failures and the exact reproducible commands in the onboarding guide.

**Exit gate:** Browser → Auth0 → FastAPI → PostgreSQL works end-to-end; persistence and authorization tests pass. Offline unit tests and a frontend build alone do not satisfy this gate.

## Milestone 2 — n8n automation with explicit approval (current)

Use a separate local instance and volume; see [n8n setup](N8N_SETUP.md).

**Technology:** n8n in a **local test environment**, authenticated FastAPI webhook integration and the existing organization permissions.

**Business goal:** A sales user prepares a lead follow-up reminder, reviews its details and explicitly approves execution.

Implementation order:

1. Run n8n locally; leave all schedules and external integrations inactive by default.
2. Specify the follow-up request, permissions and audit record in FastAPI. Do not let the frontend or n8n infer authorization from a user-supplied organization ID.
3. Build a minimal synthetic-data webhook workflow with a manual trigger or approved request. Do not embed customer details, bearer tokens or API credentials in workflow files or logs.
4. Enforce approval and an idempotency key on the backend before an action can execute. Start with a local test notification or database event—**no real email, outreach or CRM update**.
5. Test approved, rejected, expired, duplicate and failed executions, including retries and safe reporting.

**Exit gate:** One authorized, approved test action executes exactly once. Rejections, missing approvals and unauthorized requests do not produce side effects. Workflow executions are auditable.

## Milestone 3 — Usable CRM workspace

**Technology:** Next.js, FastAPI, PostgreSQL and Playwright.

**Business goal:** Sales representatives and managers can manage their pipeline without API tools.

Implement filtering and searching leads, a usable status pipeline, activity history with role restrictions, clear failure and empty states, controlled invitations and organization membership administration. Improve accessibility and responsive UI without weakening backend checks.

**Exit gate:** Real browser tests show authorized users completing core lead tasks, viewers remaining read-only and cross-organization requests being denied.

## Milestone 4 — LangGraph-powered, evidence-based sales intelligence

**Technology:** LangGraph, the existing Dify/Gemini/Claude work, approved document retrieval and AI evaluation. Consider pgvector only if search requirements justify it.

**Business goal:** Provide grounded, explainable sales-policy assistance and useful lead recommendations while keeping humans in control.

First secure organization-specific source retrieval and credible passage-level citations. Add abstention on unsupported answers and measure answer quality, leakage, prompt-injection resistance, latency and cost. Then use LangGraph for a **specific multi-step workflow**: gather permitted context, evaluate deterministic lead rules, draft a recommendation and request approval before invoking n8n. Never treat model text as permission to access data or perform side effects.

**Exit gate:** Traceable results reference authorized evidence. Cross-company retrieval is denied; unsupported answers abstain and unapproved actions do not execute. Failures and cost are measured.

## Milestone 5 — Azure staging and production engineering

**Candidates:** Azure Container Apps, Azure Database for PostgreSQL Flexible Server, Azure Key Vault, Azure Monitor / Application Insights and GitHub Actions.

**Business goal:** Deploy an operable, secured staging environment for fictional data—not an internet-facing multi-tenant production launch.

Before provisioning, select a subscription, region and estimated budget; set spending alerts, cost caps where supported and a documented shutdown plan. Containerize the actual Next.js/FastAPI services, configure network boundaries and managed secrets, add structured observability and alerts, and verify migration, rollback, backup and restore procedures. Review security and privacy implications, especially data location and vendor agreements.

**Exit gate:** Repeatable staging deployment, recoverability, monitoring and access controls are demonstrated, with bounded and understood cloud costs.

## Milestone 6 — Controlled commercial pilot

Complete vulnerability remediation, security assessment, privacy and retention/deletion controls, support procedures and service monitoring. Agree in advance with a consenting pilot customer on permitted data, use cases, measurement and incident ownership. Measure workflow completion, grounded-answer quality, time saved, reliability, model spend and customer feedback.

**Exit gate:** A real business accepts the limited pilot against documented requirements. General SaaS sales, billing and broader rollout are separate decisions after this milestone.

## Technology priorities

| Technology | Decision | Reason |
| --- | --- | --- |
| PostgreSQL, Docker, Next.js, Auth0 and FastAPI | Maintain the demonstrated local foundation | Deliver a working core CRM |
| n8n | **Current:** first new integration | Practical, human-approved sales automation |
| Playwright | Already present; expand coverage during the workspace work | Browser-level proof of behavior |
| LangGraph | After the core workflow and n8n approval boundary work | Multi-step AI orchestration with measurable value |
| Azure | After local behavior and safeguards are verified | Staging operations, secure infrastructure and cloud skills |
| Kubernetes, Kafka, complex microservices | Defer | Complexity not justified by current scale |

## Immediate hands-on task

Start the isolated n8n instance using [n8n setup](N8N_SETUP.md). Verify the editor opens before building a manual synthetic workflow. Do not publish schedules, connect real email or bypass FastAPI authorization. No additional AI orchestration or cloud deployment is needed for this step.
