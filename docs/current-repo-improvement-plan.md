# Current Repository Improvement Plan

## Purpose

This plan upgrades the existing LoopOS MVP+/Early Alpha repository toward an open-source Alpha release. It preserves working contracts and tests; it does not propose a rewrite.

Baseline captured on 2026-06-20:

- 114 Python modules under `loopos/`.
- 24 Python test files.
- 21 registered top-level CLI commands.
- 11 YAML policy packs.
- `loopos/cli/app.py` is approximately 1,850 lines.
- Latest verified baseline before this document: 119 tests and 16 subtests passing, with Ruff and mypy passing.

## Current State

### Runtime Core

- AIL and AI-ISA models, codecs, validation, legacy normalization, and JSON round-tripping exist.
- Kernel boot, run persistence, deterministic scheduling, state transitions, approval resume, trace, replay, and max-step guards exist.
- External terminal, file, and Git read actions pass through typed syscalls and Policy OS.
- The deterministic hello-file dry-run emits the expected nine-step Kernel sequence without workspace side effects.

### Goal Negotiation

- `GoalAnalysis`, `GoalOption`, `GoalProposal`, and `GoalSpec` exist.
- Vague goals are prevented from entering the Kernel without selecting one or more of five deterministic options.
- Current ambiguity detection is phrase/marker based and only distinguishes ambiguous versus concrete.

### Loop Convergence

- `ObservationSummary`, `EvaluationResult`, `ProgressDelta`, `LoopDecision`, and `HaltCondition` exist.
- The Kernel records evaluation, progress, decision, and halt trace events.
- Current scoring and decision evidence are intentionally lightweight.

### Policy OS and Execution

- YAML loading, registry, matcher, conflict resolution, audit records, and structured `PolicyDecision` exist.
- Policy packs cover core behavior, terminal safety, file/Git safety, tools, memory, skills, context, renderer, goal negotiation, convergence, and review separation.
- Dangerous remote-script pipes and destructive commands are blocked; medium/high-risk paths require approval.
- Policy decisions do not yet expose a formal L0-L5 safety level.

### Memory and Skills

- JSONL audit sources plus SQLite query/index state exist.
- Memory proposals, governance, retrieval, context budgets, user profile storage, and reindexing exist.
- Skill proposals are extracted from successful structured traces and committed through governance.

### Outer Loop

- Persistent tasks, todos, quick-win selection, triggers, task artifacts, worktree plans, review records, and role separation exist.
- Code-changing tasks require a planned worktree before review.
- Worktree materialization commands can be dry-run through the syscall/policy path.
- High-risk approval requires verifier evidence and an independent reviewer.

### Provider and Gateway

- The requested provider catalog, aliases, YAML profile loading, capability routing, mock client, local-only routing, and multi-model roles exist.
- Image inputs can add a vision companion when the primary assignment lacks vision.
- Mock ChatOps adapters, persisted messages, approval cards, and approve/deny resume decisions exist.
- No real provider or platform API is called in tests.

### CLI

The CLI exposes:

`run`, `resume`, `status`, `history`, `skills`, `trace`, `step`, `tools`, `goal`, `tasks`, `triggers`, `worktrees`, `review`, `providers`, `models`, `gateway`, `memory`, `profile`, `config`, `policy`, and `ail`.

Typer/Rich and standard-library fallback behavior are both implemented, but command logic, parser wiring, paths, and rendering are concentrated in one large module.

## Gaps

