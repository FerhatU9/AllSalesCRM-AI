# Customer web workspace

**Status:** Implemented as a local-development web frontend. A developer-observed browser journey demonstrated live development Auth0 sign-in/logout, local PostgreSQL lead creation and updates, and owner/viewer presentation. Independent security validation remains outstanding. This is not a launched SaaS product.

## What is included

- A Next.js web experience with a landing page and authenticated workspace.
- Hosted Auth0 login via the supported Next.js SDK; login/logout handled at `/auth/login` and `/auth/logout`.
- Authenticated organizations overview using the FastAPI membership endpoint.
- Organization-scoped list/create/update screens for synthetic leads, including read-only viewer role presentation.
- Server-only access tokens: requests to FastAPI are made by Next.js server components/actions, not directly by the user's browser.
- Reuses the existing FastAPI JWT verification and membership checks. Frontend role display is not the security boundary.

## Prerequisites

1. Node.js 20.9+ with npm, Python and the existing FastAPI application.
2. Auth0 account and **Regular Web Application** with your localhost callback and logout URLs configured.
3. Auth0 **API** configured with a fixed identifier (audience). Ensure its issuer and JWKS are correctly configured in FastAPI.
4. Local development PostgreSQL (recommended) or an isolated SQLite test database, migrated with Alembic.
5. A provisioned test identity with membership in a synthetic organization. **The application cannot register customers or create organization memberships yet.**

## Auth0 dashboard configuration

Create a Regular Web Application in Auth0 and register:

- Allowed callback URL: `http://localhost:3000/auth/callback`
- Allowed logout URL: `http://localhost:3000`
- Allowed web origin: `http://localhost:3000`
- Authorize the Regular Web Application for user-delegated access to the custom API if its application access policy requires a client grant. Machine-to-machine access is not needed for interactive sign-in.
- API audience: e.g. `https://api.allsales.local` (an identifier, not a public API URL)

Use one browser origin consistently. Check the configured value from the repository root with `Select-String -Path web/.env.local -Pattern '^APP_BASE_URL='` (does not print secrets). During local import validation, navigation from `localhost` to a `127.0.0.1` callback produced an invalid state error despite a successful Auth0 login; restarting the sign-in at the configured `http://127.0.0.1:3000` restored access. Do not bypass state validation. If using `http://127.0.0.1:3000`, configure its exact `/auth/callback` URL and allowed logout redirect (including the trailing slash if requested by the SDK). The issuer and JWKS URL must use HTTPS and the same actual tenant host, regardless of region.

Use the Auth0 domain, client ID and client secret from that application. Do not paste these credentials into GitHub issues or commit them.

## Configure and start

In `web/`, copy `.env.example` to `.env.local` (PowerShell: `Copy-Item .env.example .env.local`). Set:

```dotenv
AUTH0_DOMAIN=YOUR_TENANT.eu.auth0.com
AUTH0_CLIENT_ID=YOUR_WEB_APP_CLIENT_ID
AUTH0_CLIENT_SECRET=YOUR_WEB_APP_CLIENT_SECRET
AUTH0_SECRET=GENERATE_A_SECURE_HEX_SECRET
APP_BASE_URL=http://localhost:3000
AUTH0_AUDIENCE=https://api.allsales.local
BACKEND_INTERNAL_URL=http://127.0.0.1:8000
```

Generate `AUTH0_SECRET` locally with `python -c "import secrets; print(secrets.token_hex(32))"`.

Set the corresponding backend values in the root `.env`:

```dotenv
ALLSALES_ENV=local
DATABASE_URL=postgresql+psycopg://DB_USER:DB_PASSWORD@127.0.0.1:5432/allsales
OIDC_ISSUER=https://YOUR_TENANT.eu.auth0.com/
OIDC_AUDIENCE=https://api.allsales.local
OIDC_JWKS_URL=https://YOUR_TENANT.eu.auth0.com/.well-known/jwks.json
```

Create the database first and run `python -m alembic upgrade head` from the repository root. Ensure a synthetic organization and the verified Auth0 user's `(issuer, sub)` identity are provisioned as a member in the database. The existing Streamlit demo remains separate and local-only.

Start FastAPI from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

Then start the web application from `web/`:

```powershell
npm ci
npm run typecheck
npm run dev
```

Open `http://localhost:3000`. Sign in to see your assigned organizations, then view or change synthetic leads where your membership role allows it.

## Verified local configuration

The demonstrated development environment uses frontend `127.0.0.1:3000`, FastAPI `127.0.0.1:8001` and PostgreSQL on host port `5434`. These differ from the generic defaults above. Match `APP_BASE_URL`, `BACKEND_INTERNAL_URL`, the Uvicorn port and `DATABASE_URL` to the actual running services. Do not overwrite existing configuration or commit secrets.

A 404 on the account-list page may indicate the wrong backend port; a 503 may indicate invalid OIDC settings, signing-key connectivity or database failure. Use the API response details and server logs to distinguish these cases. An empty organization list for a valid unassigned identity is expected.

## Data and security boundaries

- API access tokens stay on the Next.js server and are sent only to the configured local FastAPI service. They must never be placed in `NEXT_PUBLIC_` variables.
- Auth0 and FastAPI must agree on exact issuer and audience. An Auth0 profile/ID token is not an API access token.
- The backend verifies JWT signature and expiry and performs its own membership and organization checks on each lead operation.
- Web Server Actions do not supply user identity to FastAPI; identity is always derived from the verified bearer token.
- The frontend does not implement invitation approval, tenant provisioning, persistent CRM integrations, document upload or billing.
- The existing Streamlit routes still use a separate shared development token; they must never be exposed to customers.
- Frontend and backend are loopback-only in this milestone. The backend URL explicitly rejects remote hosts.
- Use fictional data only; retain local-only restrictions until production security and operational tests pass.

## Follow-up review (draft feature)

The [follow-up feature branch](https://github.com/FerhatU9/AllSalesCRM-AI/tree/feature/followup-approval) adds a dedicated per-lead follow-up page. Owners/admins can decide a pending, unexpired request where backend checks allow it; viewers can read the history without request or decision controls. A local owner approved and rejected synthetic requests, and the restricted n8n machine identity was denied when attempting to approve. See the [automation guide](FOLLOWUP_AUTOMATION.md). The machine-only endpoint implements authorized database-only execution; no external delivery is implemented; the feature remains a draft PR.

## Next work

Implement controlled account provisioning and invitations, repeatable authenticated browser tests, live-token negative write checks, a policy assistant with organization-scoped retrieval, production-quality audit integrity, rate limiting, UI error/empty-state testing, and managed deployment only after security review. Disposable PostgreSQL integration tests and basic lead activity storage already exist.
