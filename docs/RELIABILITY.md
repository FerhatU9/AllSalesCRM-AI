# Reliability and opt-in model fallback

The application uses separate Gemini and Claude Chatflows through Dify. The backup provider is only attempted when the user opts in.

## Fallback behavior

- Fallback is **off by default** and is limited to one backup attempt for recognized temporary provider errors, including HTTP 502/503/504 and known high-demand failures.
- Authentication failures (401/403), rate/quota failures (429), timeouts, and ordinary no-policy answers are not retried with a backup provider.
- Backup requests use a separate conversation ID and the interface labels which model answered.
- Model credentials remain on the backend; they are not sent to the browser.

These behaviors have been exercised in offline tests. **A live provider-outage fallback has not been demonstrated.**

## Verify locally

Use the [README](../README.md) for setup. From the repository root, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_fallback.py
```

For a normal integration smoke test, start the two local services and send one synthetic handbook question to each configured model. Live requests can incur provider charges.

## Limitations

The shared development token is not real user authentication. This local prototype has no tenant isolation, per-user authorization, production rate limits, or operational monitoring. Do not send real customer data or expose it publicly.

See the [production development plan](PRODUCTION_PLAN.md) for future hardening.