1. CLI command logic and rendering are not modular; `app.py` is the largest maintenance risk.
2. Default Rich output is functional but not yet a coherent product UI with reusable renderers.
3. Goal Negotiation lacks ambiguity scores, medium-confirmation mode, structured scope/non-goals/deliverables, and risk-aware proposals.
4. GoalSpec validation does not yet enforce the full Alpha contract for scope and acceptance criteria.
5. Loop Convergence lacks acceptance-criterion status, regression tracking, repeated-action tracking, and richer repair/replan evidence.
6. Policy OS lacks formal L0-L5 safety levels, human-only decisions, and rollback requirements.
7. Database/data-changing operations have no Backup Guard, shadow-run, redaction, or verified-backup gate.
8. Local Workspace Intelligence does not exist: no privacy-first file index or local content search.
9. Plugin Manifest and local Registry do not exist.
10. Gateway authentication/allowlists and attachment normalization are not implemented.
11. Worktree execution remains guarded command planning rather than a complete lease/cleanup audit lifecycle.
12. Provider profiles do not yet ship as canonical repository YAML packs.
13. Open-source governance files and plugin contribution contracts are incomplete.
14. Test organization is flat, which will become difficult as Alpha scope grows.
15. CLI acceptance coverage is broad but does not yet use stable renderer-level snapshot contracts.

## Risks

- Refactoring the CLI can silently change exit codes or JSON output. Preserve public command functions and add registration tests before moving code.
- GoalSpec and convergence model upgrades affect stored run metadata and trace replay. Add defaults and compatibility readers.
- L0-L5 changes can alter existing allow/deny outcomes. Add classification without weakening current denial precedence.
- Data Guard must remain mock/local in tests and must never connect to real databases or expose credentials.
- Worktree execution and cleanup must remain Policy OS/syscall controlled; no direct subprocess path should be added.
- New indexing must exclude secrets, `.git`, virtual environments, dependency trees, and large/binary files by default.
- Plugin installation must not execute plugin code during discovery or audit.

## Ordered Improvement Plan

### Phase 1: CLI Modularization

- Create `loopos/cli/context.py`, `options.py`, `commands/`, and `renderers/`.
- Move commands incrementally while preserving the current command functions as compatibility imports.
- Keep `app.py` focused on app construction, registration, REPL entry, and fallback dispatch.
- Add command-registration and JSON-output tests before each move.

### Phase 2: Product CLI Renderers

- Implement reusable run header, step stream, goal proposal, policy decision, trace tree, approval, diff, task board, review, and result summary renderers.
- Keep `--json` strictly free of Rich markup.
- Add renderer-level plain-text assertions.

### Phase 3: Goal Negotiation v1

- Add `AmbiguityReport` with score, missing fields, risk factors, confirmation/negotiate flags, and reason codes.
- Expand proposals with scope, non-goals, deliverables, acceptance criteria, risk, estimated steps, and recommendation.
- Expand GoalSpec with direct/confirmed/selected/merged/manual origin and strict validation.
- Preserve current five-option behavior for high ambiguity.

### Phase 4: Loop Convergence v1

- Add run/step identifiers, acceptance-criteria status, failure type, regression, evidence, no-progress count, repeated failures, and repeated actions.
- Make policy block, approval, success, regression, no progress, repair, replan, and max-step decisions explicit and deterministic.
- Persist all convergence decisions in trace events.

### Phase 5: Policy Safety Levels

- Extend Policy actions/decisions with L0-L5, human-only, and rollback-required fields.
- Infer conservative levels for legacy packs.
- Classify safe reads/tests, file writes, guarded Git operations, user-only operations, and blocked destructive actions.
- Preserve deny-overrides-allow and explicit-approval rules.

### Phase 5.5: Data Safety / Backup Guard

- Add data-operation detection, backup plans/manifests, backup vault checksums, shadow-run plans, validation reports, rollback plans, and trace-safe redaction.
- Add data policy packs and mock database syscalls only; do not add real database connections.
- Block destructive data operations without verified backup and rollback evidence.

### Phase 6: Local Workspace Intelligence v0

- Build a local file/content index with privacy filtering and deterministic search.
- Exclude `.env`, private keys, credential-like files, `.git`, dependencies, caches, binaries, and oversized files.
- Add `index build/status`, `search`, and `files find` CLI commands.

### Phase 7: Plugin Manifest / Registry v0

- Add typed manifests for provider, skill, policy, gateway, MCP, execution backend, benchmark, and agent-role plugins.
- Implement local search/install/audit without importing or executing plugin code.
- Flag unsafe permissions and incompatible versions.

### Phase 8: Provider Profiles v1

