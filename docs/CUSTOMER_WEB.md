# Customer web workspace

**Status:** Implemented as a local-development web frontend. Live Auth0 sign-in, a real PostgreSQL service and a complete user journey have not yet been independently tested. This is not a launched SaaS product.

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
- API audience: e.g. `https://api.allsales.local` (an identifier, not a public API URL)

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

## Data and security boundaries

- API access tokens stay on the Next.js server and are sent only to the configured local FastAPI service. They must never be placed in `NEXT_PUBLIC_` variables.
- Auth0 and FastAPI must agree on exact issuer and audience. An Auth0 profile/ID token is not an API access token.
- The backend verifies JWT signature and expiry and performs its own membership and organization checks on each lead operation.
- Web Server Actions do not supply user identity to FastAPI; identity is always derived from the verified bearer token.
- The frontend does not implement invitation approval, tenant provisioning, persistent CRM integrations, document upload or billing.
- The existing Streamlit routes still use a separate shared development token; they must never be exposed to customers.
- Frontend and backend are loopback-only in this milestone. The backend URL explicitly rejects remote hosts.
- Use fictional data only; perform live Auth0 and PostgreSQL integration testing before claiming operational readiness.

## Next work

Implement controlled account provisioning and invitations, a real Auth0 browser-to-PostgreSQL test, a policy assistant with organization-scoped retrieval, production-quality audit integrity, rate limiting, UI error/empty-state testing, and managed deployment only after security review. Disposable PostgreSQL integration tests and basic lead activity storage already exist.
