# Identity and organization database

This is a foundation for a future authenticated product, **not a complete login system or production-ready CRM**. Existing Streamlit and lead-decision endpoints still use a shared local development token; public deployment remains blocked.

## Implemented

- SQLAlchemy organizations, external identities, and role-based memberships.
- Alembic migration with PostgreSQL-compatible tables.
- OIDC RS256 access-token validation with fixed HTTPS JWKS URL, issuer, audience and required time claims.
- A read-only `GET /v1/account/organizations` endpoint, scoped by verified issuer and subject.
- Offline tests for identity claims, membership isolation, uniqueness and role constraints.

## Database configuration

Provision a **development-only** PostgreSQL database and a least-privileged user. In local `.env` configure:

```dotenv
DATABASE_URL=postgresql+psycopg://DB_USER:DB_PASSWORD@localhost:5432/allsales
```

Never commit real credentials. From the repository root run:

```powershell
python -m alembic -c alembic.ini upgrade head
```

No signup or membership administration API is available yet. SQLite unit tests and disposable PostgreSQL CI migration tests exist. A customer or production database has not been validated.

## OIDC configuration

Register an API audience with a managed OIDC identity provider that issues RS256-signed access tokens. Configure issuer, audience and same-host HTTPS JWKS in local `.env`:

```dotenv
OIDC_ISSUER=https://your-provider.example/
OIDC_AUDIENCE=allsales-api
OIDC_JWKS_URL=https://your-provider.example/.well-known/jwks.json
```

Call the read-only account endpoint using an actual provider-issued **access token**:

```http
GET /v1/account/organizations
Authorization: Bearer YOUR_PROVIDER_ISSUED_ACCESS_TOKEN
```

The endpoint returns only organizations with memberships matching the cryptographically verified issuer and subject. Valid unprovisioned users receive an empty list.

## Important limits

- A Next.js frontend with an Auth0 SDK login flow exists, but a complete real login has not yet been verified. Self-signup, invitations and role administration are not built.
- Existing chat and lead-evaluation routes have not been migrated to OIDC authentication.
- Synthetic lead persistence, organization-scoped CRUD and activity history exist. Live Auth0 integration and database row-level security remain incomplete.
- Application checks need database-level defense, auditing and real identity-provider integration tests.
- JWT validation has offline tests, and PostgreSQL has disposable CI tests. Live OIDC integration and a production database are not validated.
- **Do not use real customer data or expose the app to the internet.**

## Next milestone

Verify hosted login against a real Auth0 development tenant; add controlled invitations and membership administration, database-level row isolation, and authenticated organization-specific knowledge retrieval. The shared dev-token demo must remain local-only.
