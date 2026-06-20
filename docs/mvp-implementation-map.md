# MVP Implementation Map

This document maps the requested LoopOS prompt phases to the MVP files now present in this repository.

## 01 Repo Audit

- `docs/repo-audit.md`
- Scope: current directory map, detected third-party snapshots, reusable components, risks, and MVP path.

## 02 Source Extraction

- `docs/source-extraction.md`
- Scope: architecture patterns from OpenHands, LangGraph, Letta, Zep, and projectmem without copying their internals.

## 03 Target Architecture

- `docs/architecture-mvp.md`
- Scope: goals, non-goals, module structure, AI-ISA, state, events, memory, loop lifecycle, terminal safety, MCP abstraction, tests, milestones, and risks.

## 04 LoopOS Core Skeleton

- `pyproject.toml`
- `README.md`
- `AGENTS.md`
- `loopos/`
- `tests/`

## 05 AI-ISA Instruction Set

- `loopos/core/isa.py`
- `tests/test_isa.py`
- Supports `PLAN`, `CALL_TOOL`, `EXEC_TERMINAL`, `OBSERVE`, `EVALUATE`, `UPDATE_STATE`, `STORE_MEMORY`, `EXTRACT_SKILL`, and `TERMINATE`.

## 06 State Machine Loop

- `loopos/core/state.py`
- `loopos/core/policy.py`
- `loopos/core/loop_engine.py`
- `tests/test_loop_engine.py`
- Includes deterministic demo policy, mock executor, evaluator, event logging, state persistence, max-step guard, and terminal statuses.

## 07 Terminal Executor

- `loopos/execution/terminal.py`
- `loopos/execution/permissions.py`
- `tests/test_terminal_executor.py`
- `tests/test_permissions.py`

## 08 MCP Tool Hub

- `loopos/mcp/types.py`
- `loopos/mcp/router.py`
- `tests/test_mcp_router.py`
- Built-ins: `terminal.exec`, `file.read`, `file.write`, `git.status`.

## 09 Memory OS

- `loopos/memory/event_log.py`
- `loopos/memory/state_store.py`
- `loopos/memory/belief_store.py`
- `loopos/memory/skill_store.py`
- `tests/test_memory.py`

## 10 Memory Governance

- `loopos/memory/governance.py`
- `docs/memory-design-from-sources.md`
- Covers confidence thresholds, duplicate rejection, conflict marking, provenance, versions, and status.

## 11 Skill Learning

- `loopos/memory/skill_store.py`
- `extract_skill_from_events()`
- Tests cover extraction from successful instruction events and tag-based lookup.

## 12 Context Compiler

- `loopos/core/context.py`
- Emits bounded structured `AgentContext` instead of large prompt text.

## 14 CLI/FLI UI

- `loopos/cli/app.py`
- `tests/test_cli.py`
- Commands: `run`, `resume`, `status`, `history`, `skills`, `memory`, `config`.
- Uses Typer/Rich when installed and a standard-library fallback otherwise.

## 15 Security and Permission Model

- `loopos/core/safety.py`
- `loopos/execution/permissions.py`
- `docs/safety.md`
- `tests/test_safety.py`

## 16 OpenHands Integration

- `loopos/integrations/openhands_adapter.py`
- `docs/integrations-openhands.md`
- Fallback adapter supports command execution and workspace file operations through LoopOS safety boundaries.

## 17 LangGraph Integration

- `loopos/core/graph_loop.py`
- `loopos/integrations/langgraph_adapter.py`
- `docs/integrations-langgraph.md`
- Optional dependency. Native LoopEngine fallback remains the default.

## 18 Letta/Zep/projectmem Memory Patterns

- `loopos/integrations/letta_adapter.py`
- `loopos/integrations/zep_adapter.py`
- `loopos/integrations/projectmem_adapter.py`
- `loopos/memory/retrieval.py`
- `loopos/memory/pre_action_gate.py`
- `docs/memory-design-from-sources.md`
- Tests cover retrieval ranking, low-confidence filtering, repeated failure blocking, and skill substitution.

## Memory-first Alpha Additions

- `loopos/memory/repository.py`
- `loopos/memory/sqlite_store.py`
- `loopos/memory/proposals.py`
- `loopos/memory/extractor.py`
- `loopos/llm/providers.py`
- `docs/memory-governance.md`
- `docs/llm-provider.md`

Added JSONL + SQLite memory indexing, governed memory proposals, user profile storage, layered context compilation, mock/OpenAI-compatible memory proposal extraction, memory/profile CLI commands, and memory-focused benchmark tasks.

## Fusion / AIL / Policy OS Additions

- `docs/LoopOS_Fusion_Codex_Prompts.md`
- `docs/LoopOS_Policy_OS.md`
- `loopos/ail/`
- `loopos/policy_os/`
- `policies/`
- `tests/test_ail.py`
- `tests/test_policy_os.py`

Added Agent Internal Language models, AI-ISA adapters, AIL validation, YAML policy packs, Policy OS loading/matching/conflict resolution, policy-aware terminal/tool/memory/context/loop integration, policy/AIL CLI commands, and a policy compliance benchmark task.

## Verification

The MVP was verified with:

```bash
python -m unittest discover -s tests
python -m pytest
python -m ruff check .
python -m mypy loopos tests
python -m loopos.cli.app --help
python -m loopos.cli.app run demo --dry-run
python -m loopos.cli.app policy list
python -m loopos.cli.app profile show
```

The local environment used a repository-local `.venv`, which is ignored by `.gitignore`.

## Kernel MVP Additions

- `loopos/kernel/`: Boot, RunManager, scheduler, process model, transitions, trace, replay, and KernelLoopEngine.
- `loopos/syscalls/`: typed registry/router and terminal, file, and Git syscall adapters.
- `loopos/context/`: bounded context manager with the previous core import retained as a compatibility export.
- `loopos/agents/skill_extractor.py`: successful-trace SkillProposal extraction.
- CLI: guarded/dry-run Kernel execution, approval resume, trace, replay, policy explain, tools, JSON, AIL, and policy views.
- `loopos/goal/`: pre-run ambiguity analysis, five-option proposals, and finalized GoalSpec.
- `loopos/convergence/`: typed evaluation, progress, loop decisions, and halt conditions.

The Kernel prompt is stored in `docs/LoopOS_Kernel_Level_Codex_Prompt.md`. Hermes remains a local ignored architecture reference and is not a dependency.

## Kernel Builder / Outer Loop Additions

- `loopos/tasks/`: persistent JSON task queue with quick-win selection.
- `loopos/triggers/`: deterministic trigger kernel; triggers create tasks only and do not execute work.
- `loopos/worktree/`: worktree planning records with branch naming and conflict detection.
- `loopos/review/`: Producer, Verifier, and Reviewer separation for high-risk/code tasks.
- `loopos/skills/`: compatibility exports for the governed skill kernel.
- `loopos/model_kernel/`: provider profiles, capability routing, mock client, and multi-model role scheduler.
- `loopos/gateway/`: ChatOps/mobile mock adapters and message-to-RunSpec conversion.
- CLI: `triggers`, `tasks`, `worktrees`, `review`, `providers`, and `gateway`.

This stage intentionally does not call real model APIs, real chat platform APIs, or materialize Git worktrees directly. Those actions must go through Policy OS and syscalls when enabled.
