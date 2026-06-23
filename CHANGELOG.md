# Changelog

## v0.3 (Universal Agent Runtime)

### Added

* **`loopos.product` (Workbench)** — the v0.3 product surface.
  `Workbench.build_context()` produces a `WorkbenchContext` snapshot;
  `build_panels_from_context()` turns it into a `PanelLayout` with
  the eight required panels (Goal / Agent / Policy / ACI / ALI /
  Trace-Replay / Fusion / Readiness); `render_plain` and `render_json`
  emit human and machine output. The Workbench is the only
  user-facing surface for v0.3 and never owns authority. See
  `docs/v0-3-readme.md`.
* **`loopos.adapters` (Agent Kernel Adapter Layer)** — universal
  contract (`AgentKernelAdapter` Protocol + manifest + capabilities).
  Default registry: `MockAdapter`, `HermesAdapter` (clean-room proof),
  `ScreamCodeAdapter` (spec + mock), `CleanroomAdapter`
  (clean-room Codex/Claude Code spec). No adapter can claim
  `direct_shell=True` or `direct_file_write=True`; the manifest
  validator refuses.
* **`loopos.agent_bus` (Agent Bus)** — translates
  `AgentKernelEvent` into governed `AgentCommand`s. Translation
  table mirrors the v0.3 spec:
  `file_patch_proposed → file.patch`,
  `syscall_requested → terminal.exec`,
  `test_requested → terminal.exec (action=test.run)`,
  `model_call_requested → provider_select (action=provider.call)`.
  The bus has **no** direct shell / file-write / execute method.
* **`loopos.providers_runtime` (Real LLM Provider Runtime)** — new
  governed transport layer on top of the v0.2 metadata-only
  `loopos.providers`. Includes `MockProviderRuntime`,
  `OpenAICompatibleProviderRuntime` (default-deny; live calls require
  explicit approval + budget + secret), `OllamaProviderRuntime`,
  `ProviderRuntimeRegistry`, `ProviderBudget`, secret redaction
  primitive. Live calls disabled by default. Budget guard blocks
  overspend. See `docs/provider-runtime.md`.
* **`loopos.opengod` (OpenGod Planning Layer)** — strategic
  meta-agent that emits **decisions only** — never executes.
  Decision kinds: `single_agent`, `adapter_agent`, `fusion_pair`,
  `fusion_committee`, `mad_dog`, `ask_user`, `halt`, `needs_repair`,
  `needs_replan`. `OpenGodBudgetGuard` refuses decisions that would
  push live spend past the configured ceiling. See
  `docs/v0-3-readme.md`.
* **Fusion Verdict Orchestration** — `loopos.fusion_router.orchestrator`.
  Caller-driven mapping of `FusionVerdict.status` to ALI state
  transitions: `needs_repair → REPAIRING (repair.plan)`,
  `needs_replan → REPLANNING (goal.replan)`, `rejected → HALTED_FAILURE`,
  `ask_user → WAITING_APPROVAL`.
* **v0.3 CLI surface** — 7 new commands: `loopos workbench`,
  `loopos adapters list|inspect|test`, `loopos providers runtime list|test`,
  `loopos model call`, `loopos opengod decide`, `loopos session list|status|events`,
  `loopos readiness check`. All commands support `--json` /
  `--plain` / structured error output / standard exit-code table.
* **`scripts/v0_3_readiness_check.py`** — 21-check v0.3 readiness
  proof covering Product Layer, Adapter Layer, Agent Bus, Provider
  Runtime, Fusion Orchestration, OpenGod, and a v0.2 regression
  guard. Exits 0 on `status == "pass"`, 1 otherwise.
* **Documentation** — `docs/v0-3-governance-boundary.md`,
  `docs/v0-3-anti-bloat.md`, `docs/v0-3-readme.md`,
  `docs/v0-3-readiness.md`, `docs/reports/v0-3-rc-audit.md`.

### Changed

* `loopos/cli/app.py` — registered 7 new top-level Typer commands.
* `loopos/cli/commands/__init__.py` — added new command exports.
* `loopos/cli/fallback.py` — added argparse subparsers for the
  new commands (so the v0.3 surface works without Typer too).
