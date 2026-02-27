import { test, expect } from "../fixtures/auth.fixture";
import { setupHappyPathMocks } from "../fixtures/api-mocks";

test.describe("Scan Wizard - Validation", () => {
  test.beforeEach(async ({ authedPage: page }) => {
    await setupHappyPathMocks(page);
  });

  test("shows error for invalid GitHub URL", async ({
    authedPage: page,
  }) => {
    await page.goto("/scan/new");
    await page.locator("#repo-url").fill("not-a-valid-url");
    await page.getByRole("button", { name: "Continue" }).click();

    await expect(page.getByText("Must be a valid GitHub URL")).toBeVisible();
  });

  test("Continue button is disabled when repo URL is empty", async ({
    authedPage: page,
  }) => {
    await page.goto("/scan/new");
    await expect(
      page.getByRole("button", { name: "Continue" }),
    ).toBeDisabled();
  });

  test("Review & Submit button is disabled with empty intake form", async ({
    authedPage: page,
  }) => {
    await page.goto("/scan/new");

    await page
      .locator("#repo-url")
      .fill("https://github.com/sindresorhus/is");
    await page.getByRole("button", { name: "Continue" }).click();

    // Step 2 with empty fields — Review & Submit should be disabled
    await expect(page.locator("#product-summary")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Review & Submit" }),
    ).toBeDisabled();
  });

  test("prevents submission when project limit is reached", async ({
    authedPage: page,
  }) => {
    // Override quota mock to show exhausted quota
    await page.route("**/api/limits", (route) =>
      route.fulfill({
        json: { tier: "forge", project_count: 3, project_limit: 3 },
      }),
    );

    await page.goto("/scan/new");

    await page
      .locator("#repo-url")
      .fill("https://github.com/sindresorhus/is");
    await page.getByRole("button", { name: "Continue" }).click();

    // Skip intake
    await page.getByRole("button", { name: "Skip for now" }).click();

    // Step 3 — Start Audit should be disabled because 3/3
    await expect(page.getByText("3 / 3")).toBeVisible({ timeout: 5000 });
    await expect(
      page.getByRole("button", { name: "Start Audit" }),
    ).toBeDisabled();
  });

  test("shows error when audit submission returns 403", async ({
    authedPage: page,
  }) => {
    await page.route("**/api/audit", (route) =>
      route.fulfill({
        status: 403,
        json: {
          detail: JSON.stringify({
            code: "limit_projects_exceeded",
            message: "Project limit reached",
          }),
        },
      }),
    );

    await page.goto("/scan/new");

    await page
      .locator("#repo-url")
      .fill("https://github.com/sindresorhus/is");
    await page.getByRole("button", { name: "Continue" }).click();

    await page.getByRole("button", { name: "Skip for now" }).click();

    await page.getByRole("button", { name: "Start Audit" }).click();

    await expect(
      page.getByText("free tier project limit"),
    ).toBeVisible({ timeout: 5000 });
  });

  test("handles rate limiting (429) gracefully", async ({
    authedPage: page,
  }) => {
    await page.route("**/api/audit", (route) =>
      route.fulfill({
        status: 429,
        json: { detail: "Rate limited" },
      }),
    );

    await page.goto("/scan/new");

    await page
      .locator("#repo-url")
      .fill("https://github.com/sindresorhus/is");
    await page.getByRole("button", { name: "Continue" }).click();

    await page.getByRole("button", { name: "Skip for now" }).click();

    await page.getByRole("button", { name: "Start Audit" }).click();

    await expect(page.getByText("Rate limited")).toBeVisible({ timeout: 5000 });
  });
});
