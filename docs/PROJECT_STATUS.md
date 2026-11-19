# Project status and limitations

**Scope:** Local development prototype using synthetic sales policies and fictional CRM leads.

## Implemented

- Streamlit and FastAPI with dedicated Dify Chatflows for Gemini and Claude.
- Handbook-grounded policy Q&A with user-selected model and opt-in fallback.
- Deterministic scoring, lead qualification, routing, follow-up recommendations and escalations.
- Optional model-generated explanation that cannot override the Python decision engine.
- Synthetic handbook, sanitized Dify exports, setup guidance and offline tests.

## Recorded evidence

- **66 offline tests passed** in the previously validated source package.
- **34 final model responses** across 17 questions per model, collected after retries. All essential policy answers were manually marked correct, with disclosed omissions and section-number issues.
- **Five local UI scenarios** were documented in the local validation report.

See [evaluation results](EVALUATION_RESULTS.md) and [local validation](LOCAL_VALIDATION.md) for methodology and limitations.

## Not demonstrated

- Fresh-workspace Dify reproduction and exact matching knowledge index.
- A real provider-outage automatic fallback.
- Real CRM integration, persistent records, notifications or automated external actions.
- Production user accounts, role-based permissions, multi-tenant security, monitoring or penetration testing.

This project is a local educational prototype, not a production CRM. See the [production development plan](PRODUCTION_PLAN.md).
