> **Historical v0.6 finding (before Dify exports).** Superseded by [v0.7 readiness decision](PORTFOLIO_READINESS_2026-11-18.md) and [workflow-export audit](WORKFLOW_EXPORT_AUDIT.md). The missing-export blocker was resolved after receiving both Dify packages.

# AllSales CRM portfolio code audit — 18 Nov 2026

## Decision: CONDITIONAL / NOT YET APPROVED FOR GITHUB PUBLICATION

The uploaded ZIP contained executable local Streamlit/FastAPI/Dify integration code, a synthetic handbook, 17 golden questions, 34 final recorded model responses, CI configuration and 28 passing unit tests. The updated candidate contains 32 passing tests and fixes several reproducibility/documentation issues.

| Check | Findings | Decision |
| --- | --- | --- |
| Backend routing | Both model keys have distinct Dify paths; per-model conversation IDs | Pass for local prototype |
| Opt-in fallback | Unit tests prove no fallback on auth/quota/timeout and new backup conversation | Pass offline; no live failure-triggered demo |
| Test suite | 28/28 original, 32/32 updated candidate | Pass locally |
| Model evaluation | 34 successful saved after retries; core correct 34, completeness / section-reference exceptions | Pass with caveats |
| Secret scan | No obvious hard-coded active keys found in scanned ZIP; placeholder/test strings detected only | Preliminary pass; review exported Dify files separately |
| Local auth | One static X-API-Key development token, no RBAC/SSO/rate limits | Acceptable only as local demo |
| README | Original described v0.3 and Claude as missing | Fixed in candidate |
| Architecture image | Original PNG showed direct Streamlit→Dify Gemini-only flow | Mermaid current architecture added; old PNG preserved as historical |
| Dify workflow export | Neither Claude nor Gemini workflow exported in uploaded ZIP | **BLOCKER** |
| Knowledge retrieval reproduction | Knowledge file present; actual index parameters & linked knowledge IDs not exported | **BLOCKER** |
| GitHub CI | Compile stage originally omitted `backend/`; corrected | Fixed in candidate |
| URL validation | HTTP localhost-prefix spoof accepted in existing Dify client | Fixed in candidate; regression test added |
| Dev token | Example placeholder was accepted if never changed | Fixed in candidate; rejected |
| Deployment | Local only, no real-user authentication, monitoring, compliance, or CRM actions | Not production ready |

## Boundaries and limitations

- This was static review, local tests and user-supplied screenshots / CSV; no access to the owner's running Dify workspace or fresh-machine environment.
- Source code and documents are educational, not deployed commercial software.
- Tests employ mocked model responses; live end-to-end evidence was supplied earlier, but the actual Dify exports and immutable model configuration were absent.
- No external penetration test or comprehensive dependency vulnerability scanning was performed.

## Gate to portfolio-ready approval

1. Export sanitized **both** Dify Chatflows without secrets. Confirm exports are the tested published versions, not untested drafts.
2. Record retrieval/embedding/index/prompt settings and add a reproducibility test or a clear set of rebuilding instructions. See `docs/DIFY_REPRODUCTION.md`.
3. Run `python -m pytest -q` with the updated files and test a normal query through Streamlit in both routes. Do **not** repeat 34 paid calls.
4. Review `git status` and `git diff --cached` before first GitHub push, ensuring secrets and private results are not staged.

Once done, this is credible as a **portfolio prototype**, not as a production-ready multi-tenant or real-CRM system.
