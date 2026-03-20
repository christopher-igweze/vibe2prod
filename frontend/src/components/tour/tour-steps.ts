export type TechnicalLevel = "engineer" | "vibe_coder" | "founder";

export interface TourStep {
  element: string;
  popover: {
    title: string;
    description: string;
    side: "top" | "bottom" | "left" | "right";
  };
}

// ---------------------------------------------------------------------------
// Dashboard Tour (5 steps)
// ---------------------------------------------------------------------------

export function getDashboardTourSteps(level: TechnicalLevel): TourStep[] {
  return [
    {
      element: '[data-tour="new-scan-btn"]',
      popover: {
        title: "Start a New Scan",
        description: {
          engineer:
            "Triggers FORGE's 12-agent discovery pipeline: SAST analysis, architecture review, and OWASP-mapped security audit. Paste any GitHub URL to begin.",
          vibe_coder:
            "Paste your GitHub repo link here to scan your code. We'll find security issues, bugs, and things to fix before you ship.",
          founder:
            "This is where your team audits code before shipping. Each scan finds risks that could cause downtime, security incidents, or tech debt.",
        }[level],
        side: "bottom",
      },
    },
    {
      element: '[data-tour="scan-list"]',
      popover: {
        title: "Your Projects & Scans",
        description: {
          engineer:
            "Scans are grouped by project (repo). Each shows health, security, reliability, and scalability scores. Click any scan to view the full discovery report.",
          vibe_coder:
            "All your previous scans show up here, grouped by project. Click any one to see what was found and track how your code improves over time.",
          founder:
            "Your project portfolio at a glance. Track health scores across every codebase to identify which products need attention before launch.",
        }[level],
        side: "top",
      },
    },
    {
      element: '[data-tour="stats-panel"]',
      popover: {
        title: "Health Overview",
        description: {
          engineer:
            "Aggregated metrics across all scans: average scores, severity distribution, and trend data. Useful for tracking regression across sprints.",
          vibe_coder:
            "A quick summary of how your code is doing overall. Watch these numbers improve as you fix issues from your scans.",
          founder:
            "Key metrics showing the production readiness of your entire portfolio. Use this to report progress to stakeholders or investors.",
        }[level],
        side: "bottom",
      },
    },
    {
      element: '[data-tour="wallet-link"]',
      popover: {
        title: "Wallet & Credits",
        description: {
          engineer:
            "Scans are charged based on repo size and complexity. Your balance is deducted per scan. Add funds here when needed.",
          vibe_coder:
            "Each scan uses a small amount from your wallet. You can add funds here anytime. Small repos cost very little.",
          founder:
            "Scan costs scale with codebase size. Monitor spend here and add funds to keep your team scanning without interruption.",
        }[level],
        side: "bottom",
      },
    },
    {
      element: '[data-tour="settings-link"]',
      popover: {
        title: "Settings",
        description: {
          engineer:
            "Connect your GitHub account via OAuth to scan private repos. Also manage tour preferences and account settings.",
          vibe_coder:
            "Connect GitHub here so you can scan your private repos, not just public ones. Takes 30 seconds.",
          founder:
            "Your team can connect GitHub here to scan private repositories. Essential for auditing proprietary codebases.",
        }[level],
        side: "bottom",
      },
    },
  ];
}

// ---------------------------------------------------------------------------
// Scan Creation Tour (4 steps)
// ---------------------------------------------------------------------------

export function getScanCreationTourSteps(level: TechnicalLevel): TourStep[] {
  return [
    {
      element: '[data-tour="repo-input"]',
      popover: {
        title: "Select Your Repository",
        description: {
          engineer:
            "Paste a GitHub URL or select from your connected repos. We run a primer analysis to understand the tech stack, entry points, and architecture before the full scan.",
          vibe_coder:
            "Paste your GitHub repo link or pick one from the list. We'll quickly analyze what your project is built with before scanning.",
          founder:
            "Point us at any GitHub repository. We auto-detect the tech stack and architecture so the audit is tailored to your codebase.",
        }[level],
        side: "bottom",
      },
    },
    {
      element: '[data-tour="intake-form"]',
      popover: {
        title: "Project Context",
        description: {
          engineer:
            "The intake form feeds context to FORGE agents: what data flows exist, deployment targets, and critical paths. Better context means fewer false positives and more actionable findings.",
          vibe_coder:
            "Tell us about your app so we know what matters most. This helps us focus on the issues that actually affect your users.",
          founder:
            "Context helps prioritize findings by business impact. Describing your users, data sensitivity, and scale expectations ensures the audit focuses on real risks.",
        }[level],
        side: "top",
      },
    },
    {
      element: '[data-tour="submit-review"]',
      popover: {
        title: "Review & Launch",
        description: {
          engineer:
            "Review your scan configuration before triggering the FORGE pipeline. The discovery phase typically takes 2-5 minutes depending on repo size and LOC count.",
          vibe_coder:
            "Double-check everything looks right, then hit launch. Your scan usually finishes in a few minutes.",
          founder:
            "Final review before launching the audit. Scans complete in minutes, and you'll get a full report with severity-ranked findings.",
        }[level],
        side: "top",
      },
    },
  ];
}

// ---------------------------------------------------------------------------
// Report Tour (4 steps)
// ---------------------------------------------------------------------------

export function getReportTourSteps(level: TechnicalLevel): TourStep[] {
  return [
    {
      element: '[data-tour="score-gauges"]',
      popover: {
        title: "Production Readiness Scores",
        description: {
          engineer:
            "Four dimension scores: Health (overall), Security (OWASP/CWE mapped), Reliability (error handling, edge cases), and Scalability (architecture bottlenecks). Each is 0-100.",
          vibe_coder:
            "Your code gets scored on four things: overall health, security, reliability, and scalability. Higher is better — aim for 70+ across the board.",
          founder:
            "A quick read on production readiness across four dimensions. These scores tell you whether the codebase is ready for real users and scale.",
        }[level],
        side: "left",
      },
    },
    {
      element: '[data-tour="findings-table"]',
      popover: {
        title: "Findings",
        description: {
          engineer:
            "Each finding includes severity, CWE ID, affected files, and a suggested fix. Findings are filtered by actionability — intentional patterns and informational items are separated.",
          vibe_coder:
            "Every issue found in your code is listed here with severity and suggested fixes. Critical and high items should be fixed before shipping.",
          founder:
            "The detailed list of issues, ranked by severity. Each finding includes specific guidance on what to fix and why it matters for your users.",
        }[level],
        side: "top",
      },
    },
    {
      element: '[data-tour="fix-button"]',
      popover: {
        title: "Auto-Fix with FORGE",
        description: {
          engineer:
            "Triggers FORGE remediation: 12 agents generate fixes, run tests, and validate changes. Creates a PR with all fixes applied. Includes a three-loop retry system for complex issues.",
          vibe_coder:
            "Click this to let FORGE automatically fix the issues it found. It creates a pull request with all the fixes so you can review them.",
          founder:
            "This is the magic button. Instead of just reporting problems, FORGE actually fixes them and delivers a pull request. No developer hours needed for common fixes.",
        }[level],
        side: "top",
      },
    },
  ];
}

// ---------------------------------------------------------------------------
// Route matcher
// ---------------------------------------------------------------------------

export function getTourStepsForPage(
  pathname: string,
  level: TechnicalLevel,
): TourStep[] | null {
  if (pathname === "/dashboard") return getDashboardTourSteps(level);
  if (pathname === "/scan/new") return getScanCreationTourSteps(level);
  if (pathname.match(/\/scan\/.*\/report/)) return getReportTourSteps(level);
  return null;
}
