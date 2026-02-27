import { test, expect } from "../fixtures/auth.fixture";

test.describe("Scan Progress Page", () => {
  test("shows failed state when scan fails", async ({
    authedPage: page,
  }) => {
    await page.route("**/api/user/scans/scan_failed_123", (route) =>
      route.fulfill({
        json: {
          id: "scan_failed_123",
          status: "failed",
          report_data: null,
        },
      }),
    );

    await page.goto("/scan/scan_failed_123");
    await expect(
      page.getByText("Scan failed unexpectedly"),
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByRole("link", { name: "Back to Dashboard" }),
    ).toBeVisible();
  });

  test("shows error when poll request fails", async ({
    authedPage: page,
  }) => {
    await page.route("**/api/user/scans/scan_err_456", (route) =>
      route.fulfill({
        status: 500,
        json: { detail: "Internal error" },
      }),
    );

    await page.goto("/scan/scan_err_456");
    await expect(
      page.getByText("Failed to load scan status"),
    ).toBeVisible({ timeout: 10000 });
  });

  test("shows View Full Report link on completed scan", async ({
    authedPage: page,
  }) => {
    await page.route("**/api/user/scans/scan_done_789", (route) =>
      route.fulfill({
        json: {
          id: "scan_done_789",
          status: "completed",
          repo_name: "sindresorhus/is",
          report_data: { discovery_report: { total_findings: 5 } },
        },
      }),
    );

    await page.goto("/scan/scan_done_789");
    await expect(page.getByText("Scan Complete")).toBeVisible({
      timeout: 10000,
    });

    // Verify report link
    await expect(
      page.getByRole("link", { name: "View Full Report" }),
    ).toHaveAttribute("href", "/scan/scan_done_789/report");
  });
});
