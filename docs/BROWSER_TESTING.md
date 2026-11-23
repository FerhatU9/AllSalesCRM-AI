# Browser test coverage

Playwright launches the real Next.js development server and Chromium. The tests exercise the public landing page and check that requests without a valid session are redirected away from the protected workspace. They use **dummy Auth0 configuration**, no real identity-provider account, and no customer data.

## Run locally

From `web/`:

```powershell
npm ci
npx playwright install chromium
npm run test:browser
```

The test server uses `http://127.0.0.1:3000`; stop any other service already using port 3000. Tests run against placeholder Auth0 settings, so they do **not** sign in or create leads. Keep real Auth0 secrets in `web/.env.local` and never commit them. Do not run the browser tests against an internet-facing service.

## What is covered

- The Next.js landing page renders its title, product positioning and sign-in entry point.
- `/workspace` redirects unauthenticated visitors to the login flow.
- A direct visit to an organization lead workspace also requires login.

## Still requires hands-on validation

- A real Auth0 development login, issuer/audience matching and callback flow.
- Organization membership provisioning and role-based access through the browser.
- Creating and updating a fictional lead, then confirming persistence in PostgreSQL after application restart.
- Errors, expired sessions, cross-organization access, and safe handling of retry and failure cases.

These browser smoke tests **do not claim that a complete commercial login or sales journey is working**. Follow [customer web setup](CUSTOMER_WEB.md) and [local onboarding](LOCAL_ONBOARDING.md) for the next stage.
