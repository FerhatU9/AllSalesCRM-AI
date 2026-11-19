# AllSales CRM v0.8 — local live UI validation

**Date:** 19 November 2026  
**Evidence:** user-supplied screenshots from the working local Streamlit application (FastAPI v0.8 on localhost).  
**Scope:** five user-executed scenarios using entirely synthetic CRM data. Screenshot observations only; this is not a fresh-install test, penetration test, or performance benchmark.

| Scenario | Screenshot evidence | Observed result | Finding |
| --- | --- | --- | --- |
| Normal qualified lead (earlier live screenshot) | Previously confirmed in development session | 85/100, Priority A, EU, SMB Sales Team, first contact within one business day | Pass |
| Missing employee count | [Incomplete lead](screenshots/v08_incomplete_lead.png) | Incomplete; score unknown, no assigned tier, region EU, routing pending employee count, queue on hold; missing `employee_count` | Pass |
| Discount of 15% | [Manager approval](screenshots/v08_discount_approval.png) | 85/100 Priority A; qualified but one or more decisions require human review; written manager approval required **before** offering discount | Pass |
| Suspected security incident | [Security escalation](screenshots/v08_security_escalation.png) | 85/100 Priority A; Security Team escalation prioritized before routine follow-up, same-business-day target | Pass |
| Optional Claude policy explanation | [Explanation 1](screenshots/v08_claude_explanation_1.png), [Explanation 2](screenshots/v08_claude_explanation_2.png) | Claude returned an explanation that included 85-point breakdown and policy references | Functional pass; factual commentary requires human review |

## Interpretation and limitations

The first four cases demonstrate expected **rules-based** behavior through the actual local UI and backend. The optional Claude request demonstrates that the **separate, non-authoritative** explanation call can complete, not that every sentence is accurate. It infers possible employee-count ranges from the returned routing classification while the original contact/record details are intentionally withheld. It also speculates about certain scoring information being absent; do not treat this as proof of handbook contents. The deterministic Python output remains the decision source.

This local project does **not** save CRM records, grant approvals, send notifications, or create tickets. The sample records are fictional. Tests should not be presented as evidence of production availability, enterprise security, real-world prediction accuracy, or live automatic model fallback.

## Public portfolio claims supported by this evidence

- Implemented and manually demonstrated a Python rules-based lead qualification workflow behind an authenticated local FastAPI endpoint and Streamlit form.
- Correctly handled incomplete data, an approval-dependent discount, and a security escalation in local demonstrations.
- Added a privacy-reduced, opt-in Claude explanation path without letting an LLM change the computed score.
- Previous automated test suite and 34-response dual-model handbook evaluation are documented separately. Do not confuse response success with generalization or production assurance.
