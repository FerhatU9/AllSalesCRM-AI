# Local development onboarding

**Purpose:** Create a synthetic company and verify real PostgreSQL access safely. This is an administrator-only, local-development workflow — not customer self-registration.

## 1. Prepare local PostgreSQL

Install PostgreSQL or start a local Docker database. One example for an isolated developer machine:

```powershell
docker run --name allsales-local-db -e POSTGRES_USER=allsales_dev -e POSTGRES_PASSWORD=local-test-only -e POSTGRES_DB=allsales_dev -p 127.0.0.1:5432:5432 -d postgres:17
```

Use a strong unique password for a persistent local environment; this example password is only for disposable synthetic testing. Do not deploy this setup to the internet.

Set the following locally in root `.env` (do not commit it):

```dotenv
ALLSALES_ENV=local
DATABASE_URL=postgresql+psycopg://allsales_dev:local-test-only@127.0.0.1:5432/allsales_dev
OIDC_ISSUER=https://YOUR_DEV_TENANT.eu.auth0.com/
```

Make sure the URL points to a dedicated local PostgreSQL instance and not to any customer or production database.

## 2. Apply the schema

From the repository root with your Python virtual environment:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

The Alembic migration creates organization, identity, membership and synthetic lead tables.

## 3. Configure a development identity

Configure the Auth0 application and API audience using the [customer web setup](CUSTOMER_WEB.md). Use a development account and capture the exact `sub` identifier from Auth0. Do not share access tokens, credentials or private authentication claims in public issues.

## 4. Provision a fictional workspace

```powershell
.\.venv\Scripts\python.exe -m scripts.provision_demo_workspace --subject 'auth0|YOUR_DEV_SUBJECT' --confirm-synthetic
```

This creates **AllSales Demo** and owner membership for that exact identity. Re-running the command with the same identity is safe and does not elevate an existing role. It refuses to attach a new identity to an organization that already exists. No public provisioning endpoint is exposed.

## 5. Run the web interface

Run the Python API on `127.0.0.1:8000` and the Next.js application on `localhost:3000`, following [customer web setup](CUSTOMER_WEB.md). Sign in with the same development account and check that only your assigned organization appears. Use synthetic leads only.

## 6. PostgreSQL CI verification

The [PostgreSQL integration workflow](../.github/workflows/postgres.yml) automatically starts a disposable PostgreSQL service in GitHub Actions, applies Alembic migrations, then tests organization listing, lead creation, lead status changes, cross-company access denial and read-only memberships.

The integration test refuses to execute unless it finds a CI environment and an explicitly named local `allsales_test` database. SQLite-based offline tests remain separate.

## Remaining commercial requirements

Real account invitations and role administration, a production-ready authentication configuration, tenant-scoped RAG access, audit logging, rate limits, row-level data protection, backup restoration, monitoring, and privacy review are **not complete**. No public customer deployment is authorized by this milestone.
