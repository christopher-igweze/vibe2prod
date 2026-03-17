"use client";

export const dynamic = "force-dynamic";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api/client";
import { useTour } from "@/components/tour/tour-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface GitHubStatus {
  github_username: string | null;
  avatar_url: string | null;
  connected: boolean;
}

export default function SettingsPage() {
  const { getToken } = useAuth();
  const router = useRouter();
  const { startTour } = useTour();
  const [github, setGithub] = useState<GitHubStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [resettingTour, setResettingTour] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // API Key state: hasExistingKey = persisted key exists, apiKey = freshly generated (visible)
  const [hasExistingKey, setHasExistingKey] = useState(false);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [apiKeyLoading, setApiKeyLoading] = useState(false);
  const [apiKeyCopied, setApiKeyCopied] = useState(false);

  // Fetch GitHub connection status + API key status on mount
  useEffect(() => {
    async function fetchStatus() {
      try {
        const token = (await getToken()) ?? undefined;
        const [ghStatus, keyStatus] = await Promise.allSettled([
          apiFetch<GitHubStatus>("/api/github/status", { token }),
          apiFetch<{ has_key: boolean }>("/api/user/api-key", { token }),
        ]);
        if (ghStatus.status === "fulfilled") setGithub(ghStatus.value);
        if (keyStatus.status === "fulfilled") setHasExistingKey(keyStatus.value.has_key);
      } catch {
        // Not connected or error — leave as defaults
      }
    }
    fetchStatus();
  }, [getToken]);

  // Check if we just returned from GitHub OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");

    if (code && state) {
      exchangeCode(code, state);
      // Clean URL
      window.history.replaceState({}, "", "/settings");
    }
  }, []);

  async function exchangeCode(code: string, state: string) {
    setLoading(true);
    setError("");
    try {
      const token = (await getToken()) ?? undefined;
      const result = await apiFetch<GitHubStatus>("/api/github-oauth", {
        method: "POST",
        token,
        body: JSON.stringify({
          action: "exchange_code",
          code,
          state,
          redirect_uri: `${window.location.origin}/settings`,
        }),
      });
      setGithub(result);
      setMessage("GitHub connected successfully!");
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Failed to connect GitHub");
      }
    } finally {
      setLoading(false);
    }
  }

  async function connectGitHub() {
    setLoading(true);
    setError("");
    try {
      const token = (await getToken()) ?? undefined;
      const result = await apiFetch<{ auth_url: string }>("/api/github-oauth", {
        method: "POST",
        token,
        body: JSON.stringify({
          action: "get_auth_url",
          redirect_uri: `${window.location.origin}/settings`,
        }),
      });
      if (result.auth_url) {
        window.location.href = result.auth_url;
      }
    } catch (e) {
      setLoading(false);
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Failed to start GitHub connection");
      }
    }
  }

  async function disconnectGitHub() {
    setLoading(true);
    setError("");
    try {
      const token = (await getToken()) ?? undefined;
      await apiFetch("/api/github-oauth", {
        method: "POST",
        token,
        body: JSON.stringify({ action: "disconnect" }),
      });
      setGithub({ github_username: null, avatar_url: null, connected: false });
      setMessage("GitHub disconnected.");
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Failed to disconnect GitHub");
      }
    } finally {
      setLoading(false);
    }
  }

  async function restartTour() {
    setResettingTour(true);
    try {
      const token = (await getToken()) ?? undefined;
      await apiFetch("/api/user/tour/reset", {
        method: "POST",
        token,
      });
      router.push("/dashboard");
    } catch {
      setResettingTour(false);
      setError("Failed to reset tour.");
    }
  }

  async function generateApiKey() {
    setApiKeyLoading(true);
    setError("");
    try {
      const token = (await getToken()) ?? undefined;
      const result = await apiFetch<{ api_key: string; message: string }>("/api/user/api-key", {
        method: "POST",
        token,
      });
      setApiKey(result.api_key);
      setHasExistingKey(true);
      setMessage("API key generated. Copy it now — it won't be shown again.");
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Failed to generate API key");
      }
    } finally {
      setApiKeyLoading(false);
    }
  }

  async function revokeApiKey() {
    setApiKeyLoading(true);
    setError("");
    try {
      const token = (await getToken()) ?? undefined;
      await apiFetch("/api/user/api-key", {
        method: "DELETE",
        token,
      });
      setApiKey(null);
      setHasExistingKey(false);
      setMessage("API key revoked.");
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError("Failed to revoke API key");
      }
    } finally {
      setApiKeyLoading(false);
    }
  }

  function copyApiKey() {
    if (apiKey) {
      navigator.clipboard.writeText(apiKey);
      setApiKeyCopied(true);
      setTimeout(() => setApiKeyCopied(false), 2000);
    }
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <h1 className="text-2xl font-bold font-[family-name:var(--font-heading)]">Settings</h1>

      {error && (
        <Card className="border-red-500/50 bg-red-950/20 p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </Card>
      )}

      {message && (
        <Card className="border-forge-emerald/50 bg-forge-emerald/10 p-4">
          <p className="text-forge-emerald text-sm">{message}</p>
        </Card>
      )}

      {/* GitHub Connection */}
      <Card className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold mb-1">GitHub Connection</h2>
            <p className="text-sm text-[#8692A8]">
              Connect your GitHub account to scan private repositories.
            </p>
          </div>
          {github?.connected && (
            <Badge className="bg-forge-emerald/10 text-forge-emerald border-forge-emerald/20">
              Connected
            </Badge>
          )}
        </div>

        {github?.connected && github.github_username ? (
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              {github.avatar_url && (
                <img
                  src={github.avatar_url}
                  alt={github.github_username}
                  className="w-10 h-10 rounded-full"
                />
              )}
              <div>
                <p className="font-medium">{github.github_username}</p>
                <p className="text-xs text-[#4E586E]">
                  Private repo access enabled
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={disconnectGitHub}
              disabled={loading}
              className="border-red-500/30 text-red-400 hover:bg-red-500/10"
            >
              Disconnect
            </Button>
          </div>
        ) : (
          <div className="mt-4">
            <Button
              onClick={connectGitHub}
              disabled={loading}
              className="bg-forge-nav hover:bg-forge-surface-hover text-neutral-100"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 border-2 border-neutral-500 border-t-neutral-100 rounded-full animate-spin" />
                  Connecting...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                  </svg>
                  Connect GitHub
                </span>
              )}
            </Button>
            <p className="text-xs text-[#4E586E] mt-2">
              Grants access to your repositories for scanning. You can disconnect at any time.
            </p>
          </div>
        )}
      </Card>

      {/* CLI API Key */}
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
                onClick={copyApiKey}
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
                onClick={generateApiKey}
                disabled={apiKeyLoading}
                className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
              >
                Roll New Key
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={revokeApiKey}
                disabled={apiKeyLoading}
                className="border-red-500/30 text-red-400 hover:bg-red-500/10"
              >
                Revoke
              </Button>
            </div>
          </div>
        ) : hasExistingKey ? (
          /* State 2: Key exists but not visible (returning user) */
          <div className="mt-4 space-y-3">
            <div className="flex items-center gap-2 bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800">
              <code className="text-zinc-500 text-sm font-mono flex-1">
                v2p_••••••••••••••••••••••••••••••••
              </code>
            </div>

            <p className="text-xs text-[#4E586E]">
              You have an active API key. The key value is hidden for security.
              Roll a new key if you need to see it again.
            </p>

            <div className="flex gap-2">
              <Button
                onClick={generateApiKey}
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
                onClick={revokeApiKey}
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
              onClick={generateApiKey}
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

      {/* Guided Tour */}
      <Card className="p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold mb-1">Guided Tour</h2>
            <p className="text-sm text-[#8692A8]">
              Retake the interactive walkthrough to learn how the platform works.
            </p>
          </div>
        </div>
        <div className="mt-4">
          <Button
            onClick={restartTour}
            disabled={resettingTour}
            className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]"
          >
            {resettingTour ? "Resetting..." : "Restart Tour"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
