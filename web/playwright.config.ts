import { randomBytes } from "node:crypto";
import { defineConfig, devices } from "@playwright/test";

const baseURL = "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./tests/browser",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "npm run dev",
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    env: {
      AUTH0_DOMAIN: "example.eu.auth0.com",
      AUTH0_CLIENT_ID: "browser-test-client",
      AUTH0_CLIENT_SECRET: "browser-test-secret",
      AUTH0_SECRET: randomBytes(32).toString("hex"),
      APP_BASE_URL: baseURL,
      AUTH0_AUDIENCE: "https://api.allsales.local",
      BACKEND_INTERNAL_URL: "http://127.0.0.1:8000",
    },
  },
});
