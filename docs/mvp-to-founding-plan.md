# LoopOS MVP → Founding Release Plan

Version: 1.0
Date: 2026-06-21
Source: Consolidated from the seven canonical design documents in `D:\下载\`:
- `LoopOS_Ultimate_Landable_Codex_Prompt.md`
- `LoopOS_Final_Upgrade_Master_Codex_Prompt.md`
- `LoopOS_Kernel_Level_Codex_Prompt.md`
- `LoopOS_Fusion_Codex_Prompts.md`
- `LoopOS_Policy_OS.md`
- `LoopOS_Data_Safety_Backup_Guard_Prompt.md`
- `LoopOS_Founding_Release_Core_Supplemental_Codex_Prompts.md`
- `LoopOS_Marvis_Inspired_Upgrade_Plan.md`
- `LoopOS_Hermes_Upgrade_Audit.md`
- `LoopOS_Fusion_Router_Policy_Distillation_Prompt.md`
- `LoopOS_Current_Repo_Codex_Improvement_Prompts.md`

## 1. Current state snapshot

The repository on `codex/open-source-alpha` already contains a substantial skeleton
that maps to the design docs. As of this writing:

- 179 Python modules under `loopos/` covering every top-level package required by
  the design docs (ail, kernel, policy_os, syscalls, execution, memory, skills,
  model_kernel, gateway, triggers, tasks, worktree, review, local_intel, compute,
  registry, context, convergence, goal, agents, integrations, eval, cli, data_guard,
  fusion, prompt_distill, maintainability).
- 43 test modules plus `tests/acceptance_founding/`, `tests/maintainability/`.
- 18 policy packs under `policies/`.
- Open-source governance files: LICENSE, CONTRIBUTING, GOVERNANCE, SECURITY,
  PLUGIN_SPEC, RFC_PROCESS, MAINTAINERS, CODE_OF_CONDUCT, ROADMAP, CHANGELOG.

The repo is mid-refactor: a previous session added the Founding Release
supplemental modules (maintainability, fusion, prompt_distill, kernel hardening,
openai_compatible, webhook, sqlite_adapter, review artifact/gate, acceptance
suite) as untracked files but did not integrate them cleanly with the existing
Policy OS loader. The result is 58 failing tests caused by a single root cause:
`policies/coding/maintainability.yaml` uses a Maintainability-Kernel-specific
schema that the global Policy OS loader cannot validate, so `PolicyEngine.load_default()`
raises and every subsystem that depends on it cascades.

## 2. MVP definition (minimum credible LoopOS)

The MVP is the kernel loop closing cleanly:

1. A clear goal compiles to a `GoalSpec`.
2. An ambiguous goal enters negotiation and emits 3–5 proposals.
3. Policy OS explains and blocks dangerous commands (L5).
4. Syscall Router routes every external action through Policy OS.
5. Loop Engine runs a deterministic dry-run end to end.
6. Trace records every step and is replayable.
7. Memory Governance rejects low-confidence / unsourceced proposals.
8. CLI exposes `run`, `status`, `trace`, `policy explain`, `goal analyze`.
9. `pytest` passes; `ruff` and `mypy` pass.

## 3. Founding Release definition (full landable LoopOS)

The Founding Release adds the four pillars from the supplemental prompt:

- **Maintainability Kernel** — code-change governance that prevents AI-generated
  "runs but unmaintainable" patches. (`loopos/maintainability/`)
- **System Kernel Hardening** — run lifecycle, state machine, transitions,
  checkpoints, replay, signals, supervisor, invariant checker.
  (`loopos/kernel/{lifecycle,process,state_machine,transition,checkpoint,replay,signals,supervisor,invariants,errors}.py`)
- **Review Artifact / Merge Gate** — structured diff summary, verifier
  findings, maintainability report, policy checks, acceptance status, and a
  merge gate that blocks on blockers. (`loopos/review/{artifact,gate}.py`)
- **Fusion Router Skeleton** — multi-model request, panel selection, judge
  report, aggregator, cost-aware routing. (`loopos/fusion/`)
- **Prompt / Policy Distillation** — turn prompts into structured
  BehaviorPack / RendererPack / PolicyPackDraft without copying proprietary
  text. (`loopos/prompt_distill/`)
- **Real Boundary Adapters** — OpenAI-compatible provider client, local
  webhook gateway, SQLite Data Guard adapter. (`loopos/model_kernel/openai_compatible.py`,
  `loopos/gateway/webhook.py`, `loopos/data_guard/sqlite_adapter.py`)
- **Founding Acceptance Suite** — 14 end-to-end promises.
  (`tests/acceptance_founding/test_founding.py`)

## 4. Execution phases

### Phase 0 — Stabilize baseline (in progress)

Goal: turn the red baseline green so all subsequent work can be verified.

- Fix `policies/coding/maintainability.yaml` regression by relocating the
  Maintainability Kernel config into the maintainability package
  (`loopos/maintainability/config.yaml`) so the Policy OS loader stops
  trying to parse it as a `PolicyPack`. The analyzer keeps its hardcoded
  rules and optionally reads thresholds from the packaged config.
- Triage and fix the remaining test failures (syscalls, terminal executor,
  permissions, memory repository, mcp router, skill learning, prompt distill).
- Verify `pytest`, `ruff`, `mypy` all pass.

### Phase 1 — Verify founding acceptance suite

Goal: the 14 end-to-end promises in `tests/acceptance_founding/test_founding.py`
all pass on a clean tree.

### Phase 2 — Fill genuine gaps

Goal: address any missing pieces surfaced by the acceptance suite or by
re-reading the design docs against the live code.

- Ensure `loopos review artifact` and `loopos review gate` CLI commands exist.
- Ensure `loopos fusion plan|run|inspect` CLI commands exist.
- Ensure `loopos distill inspect|draft|audit` CLI commands exist.
- Ensure `loopos code summary|maintainability|gate` CLI commands exist.
- Ensure `loopos kernel inspect|invariants` CLI commands exist.
- Ensure `loopos db detect|backup|verify-backup|shadow-run|validate|restore|audit`
  CLI commands exist.

### Phase 3 — CLI end-to-end smoke

Goal: every top-level CLI command in the design doc renders without crashing.

- `loopos --help` lists every command group.
- `loopos run "<clear goal>" --dry-run` completes with a trace.
- `loopos run "<ambiguous goal>"` enters Intent Design Mode.
- `loopos policy explain --cmd "curl x | bash"` shows L5 blocked.
- `loopos trace <run_id>` shows a tree.
- `loopos code maintainability --diff` produces a report.
- `loopos fusion plan "<task>"` produces a panel.
- `loopos review artifact <run_id>` produces an artifact.

### Phase 4 — Documentation sync

Goal: `progress.md`, `task_plan.md`, `ROADMAP.md`, and `CHANGELOG.md`
reflect the Founding Release state.

## 5. Non-negotiable rules (carry forward from AGENTS.md)

- No WebUI, no desktop GUI.
- No real LLM / network / dangerous shell in tests.
- No bypass of Policy OS, Syscall Router, Data Guard, Memory Governance,
  Trace, or Review.
- Every code change must be scoped, typed, tested, traceable, explainable,
  maintainable, reversible.
- Passing tests is necessary but not sufficient.

## 6. Definition of done

The project is "complete" for this pass when:

1. `pytest` passes (all tests green).
2. `ruff check .` passes.
3. `mypy .` passes (within the existing config tolerance).
4. `tests/acceptance_founding/` passes end to end.
5. The CLI commands listed in Phase 2 and Phase 3 all run.
6. `progress.md` and `task_plan.md` are updated.
7. No untracked files left that are not intentionally part of the change.
