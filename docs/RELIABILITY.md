# Model availability & opt-in fallback (v0.4)

Gemini Flash-Lite answered successfully in Dify on 18 Nov 2026 after an earlier
Gemini Flash model was overloaded. This is evidence for one successful call,
not a guarantee of availability.

## What this upgrade does
- Per-request checkbox (OFF by default) to allow a backup provider during
  temporary model overload (Dify HTTP 503/502/504 or a known wrapped HTTP 400 high-demand error).
- **No automatic fallback** on 401/403 (invalid access), 429 (rate/quota), timeout
  (unknown if prior POST succeeded), or a model answer saying no policy found.
- Exactly one backup attempt; never loops across providers.
- Fallback creates a fresh conversation in the backup provider. Streamlit **does
  not** store that ID under the originally selected model and visibly labels it.
- Never sends API keys to the browser; still local-only and NOT production authentication.

## Upgrade existing Windows project without losing API keys
1. Backup your current `app.py` and `backend/api.py`.
2. Replace these two files with the supplied v0.4 versions (copy folder contents,
   keeping the same `backend` directory). Add `tests/test_fallback.py`.
3. Keep your current `.env` and `.venv`; DO NOT overwrite or share them.
4. From the VS Code project folder run ` .\.venv\Scripts\python.exe -m pytest -q`.
5. Stop the previous FastAPI process with Ctrl+C in **its** terminal, then start
   ` .\.venv\Scripts\python.exe -m uvicorn backend.api:app --host 127.0.0.1 --port 8000`.
   If port 8000 is occupied, stop ONLY your old FastAPI process; don't start another.
6. Refresh Streamlit at `http://localhost:8501` (Streamlit normally reloads on file changes).
7. Run one normal Gemini Flash-Lite question and one Claude question. Leave the
   fallback checkbox off. Then optionally test fallback with a mocked offline test.

## Dify publication reminder
If you changed Gemini's model within the Dify editor, **Publish** the latest
version. The Dify preview tests the draft while API calls may use the published
workflow. Don't change the Dify app key for the model switch.

## Future production requirements
Real user identities, tenant isolation, per-tenant provider authorization and
privacy settings, per-user rate limits, audit records, latency budgets, idempotent
request handling, model health tracking, backoff policy, and a proper graded
regression suite. Automatic cross-provider routing is inappropriate until
customers explicitly approve both providers for their data.
