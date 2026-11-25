# Local n8n setup

**Status:** Setup instructions; AllSales CRM integration is not yet implemented or tested. Use fictional data only.

## Isolated development instance

Use the n8n image already available locally, a dedicated container and a named volume. Keep any other project's n8n instance, credentials and workflows unchanged. Host port 5679 avoids the existing port 5678; check availability before starting.

From Windows PowerShell:

```powershell
docker ps --format "table {{.Names}}\t{{.Ports}}"
docker image inspect n8nio/n8n:2.48.6 --format '{{.Id}}'
docker run -d --name allsales-n8n --pull never -p 127.0.0.1:5679:5678 -e GENERIC_TIMEZONE=Europe/Amsterdam -e TZ=Europe/Amsterdam -e WEBHOOK_URL=http://127.0.0.1:5679/ -v allsales-n8n-data:/home/node/.n8n n8nio/n8n:2.48.6
docker logs --tail 30 allsales-n8n
```

Open http://localhost:5679 and configure the separate local n8n owner account. Use a unique password; do not reuse Auth0 credentials. If the container already exists, inspect it before running `docker start allsales-n8n`. Do not remove the named volume: it stores workflows, credentials and configuration. The pinned image is for local learning, not a claim of current production security. Review upstream security updates and licensing before any commercial use. See [official Docker installation](https://docs.n8n.io/hosting/installation/docker/).

## First workflow

Build a manual trigger with fictional lead data. Then design the FastAPI approval record, authorization checks, idempotency key and audit trail before connecting the workflow to live endpoints. No schedules, email delivery, external CRM writes or shared credentials. Docker-to-host connectivity requires a separate verified network design; do not weaken the API's loopback restriction merely to make a container connection work.

## Acceptance checks

- Editor opens on the local port; other project containers remain untouched.
- Manual execution with synthetic data only.
- Backend rejects unauthorized, unapproved, expired or duplicate requests.
- An approved local test action produces one auditable result; retries do not duplicate it.

Export only reviewed, sanitized workflow definitions after manual testing; never commit credentials, execution logs or private identifiers.
