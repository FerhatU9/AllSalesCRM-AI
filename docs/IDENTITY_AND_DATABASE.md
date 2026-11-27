# Identity and organization database

This is a locally demonstrated authenticated CRM foundation, **not a complete account-management system or production-ready CRM**. Existing Streamlit and lead-decision endpoints still use a shared local development token; public deployment remains blocked.

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

- A development Auth0 tenant was used successfully for local Next.js sign-in/logout and organization-scoped lead management. Self-signup, invitations and role administration are not built.
- Existing chat and lead-evaluation routes have not been migrated to OIDC authentication.
- Synthetic lead persistence, organization-scoped CRUD and activity history exist. Local Auth0 integration has been demonstrated; database row-level security remains incomplete.
- Application checks need database-level defense, auditing and real identity-provider integration tests.
- JWT validation has offline tests, and PostgreSQL has disposable CI tests. Live development OIDC and local PostgreSQL have been demonstrated; production database and independent security validation remain outstanding.
- **Do not use real customer data or expose the app to the internet.**

## Machine identity (draft feature)

Migration 005 adds the `automation` membership role. On the [feature branch](https://github.com/FerhatU9/AllSalesCRM-AI/tree/feature/followup-approval), a signed Auth0 machine token requires `request:followups` and a restricted organization membership. The synthetic provisioning script and n8n guide are documented in [follow-up automation](FOLLOWUP_AUTOMATION.md). Machine actors can read scoped leads and request follow-ups, but cannot write leads or decide requests.

## Next milestone

Extend the demonstrated local Auth0 login with controlled invitations and membership administration, database-level row isolation, and authenticated organization-specific knowledge retrieval. The shared dev-token demo must remain local-only.
