import { test, expect } from "../fixtures/auth.fixture";
import {
  setupHappyPathMocks,
  MOCK_AUDIT_RESPONSE,
} from "../fixtures/api-mocks";

test.describe("Scan Wizard - Happy Path", () => {
  test.beforeEach(async ({ authedPage: page }) => {
    await setupHappyPathMocks(page);
  });

  test("completes scan wizard with intake form filled", async ({
    authedPage: page,
  }) => {
    // Step 1: Enter repo URL
    await page.goto("/scan/new");
    await expect(page.locator("h1")).toContainText("New Scan");

    await page.locator("#repo-url").fill("https://github.com/sindresorhus/is");
    await page.getByRole("button", { name: "Continue" }).click();

    // Step 2: Fill intake form
    await expect(page.locator("#product-summary")).toBeVisible();

    await page
      .locator("#product-summary")
      .fill("A TypeScript type-checking utility library");
    await page
      .locator("#target-users")
      .fill("TypeScript developers building type-safe apps");

    await page.getByText("None", { exact: true }).click();
    await page.locator("#deployment-target").fill("npm registry");
    await page.locator("#scale-expectation").fill("Library — no server");

    await page.getByRole("button", { name: "Review & Submit" }).click();

    // Step 3: Review
    await expect(page.getByText("Confirm your scan details")).toBeVisible();
    await expect(
      page.getByText("https://github.com/sindresorhus/is"),
    ).toBeVisible();

    await page.getByRole("button", { name: "Start Audit" }).click();

    // Should redirect to progress page
    await page.waitForURL(`**/scan/${MOCK_AUDIT_RESPONSE.scan_id}`);
    await expect(page.getByText("Scanning your codebase")).toBeVisible();
  });

  test("completes scan wizard by skipping intake form", async ({
    authedPage: page,
  }) => {
    // Step 1: Enter repo URL
    await page.goto("/scan/new");

    await page.locator("#repo-url").fill("https://github.com/sindresorhus/is");
    await page.getByRole("button", { name: "Continue" }).click();

    // Step 2: Skip intake entirely
    await expect(page.locator("#product-summary")).toBeVisible();
    await page.getByRole("button", { name: "Skip for now" }).click();

    // Step 3: Review & submit (no intake details shown)
    await expect(page.getByText("Confirm your scan details")).toBeVisible();

    await page.getByRole("button", { name: "Start Audit" }).click();

    await page.waitForURL(`**/scan/${MOCK_AUDIT_RESPONSE.scan_id}`);
    await expect(page.getByText("Scanning your codebase")).toBeVisible();
  });

  test("progress page transitions from scanning to completed", async ({
    authedPage: page,
  }) => {
    await page.goto(`/scan/${MOCK_AUDIT_RESPONSE.scan_id}`);

    // Initially shows scanning state
    await expect(page.getByText("Scanning your codebase")).toBeVisible();

    // Wait for completed state (mock returns completed after 2 polls at 4s each)
    await expect(page.getByText("Scan Complete")).toBeVisible({
      timeout: 15000,
    });

    // Verify report link exists
    await expect(
      page.getByRole("link", { name: "View Full Report" }),
    ).toBeVisible();
  });
});
