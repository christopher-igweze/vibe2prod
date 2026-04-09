"use client";

export const dynamic = "force-dynamic";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api/client";
import { useTour } from "@/components/tour/tour-provider";
import { Card } from "@/components/ui/card";
import { GitHubConnection } from "@/components/settings/github-connection";
import { ApiKeySection } from "@/components/settings/api-key-section";
import { OpenRouterKeySection } from "@/components/settings/openrouter-key-section";
import { GuidedTourSection } from "@/components/settings/guided-tour-section";

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

  const [hasExistingKey, setHasExistingKey] = useState(false);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [apiKeyLoading, setApiKeyLoading] = useState(false);
  const [apiKeyCopied, setApiKeyCopied] = useState(false);

  const [hasOpenRouterKey, setHasOpenRouterKey] = useState(false);
  const [openRouterKeyHint, setOpenRouterKeyHint] = useState<string | null>(null);
  const [savingOpenRouterKey, setSavingOpenRouterKey] = useState(false);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const token = (await getToken()) ?? undefined;
        const [ghStatus, keyStatus, orKeyStatus] = await Promise.allSettled([
          apiFetch<GitHubStatus>("/api/github/status", { token }),
          apiFetch<{ has_key: boolean }>("/api/user/api-key", { token }),
          apiFetch<{ has_key: boolean; key_hint: string | null }>("/api/user/openrouter-key", { token }),
        ]);
        if (ghStatus.status === "fulfilled") setGithub(ghStatus.value);
        if (keyStatus.status === "fulfilled") setHasExistingKey(keyStatus.value.has_key);
        if (orKeyStatus.status === "fulfilled") {
          setHasOpenRouterKey(orKeyStatus.value.has_key);
          setOpenRouterKeyHint(orKeyStatus.value.key_hint);
        }
      } catch {
        // Not connected or error
      }
    }
    fetchStatus();
  }, [getToken]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");
    if (code && state) {
      exchangeCode(code, state);
      window.history.replaceState({}, "", "/settings");
    }
  }, []);

  async function exchangeCode(code: string, state: string) {
    setLoading(true);
    setError("");
    try {
      const token = (await getToken()) ?? undefined;
      const result = await apiFetch<GitHubStatus>("/api/github-oauth", {
        method: "POST", token,
        body: JSON.stringify({ action: "exchange_code", code, state, redirect_uri: `${window.location.origin}/settings` }),
      });
      setGithub(result);
      setMessage("GitHub connected successfully!");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to connect GitHub");
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
        method: "POST", token,
        body: JSON.stringify({ action: "get_auth_url", redirect_uri: `${window.location.origin}/settings` }),
      });
      if (result.auth_url) window.location.href = result.auth_url;
    } catch (e) {
      setLoading(false);
      setError(e instanceof ApiError ? e.message : "Failed to start GitHub connection");
    }
  }

  async function disconnectGitHub() {
    setLoading(true);
    setError("");
    try {
      const token = (await getToken()) ?? undefined;
      await apiFetch("/api/github-oauth", { method: "POST", token, body: JSON.stringify({ action: "disconnect" }) });
      setGithub({ github_username: null, avatar_url: null, connected: false });
      setMessage("GitHub disconnected.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to disconnect GitHub");
    } finally {
      setLoading(false);
    }
  }

  async function restartTour() {
    setResettingTour(true);
    try {
      const token = (await getToken()) ?? undefined;
      await apiFetch("/api/user/tour/reset", { method: "POST", token });
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
      const result = await apiFetch<{ api_key: string; message: string }>("/api/user/api-key", { method: "POST", token });
      setApiKey(result.api_key);
      setHasExistingKey(true);
      setMessage("API key generated. Copy it now — it won't be shown again.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to generate API key");
    } finally {
      setApiKeyLoading(false);
    }
  }

  async function revokeApiKey() {
    setApiKeyLoading(true);
    setError("");
    try {
      const token = (await getToken()) ?? undefined;
      await apiFetch("/api/user/api-key", { method: "DELETE", token });
      setApiKey(null);
      setHasExistingKey(false);
      setMessage("API key revoked.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to revoke API key");
    } finally {
      setApiKeyLoading(false);
    }
  }

  async function handleSaveOpenRouterKey(key: string) {
    setSavingOpenRouterKey(true);
    setError("");
    try {
      const token = (await getToken()) ?? undefined;
      const result = await apiFetch<{ has_key: boolean; key_hint: string | null }>("/api/user/openrouter-key", {
        method: "PUT",
        token,
        body: JSON.stringify({ api_key: key }),
      });
      setHasOpenRouterKey(result.has_key);
      setOpenRouterKeyHint(result.key_hint);
      setMessage("OpenRouter key saved.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to save OpenRouter key");
    } finally {
      setSavingOpenRouterKey(false);
    }
  }

  async function handleRemoveOpenRouterKey() {
    setSavingOpenRouterKey(true);
    setError("");
    try {
      const token = (await getToken()) ?? undefined;
      await apiFetch("/api/user/openrouter-key", { method: "DELETE", token });
      setHasOpenRouterKey(false);
      setOpenRouterKeyHint(null);
      setMessage("OpenRouter key removed.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to remove OpenRouter key");
    } finally {
      setSavingOpenRouterKey(false);
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
    <div className="space-y-6 max-w-5xl mx-auto">
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GitHubConnection
          github={github}
          loading={loading}
          onConnect={connectGitHub}
          onDisconnect={disconnectGitHub}
        />

        <ApiKeySection
          hasExistingKey={hasExistingKey}
          apiKey={apiKey}
          apiKeyLoading={apiKeyLoading}
          apiKeyCopied={apiKeyCopied}
          onGenerate={generateApiKey}
          onRevoke={revokeApiKey}
          onCopy={copyApiKey}
        />

        <OpenRouterKeySection
          hasKey={hasOpenRouterKey}
          keyHint={openRouterKeyHint}
          onSave={handleSaveOpenRouterKey}
          onRemove={handleRemoveOpenRouterKey}
          saving={savingOpenRouterKey}
        />

        <div className="lg:col-span-2">
          <GuidedTourSection resetting={resettingTour} onRestart={restartTour} />
        </div>
      </div>
    </div>
  );
}
