# Qualification history and sales intelligence dashboard

**Status (28 November 2026):** implemented on the draft feature branch; offline API/migration tests, TypeScript and a synthetic-config production build passed. The real authenticated browser and local PostgreSQL journey for this milestone remain to be demonstrated.

## Why this milestone exists

The qualification preview computes a recommendation without changing the CRM. A reviewer can now explicitly save that deterministic decision, then compare saved evaluations across active leads. Dify is not required and no model output is persisted. The record is a historical recommendation, not a new lead status, follow-up approval or authorization to contact anyone.

| Component | Responsibility |
| --- | --- |
| Next.js | Confirm synthetic inputs, preview, explicitly save, present history and organization metrics |
| FastAPI | Verify human membership, recalculate score and compare the reviewed decision fingerprint |
| SQLAlchemy / PostgreSQL | Persist derived decision, reviewer identity, lead link, request key and timestamp |
| Alembic 006 | Add the qualification records table and lookup index without modifying existing lead or follow-up records |
| Python rules / LangGraph | Use the same handbook rules for preview and save; optional Dify branch is preview-only |

The policy version, score components, tier, routing, flags, policy actions and source section labels are saved, together with the lead's status at save time. Raw form fields (including contact name, email, assigned owner and summary) and model explanations are not saved. Derived policy details such as a requested discount can appear in the policy actions. The server records the verified reviewing identity ID; the UI does not display identity credentials. The snapshot is append-only through the application, not a tamper-proof audit log. Changing policy rules or lead status may make older decisions stale; the dashboard shows the latest saved decision, not an automatic recalc.

## Local demonstration (synthetic data only)

Stop the running FastAPI service before applying the additive migration. From the activated project virtual environment:

```powershell
git pull --ff-only origin feature/followup-approval
python -m alembic upgrade head
python -m alembic current
python -m pytest -q
```

Expected current revision: `006_qualification_records (head)`. Keep the existing database and credentials; don't reset or downgrade a database with records you want to retain. Restart the FastAPI and Next.js services using their existing configuration.

1. Sign in at your configured local frontend origin. Open **AllSales Demo** → **View qualification** for Nordvale Technologies (or **Evaluate lead** from Follow-ups).
2. Load the synthetic example, confirm fictional data, select **Local rules only** and preview. Expect 85/100, Tier A and SMB Sales Team routing. No snapshot is created by preview.
3. Read the result and click **Save qualification**. Confirm the new decision appears under **Saved qualification history**. Refresh the page; it should remain.
4. Open **Sales intelligence dashboard**. The evaluated count and Tier A count should include this lead once. Unassessed active leads appear as not evaluated; archived leads are excluded from the dashboard.
5. Optional: load the example again, change Days to decision to 45 and Decision authority to None; confirm, preview (50/100, Tier B) and save. History should have two decisions; the dashboard counts only the latest (Tier B). The CRM status and follow-up history must remain unchanged.
6. With an existing viewer account, verify history/dashboard are readable without save controls. A machine caller cannot read or save snapshots; another tenant cannot access them.

No Dify call or extra provider cost is needed.

## API contract

- `POST /v1/organizations/{organization_id}/leads/{lead_id}/qualification-preview` remains read-only, now returning `review_digest`.
- `POST /v1/organizations/{organization_id}/leads/{lead_id}/qualifications` requires owner/admin/sales; body contains the same `facts`, `confirm_synthetic: true`, a UUID `request_key`, and the reviewed `review_digest`. The server derives the reviewer and recalculates the same deterministic output. No score, model output or identity can be provided as input. A new snapshot returns 201; retry with the same reviewer, key and decision digest returns the stored snapshot (200). A conflicting key/reviewer or changed decision returns 409. A stale preview is not a substitute for authorization. The fingerprint is a consistency guard, not a signature or evidence that a person read it.
- `GET /v1/organizations/{organization_id}/leads/{lead_id}/qualifications?limit=50&offset=0` returns snapshots newest first, including archived lead history. Human members including viewers may read.
- `GET /v1/organizations/{organization_id}/qualification-dashboard?limit=50&offset=0` returns organization-wide active lead counts and a page of latest decisions. Tier counts include scored recommendations; the no-tier bucket contains incomplete or clarification decisions. A tier does not mean policy exceptions have been cleared.

Read and write paths are tenant-scoped, human-only, and no-store. PostgreSQL locks the lead row during save to protect against concurrent status changes; the same lead/request key is database-unique. The dashboard uses latest sequence per lead, not the number of historical evaluations; count and page queries may observe different committed states during concurrent writes. No follow-up, lead write or model call occurs on save. Offset pages are bounded; historical records retain their stored policy version. Future policy schema evolution will need backward-compatible history decoding.

## Evidence and remaining gates

- Automated migration 005 → 006 on populated SQLite data; downgrade tested on disposable data only. API regression covers no-write preview, recomputation, invalid submitted scores, stale decisions, same-key retry, conflicting actor, viewer/machine denial, cross-tenant access, archived history, aggregate/latest semantics, pagination, data minimization and unchanged lead/follow-up records.
- The disposable PostgreSQL CI case now verifies 006, save/retry, tenant isolation, dashboard JSON aggregates and reviewer persistence. PostgreSQL-specific execution is skipped without a disposable service.
- Full local suite: **153 passed, 1 skipped, 10 warnings, 21 subtests passed**. TypeScript and synthetic production build passed. The new authenticated browser journey, running against the developer's existing local PostgreSQL, remains pending. No live provider calls were made for this milestone.
- Database-enforced tenancy, immutable audit infrastructure, real-lifecycle schema versioning, concurrent load testing, authenticated browser automation, production privacy review and controls remain release gates.