* `loopos/fusion_router/__init__.py` — re-exports
  `FusionVerdictOrchestrator` and `OrchestrationResult`.

### Testing

* 90 new v0.3 tests across 9 test files
  (`test_providers_runtime`, `test_agent_bus`, `test_opengod`,
  `test_product`, `test_v0_3_cli`, `test_adapters_v0_3`,
  `test_fusion_orchestrator`, `test_v0_3_readiness_check`,
  `test_v0_3_deep_smoke`).
* 932 not-slow tests pass (842 v0.2 + 90 v0.3).
* v0.3 readiness: 21/21 checks pass.
* v0.2 readiness: pass (regression guard).
* Anti-bloat hard-fail count: 0.
* Ruff: All checks passed.

## Unreleased

### Added

- **`loopos.providers`** — metadata-only Provider Runtime Registry.
  Pydantic v2 typed contracts (`ModelProviderProfile`,
  `ProviderCapabilityHints`, `ProviderRegistry`) with deterministic
  insertion-order semantics, strict duplicate rejection, and explicit
  capability / kind / feature lookups. Built-in profile catalog loaded
  from `providers/defaults.yaml` (27 entries). No network I/O. See
  `docs/source-transplant/provider-runtime-map.md` for the Hermes Agent
  source-transplant map and `docs/source-transplant/loopos-transplant-plan.md`
  for the unified Claude Code Main + Hermes Agent audit plan.
- **`loopos.aci`** — Agent Command Interface (Phase 2). Stable Pydantic v2
  contracts (`AgentCommand`, `AgentCommandResult`) with
  `schema_version="0.2"`. Adds `ProviderHint`, `ResolvedProvider`,
  `RiskHint`, `PolicyDecisionSummary`, `SyscallSummary`,
  `EvaluationSummary`, `ProgressSummary`, and `ConvergenceSummary`.
  Extended `AgentCommandKind` (`provider_select`, `explain_only`,
  `file.patch`, `git.commit`) and `AgentCommandStatus`
  (`unsupported`). `CommandRunner` resolves `ProviderHint` against
  `loopos.providers` BEFORE syscall dispatch and never fakes a
  successful command when the provider context is un-honorable.
  Wire-format helpers in `loopos/aci/serialization.py`. See
  `docs/agent-command-interface.md`.
- **`loopos.ali` -> ACI consumption (Phase 3)** —
  `consume_aci_result(session, result)` drives the existing
  `AgentLoopFSM` from a real `AgentCommandResult`. The consumer
  attaches an audit reference, computes a state-aware event
  sequence (`progress_updated` + `syscall_completed` for completed,
  `policy_denied` for policy blocks, `syscall_failed` /
  `convergence_replan` / `convergence_halt_failure` for failed,
  `convergence_halt_failure` for unsupported, `approval_required`
  for approval, `convergence_halt_blocked` for structural blocks),
  and applies each event through the existing transition table.
  Reason codes, trace ids, syscall ids, and resolved provider ids
  are propagated into every event payload. See
  `docs/agent-loop-interface.md`.
- **Provider consistency guard** —
  `tests/test_provider_model_kernel_consistency.py` asserts the
  boundary between `loopos.providers` (metadata substrate) and
  `loopos.model_kernel` (scheduler / client layer).
- **`KernelLoopEngine.submit_agent_command` (Phase 4)** — a thin
  opt-in integration point that runs an `AgentCommand` through
  `CommandRunner`, drives an `AgentLoopSession` via
  `consume_aci_result`, and mirrors the audit metadata
  (`trace_id`, `syscall_id`, `provider_id`, reason codes) onto
  `run.metadata["aci_outcomes"]`. Uses the kernel runtime's
  policy engine and syscall router, so Policy OS, Syscall Router,
  and Trace remain the single source of truth. The existing
  `KernelLoopEngine.run()` / `resume()` paths are untouched. See
  `docs/kernel-aci-ali-integration.md` for the full contract.
