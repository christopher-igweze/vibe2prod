# Vibe2Prod — Task Backlog

## In Progress

_(none)_

## Upcoming

### Vulnerability Pattern Library
**Spec:** `forge-engine/tasks/vulnerability-pattern-library-spec.md`

Technology-agnostic vulnerability pattern detection with learning loop. Addresses the Supabase RLS bypass class of vulnerabilities without overfitting to specific technologies.

Key deliverables:
- [ ] Pattern schema + 3 starter patterns (VP-001 through VP-003)
- [ ] Integration into Tier 1 scanner (deterministic signal scoring)
- [ ] Integration into FORGE/Hive agents (LLM prompt context injection)
- [ ] Extraction pipeline (post-scan pattern learning)
- [ ] Proof benchmark showing VP-001 triggers on frostflow_app

### Testing Documentation
- [ ] Add "Analysis Methodology" section to discovery report HTML
- [ ] Document: FORGE is 100% static analysis + LLM reasoning, no runtime tests
- [ ] Clarify what each agent does vs what it does NOT do

### Loveable App Benchmark
- [ ] Run `--swarm` discovery on a Loveable-hosted project (URL TBD)
- [ ] Compare findings vs traditional codebases

## Done

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
