# v0.8 — Intelligent lead qualification and sales decision workflow

**Scope:** Educational local prototype. Company, handbook and leads are entirely fictional. The new scoring workflow is **rules-based**, rather than having an LLM guess policy decisions. Dify/Gemini/Claude are used **only when someone explicitly requests a policy explanation**.

## What changed

- In Streamlit, open the **Workspace** radio and select **Lead qualification**.
- Complete the CRM record, scoring evidence and optional exceptions, then choose **Evaluate fictional lead**.
- Streamlit makes an authenticated HTTP POST to `http://127.0.0.1:8000/v1/leads/evaluate`.
- FastAPI checks the input structure and calls `allsales.lead_qualification.evaluate_lead` locally.
- The rule engine returns a score breakdown, qualification state, tier, recommended route, queue state, target, actions, explanations and handbook section numbers.
- No customer record is saved, no CRM mutation takes place, and no message is sent to a sales rep.
- The **optional** model explanation uses `/v1/chat`, sending only the derived policy decision, not original customer identifiers or free-text lead fields. It may consume Dify model-provider credits. It cannot change the deterministic decision.

## Scoring rules — Handbook v1.0

| Factor | Possible points | Rule |
| --- | --- | --- |
| Company fit | 0, 20, 40 | 40 if all three: 10–500 employees, EU/UK, preferred industry. 20 if exactly two. Otherwise 0. |
| Purchase urgency | 0, 10, 25 | 25 if decision in <=30 days; 10 for 31–90; otherwise 0. |
| Authority | 0, 10, 20 | 20 final approver/budget owner, 10 influencer, 0 confirmed none. |
| Engagement | 0, 5, 15 | 15 demo booked, 5 email reply without demo, 0 confirmed neither. |

Score maximum = 100. Priority A = 75–100 and personalized contact within 1 **business** day; B = 50–74 and within 3 business days; C = 0–49 and nurture/review after 30 **calendar** days.

### Important safeguards

1. **Incomplete records never receive a priority tier.** Required company, country, employees, industry, contact, business email, use case, source, consent status and owner are checked; business email has a basic format check. A score may be shown as **provisional** if all scoring factors are known, but qualification must be completed before the priority tier is assigned.
2. **Unknown is not zero.** Unspecified urgency, authority or engagement prevents a final score. This is deliberate; making up a zero could misclassify a lead. An unrecognized country also requires market verification.
3. **Country lookups are deliberately conservative.** The demo recognizes EU member countries, UK and a limited list of common outside-region countries. Unrecognized country spellings/names trigger a manual region review; don't automatically classify them as outside. Country classification is not live geopolitical verification.
4. **Sales-team routing and priority are independent.** EU/UK 10–200 employees goes to SMB; 201–500 Enterprise; >500 Enterprise Sales Manager review; outside EU/UK Sales Manager eligibility review regardless of score; under 10 normally nurture. No records enter a live queue in this demo.
5. **Consent and approvals:** Opted Out prohibits marketing campaigns; Unknown is not permission. Discount greater than 10% requires **written sales manager approval before the offer**. Custom contract terms go to the sales manager. These approval tasks are **recommendations only**.
6. **Urgent exception:** suspected security incident goes to Security Team the same business day; urgent existing-customer outage to Customer Support within 4 business hours. These are escalation targets, NOT resolution guarantees.
7. **No computed calendar dates.** Fictional company holidays aren't supplied, so the system reports business-day targets rather than inventing a precise deadline date.

## Example

Use the Streamlit form defaults: ExampleTech Ltd, Netherlands, 120 employees, SaaS, decision in 20 days, final budget authority, no prior engagement, required synthetic CRM fields present.

Expected result: company fit 40 + urgency 25 + authority 20 + engagement 0 = **85/100**, **Priority A**, **SMB Sales Team**, **first personalized contact within 1 business day**.

A manager review or missing mandatory field may prevent the lead from entering an active queue even when a provisional score is available.

## Run locally

From the project folder containing `app.py`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

In another VS Code terminal:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open `http://localhost:8501` → **Workspace** → **Lead qualification**. Keep the existing `.env` file (never commit it); FastAPI uses the same `API_APP_TOKEN` as the original assistant.

FastAPI also exposes the new endpoint in its local docs: `http://127.0.0.1:8000/docs`.

## Test the API without LLM credits

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_lead_qualification.py
```

The test suite verifies boundaries, missing data, scoring, routing, consent, discounts, security escalation, API authentication and the minimal-data model-explanation prompt. The API route itself makes no Dify calls.

## Limitations and next iteration

- Not an actual CRM integration: no persistent lead storage, task scheduling, sales notifications, user accounts or approvals.
- Country and email checks are demonstration-level. Do not use real customer details.
- The AI explanation is non-authoritative and must be checked against the actual handbook.
- The v0.8 Streamlit interface and backend were verified in a local browser session on **19 November 2026** for the five scenarios listed in [the live UI validation report](LIVE_UI_VALIDATION_2026-11-19.md). This is a single local demonstration, not a fresh-workspace reproducibility or production deployment test.
- Future commercial requirements: real authentication/RBAC, audit trail, regulatory/privacy review, approved CRM data access, time-zone/company-calendar integration, and human approval workflow.

For a quick demonstration without either server or any model credits:

```powershell
.\.venv\Scripts\python.exe -m scripts.demo_lead_decisions
```
