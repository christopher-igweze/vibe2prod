import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isProtectedRoute = createRouteMatcher([
  "/dashboard(.*)",
  "/scan(.*)",
  "/settings(.*)",
  "/onboarding(.*)",
]);

// In E2E test mode, run clerkMiddleware for proper Clerk SDK initialization
// but skip auth.protect() so unauthenticated Playwright tests can access
// protected routes.
const isE2ETesting = process.env.E2E_TESTING === "true";

export default clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req) && !isE2ETesting) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
