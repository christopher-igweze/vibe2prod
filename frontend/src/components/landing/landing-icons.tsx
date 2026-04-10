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

/**
 * Anthropic Claude logomark — the starburst asterisk, extracted directly
 * from the inline SVG on claude.ai/login. The path sits in a 24x24 box.
 */
export function IconClaude(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" stroke="none" {...props}>
      <path d="M11.376 24L10.776 23.544L10.44 22.8L10.776 21.312L11.16 19.392L11.472 17.856L11.76 15.96L11.928 15.336L11.904 15.288L11.784 15.312L10.344 17.28L8.16 20.232L6.432 22.056L6.024 22.224L5.304 21.864L5.376 21.192L5.784 20.616L8.16 17.568L9.6 15.672L10.536 14.592L10.512 14.448H10.464L4.128 18.576L3 18.72L2.496 18.264L2.568 17.52L2.808 17.28L4.704 15.96L9.432 13.32L9.504 13.08L9.432 12.96H9.192L8.4 12.912L5.712 12.84L3.384 12.744L1.104 12.624L0.528 12.504L0 11.784L0.048 11.424L0.528 11.112L1.224 11.16L2.736 11.28L5.016 11.424L6.672 11.52L9.12 11.784H9.504L9.552 11.616L9.432 11.52L9.336 11.424L6.96 9.84L4.416 8.16L3.072 7.176L2.352 6.672L1.992 6.216L1.848 5.208L2.496 4.488L3.384 4.56L3.6 4.608L4.488 5.304L6.384 6.768L8.88 8.616L9.24 8.904L9.408 8.808V8.736L9.24 8.472L7.896 6.024L6.456 3.528L5.808 2.496L5.64 1.872C5.576 1.656 5.544 1.416 5.544 1.152L6.288 0.144001L6.696 0L7.704 0.144001L8.112 0.504001L8.736 1.92L9.72 4.152L11.28 7.176L11.736 8.088L11.976 8.904L12.072 9.168H12.24V9.024L12.36 7.296L12.6 5.208L12.84 2.52L12.912 1.752L13.296 0.840001L14.04 0.360001L14.616 0.624001L15.096 1.32L15.024 1.752L14.76 3.6L14.184 6.504L13.824 8.472H14.04L14.28 8.208L15.264 6.912L16.92 4.848L17.64 4.032L18.504 3.12L19.056 2.688H20.088L20.832 3.816L20.496 4.992L19.44 6.336L18.552 7.464L17.28 9.168L16.512 10.536L16.584 10.632H16.752L19.608 10.008L21.168 9.744L22.992 9.432L23.832 9.816L23.928 10.2L23.592 11.016L21.624 11.496L19.32 11.952L15.888 12.768L15.84 12.792L15.888 12.864L17.424 13.008L18.096 13.056H19.728L22.752 13.272L23.544 13.8L24 14.424L23.928 14.928L22.704 15.528L21.072 15.144L17.232 14.232L15.936 13.92H15.744V14.016L16.848 15.096L18.84 16.896L21.36 19.224L21.48 19.8L21.168 20.28L20.832 20.232L18.624 18.552L17.76 17.808L15.84 16.2H15.72V16.368L16.152 17.016L18.504 20.544L18.624 21.624L18.456 21.96L17.832 22.176L17.184 22.056L15.792 20.136L14.376 17.952L13.224 16.008L13.104 16.104L12.408 23.352L12.096 23.712L11.376 24Z" />
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