- **`loopos.trace.ali_bridge` (Phase 5)** — thin adapter that
  persists ALI event records into the existing kernel trace
  store. Each `AgentLoopEventRecord` becomes a `TraceEvent`
  with `kind="signal"` and `type="ali.event"`. The audit payload
  carries `aci_command_id`, `aci_goal_id`, `aci_status`,
  `aci_success`, `reason_codes`, `messages`, `trace_id`,
  `syscall_id`, `provider_id`, `provider_source`,
  `policy_decision`, `convergence_reason_code`, `kernel_run_id`,
  `kernel_step`, `kernel_status`, `kernel_phase`. The bridge is
  invoked from `KernelLoopEngine.submit_agent_command` after
  `consume_aci_result` returns the new event records; the
  existing `run.metadata["aci_outcomes"]` shape is unchanged.
  See `docs/trace-and-ali.md`.
- **`loopos.fusion_router` (Phase 6 / 7) — Fusion Router / Mad Dog
  Mode** — the planning-only escalation layer above the default
  single-model agent loop. Default execution stays single-model;
  fusion activates only when there is evidence the normal path
  is insufficient (explicit user request, repeated failure, no
  progress, large refactor, nasty bug, release blocker, high
  user dissatisfaction, model mismatch). Five modes (`single`,
  `pair`, `committee`, `attack`, `mad_dog`) selected by a
  deterministic integer score + severity multiplier, with
  explicit user request as the only threshold override. Role
  assignment reads the metadata-only `loopos.providers`
  registry and degrades gracefully when the registry cannot
  honour a role. The router is aggressive in reasoning but
  conservative in authority: it recommends ACI commands; only
  ACI / Kernel / Syscall Router may execute governed commands.
  **Phase 7** adds `loopos.fusion_router.persistence`
  (`FusionPlanStore`, atomic JSON write, deterministic key
  order, list/load helpers) and `loopos.fusion_router.runner`
  (`FusionRunner`, `FusionRunResult`, `describe_plan_mode`).
  `fusion-router status`, `mad-dog status`, `fusion-router list`,
  `mad-dog list`, `fusion-router route`, and `mad-dog route`
  consume the persistence layer so callers can inspect a
  previously-built plan and (with a kernel engine) opt into
  routing the recommended commands through
  `KernelLoopEngine.submit_agent_command`. CLI commands live
  under `loopos fusion-router ...` and `loopos mad-dog ...`.
  CLI: `loopos fusion-router plan/explain/run/escalate/status`
  + `loopos mad-dog` alias. Live multi-provider fanout, model
  debate loops, and automatic paid API spending are deferred to
  v0.3+. See `docs/fusion-router.md` and `docs/mad-dog-mode.md`.
- **Phase 8 — v0.2 Readiness Proof + Deterministic Deep Smoke**.
  Delivers the v0.2 RC proof loop without modifying
  `loopos/kernel/*` or `loopos/model_kernel/*`. New surface:
  - `loopos/trace/ali_replay.py` — **ALI Replay Engine**: reads
    persisted `ali.event` records from the existing
    `TraceStore`, rebuilds a fresh `AgentLoopSession`, and
    re-applies events through the existing `AgentLoopFSM`.
    Does not re-run ACI / Policy OS / Syscall Router. Does
    not call providers or run subprocesses. Deterministic:
    same ordered event stream -> same final session state.
  - `tests/test_ali_replay_engine.py` — 21 replay tests
    covering single-event, happy-path, blocked, approval,
    repair, replan, unsupported, trace-store roundtrip,
    determinism across runs, dropped-event accounting,
    and source-level safety.
  - `tests/test_v0_2_deep_smoke.py` — 23 deep-smoke tests
    that exercise the full Provider -> ACI -> ALI -> Kernel
    -> Trace -> Replay -> Fusion Router -> Persistence ->
    Runner pipeline end-to-end.
  - `scripts/v0_2_readiness_check.py --json` — emits a
    structured 15-check readiness proof
    (`schema_version="0.2"`, `status="pass"`,
    `hard_fail_count=0`).
  - `tests/test_v0_2_readiness_check.py` — 18 readiness
    regression tests.
  - `docs/v0-2-readiness.md` — release-readiness evidence:
    the proof matrix, the deep smoke scenario, the replay
    proof, the Fusion Router proof, the safety invariants,
    and the remaining limitations.

