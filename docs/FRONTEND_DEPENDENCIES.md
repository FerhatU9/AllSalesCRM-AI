# Frontend dependency installation

The Next.js application uses a committed npm lockfile: `web/package-lock.json`.

- Use Node.js 22 with a supported npm release.
- Run `npm ci` from `web/` for reproducible dependency installation. It refuses to silently modify the lockfile.
- Run `npm run typecheck` and `npm run build` after changes.
- To intentionally update dependencies, change `web/package.json`, run `npm install` in `web/`, review both the manifest and lockfile differences, and validate a clean `npm ci` installation before committing.
- GitHub Actions caches npm downloads using the lockfile and runs `npm ci`. It then checks TypeScript and builds the frontend with synthetic configuration.

The lockfile was generated using the npm registry in a GitHub-hosted runner and verified in that runner with `npm ci`, TypeScript and the Next.js build. It captures **dependency resolution**, not a security guarantee. Dependabot changes still need individual compatibility and security review.

These checks do not replace end-to-end Auth0/browser testing or establish deployment readiness.
