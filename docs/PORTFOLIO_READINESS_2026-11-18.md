# AllSales CRM — portfolio release readiness (v0.7)

**Decision: APPROVED AS A PUBLIC GITHUB PORTFOLIO PROTOTYPE**, subject to final review of the user's local `git add`/`git diff --cached` before the first push. **NOT** approved as a secure, public-facing production CRM or commercial service.

## Evidence

- Source was inspected and the offline Python test suite passed in the audit environment.
- The original workflow packages were parsed, matched to two known model configurations, and checked for manifest integrity.
- Two **sanitized** Dify app packages are now included. Import instructions explain how to create and rebind a fresh synthetic handbook knowledge base.
- An earlier live run demonstrated Gemini and Claude answering through Streamlit → FastAPI → Dify; this review did **not** re-run paid API calls.
- The saved evaluation covers 17 curated questions x 2 models, with all 34 final answers successfully recorded after retries. Manual review found 34/34 correct **core policy answers**, with disclosed completeness and section-reference limitations.
- Source/document contents contain only fictional company policies and training scenarios, and the published packages remove the workspace knowledge-base identifier. No obvious keys were detected by pattern-based scan; this does **not** replace a secret scanner on the final Git staging area or entire Git history.

## Limitations to state honestly on a CV or README

- Local development prototype, not deployed public SaaS.
- Dify knowledge base must be re-created and indexed externally; exact index reproducibility was not validated in a new workspace.
- Shared development token is not per-user identity, authorization, roles, access-control lists or tenant separation.
- Offline tests exercise simulated errors; real automatic fallback during a provider outage has not been demonstrated.
- 17 synthetic questions are insufficient to claim general accuracy or robust adversarial resistance.
- No dependency vulnerability scan or production penetration test was run as part of this review.

## GitHub publication procedure

1. Check `.env` is never included; the public zip includes only `.env.example` with blanks/placeholders.
2. In the project root use `git status`, then `git add .`, then `git diff --cached --name-only` and inspect `git diff --cached`/`git diff --cached --stat`. Ensure no `.env`, `.venv`, secrets, local `results/`, backups or token-bearing logs.
3. Run `python -m pytest -q` and verify no new failures. Record the test count accurately.
4. Publish a repository description such as: **“Evaluated dual-model RAG sales-policy assistant using FastAPI, Streamlit, Dify, Gemini and Claude — synthetic data, opt-in fallback, offline tests.”**
5. For interviews, demonstrate the local application and discuss reproducibility limitations; do not claim real production deployment.
