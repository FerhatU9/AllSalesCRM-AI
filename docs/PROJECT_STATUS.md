# Project status and limitations

**Snapshot: November 28, 2026.** Local development prototype using synthetic sales policies, fictional leads and a local development Auth0 tenant. The [technical engineering report](AllSales_CRM_Technical_Report.pdf) records the earlier approval-stage snapshot (1409a49); this status page includes the later execution and sales-intelligence milestones.

## Main foundation

- Separate Streamlit/FastAPI policy Q&A with Dify Gemini and Claude Chatflows, user-selected temporary provider-failure fallback and deterministic Python lead qualification. Model output cannot modify scoring or authorization.
- Next.js workspace with hosted Auth0 login, authorized organizations, synthetic lead CRUD and role-aware presentation.
- OIDC RS256 access-token verification, organization memberships, SQLAlchemy, Alembic and PostgreSQL-compatible lead and activity records.
- Read-only owner/admin lead activity API; lead changes and activity entries commit together. Not a tamper-resistant audit service.
- Python and disposable PostgreSQL test coverage, TypeScript builds, public/unauthenticated Chromium smoke tests and CodeQL.

## Follow-up feature — validated locally, not merged

[Draft PR #32](https://github.com/FerhatU9/AllSalesCRM-AI/pull/32), validated implementation snapshot [da5af67](https://github.com/FerhatU9/AllSalesCRM-AI/commit/da5af676d757e6500026c47b3f2042e8e1210e5b):

- Migrations 004 and 005 add follow-up requests and the restricted automation membership role.
- Organization-scoped follow-up creation/listing, UUID request key, 24-hour expiry, owner/admin decisions, and lead qualification checks.
- Dedicated follow-up UI in the authenticated Next.js workspace. Owner approved/rejected synthetic requests; viewer could read but could not request.
- Auth0 machine identity with `request:followups` and separately authorized `execute:followups` scopes and database membership can read assigned demo organizations/leads and create pending requests. Machine approval attempt returned HTTP 403; machine lead writes are denied.
- n8n manual workflow verified health, organization lookup, qualified lead filtering, request creation, same-key retry, human approval and status retrieval. Final workflow filter retained one matching approved item; the execution endpoint returned `executed`. Execution updates the follow-up record only, with no external delivery. Backend authorization, expiry, qualification and requester ownership checks protect the transition; repeated execution returns the stored result.
- The [sanitized importable workflow](../n8n-workflows/sales_followup_automation.json) passed static contract checks and was imported as a separate local n8n workflow. Screenshots showed a new pending synthetic record and an inactive execution node, followed by the same record in executed state after owner approval. Direct live retry/timestamp comparison is not recorded. See [import guide](FOLLOWUP_AUTOMATION.md) and [n8n setup](N8N_SETUP.md).

## LangGraph recommendation milestone — implemented and demonstrated locally

- Authenticated human-only per-lead GET recommendation endpoint; organization and lead access checked before invoking the graph.
- LangGraph routes stored status and summary presence into a deterministic review or hold checklist. It does not infer policy scores, access free text, call an LLM, retain graph state or create follow-up requests. Remote tracing is disabled.
- Next.js displays the recommendation beside existing human approval controls and shows stored execution timestamps. See [implementation and verification guide](LEAD_RECOMMENDATIONS.md).

## Structured qualification preview — deterministic path and provider connectivity demonstrated

- Active synthetic leads can be evaluated by human owner/admin/sales members in the CRM. The shared policy engine calculates a score and routing; missing facts prevent a tier. The preview itself persists no facts or decisions; explicit save is a separate operation.
- A separate LangGraph conditional branch explains derived policy facts through the explicitly selected Dify Gemini or Claude Chatflow. No raw contact identifiers, free text, CRM tokens or tenant IDs enter that prompt. This is advisory, not approval; failed provider calls preserve the deterministic result.
- The existing approval/execution boundary remains independent. See [qualification preview guide](QUALIFICATION_PREVIEW.md).

## Qualification history and sales intelligence — implemented, local validation pending

- Migration 006 adds append-only derived decision snapshots linked to the lead and verified human reviewer. Explicit save re-evaluates the rules and rejects changed decisions; same-key retries return the existing snapshot. Raw form inputs and Dify text are excluded.
- Human owner/admin/sales members may save; viewers read only. Machine callers and unassigned tenants are denied. The dashboard counts latest saved decisions per active lead, not historical repetitions; archived history remains readable.
- No lead status update, follow-up approval, delivery or model call occurs during save. See [qualification history and dashboard](QUALIFICATION_HISTORY.md).

## Recorded evidence

| Evidence | Result and limitation |
| --- | --- |
| Recommendation implementation checkout | 130 passed, 1 skipped, 7 warnings, 21 subtests passed; TypeScript and synthetic Next.js build passed. Owner panel and execution timestamps demonstrated locally. |
| Qualification preview implementation checkout | 135 passed, 1 skipped, 7 warnings, 21 subtests passed; TypeScript and production build passed. Provider integration mocked; the authenticated local preview returned 85/100 Tier A for the synthetic sample. Initially both provider keys were missing; after configuring them, both live model routes returned a canonical no-evidence answer. Connectivity is demonstrated, grounded explanation quality is not. |
| Retrieval-query and abstention update | 152 passed, 1 skipped, 7 warnings, 21 subtests passed; TypeScript/build passed. Explicit handbook-section query; distinguish a model's no-evidence response from completed explanation, with score unchanged. Live revised query demonstrated: Gemini supported all four components, tier and routing; Claude supported tier and routing but abstained on the breakdown. Neither reported source documents; grounded citation completeness remains unverified. |
| Qualification history/dashboard checkout | 153 passed, 1 skipped, 10 warnings, 21 subtests passed; TypeScript/build passed. PostgreSQL CI case extended; new live local persistence journey pending. |
| GitHub Actions at b1dcccc | 5/5: Python, web, browser smoke, PostgreSQL integration and CodeQL |
| Local full Python regression at da5af67 | 122 passed, 1 skipped, 7 warnings, 21 subtests passed (developer-observed) |
| GitHub Actions at da5af67 | 5/5: Python, web, browser smoke, PostgreSQL integration and CodeQL |
| Local PostgreSQL | Migration 005 applied; real local synthetic lead and follow-up data persisted |
| Local human identity journey | Login/logout; creation/update; persistence across sessions; unassigned identity, cross-organization 404, viewer presentation; owner approval/rejection |
| Local machine journey | Successful token, restricted organization, request, 403 approval denial, approved-result verification and database-only execution |
| Dual-model evaluation | 34 final answers across 17 curated questions/model after retries; correct essential facts in manual review, with completeness and reference limitations |
| Earlier local baseline | 118 passed, 1 skipped, 4 warnings, 21 subtests passed; historical, not a current total |
| Earlier source package | 66 passing offline tests; historical baseline |

The dedicated PostgreSQL CI workflow covers migrations and lead isolation. Follow-up and machine cases were tested with targeted SQLite API tests and live local PostgreSQL; full PostgreSQL concurrency coverage and authenticated browser automation are still outstanding. See [evaluation report](EVALUATION_RESULTS.md), [local validation](LOCAL_VALIDATION.md), [lead activity guide](LEAD_ACTIVITY.md), [local onboarding](LOCAL_ONBOARDING.md) and [current Actions runs](https://github.com/FerhatU9/AllSalesCRM-AI/actions).

## Remaining gates

- Review least-privilege Auth0 grants, the locally reproduced template, direct live replay/timestamp evidence, the draft feature and full PostgreSQL execution concurrency/ownership and changed-lead-state cases. No scheduled execution or real outreach.
- Self-service organization onboarding, invitations, role administration, full authenticated browser automation and live-token negative write tests.
- Validate the new qualification history/dashboard against local PostgreSQL and investigate missing Dify source reporting; validate grounded model explanations using synthetic data. The deterministic authenticated preview has been demonstrated. Organization-specific retrieval, source-span citations, abstention and leakage evaluation remain outstanding.
- Database-enforced tenant isolation, tamper-resistant audit retention, independent security/privacy assessment.
- Staging deployment, backups and restore drills, load testing, rate limiting, monitoring, support and controlled pilot.

**Development only.** Approval is not execution; passing tests do not establish commercial readiness. Read the [commercial architecture](COMMERCIAL_ARCHITECTURE.md), [production plan](PRODUCTION_PLAN.md) and [security policy](../SECURITY.md).
