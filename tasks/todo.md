# Vibe2Prod — Task Backlog

## In Progress

_(none)_

## Upcoming

### Testing Documentation
- [ ] Add "Analysis Methodology" section to discovery report HTML
- [ ] Document: FORGE is 100% static analysis + LLM reasoning, no runtime tests
- [ ] Clarify what each agent does vs what it does NOT do

### Loveable App Benchmark
- [ ] Run `--swarm` discovery on a Loveable-hosted project (URL TBD)
- [ ] Compare findings vs traditional codebases

## Done

### Vulnerability Pattern Library (v1, 2026-04-09)
Shipped in `forge-engine/forge/patterns/` — schema, loader, prompt context injection, extractor, learner. Three starter patterns (VP-001 client-writable server-authority columns, VP-002 client-only premium gating, VP-003 unprotected admin/internal endpoints). Orchestrator + discovery reasoner wired. Deferred: proof benchmark on frostflow_app, proposed-pattern promotion UI.

### security-probe removal (2026-04-09)
Live vulnerability scanning microservice fully excised from vibe2prod (backend routes/services/models, frontend pages, tests, migrations, config). `DROP TABLE` migration 20260409120000 added. Sibling `security-probe` repo deleted from disk.

### Dependency Graph Visualization
- [x] Thread CodeGraph data from hive to report generation
- [x] Build SVG segment network, interconnection table, blast radius, import chains
- [x] 34 unit tests + 506 forge-engine total pass
- [x] Proof benchmarks: vibe2prod (25 findings, $0.66) + forge-engine (30 findings, $0.55)
- [x] Merged to main

## Notes

### What FORGE Tests (FAQ)
FORGE does NOT run unit tests, load tests, UI tests, or integration tests. It performs:
- **Deterministic scanning:** 15 static checks (secrets, auth guards, CORS, SQL injection, etc.)
- **LLM-based code review:** 3 security passes (auth_flow, data_handling, infrastructure), 3 quality passes, 1 architecture review
- **Hive discovery (swarm mode):** AST-parsed code graph → parallel worker analysis → synthesis

Agent 11 (Integration Validator) has a stub for runtime test execution but is not yet implemented.
