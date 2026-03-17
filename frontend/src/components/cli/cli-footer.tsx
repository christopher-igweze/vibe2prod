"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";

export function CLIFooter() {
  return (
    <footer className="relative z-10 border-t border-zinc-800/50 px-6 md:px-12 py-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between text-zinc-600 text-xs">
        <span>
          FORGE by{" "}
          <a href="/" className="text-zinc-400 hover:text-white transition-colors">
            Vibe2Prod
          </a>
        </span>
        <div className="flex gap-4">
          <a
            href="https://github.com/christopher-igweze/forge-engine"
            target="_blank"
            className="hover:text-zinc-400 transition-colors flex items-center gap-1"
          >
            GitHub <ExternalLink className="w-3 h-3" />
          </a>
          <Link href="/" className="hover:text-zinc-400 transition-colors">
            Cloud Platform
          </Link>
        </div>
      </div>
    </footer>
  );
}
