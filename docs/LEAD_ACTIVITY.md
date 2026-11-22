# Lead activity history

AllSales CRM records a minimal audit trail for changes to **synthetic, organization-scoped leads**. This feature is for local development. It is not a regulatory-grade or tamper-proof audit system.

## Recorded events

When an authenticated user creates or meaningfully updates a lead, the API writes a \`lead_audit_events\` entry in the **same database transaction** as the lead change.

Each event contains:

- Organization and lead UUIDs
- Verified actor's database identity UUID
- Action: \`created\` or \`updated\`
- Sorted names of the changed fields
- Previous and new status, when status changes
- Database-generated timestamp

The audit table deliberately excludes company names, lead summaries, access tokens and model outputs. An update that does not actually change values produces no new event.

## Access permissions

Authorized **organization owners and admins** can read a lead's history:

\`\`\`http
GET /v1/organizations/{organization_id}/leads/{lead_id}/activity?limit=50&offset=0
Authorization: Bearer YOUR_PROVIDER_ISSUED_ACCESS_TOKEN
\`\`\`

This route requires a validated OIDC access token, matching organization membership, an existing lead in that organization and owner/admin role. Viewers and sales-role users cannot read activity records. Nonmembers and cross-organization requests return 404. No public endpoint is provided to write, delete or alter audit records directly.

## Migration and tests

Run Alembic migration \`003_lead_audit\` in an isolated development database:

\`\`\`powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
\`\`\`

The new automated tests verify event accuracy, changed-field minimization, no-op updates, authorization and rollback behavior. PostgreSQL CI also checks migration and transactional event persistence.

## Limitations and next steps

- The existing local Streamlit demo is separate from the authenticated lead CRUD endpoints.
- Database administrators can still modify or erase audit rows; this is **not immutable evidence**.
- Append-only database privileges, signed/integrity-protected logs, retention controls, monitoring and independent audit storage remain necessary before real business use.
- Live Auth0 login, production PostgreSQL operations, organization-scoped RAG, logging redaction and full security review remain incomplete.
- Do not process real customers' personal information or deploy these development endpoints publicly.
