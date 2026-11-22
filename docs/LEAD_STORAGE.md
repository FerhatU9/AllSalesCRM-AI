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

Offline tests check Company A versus Company B, viewer read-only access, invalid updates, and missing Bearer authorization. Tests use SQLite in memory and fake authenticated identities injected through FastAPI's testing dependency override; a real identity provider and PostgreSQL remain untested.

## Still required before any customer deployment

Real provider login, organization provisioning, server-side row-level security, an audit log, request limiting, organization-safe knowledge retrieval, encrypted personal-data handling, retention/deletion, backups, security review and deployment controls.

The current `ALLSALES_ENV` startup guard remains local-only. **Do not enter real customer information.**
