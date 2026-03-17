"use client";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface ApiKeySectionProps {
  hasExistingKey: boolean;
  apiKey: string | null;
  apiKeyLoading: boolean;
  apiKeyCopied: boolean;
  onGenerate: () => void;
  onRevoke: () => void;
  onCopy: () => void;
}

export function ApiKeySection({
  hasExistingKey,
  apiKey,
  apiKeyLoading,
  apiKeyCopied,
  onGenerate,
  onRevoke,
  onCopy,
}: ApiKeySectionProps) {
  return (
    <Card className="p-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold mb-1">CLI API Key</h2>
          <p className="text-sm text-[#8692A8]">
            Connect the FORGE CLI to your dashboard. Scan history and readiness trends sync automatically.
          </p>
        </div>
        {hasExistingKey && (
          <Badge className="bg-forge-emerald/10 text-forge-emerald border-forge-emerald/20">
            Active
          </Badge>
        )}
      </div>

      {/* State 1: Just generated — show the key */}
      {apiKey ? (
        <div className="mt-4 space-y-3">
          <div className="flex items-center gap-2 bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800">
            <code className="text-forge-emerald text-sm font-mono flex-1 break-all select-all">
              {apiKey}
            </code>
            <button
              onClick={onCopy}
              className="shrink-0 p-1.5 rounded-md hover:bg-zinc-800 transition-colors"
              title="Copy"
            >
              {apiKeyCopied ? (
                <svg className="w-4 h-4 text-forge-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              )}
            </button>
          </div>

          <div className="bg-zinc-900/60 rounded-lg px-4 py-3 border border-zinc-800/50">
            <p className="text-xs text-zinc-500 mb-2">Add to your MCP setup:</p>
            <code className="text-xs text-zinc-400 font-mono">
              -e VIBE2PROD_API_KEY={apiKey}
            </code>
          </div>

          <p className="text-xs text-amber-400/80">
            Save this key now — it won&apos;t be shown again after you leave this page.
          </p>

          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={onGenerate}
              disabled={apiKeyLoading}
              className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
            >
              Roll New Key
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={onRevoke}
              disabled={apiKeyLoading}
              className="border-red-500/30 text-red-400 hover:bg-red-500/10"
            >
              Revoke
            </Button>
          </div>
        </div>
      ) : hasExistingKey ? (
        /* State 2: Key exists but not visible */
        <div className="mt-4 space-y-3">
          <div className="flex items-center gap-2 bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800">
            <code className="text-zinc-500 text-sm font-mono flex-1">
              v2p_\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022
            </code>
          </div>

          <p className="text-xs text-[#4E586E]">
            You have an active API key. The key value is hidden for security.
            Roll a new key if you need to see it again.
          </p>

          <div className="flex gap-2">
            <Button
              onClick={onGenerate}
              disabled={apiKeyLoading}
              className="bg-forge-nav hover:bg-forge-surface-hover text-neutral-100"
            >
              {apiKeyLoading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 border-2 border-neutral-500 border-t-neutral-100 rounded-full animate-spin" />
                  Generating...
                </span>
              ) : (
                "Roll New Key"
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={onRevoke}
              disabled={apiKeyLoading}
              className="border-red-500/30 text-red-400 hover:bg-red-500/10"
            >
              Revoke
            </Button>
          </div>
        </div>
      ) : (
        /* State 3: No key at all */
        <div className="mt-4">
          <Button
            onClick={onGenerate}
            disabled={apiKeyLoading}
            className="bg-forge-nav hover:bg-forge-surface-hover text-neutral-100"
          >
            {apiKeyLoading ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 border-2 border-neutral-500 border-t-neutral-100 rounded-full animate-spin" />
                Generating...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
                Generate API Key
              </span>
            )}
          </Button>
          <p className="text-xs text-[#4E586E] mt-2">
            Generates a <code className="text-zinc-500">v2p_</code> key for CLI authentication.
            See{" "}
            <a href="/cli" className="text-forge-emerald hover:underline">
              CLI setup guide
            </a>{" "}
            for usage.
          </p>
        </div>
      )}
    </Card>
  );
}