### Notes

- The new substrate is metadata-only; transport hooks (`fetch_models`,
  `prepare_messages`, `build_extra_body`, ...) and plugin auto-discovery
  are deferred to v0.3+ per `loopos-transplant-plan.md`.
- The new substrate coexists with `loopos.model_kernel` (the v0.1.0
  scheduler-aware registry); the two modules do not import from each
  other.
- ACI does not import `loopos.kernel.*` or touch `KernelLoopEngine`.
  Kernel integration is deferred to Phase 3+.
- ACI does not modify `loopos.model_kernel.*`, `loopos.kernel.*`, the
  v0.1.0 tag, the dist artifact, `docs/release-notes/`, or
  `docs/reports/`.

## 0.1.0 - 2026-06-21

Founding Release. See docs/release-notes/founding-preview.md for details.

### Added

- Versioned Kernel run processes, deterministic scheduling, approval signals, and validated transitions.
- Policy-governed syscalls, trace/replay, Kernel boot, and guarded/dry-run execution.
- Governed skill proposals, standalone context manager, and idempotent SQLite migrations.
- Kernel CLI commands for trace, replay, policy explain, tools, JSON, and approval resume.
- Goal Negotiation and typed Loop Convergence with evaluation, progress, decision, and halt traces.
- Python-only LoopOS MVP skeleton.
- Typed AI-ISA instruction schema.
- Deterministic state-machine loop.
- Permission-gated terminal executor.
- Memory OS primitives, governance, retrieval, pre-action gate, and skill extraction.
- MCP-like tool hub.
- CLI/FLI commands.
- Optional adapter boundaries for OpenHands, LangGraph, Letta, Zep, and projectmem.
- Deterministic tests, golden trace test, CI workflow, and benchmark runner.
- Modular CLI command, fallback, and renderer packages with UTF-8 output.
- Goal Negotiation v1, convergence evidence, and Policy OS L0-L5 safety contracts.
- Mock-only Data Guard with local backup verification, redaction, and database syscalls.
- Privacy-first local indexing, compute modes, plugin registry, and canonical Provider YAML.
- Gateway authentication/session/delivery records and leased worktree review flow.
- Apache-2.0 license, governance documents, and Loopi brand assets.
- Maintainability Kernel: `CodeChangeSummary`, `MaintainabilityFinding`,
  `MaintainabilityReport`, `MaintainabilityGateDecision`, scored analyzer with
  large-diff, missing-test, complexity, bypass, hardcoded-value, broad-exception,
  and hidden-global-state rules.
- System Kernel Hardening: `KernelLifecycle`, `RunProcess`, `KernelSignal`,
  `StateTransition`/`TransitionEngine`, `KernelInvariantChecker`,
  `KernelCheckpoint`/`CheckpointStore`, `ReplayEngine`, `Supervisor`.
- Review Artifact and Merge Gate: `ReviewArtifact`, `MergeGateDecision`,
  `ReviewArtifactBuilder`, `MergeGate` with eight blocker rules.
- Fusion Router skeleton: `FusionRequest`, `FusionPanel`, `ModelResponse`,
  `JudgeReport`, `FusionResult`, `FusionRouter`, `FusionJudge`,
  `FusionAggregator` (mock models only, no real provider calls).
- Prompt/Policy Distillation: `PromptSource`, `PromptSegment`, `BehaviorPack`,
  `RendererPack`, `PolicyPackDraft`, `PromptDistiller`, `DistillationAudit`
  with safety-conflict detection and no-source-text-copied audit.
- Real boundary adapters: OpenAI-compatible provider client with mock transport,
  local webhook gateway (message/approval/health handlers), and SQLite Data
  Guard adapter with backup, verify, shadow restore, and redaction.
- Founding Release Acceptance Suite: 14 end-to-end tests covering dry-run trace,
  transitions, invariants, SQLite backup, maintainability gate, review gate,
  fusion judge, distillation drafts, provider boundary, webhook approval,
  checkpoint replay, supervisor, lifecycle, and signal events.
