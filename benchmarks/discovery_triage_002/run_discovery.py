#!/usr/bin/env python3
"""Run FORGE discovery+triage against a provided repo and save benchmark artifacts.

Usage:
    # By GitHub URL (clones to /tmp):
    python benchmarks/discovery_triage_002/run_discovery.py https://github.com/user/repo

    # By local path:
    python benchmarks/discovery_triage_002/run_discovery.py /path/to/local/repo

    # With custom output name:
    python benchmarks/discovery_triage_002/run_discovery.py https://github.com/user/repo --name my-app

Requires:
    - OPENROUTER_API_KEY env var (or in backend/.env)
    - forge-engine on PYTHONPATH (pip install -e ../forge-engine)

Artifacts saved to: benchmarks/discovery_triage_002/{repo_name}/
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

# Add forge-engine to path if needed
FORGE_ENGINE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "forge-engine"
)
if os.path.isdir(FORGE_ENGINE_DIR):
    sys.path.insert(0, os.path.abspath(FORGE_ENGINE_DIR))

# Load .env for OPENROUTER_API_KEY
BACKEND_ENV = os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env")
if os.path.isfile(BACKEND_ENV):
    with open(BACKEND_ENV) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                if key.strip() not in os.environ:
                    os.environ[key.strip()] = value.strip()


def _repo_name_from_url(url: str) -> str:
    match = re.search(r"/([^/]+?)(?:\.git)?$", url.rstrip("/"))
    return match.group(1) if match else "repo"


async def run(
    repo_input: str,
    name: str | None = None,
    swarm: bool = False,
) -> None:
    from forge.standalone import run_standalone

    # Determine repo_url vs repo_path
    is_url = repo_input.startswith("http://") or repo_input.startswith("https://")
    repo_name = name or (
        _repo_name_from_url(repo_input) if is_url else Path(repo_input).name
    )

    benchmark_dir = os.path.dirname(__file__)
    output_dir = os.path.join(benchmark_dir, repo_name)
    os.makedirs(output_dir, exist_ok=True)

    discovery_mode = "swarm" if swarm else "classic"

    print(f"{'=' * 60}")
    print(f"  FORGE Discovery Benchmark")
    print(f"  Repo: {repo_input}")
    print(f"  Mode: {discovery_mode}")
    print(f"  Output: {output_dir}")
    print(f"{'=' * 60}")
    print()

    start = time.time()

    result = await run_standalone(
        repo_url=repo_input if is_url else "",
        repo_path="" if is_url else repo_input,
        config={
            "mode": "discovery",
            "dry_run": True,
            "discovery_mode": discovery_mode,
        },
    )

    elapsed = time.time() - start

    # Print summary
    print()
    print(f"{'=' * 60}")
    print(f"  RESULT: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"  Findings: {result.total_findings}")
    print(f"  Cost: ${result.cost_usd:.4f}")
    print(f"  Duration: {elapsed:.1f}s")
    print(f"  Run ID: {result.forge_run_id}")
    print(f"{'=' * 60}")

    # Locate artifacts from the workspace
    if is_url:
        workspace = os.path.join(
            os.environ.get("WORKSPACES_DIR", "/tmp/vibe2prod-workspaces"),
            repo_name,
        )
    else:
        workspace = repo_input

    artifacts_src = os.path.join(workspace, ".artifacts")

    # Copy artifacts to benchmark output
    for subdir in ("report", "scan", "telemetry", "hive"):
        src = os.path.join(artifacts_src, subdir)
        dst = os.path.join(output_dir, subdir)
        if os.path.isdir(src):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"  Copied: {subdir}/")

    # Write run summary
    summary = {
        "repo": repo_input,
        "repo_name": repo_name,
        "forge_run_id": result.forge_run_id,
        "success": result.success,
        "mode": result.mode.value if hasattr(result.mode, "value") else str(result.mode),
        "total_findings": result.total_findings,
        "findings_fixed": result.findings_fixed,
        "findings_deferred": result.findings_deferred,
        "agent_invocations": result.agent_invocations,
        "cost_usd": round(result.cost_usd, 4),
        "duration_seconds": round(elapsed, 1),
        "summary": result.summary,
    }
    summary_path = os.path.join(output_dir, "run_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  Written: run_summary.json")

    print()
    print(f"  View report: open {output_dir}/report/discovery_report.html")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Run FORGE discovery+triage benchmark against a repo"
    )
    parser.add_argument("repo", help="GitHub URL or local path to repo")
    parser.add_argument(
        "--name", help="Override the output directory name (default: derived from URL/path)"
    )
    parser.add_argument(
        "--swarm", action="store_true",
        help="Use swarm/hive discovery mode (generates dependency graph visualization)"
    )
    args = parser.parse_args()

    if not os.environ.get("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY not set. Add to env or backend/.env")
        sys.exit(1)

    asyncio.run(run(args.repo, args.name, swarm=args.swarm))


if __name__ == "__main__":
    main()
