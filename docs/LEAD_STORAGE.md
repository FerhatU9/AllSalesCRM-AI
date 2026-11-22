# Organization-scoped lead records

This is a **local development feature** using synthetic lead records only. It adds persistent metadata to the database, while leaving the existing Streamlit sales-policy and lead-scoring demos unchanged.

## Database

Apply migration `002_scoped_leads` from the repository root:

```powershell
python -m alembic upgrade head
```

Each lead belongs to exactly one organization and references the identity that created it. The stored fields are `company_name`, `summary`, and `status`. The database enforces allowed statuses: `new`, `qualified`, and `archived`.

## Authenticated API

Requests require an actual RS256-signed provider-issued OIDC access token. No self-issued dev tokens or caller-provided identity headers are accepted.

- `GET /v1/organizations/{organization_id}/leads` — list leads (viewer, sales, admin, owner).
- `POST /v1/organizations/{organization_id}/leads` — create lead (sales, admin, owner).
- `GET /v1/organizations/{organization_id}/leads/{lead_id}` — read one lead (member).
- `PATCH /v1/organizations/{organization_id}/leads/{lead_id}` — update lead metadata (sales, admin, owner).

The API checks memberships from the **verified issuer and subject** on every request and restricts lead queries to the authorized organization ID. Nonmembers receive 404 without a company-existence signal. Viewer-role members can read but cannot write. No bulk export, destructive deletion, CRM integration, or external action is available.

## Isolation and validation

SQLite tests cover two-company isolation, read-only roles, invalid updates and missing Bearer authorization. A separate disposable PostgreSQL CI workflow checks migrations and cross-company API operations. Live OIDC sign-in and a production database remain unverified.

## Still required before any customer deployment

Live provider login, controlled customer onboarding, database row-level security, rate limits, organization-safe knowledge retrieval, data retention/deletion, backups, independent audit integrity and security review remain missing. Basic lead activity history is implemented; see [lead activity](LEAD_ACTIVITY.md).

The current `ALLSALES_ENV` startup guard remains local-only. **Do not enter real customer information.**