- Ship canonical YAML profiles using the current loader.
- Add capability/cost/latency/reliability validation and deterministic routing explanations.
- Keep all clients mock-only for Alpha tests.

### Phase 9: Webhook Gateway v0

- Add authentication allowlists, normalized inbound messages, attachment metadata, delivery records, and persisted sessions.
- Connect approval decisions to waiting Kernel runs through explicit Kernel signals.
- Keep platform adapters mock-only.

### Phase 10: Worktree / Review Hardening

- Add worktree leases, owner/run identity, expiry, audited cleanup plans, and read-only reviewer constraints.
- Require verifier pass plus reviewer approval before PR artifacts can become ready.
- Keep automatic merge disabled.

### Phase 11: Open-Source Governance

- Add `GOVERNANCE.md`, `SECURITY.md`, `PLUGIN_SPEC.md`, `RFC_PROCESS.md`, `MAINTAINERS.md`, `CODE_OF_CONDUCT.md`, and `ROADMAP.md`.
- Document core-versus-plugin ownership and registry audit expectations.

### Phase 12: Acceptance Suite

- Add end-to-end tests for goal negotiation, dry-run execution, policy block, trace replay, outer-loop worktree/review, model routing, gateway approval, data guard, local index, and plugin audit.
- Keep all external systems mocked and all dangerous operations unexecuted.

## Top 15 Concrete Tasks

1. Add CLI command-registration tests and a shared CLI context object.
2. Extract path/config helpers from `app.py`.
3. Extract policy/goal/trace renderers without changing JSON output.
4. Split the first low-coupling command groups: providers/models, gateway, and outer-loop commands.
5. Add `AmbiguityReport` and three-mode goal negotiation.
6. Enforce non-empty GoalSpec scope and acceptance criteria with compatibility defaults.
7. Add convergence regression/no-progress/repeated-action tracking.
8. Add L0-L5 fields and legacy inference to Policy OS.
9. Add terminal/file/Git safety-level tests.
10. Implement Data Guard models and SQL/goal detector.
11. Add backup vault manifest/checksum verification and redaction.
12. Implement privacy-first local file indexing and search.
13. Implement plugin manifest validation and local registry audit.
14. Add gateway authentication allowlists and Kernel-signal approval integration.
15. Add governance documents and full Alpha acceptance tests.

## Test Plan

- Run focused tests after each module extraction or schema change.
- Run `python -m pytest` after each phase.
- Run `python -m ruff check .` and `python -m mypy loopos tests` before every commit.
- Preserve subprocess CLI tests for command names, options, exit codes, and JSON validity.
- Add compatibility tests for persisted RunRecord, TraceEvent, GoalSpec, PolicyDecision, memory, task, review, and gateway records.
- Use temporary directories for files, indexes, backup vaults, registries, tasks, and worktree plans.
- Never call real LLM, provider, platform, database, or network APIs.
- Never execute destructive commands; assert that policy blocks them before adapters run.

## Alpha Acceptance Criteria

- All existing commands remain registered and backward compatible.
- `app.py` becomes registration-focused and command/render logic is modular.
- High/medium/low goal ambiguity paths are structured and tested.
- Every Kernel iteration emits evaluation, progress, decision, and halt evidence.
- Policy decisions include L0-L5 and preserve current safety behavior.
- Destructive data operations cannot proceed without verified backup, shadow-run/validation policy, rollback plan, and approval.
- Local indexing never includes blocked secret/private paths.
- Plugin manifests validate and local registry audit flags unsafe permissions.
- Code tasks require worktree policy, verifier evidence, and reviewer approval.
- Provider and gateway tests remain deterministic and offline.
- `python -m loopos.cli.app --help`, pytest, Ruff, and mypy all pass.

## Explicit Non-Goals for the Alpha Upgrade

- No Web UI or desktop GUI.
- No real LLM/provider calls in tests.
- No real chat-platform calls in tests.
- No real production database connections.
- No automatic PR merge.
- No direct execution path around Policy OS, Syscall Router, Memory Governance, or review separation.
