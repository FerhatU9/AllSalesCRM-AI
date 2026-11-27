# Authenticated follow-up automation — local demonstration

**Status (November 27, 2026):** Locally demonstrated on the [follow-up feature branch](https://github.com/FerhatU9/AllSalesCRM-AI/tree/feature/followup-approval), code snapshot [acd7af2](https://github.com/FerhatU9/AllSalesCRM-AI/commit/acd7af2b66cee07fe2d9430c0c035cc0d42e54c4), [draft PR #32](https://github.com/FerhatU9/AllSalesCRM-AI/pull/32). The feature is not merged. The [technical report](AllSales_CRM_Technical_Report.pdf) records the earlier approval-stage snapshot (1409a49). This guide includes the subsequent execution milestone.

## 1. What the workflow proves

A restricted automation identity can read its assigned demo organization and qualified leads, create a pending follow-up, retrieve the human decision and execute its own approved request. Only a verified organization owner or administrator can approve or reject requests. **Execution changes only the follow-up database record. No email, customer outreach, external notification or scheduled job is enabled.**

New requests use a UUID request key unique per lead (HTTP 201). Retrying the same key with the same requester returns the existing record (HTTP 200). Another requester using the key is denied. Requests expire after 24 hours; approval and initial execution require a currently qualified lead and an unexpired request. Executed retries return the persisted result without changing its execution timestamp.

## 2. Prepare the local environment

- Use the feature branch, active Python virtual environment, local PostgreSQL, and development Auth0 web application from [local onboarding](LOCAL_ONBOARDING.md) and [customer web setup](CUSTOMER_WEB.md).
- Prepare the fictional `allsales-demo` organization with a human owner/admin and **exactly one** qualified synthetic lead named Nordvale Technologies.
- Run the isolated [n8n instance](N8N_SETUP.md); observed local ports: web 3000, FastAPI 8001, PostgreSQL 5434 and n8n 5679. Do not expose local services publicly.

From the project root in PowerShell:

```powershell
python -m alembic upgrade head
python -m alembic current
```

Expected feature branch revision: `005_automation_membership (head)`.

## 3. Configure Auth0 and restricted membership

1. Use a dedicated development Auth0 **Machine to Machine Application**, not the Regular Web Application for interactive users.
2. Under the CRM API's **Permissions**, define `request:followups` (create pending follow-ups) and `execute:followups` (execute approved follow-ups). Under **Application Access**, grant both permissions under **Client Access** for the dedicated automation application only where needed. Do not grant anonymous access or unnecessary user-delegated scopes; review other client grants and keep any unrelated permissions required by their verified use cases.
3. Use the machine application's own Client ID and secret in the local n8n credential manager. Never reveal the secret in a screenshot, command, repository or workflow export.
4. Provision the database-backed membership in the demo organization using the guarded local script:

```powershell
python -m scripts.provision_automation_identity --confirm-synthetic
```

Enter the automation application's **Client ID**, not its secret. The script checks for a local database and an existing `allsales-demo` organization, and refuses conflicting memberships. Expected role: `automation`.

The backend validates signed RS256 access tokens, issuer, audience, time claims and subject. A machine identity has a subject ending in `@clients` and requires the relevant token scopes and organization membership. The execution endpoint additionally checks requester ownership, approval metadata, expiry and qualification on the initial transition.

## 4. Configure the n8n OAuth2 API credential

Create or update the local generic **OAuth2 API** credential named AllSales CRM Automation.

| Field | Value |
| --- | --- |
| Grant type | Client Credentials |
| Access token URL | `https://YOUR_TENANT.us.auth0.com/oauth/token` (use exact tenant domain) |
| Client ID / Client Secret | From your dedicated automation application |
| Scope | `request:followups execute:followups` |
| Authentication | Body (client secret post) |
| Audience | `https://api.allsales.local` — send in the token request's additional body parameters using your n8n credential UI |

Use the exact audience configured in Auth0 and FastAPI. It is an identifier, not an HTTP destination. A token exchange with `access_denied` or “Client has not been granted scopes” requires checking the machine application's **Client Access** grant rather than relaxing backend permissions.

## 5. Import the ten-node workflow

The [credential-free JSON template](../n8n-workflows/sales_followup_automation.json) is derived from the locally demonstrated export. Local credential IDs, original request UUID, workflow instance IDs and pinned data were removed; the workflow is inactive by default. A static contract test checks the graph and approval filter. The sanitized version still needs a fresh n8n import/run to establish reproducibility.

1. Open the isolated local n8n editor (`http://localhost:5679`), create a **new workflow**, then use its three-dot menu → **Import → From file**. Choose `n8n-workflows/sales_followup_automation.json` from the feature branch. Do not overwrite your working original.
2. On the five protected HTTP Request nodes (List Assigned Organizations, List Demo Leads, Request Sales Follow-up, Check Follow-up Status, Execute Approved Follow-up), select Generic Credential Type → OAuth2 API → AllSales CRM Automation. The health node remains unauthenticated.
3. Generate a new UUID in PowerShell:

```powershell
[guid]::NewGuid().ToString()
```

4. In **Demo Configuration**, replace `REPLACE_WITH_NEW_UUID` with that value. Keep it unchanged through creation, approval and retries; generate a new key only for an intentional new request. Keep the company name set to the unique fictional lead. The placeholder deliberately fails server UUID validation if left unchanged.
5. Leave the workflow manual and unpublished. Verify there is exactly one matching qualified lead before proceeding beyond the lead filter. This is a one-lead demonstration; generalizing requires per-item linkage and stable per-lead keys rather than `.first()`.

| Order | Node | Function |
| --- | --- | --- |
| 1 | Manual Trigger | Explicit manual run |
| 2 | Demo Configuration | Fictional company name and stable request key |
| 3 | Check API Health | GET /health |
| 4 | List Assigned Organizations | GET /v1/account/organizations with OAuth2 |
| 5 | List Demo Leads | GET /v1/organizations/{organization_id}/leads |
| 6 | Filter Qualified Leads | Qualified status and exact demo company name |
| 7 | Request Sales Follow-up | POST scoped /followups with UUID request_key |
| 8 | Check Follow-up Status | GET scoped /followups |
| 9 | Verify Approved Request | Both returned ID matches the just-requested ID and status equals approved |
| 10 | Execute Approved Follow-up | POST scoped /followups/{followup_id}/execute, without a body |

## 6. Run and verify safely

1. Run the workflow manually with the new stable UUID. Verify Request Sales Follow-up returns `pending` and the approval filter returns no items. No execution should occur.
2. Sign in to the local CRM as the organization owner/admin. Open the specific demo lead's follow-up page and deliberately approve that exact pending request.
3. Rerun with the **same** request key. The create node should retrieve the existing request; the approval filter should retain only its matching approved record. The execute node should return status `executed` and a populated `executed_at`.
4. Rerun the complete workflow again. The same request returns `executed`, so the approval filter retains zero items. No new request or execution is expected. Replaying the execute API call directly with the same authorized requester is also covered by automated same-result retry tests.

The execution endpoint is:

```text
POST /v1/organizations/{organization_id}/leads/{lead_id}/followups/{followup_id}/execute
```

To verify backend retry behavior separately, repeat the execution node with the same authorized approved-item input from the previous successful run and compare the returned ID and timestamp. Do not change approval, tenant or requester data to force a result. No live repeated timestamp comparison has yet been recorded.

## 7. Authorization and failure checks

| Scenario | Expected API outcome |
| --- | --- |
| Missing bearer token | 401 |
| Automation attempts to decide a follow-up | 403 (observed locally) |
| Human caller, missing execution scope or different requester attempts execution | 403 |
| Wrong scoped organization, lead or follow-up | 404 |
| Pending, rejected or expired request; lead no longer qualified (first execution) | 409 |
| Original machine executes its own approved, unexpired request on a qualified lead | 200, executed |
| Original authorized machine retries executed request | 200, unchanged result |

The automation approval-denial test uses POST /followups/{followup_id}/decision with JSON `{"decision":"approved"}` on the synthetic record. It is **not** part of the normal workflow. Never grant an owner/admin membership to automation to resolve an expected 403.

## 8. Recorded evidence and remaining gates

- The developer's original local n8n workflow successfully returned `executed` after human approval, and machine approval was denied with 403.
- At code snapshot acd7af2, the reported full local Python suite passed: **121 passed, 1 skipped, 7 warnings, 21 subtests passed**. All five PR CI workflows passed (Python, web, browser smoke, PostgreSQL integration, CodeQL).
- [Execution tests](../tests/test_automation_access.py) cover scope, human caller, pending/rejected/expired cases, successful execution and identical retry result. [Template contract test](../tests/test_n8n_workflow.py) checks the sanitized JSON.
- PostgreSQL CI covers migrations and lead isolation, not complete follow-up concurrency coverage. Fresh template import, verified least-privilege grants, direct live retry comparison and additional ownership/changed-lead-state and concurrency tests remain.

Keep the integration local, synthetic and unpublished. Passing tests and a successful simulation do not demonstrate production readiness or external delivery. See [project status](PROJECT_STATUS.md) and [production plan](PRODUCTION_PLAN.md).
