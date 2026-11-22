# Security policy

This repository is an educational local prototype of an AI sales-policy assistant, not a production service.

## Supported usage

- **Synthetic lead data and synthetic policy documents only.**
- The development API token is a shared local secret, not a user login or tenant security boundary.
- Do not expose FastAPI or Streamlit to the public internet, run a public cloud deployment, or store real customer information.
- `ALLSALES_ENV` modes other than `local` are deliberately rejected until a secure production architecture exists.
- Docker Compose publishes its services only to the local host. Never remove the loopback bind in a shared deployment.

## Credentials

Keep Dify app keys and the local development token in `.env` outside version control. Provider API keys belong inside the Dify provider configuration, not this repository. If credentials were exposed, revoke and rotate them immediately. Check commit history as well as current files.

## Vulnerability reporting

For non-sensitive issues, use the repository issue tracker. **Do not publish vulnerabilities, credentials, customer data, or exploit details in public issues.** Contact the repository owner privately through an appropriate secure channel for sensitive disclosures.

## Before any live deployment

Require user authentication, authorization, organization-level isolation, signed token checks, rate limiting, monitoring, privacy documentation, threat modeling, backup recovery, secret rotation, and security evaluation. See [commercial architecture](docs/COMMERCIAL_ARCHITECTURE.md).
