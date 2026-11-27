# AllSales CRM

**AI-assisted sales policy intelligence · Deterministic lead qualification · Organization-scoped CRM · Human-approved automation**

AllSales CRM is a local-development software project exploring how B2B sales teams can retrieve policy information, qualify leads consistently, manage a shared pipeline, and request follow-up actions without giving an AI model or automation service unrestricted authority.

> **Development status — November 27, 2026:** Synthetic-data prototype, not a deployed SaaS or a production CRM. The authenticated CRM foundation is on `main`; the locally demonstrated, machine-to-machine follow-up approval workflow is under review in [draft PR #32](https://github.com/FerhatU9/AllSalesCRM-AI/pull/32). No external outreach or execution endpoint is enabled.

## Start here

| Resource | Description |
| --- | --- |
| [**Technical engineering report (PDF)**](docs/AllSales_CRM_Technical_Report.pdf) | Nine-page architecture, security, API, evaluation, n8n integration and release-readiness report |
| [Follow-up automation guide](docs/FOLLOWUP_AUTOMATION.md) | Reproduce the locally demonstrated Auth0 → n8n → CRM workflow on the feature branch |
| [Project status and limitations](docs/PROJECT_STATUS.md) | Demonstrated behavior, automated checks and open gates |
| [Product roadmap](docs/PRODUCTION_PLAN.md) | Hands-on implementation milestones toward a controlled pilot |
| [Public website source](site/) | Static product showcase; it does not run the CRM backend or provide live customer access |

## Capabilities

| Capability | Development evidence | Boundary |
| --- | --- | --- |
| Sales-policy Q&A | Gemini and Claude through separate Dify Chatflows | Synthetic policy knowledge; external Dify configuration required |
| Lead qualification | Deterministic Python scoring, priority, team routing and recommendations | Model explanations cannot override scores or approve actions |
| Authenticated workspace | Next.js, live development Auth0 login/logout, synthetic leads | Not self-service customer onboarding |
| Lead API and storage | FastAPI membership checks, PostgreSQL, SQLAlchemy, Alembic and lead activity history | Application-level tenant isolation; additional database and security controls required |
| Human-approved follow-ups | Draft feature: pending requests, idempotent creation, owner/admin decisions | Approval is not execution |
| n8n integration | Draft feature: restricted Auth0 machine token, lead filtering, request creation, status verification | Local manual workflow, synthetic data only |
| Quality engineering | Python, TypeScript, Chromium smoke tests, PostgreSQL integration, CodeQL | Not an independent security assessment |

## Architecture

There are two deliberately separate local development paths.

```mermaid
flowchart LR
    subgraph Demo["Policy and scoring demonstration"]
        ST[Streamlit] --> DEV[FastAPI demo API]
        DEV --> RULES[Deterministic Python rules]
        DEV --> DIFY[Dify Chatflows]
        DIFY --> MODELS[Gemini / Claude]
    end
    subgraph CRM["Authenticated CRM and draft automation"]
        WEB[Next.js workspace] --> API[FastAPI account and lead API]
        API --> AUTH[OIDC validation and membership checks]
        AUTH --> DB[(PostgreSQL)]
        N8N[n8n manual workflow] -.-> M2M[Auth0 machine token]
        M2M -.-> API
        API -.-> FU[Follow-up approval API]
        FU -.-> DB
    end
```

Solid connections represent the CRM foundation; dotted connections represent the draft follow-up integration. The legacy Streamlit demo uses a shared local development token. The authenticated workspace uses provider-issued access tokens; all authorization decisions are made in FastAPI, not the browser or n8n. The authenticated workspace does not yet expose the Dify policy assistant or organization-specific retrieval.

See [architecture and commercial requirements](docs/COMMERCIAL_ARCHITECTURE.md) and the [security policy](SECURITY.md).

## Sales intelligence

A fictional EU SaaS company with 120 employees, a purchase decision expected within 20 days, final budget authority and no recorded engagement receives **85/100 — Priority A**, routing to the SMB Sales Team and recommended first contact within one business day. Missing mandatory fields prevent a final tier; discount and security exceptions require human review.

![Local lead qualification demonstration](docs/screenshots/discount_approval.png)

*Actual synthetic-data Streamlit demonstration. This interface does not perform CRM writes or send messages.*

Read the [lead qualification specification](docs/LEAD_QUALIFICATION.md) and [local scenario evidence](docs/LOCAL_VALIDATION.md).

## Human-in-the-loop CRM automation (draft PR)

The verified local workflow uses a dedicated machine identity with the `request:followups` permission and an `automation` membership in the fictional demo organization. The service retrieves permitted leads, requests a follow-up for the qualified demo lead, and reads the stored decision after a human owner approves it in the CRM.

```text
Manual Trigger → Edit Fields → API health → List organizations
 → List Demo Leads → Filter Qualified Leads → Request Sales Follow-up
 → Check Follow-up Status → Verify Approved Request
```

The final manual execution retained one approved request. A separate attempt to approve using the machine identity returned HTTP 403. No email, real notification, customer outreach or execution was performed. See the [workflow reconstruction and verification guide](docs/FOLLOWUP_AUTOMATION.md) and [feature branch](https://github.com/FerhatU9/AllSalesCRM-AI/tree/feature/followup-approval).

## Run locally

**Requirements:** Python 3.11/3.12; Node.js 20.9+ for the web workspace; Docker and a development PostgreSQL database for CRM and n8n. Use fictional data only. The following commands target Windows PowerShell.

### 1. Streamlit policy and scoring demo

From a fresh clone at the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
notepad .env
```

Set `ALLSALES_ENV=local` and replace `API_APP_TOKEN` with the generated secret. For policy Q&A, configure `DIFY_GEMINI_API_KEY` and `DIFY_CLAUDE_API_KEY` after following the [Dify reproduction guide](docs/DIFY_REPRODUCTION.md). Do not overwrite an existing environment or commit secrets.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Open separate terminals:

| FastAPI | Streamlit |
| --- | --- |
| `.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8000` | `.\.venv\Scripts\python.exe -m streamlit run app.py` |

Open http://127.0.0.1:8501. See the [local container guide](docs/CONTAINERS.md) for the alternative Compose setup.

### 2. Authenticated CRM

Follow [local onboarding](docs/LOCAL_ONBOARDING.md), [identity/database configuration](docs/IDENTITY_AND_DATABASE.md) and [customer web setup](docs/CUSTOMER_WEB.md). The observed CRM development ports were web **3000**, FastAPI **8001**, and PostgreSQL **5434**. Configure exact issuer, audience, JWKS URL and local database connection. Run Alembic migrations and provision a fictional organization and verified human owner before logging in.

For the draft automation feature, use the [follow-up guide](docs/FOLLOWUP_AUTOMATION.md) and isolated [n8n setup](docs/N8N_SETUP.md) (host port 5679). Never reuse a web client secret as an automation credential.

## Validation and evaluation

**Validated feature snapshot:** [1409a49](https://github.com/FerhatU9/AllSalesCRM-AI/commit/1409a499ef7be81ca4c7ed17597b6b1c8ed32598).

- All five PR workflows passed: Python tests, web workspace checks, browser smoke tests, PostgreSQL integration and CodeQL.
- Local focused Python regression: 20 passed; separate machine-identity access test: 1 passed. Local PostgreSQL migration 005 applied successfully.
- Development Auth0 browser journey verified login/logout, membership, lead persistence and owner/viewer presentation. Owner approval/rejection and n8n machine approval denial were tested on the feature branch.
- The earlier 118-pass local baseline is historical. Check [current Actions runs](https://github.com/FerhatU9/AllSalesCRM-AI/actions) for the latest results. Browser smoke checks are not a full authenticated browser suite; PostgreSQL CI covers migrations and lead isolation, not all follow-up concurrency behavior.

| Curated evaluation metric | Gemini | Claude |
| --- | ---: | ---: |
| Correct essential facts, stored final answers | 17/17 | 17/17 |
| All expected details | 14/17 | 17/17 |
| Wrong numbered section references | 1 | 2 |
| Mean recorded latency | 8.84 s | 4.30 s |
| Reported tokens (sum) | 9,783 | 16,167 |

The 34 stored final responses were manually reviewed **after retries** on 17 curated synthetic handbook questions per model. These results do not establish first-attempt reliability, general accuracy or comparative cost. See the [evaluation report](docs/EVALUATION_RESULTS.md), [reviewed responses](data/evaluation_34_reviewed.csv) and [Dify workflow review](docs/DIFY_WORKFLOW_REVIEW.md).

## Repository map

| Path | Responsibility |
| --- | --- |
| `app.py`, `allsales/` | Streamlit interface, scoring rules, Dify adapters, identity verification and persistence |
| `backend/` | FastAPI demo and authenticated CRM endpoints |
| `web/` | Next.js / TypeScript workspace |
| `migrations/` | Alembic database schema history |
| `knowledge/`, `dify_exports/` | Synthetic sales handbook and sanitized Chatflows |
| `data/`, `scripts/`, `tests/` | Evaluation data, development commands and tests |
| `docs/` | Engineering report, setup, architecture and evidence |
| `site/` | Static product showcase |
| `.github/workflows/` | CI and static site publishing configuration |

## Roadmap

1. Complete the follow-up lifecycle with an authorized, retry-safe **internal simulation**, never real outreach.
2. Export and review a sanitized portable n8n workflow; reproduce it from a clean local environment.
3. Improve multi-user CRM usability, authenticated browser coverage and organization administration.
4. Introduce evidence-based, tenant-authorized retrieval and justified LangGraph orchestration.
5. Design secured Azure staging, monitoring, backup/restore, cost controls and security review.
6. Consider a consenting controlled pilot only after release gates are met.

See the [production plan](docs/PRODUCTION_PLAN.md). The local-only restriction remains in force; no real customer data, automatic outreach, public SaaS availability or production readiness is claimed.
