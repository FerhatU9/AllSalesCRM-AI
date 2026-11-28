# Local n8n setup

**Status:** Local health connectivity and authenticated follow-up workflow have been demonstrated on the draft feature branch at da5af67, including reproduction from the sanitized workflow template and database-only execution. Use fictional data only.

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

## Observed connectivity

The developer created a dedicated local n8n owner account and manually executed a Manual Trigger, Edit Fields (JSON) and HTTP Request sequence. The request to `http://host.docker.internal:8001/health` returned `status: ok` and `version: 0.8.0` without changing the loopback binding. This checks process connectivity only; it does not authorize access to CRM data or perform an action. The sample approval fields are not trusted authorization evidence.

## Authenticated demonstration

Follow the [follow-up automation guide](FOLLOWUP_AUTOMATION.md) to grant the minimum Auth0 client scopes, provision the restricted local machine membership, and import the [sanitized ten-node manual workflow](../n8n-workflows/sales_followup_automation.json). This requires draft PR #32's code, including migrations 004 and 005. The workflow creates a pending request, a human owner approves it in the CRM, and n8n retrieves the stored decision; the final filter retained one matching approved item and the execution node returned `executed`. The machine's attempt to approve returned HTTP 403.

## Acceptance checks

- Demonstrated: isolated local editor, API health, OAuth2 machine token, assigned organization/lead reads, pending request, same-key retry, human decision and result verification.
- Remaining: independent clean-instance reproduction beyond the developer’s separate local workflow import, least-privilege grant review, live replay/timestamp evidence and full PostgreSQL execution concurrency coverage.
- No schedule, real email, outbound integration or external delivery; execution modifies only the follow-up database record. Do not weaken the API's loopback restriction to make a container connection work.

Export only reviewed, sanitized workflow definitions after manual testing; never commit credentials, execution logs or private identifiers.
