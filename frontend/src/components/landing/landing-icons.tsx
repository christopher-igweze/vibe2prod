"use client";

import type { SVGProps } from "react";

/**
 * Hand-rolled SVG icon set for the landing page. Keeps the CLI /
 * terminal aesthetic — stroke-based, corner brackets, dotted rings.
 * Every icon accepts standard SVG props including className for sizing
 * and currentColor tinting.
 */

type IconProps = SVGProps<SVGSVGElement>;

const baseProps = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

/** forge_scan — viewfinder brackets + radar dot */
export function IconScan(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <path d="M4 8V5a1 1 0 0 1 1-1h3" />
      <path d="M16 4h3a1 1 0 0 1 1 1v3" />
      <path d="M20 16v3a1 1 0 0 1-1 1h-3" />
      <path d="M8 20H5a1 1 0 0 1-1-1v-3" />
      <circle cx="12" cy="12" r="4.5" strokeDasharray="2 2" opacity="0.55" />
      <circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** forge_status — terminal waveform */
export function IconStatus(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <path d="M3 12h3l2-6 3 12 3-9 2 5h5" />
    </svg>
  );
}

/** forge_config — braces around a dot grid */
export function IconConfig(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <path d="M8 4c-2.5 0-3 1.5-3 3v3c0 1-.5 2-1.5 2 1 0 1.5 1 1.5 2v3c0 1.5.5 3 3 3" />
      <path d="M16 4c2.5 0 3 1.5 3 3v3c0 1 .5 2 1.5 2-1 0-1.5 1-1.5 2v3c0 1.5-.5 3-3 3" />
      <circle cx="9.5" cy="12" r="0.7" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="0.7" fill="currentColor" stroke="none" />
      <circle cx="14.5" cy="12" r="0.7" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** forge_health — connected nodes / heartbeat circuit */
export function IconHealth(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <circle cx="5" cy="7" r="1.6" />
      <circle cx="19" cy="7" r="1.6" />
      <circle cx="12" cy="17" r="1.6" />
      <path d="M6.4 7.6 10.8 16" />
      <path d="M17.6 7.6 13.2 16" />
      <path d="M6.6 7h10.8" strokeDasharray="2 2" opacity="0.55" />
    </svg>
  );
}

/** Browser / web UI globe — grid + longitude lines */
export function IconBrowser(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 9h18" />
      <circle cx="6" cy="6.5" r="0.5" fill="currentColor" stroke="none" />
      <circle cx="8" cy="6.5" r="0.5" fill="currentColor" stroke="none" />
      <circle cx="10" cy="6.5" r="0.5" fill="currentColor" stroke="none" />
      <path d="M12 13l-2 4m4-4 2 4m-4-4v4" />
      <path d="M8 17h8" />
    </svg>
  );
}

/** Terminal prompt — >_ for window chrome labels */
export function IconPrompt(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <path d="M5 7l4 5-4 5" />
      <path d="M13 17h6" />
    </svg>
  );
}

/** Wallet — stylized card with pocket */
export function IconWallet(props: IconProps) {
  return (
    <svg {...baseProps} {...props}>
      <rect x="3" y="6" width="18" height="13" rx="2" />
      <path d="M3 10h18" />
      <circle cx="16.5" cy="14.5" r="1.1" fill="currentColor" stroke="none" />
    </svg>
  );
}
