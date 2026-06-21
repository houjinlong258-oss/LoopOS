# Changelog

## 0.1.0 - Unreleased

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
  benchmark-basic — each with a manifest and README.
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

### Notes

- Real provider, ChatOps, and database connections remain disabled in Alpha tests.
- No Web UI.
- Licensed under Apache-2.0.
