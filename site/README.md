# AllSales CRM — Public website

This folder contains the **static public showcase** of AllSales CRM. It is not the Next.js application or a hosted CRM service.

## What the website shows

- Product purpose and capabilities implemented in the source code.
- Screenshots taken from the documented local Streamlit demonstration, using fictional records.
- Architecture of the original Dify policy assistant and the separate Next.js/FastAPI/PostgreSQL workspace.
- Current limitations, development roadmap and a link to this repository.

The site contains no customer credentials, real customer data, API tokens, login requests, model API calls or contact forms. It does not connect to the existing development services.

## Local preview

Open `site/index.html` in a browser, or run a basic local server from the repository root:

```powershell
py -m http.server 8080 --directory site
```

Then visit `http://127.0.0.1:8080`.

To run the standalone site tests:

```powershell
py -m unittest discover -s tests -p test_public_site.py -v
```

## Publishing to GitHub Pages

The workflow in `.github/workflows/site.yml` validates the site and prepares GitHub Pages deployment from the `site/` folder on pushes to `main`. It uses GitHub-hosted Actions and never deploys FastAPI, Dify, Next.js, PostgreSQL or any internal service.

**The repository owner must configure GitHub Pages if it is not already enabled:**

1. Open **Settings → Pages** for `FerhatU9/AllSalesCRM-AI`.
2. Under **Build and deployment**, choose **GitHub Actions**.
3. Open **Actions → AllSales CRM website**, and run the workflow if publication does not start automatically after the setting is enabled.
4. Confirm the deployment shows success before sharing the public website URL.

Expected project-site address after a successful Pages deployment:

`https://ferhatu9.github.io/AllSalesCRM-AI/`

An expected address is not proof that the site is live. A successful GitHub Pages deployment and a visit to the URL must be verified first.

## Source of screenshots

The three website images reuse the image bytes from `docs/screenshots/` in this repository; the CI test checks they match. The web site does not fabricate live account dashboards or business results.

## Production boundaries

GitHub Pages can serve this static showcase only. A complete commercial AllSales CRM requires separate secure hosting, a working identity provider, database isolation, compliant data processing, operations and a security review. See the [roadmap](../docs/PRODUCTION_PLAN.md).
