# Repository security checks

AllSales CRM runs GitHub CodeQL static analysis on Python and JavaScript/TypeScript source.

The workflow is defined in [CodeQL security analysis](../.github/workflows/codeql.yml).

It runs for pull requests targeting `main`, pushes to `main`, a weekly schedule, and manual dispatch. Results are visible under **Security → Code scanning** when GitHub enables code scanning for this repository. The workflow requires permission to write security scan findings, but does not have repository content write access.

CodeQL complements, but does not replace, application security reviews, dependency audits, access-control integration tests, threat modeling, secret scanning, and production testing.

## What is not verified by this workflow

- Live Auth0 and organization onboarding
- Access control for each customer's Dify knowledge
- Dependency reproducibility (the Next.js lockfile still needs generation and validation)
- Rate limiting, production logging, data retention, or backup restoration
- Vulnerability-free code

Do not treat a green CodeQL job as a certification or a sign that the application is safe to deploy.
