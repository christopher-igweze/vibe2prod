"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

interface OpenRouterKeySectionProps {
  hasKey: boolean;
  keyHint: string | null;
  onSave: (key: string) => Promise<void>;
  onRemove: () => Promise<void>;
  saving: boolean;
}

export function OpenRouterKeySection({
  hasKey,
  keyHint,
  onSave,
  onRemove,
  saving,
}: OpenRouterKeySectionProps) {
  const [keyInput, setKeyInput] = useState("");

  async function handleSave() {
    if (!keyInput.trim()) return;
    await onSave(keyInput.trim());
    setKeyInput("");
  }

  if (hasKey) {
    return (
      <Card className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold mb-1">OpenRouter API Key</h2>
            <p className="text-sm text-[#8692A8]">
              Bring your own OpenRouter key to pay true scan costs directly. No markup, no wallet charges.
            </p>
          </div>
          <Badge className="bg-forge-emerald/10 text-forge-emerald border-forge-emerald/20">
            Active
          </Badge>
        </div>

        <div className="mt-4 space-y-3">
          <div className="flex items-center gap-2 bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800">
            <code className="text-zinc-500 text-sm font-mono flex-1">
              {keyHint ?? "sk-or-v1-" + "\u2022".repeat(32)}
            </code>
          </div>

          <p className="text-xs text-forge-emerald/80">
            Scans use your key — you pay OpenRouter directly, $0 from wallet.
          </p>

          <Button
            variant="outline"
            size="sm"
            onClick={onRemove}
            disabled={saving}
            className="border-red-500/30 text-red-400 hover:bg-red-500/10"
          >
            {saving ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 border-2 border-neutral-500 border-t-neutral-100 rounded-full animate-spin" />
                Removing...
              </span>
            ) : (
              "Remove Key"
            )}
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">OpenRouter API Key</h2>
        <p className="text-sm text-[#8692A8]">
          Bring your own OpenRouter key to pay true scan costs directly. No markup, no wallet charges.
        </p>
      </div>

      <div className="mt-4 space-y-3">
        <div className="flex gap-2">
          <Input
            type="password"
            placeholder="sk-or-v1-..."
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            className="bg-forge-surface border-white/[0.06] font-mono text-sm"
          />
          <Button
            onClick={handleSave}
            disabled={saving || !keyInput.trim()}
            className="bg-forge-nav hover:bg-forge-surface-hover text-neutral-100 shrink-0"
          >
            {saving ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 border-2 border-neutral-500 border-t-neutral-100 rounded-full animate-spin" />
                Saving...
              </span>
            ) : (
              "Save Key"
            )}
          </Button>
        </div>

        <p className="text-xs text-[#4E586E]">
          Get a key at{" "}
          <a
            href="https://openrouter.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="text-forge-emerald hover:underline"
          >
            openrouter.ai
          </a>
        </p>
      </div>
    </Card>
  );
}
