import { test as base, type Page } from "@playwright/test";

/**
 * Custom test fixture providing an `authedPage`.
 *
 * Auth is bypassed via E2E_TESTING=true which makes clerkMiddleware skip
 * auth.protect(). Clerk SDK still initializes normally so useAuth() works,
 * but getToken() returns null (no real session). All API calls are mocked
 * via page.route() so the null token is irrelevant.
 */
export const test = base.extend<{ authedPage: Page }>({
  authedPage: async ({ page }, use) => {
    await use(page);
  },
});

export { expect } from "@playwright/test";
