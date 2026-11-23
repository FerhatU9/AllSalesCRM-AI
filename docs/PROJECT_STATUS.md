# Project status and limitations

**Scope:** Local development prototype with synthetic sales policies, fictional leads and a separate, not-yet-live-tested Auth0 web integration.

## Implemented in code

- Streamlit demonstration using FastAPI endpoints for policy Q&A (Dify Chatflows for Gemini and Claude), and Python-based lead qualification.
- User-selected model fallback restricted to configured temporary provider failures.
- Deterministic lead scoring, routing and escalation recommendations; model output cannot modify these rules.
- Next.js workspace for signing in through Auth0, viewing authorized organizations, and creating or updating synthetic leads. **Actual sign-in with an Auth0 tenant has not been verified.**
- FastAPI OIDC token verification and organization membership enforcement for the account and lead endpoints; the separate Streamlit demo still uses a shared local token.
- SQLAlchemy organization, identity, membership, lead and activity-event models with Alembic migrations.
- A read-only activity endpoint for organization owners/admins, tracking verified actors and field changes.
- Automated Python tests and a disposable PostgreSQL integration workflow.

## Recorded evidence

- An earlier source package recorded **66 passing offline tests**. This is **historical evidence**, not the current test count.
- The saved dual-model evaluation contains 34 final responses across 17 questions per model, **after retries**; the essential policy facts were manually marked correct, with documented limitations.
- Five synthetic local UI scenarios were recorded for the earlier Streamlit demonstration.
- GitHub Actions checks exercise Python 3.11, 3.12, frontend TypeScript/production build and a disposable PostgreSQL test database. Consult current workflow runs for their latest results.

See the [evaluation report](EVALUATION_RESULTS.md), [local validation](LOCAL_VALIDATION.md), [lead activity guide](LEAD_ACTIVITY.md), and [local onboarding](LOCAL_ONBOARDING.md).

## Not yet demonstrated or implemented

- A complete live Auth0 browser login and organization onboarding flow.
- Production application deployment, backups, load testing, rate limiting, monitoring and a security review.
- Organization-specific Dify knowledge access or independently reproduced indexed knowledge in a fresh workspace.
- Actual CRM integrations, approvals or external writes.
- Database-enforced row-level security, tamper-resistant audit retention and safe handling of real customer data.
- Public SaaS billing, customer support, or a completed commercial pilot.

This remains a **synthetic-data local development prototype**, not a production CRM. See the [commercial architecture](COMMERCIAL_ARCHITECTURE.md) and [production development plan](PRODUCTION_PLAN.md).
