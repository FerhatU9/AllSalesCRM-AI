import { expect, test } from "@playwright/test";

test("landing page clearly identifies the development application", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle(/AllSales CRM/);
  await expect(page.getByRole("heading", { name: "Decisions your sales team can trust." })).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in to workspace" })).toHaveAttribute("href", "/auth/login");
  await expect(page.getByText("Development environment", { exact: false })).toBeVisible();
  await expect(page.getByRole("region", { name: "Product capabilities" })).toBeVisible();
});

for (const path of ["/workspace", "/workspace/00000000-0000-4000-8000-000000000001"]) {
  test(`unauthenticated visitors cannot access ${path}`, async ({ request }) => {
    const response = await request.get(path, { maxRedirects: 0 });
    expect([302, 303, 307, 308]).toContain(response.status());
    const location = response.headers()["location"];
    expect(location).toBeTruthy();
    expect(new URL(location!, "http://127.0.0.1:3000").pathname).toBe("/auth/login");
  });
}
