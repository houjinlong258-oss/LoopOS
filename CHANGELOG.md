# Changelog

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
