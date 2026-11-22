# Containerized local development

This Docker Compose setup runs the existing FastAPI backend and Streamlit interface on a developer's **own computer**. It is **not** a public deployment or commercially secure environment.

## Prerequisites

- Docker Engine / Docker Desktop with Compose
- A Dify workspace with the two Chatflows and synthetic handbook configured

## Start

From the repository root:

```powershell
Copy-Item .env.example .env
```

Generate a development token using:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put that token into `API_APP_TOKEN` in `.env`. Add the two **Dify application** API keys. Do not store the underlying Gemini or Anthropic provider credentials in this file. Set `ALLSALES_ENV=local`. Never commit `.env`.

```powershell
docker compose up --build
```

Use `http://127.0.0.1:8501` for the Streamlit UI and `http://127.0.0.1:8000/health` for the process health check. The API is only reachable on the host loopback interface. The UI connects to the API through the Compose service name `api`.

Stop with `Ctrl+C`, then run `docker compose down`.

## Local checks

```powershell
docker compose config
docker compose ps
```

A successful `/health` check does **not** mean Dify or its language-model providers are available. A real policy question may consume Dify credits.

## Security boundaries

- Both host ports are bound to `127.0.0.1`. Do **not** change them to public interfaces.
- A common shared development token is passed to both containers. It is **not** production authentication.
- `ALLSALES_ENV` is fail-closed for nonlocal modes. It must not be circumvented to deploy publicly.
- Containers run as a non-root user. Secrets are provided as local environment variables and excluded from the image build context.
- No real customer information, external CRM writes, user isolation or persistent multi-tenant data are supported.

For planned production infrastructure, see [commercial architecture](COMMERCIAL_ARCHITECTURE.md).
