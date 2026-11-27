# Authenticated follow-up automation — local demonstration

**Status (November 27, 2026):** implemented and locally validated on the [follow-up feature branch](https://github.com/FerhatU9/AllSalesCRM-AI/tree/feature/followup-approval), code snapshot [1409a49](https://github.com/FerhatU9/AllSalesCRM-AI/commit/1409a499ef7be81ca4c7ed17597b6b1c8ed32598), [draft PR #32](https://github.com/FerhatU9/AllSalesCRM-AI/pull/32). The feature is not merged into main. This guide reconstructs the manually demonstrated workflow; it is not a portable n8n export. See the [technical report](AllSales_CRM_Technical_Report.pdf) for architecture and recorded evidence.

## 1. What the workflow proves

A machine identity can read assigned demo organizations and qualified leads, create a **pending** follow-up request, and retrieve its approval status. Only a verified organization owner or administrator can approve or reject it. A successful n8n status check is not delivery: no execution endpoint, external notification or real CRM write is enabled.

The request key is a UUID, unique per lead. A valid repeated request with the same key and requester returns the existing record (HTTP 200); a new request returns HTTP 201. Reuse the same key for retries, not a fresh UUID. Conflicting requesters are rejected. Pending requests expire after 24 hours; approval requires a still-qualified lead.

## 2. Prepare the development environment

- Use the feature branch, an active local virtual environment, local PostgreSQL, and the working Auth0 web application from [local onboarding](LOCAL_ONBOARDING.md) and [customer web setup](CUSTOMER_WEB.md).
- Prepare the fictional `allsales-demo` organization, an owner identity and a qualified lead named **Nordvale Technologies** through the CRM workspace.
- Use the isolated [local n8n instance](N8N_SETUP.md). Verified ports: web 3000, FastAPI 8001, PostgreSQL 5434 and n8n 5679. Do not expose services publicly.

From the repository root in PowerShell:

```powershell
python -m alembic upgrade head
python -m alembic current
```

Expected feature-branch revision: `005_automation_membership (head)` at the validated snapshot.

## 3. Configure Auth0 and restricted membership

1. In the development Auth0 dashboard, create a distinct **Machine to Machine Application** for automation. Do not reuse the Regular Web Application.
2. Under the custom CRM API's **Permissions**, add `request:followups`. Under **Application Access**, edit the automation application and grant the permission in **Client Access** (not User-Delegated Access). The automation application's client access should show 1/1 permissions granted. Other clients do not need this machine grant unless independently justified.
3. Copy the automation application's own Client ID and Client Secret from its Settings to the local n8n credential. Never paste the secret into a command, repository, screenshot or workflow JSON.
4. Assign the machine identity to the synthetic organization using the guarded script:

```powershell
python -m scripts.provision_automation_identity --confirm-synthetic
```

Enter the automation **Client ID** when prompted (not its secret). The script checks for a local database, requires the existing `allsales-demo` organization, and refuses conflicting memberships. Expected role: `automation`. No Auth0 Organization Support toggle is required for this application's database-backed membership.

The API validates signed RS256 access tokens, issuer, audience, time claims and subject. A machine identity has a subject ending in `@clients`; it needs both the required scope and its automation membership. The audience is an identifier, not a network destination.

## 4. Configure n8n credential

Create a generic **OAuth2 API** credential named `AllSales CRM Automation`.

| Field | Value |
| --- | --- |
| Grant type | Client Credentials |
| Access token URL | `https://YOUR_TENANT.us.auth0.com/oauth/token` (use the exact tenant domain) |
| Client ID / Client Secret | From the automation application |
| Scope | `request:followups` |
| Authentication | Body (client secret post) |
| Audience | `https://api.allsales.local` — send in the token request's additional body parameters using your n8n version's credential UI |

Use the exact API identifier configured in Auth0 and FastAPI. The example audience is not an HTTP request URL. Store credentials only in the local n8n credential manager. A token exchange with `access_denied` / “Client has not been granted scopes” means the machine application's **Client Access** grant must be checked; creating the API permission or granting user-delegated access alone is insufficient.

## 5. Build the nine-node local workflow

Connect each node to the next. Keep the workflow manual and unpublished. For authenticated HTTP Request nodes, select Generic Credential Type → OAuth2 API → AllSales CRM Automation. Use Expression mode for URLs containing `{{ ... }}`.

| Step | Node | Configuration / purpose |
| --- | --- | --- |
| 1 | Manual Trigger | Explicit local run |
| 2 | Edit Fields | Fictional example fields only; never permissions or approval proof |
| 3 | HTTP Request | GET `http://host.docker.internal:8001/health`, no credential; process health |
| 4 | HTTP Request1 | GET `http://host.docker.internal:8001/v1/account/organizations`, OAuth2; find assigned organizations |
| 5 | List Demo Leads | GET organization-scoped leads using expression below |
| 6 | Filter Qualified Leads | String conditions: status = qualified AND company_name = Nordvale Technologies |
| 7 | Request Sales Follow-up | POST scoped follow-ups endpoint; send JSON request_key |
| 8 | Check Follow-up Status | GET scoped follow-ups endpoint; returns list of stored requests |
| 9 | Verify Approved Request | Keep only matching request ID AND status approved |

**List Demo Leads — URL**

```text
http://host.docker.internal:8001/v1/organizations/{{ $json.organizations.find(o => o.slug === 'allsales-demo' && o.role === 'automation').id }}/leads
```

First confirm exactly one matching organization exists; if not, stop and check membership. This expression deliberately selects the synthetic demonstration organization.

**Filter Qualified Leads — conditions (AND)**

- `{{ $json.status }}` equals `qualified`
- `{{ $json.company_name }}` equals `Nordvale Technologies`

**Request Sales Follow-up — URL and body**

```text
http://host.docker.internal:8001/v1/organizations/{{ $json.organization_id }}/leads/{{ $json.id }}/followups
```

Enable Send Body → JSON → Using Fields Below; field `request_key` is a UUID string. Generate one with PowerShell `[guid]::NewGuid().ToString()`. Copy that single demo value into the node and keep it unchanged on retries. Use a different value only for an intentionally new request. The key is a deduplication identifier, not a credential.

Execute up to the request node. Output includes `id`, `lead_id`, `request_key`, `status`, `created_at`, `expires_at`, `decided_at` and `executed_at`. Expect pending on a new request. In the local web CRM, sign in as the organization owner or admin, open the lead's follow-up page, and deliberately approve the specific synthetic pending request.

**Check Follow-up Status — URL**

```text
http://host.docker.internal:8001/v1/organizations/{{ $('Filter Qualified Leads').first().json.organization_id }}/leads/{{ $json.lead_id }}/followups
```

This expression is intentionally limited to a single filtered demo lead. The response list may contain previous approved, rejected or pending requests; do not assume the first item is the current request.

**Verify Approved Request — conditions (AND)**

- `{{ $json.id }}` equals `{{ $('Request Sales Follow-up').first().json.id }}`
- `{{ $json.status }}` equals `approved`

Execute the final nodes after human approval. For the demonstrated one-lead workflow, the check returned three historical/current records and the final filter retained exactly one approved item. If no approved record matches, the result should be empty; do not execute an action. Generalizing to multiple leads requires per-item linkage and stable keys rather than `.first()`.

## 6. Test the authorization boundary

During development only, test a temporary HTTP Request node with the same machine credential:

```text
POST http://host.docker.internal:8001/v1/organizations/{{ $('Filter Qualified Leads').first().json.organization_id }}/leads/{{ $json.lead_id }}/followups/{{ $json.id }}/decision
```

JSON body: `{"decision":"approved"}`. The observed response is HTTP 403: “Only owners and administrators can decide follow-ups.” This is expected. Delete or disconnect this temporary test node when done so the normal workflow cannot attempt approval. Do not grant the machine identity owner/admin privileges.

| Check | Expected / demonstrated behavior |
| --- | --- |
| Valid machine credential and membership | Only assigned fictional organization returned |
| Qualified demo lead | Kept by filter |
| First request, then same-key retry | One pending request; identical returned ID |
| Machine decision | Denied with HTTP 403 |
| Human owner approval | Stored approved decision |
| Matching approved request | Exactly one retained item in final n8n demonstration |
| Missing scope / wrong organization / lead write | Denied by backend; targeted tests |
| Expired or decided request | Decision rejected; no execution enabled |

Local focused tests: 20 passed, plus one separate automation access test. CI succeeded for all five PR workflows at 1409a49. Follow-up and machine access are tested with SQLite API and signed-token cases, plus the observed local PostgreSQL integration. PostgreSQL CI is not a complete concurrency test of the follow-up lifecycle. Review the [automated test file at the validated commit](https://github.com/FerhatU9/AllSalesCRM-AI/blob/1409a499ef7be81ca4c7ed17597b6b1c8ed32598/tests/test_automation_access.py).

## 7. Remaining release gates

- Preserve the owner/admin decision boundary. Implement a separate authorized, retry-safe **internal simulation** for approved requests before considering real side effects.
- Verify rejected, expired, conflicting, unauthorized and duplicate execution attempts, including PostgreSQL concurrency.
- Export a reviewed, sanitized workflow definition with no credentials, personal identifiers, execution logs or private configuration; reproduce it on a clean local instance.
- Maintain local-only services and synthetic data. No schedule, real email, external CRM integration or production deployment is authorized by this demonstration.

See [project status](PROJECT_STATUS.md), [roadmap](PRODUCTION_PLAN.md) and [security policy](../SECURITY.md).
