# Lessons Learned

## 2026-03-04: Live E2E cost blowout (~300,000 NGN / ~$185 USD)

**What happened**: Ran convergence loop live E2E on `express_api_nosec` (42 findings) without cost estimation. The loop ran for 45+ minutes in iteration 0 alone, burning through hundreds of OpenRouter API calls (Sonnet 4.6 coders × 3 retries × test gen × code review × escalation agents per finding).

**Root cause**: No cost ceiling, no upfront estimation, ran on a large finding set, ran in background where it couldn't be stopped quickly.

**Rules to prevent this**:
1. NEVER run live E2E tests without calculating expected cost first (findings × agents × retries × avg cost per call)
2. ALWAYS test convergence loop on a tiny repo first (2-3 findings max)
3. ADD a `max_cost_usd` config to ForgeConfig that halts the pipeline if telemetry.total_cost exceeds it
4. NEVER run expensive live tests in background — run in foreground so user can Ctrl+C
5. Present cost estimate to user and get explicit approval before running
