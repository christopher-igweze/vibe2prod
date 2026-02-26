"use client";

export const dynamic = "force-dynamic";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { apiFetch, ApiError } from "@/lib/api/client";
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
  const [github, setGithub] = useState<GitHubStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

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
        setError(e.detail);
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
        setError(e.detail);
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
        setError(e.detail);
      } else {
        setError("Failed to disconnect GitHub");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <h1 className="text-2xl font-bold">Settings</h1>

      {error && (
        <Card className="border-red-500/50 bg-red-950/20 p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </Card>
      )}

      {message && (
        <Card className="border-emerald-500/50 bg-emerald-950/20 p-4">
          <p className="text-emerald-400 text-sm">{message}</p>
        </Card>
      )}

      {/* GitHub Connection */}
      <Card className="bg-neutral-900 border-neutral-800 p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold mb-1">GitHub Connection</h2>
            <p className="text-sm text-neutral-400">
              Connect your GitHub account to scan private repositories.
            </p>
          </div>
          {github?.connected && (
            <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
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
                <p className="text-xs text-neutral-500">
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
              className="bg-neutral-800 hover:bg-neutral-700 text-neutral-100"
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
            <p className="text-xs text-neutral-500 mt-2">
              Grants access to your repositories for scanning. You can disconnect at any time.
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