- CLI command groups: `loopos code`, `loopos fusion`, `loopos distill`,
  `loopos kernel`, plus `loopos review artifact` and `loopos review gate`.
- Plugin examples under `examples/plugins/`: provider-openai-compatible,
  skill-pytest-repair, policy-strict-terminal, gateway-webhook,
  benchmark-basic - each with a manifest and README.
- Maintainability Kernel v0.5: `ArchitectureBoundaryRules` (module-boundary
  graph, cross-package import detection, public-API change checks),
  `TestQualityRules` (trivial-assertion, try/except-pass, skip/xfail
  detection), `TechnicalDebtRegistry` (append-only JSONL with fingerprint
  dedup and mark-paid).
- Kernel Invariants v0.5: seven new invariants covering Data Guard,
  provider policy, gateway auth, skill governance, maintainability gate,
  review artifact before merge, and checkpoint before high-risk action,
  plus a `check_all_extended` aggregator.
- CLI workspace validation: `run` and `worktrees` return a clean
  exit-code-2 error with a suggestion when the workspace does not exist
  or is not a directory, instead of a Rich traceback.
- Prompt Distillation v0.5: per-rule routing across behavior / renderer /
  policy / safety buckets so a single segment can populate multiple
  packs.
- Fusion + Provider integration: `FusionRouter` optionally backed by
  `ProviderRegistry`; `FusionRunner` writes fusion events to `TraceStore`
  and downgrades `cloud_allowed` to `local_only` when the prompt carries
  sensitive context.
- Webhook Gateway demo path: `loopos gateway webhook-flow` and
  `loopos gateway webhook-health` commands demonstrating the full
  message -> run_spec -> approval -> resume contract.
- SQLite Data Guard demo path: `loopos db sqlite-demo` command
  demonstrating inspect -> backup -> verify -> shadow -> validate on a
  temp database with no production impact.
- Founding release readiness gate with isolated package hygiene, README link,
  governance, plugin example, metadata, CLI, policy explanation, and release-note checks.
- Release packaging top-level allowlist and blocking for runtime databases, logs,
  environment files, private keys, oversized artifacts, and broken README links.
- Python AST symbol/import indexing with symbol search and file explanation commands.
- Productized Kernel inspect and trace-tree output with run, approval, checkpoint,
  invariant, and no-side-effect replay context.
- Review Artifact pipeline aggregation for trace, diff, test, policy, Data Guard,
  and Maintainability Gate evidence.
- Founding documentation, offline demo inputs, screenshot guidance, limitations,
  plugin contributor guidance, and release notes.
- Founding Release final hardening: readiness tier separation, generated CI
  reports, deep smoke suite, invalid-diff maintainability safety, risk-aware
  MergeGate, structured review evidence, Fusion trace event IDs, SQLite real
  file Data Guard flow, Prompt Distillation v0.9 safety fields, registry
  permission explanations, and local import/diff intelligence.

### Fixed

- Added an observation-driven Kernel evaluation source so real policy, syscall,
  and observation failures override compatibility hints.
- Added per-run progress accumulation for repeated failures, repeated actions,
  and no-progress tracking.
- Routed syscall failures through evaluation, progress, convergence, and the
  scheduler instead of a direct halt transition.
- Made strict-source release checks inspect local development state while
  retaining a separate package-from-development-tree mode.
- Added bounded per-check Deep Smoke execution with duration, command, output
  tails, filtering, and structured timeout reports.
- Narrowed remote script chain detection so unchained `curl`/`wget` and shell
  words are not incorrectly classified as L5.

### Changed

- `EVAL.APPLY` and `PROGRESS.MEASURE` arguments are compatibility hints rather
  than authoritative runtime truth.
- Convergence-to-scheduler handoffs now include evaluation, progress, scheduler
  input, scheduler decision, and runtime source in Trace.
- Founding Release test reports must be generated by `scripts/ci_report.py` and
  reference the current commit or its direct parent.

### Notes

- Real provider, ChatOps, and database connections remain disabled in Alpha tests.
- No Web UI.
- Licensed under Apache-2.0.
