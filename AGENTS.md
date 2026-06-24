# AGENTS.md - LoopOS Coding Agent Instructions

## Project Identity (v0.4.0)

> **LoopOS is a Loop Engineering Runtime for AI agents.**

User gives a goal. LoopOS plans, builds, tests, reviews, repairs, optimizes,
and repeats until the work is ready to deliver.

> User goal is the north star. Loop is the engine. Safety is the boundary.

The v0.4.0 product surface is the ``loopos.loop_engine`` package — the
**product-facing orchestrator** that drives the Goal → Plan → Build → Test
→ Review → Repair → Optimize → Deliver cycle. The Kernel Loop Engine
(``loopos.kernel``) remains the **low-level execution backend**. Policy OS,
the Syscall Router, Memory OS, and Trace are the **boundary layer** —
real and intact, but no longer the product's first screen.

Codex is the engineering agent that implements and verifies LoopOS. Codex
is not the LoopOS runtime, must not impersonate its Kernel, and must
deliver changes in auditable phases with tests.

It combines:
- AIL: Agent Internal Language for structured runtime communication.
- AI-ISA: typed instructions for agent actions.
- **LoopEngine**: the v0.4.0 product-facing orchestrator.
- **Quality Engine**: scoring, convergence, and delivery decisions.
- **Fusion Optimizer**: multi-candidate next-plan optimization.
- **Imagination Sandbox**: thought-only creative space.
- **Commitment Boundary / Action Boundary**: idea → action gating.
- State Machine Loop: deterministic execution of instructions.
- MCP Tool Hub: external tools behind protocol-like interfaces.
- Terminal Runtime: shell execution as a first-class, permission-gated tool.
- Policy OS: behavior, tool, terminal, memory, context, and render policy decisions.
- Memory OS: state, events, beliefs, skills, and preferences.
- Memory Governance: memory writes are validated, deduplicated, versioned, and confidence-scored.
- Skill Learning: successful traces can be compressed into reusable skills.
- CLI/FLI: no Web UI in the MVP.

## Core Principle

Do not build a chatbot. Build a **state-driven loop engineering runtime**.

Natural language may exist at the input and output boundaries, but internal
runtime communication must use structured objects:

- AIL models
- AI-ISA instructions
- Pydantic models
- JSON-compatible schemas
- typed events
- explicit state transitions
- deterministic functions
- structured policy decisions

The v0.4.0 loop adds one more principle: **the loop is the engine**. The
product is the closed Goal → Plan → Build → Test → Review → Repair →
Optimize → Deliver cycle, not any single phase. Safety / governance is a
**boundary layer** that protects real side effects; it is not the loop.

Avoid:
- large prompt blobs embedded in business logic
- hidden global state
- unbounded loops
- direct shell execution without permission checks
- tool calls without Policy OS / permission checks
- memory writes without governance metadata
- **pretending a simulated executor is a real one** — always set
  ``status="simulated"`` and never claim a side effect actually happened
- **bypassing the commitment boundary** — an idea becomes an action only
  via ``CommitmentBoundary.commit()``

## Language Choices

MVP implementation is Python-only:
- Python 3.11+
- Pydantic v2 for schemas
- PyYAML for policy packs
- Typer and Rich for CLI when available, with a standard-library fallback for local bootstrapping
- pytest-compatible tests

## Architecture Rules

The MVP structure follows:

```text
loopos/
  ail/                      # Agent Internal Language
  cli/                      # CLI / FLI
  core/                     # Legacy state-machine core (deprecated)
  agents/                   # Agent adapters
  execution/                # Execution backend
  memory/                   # Memory OS
  mcp/                      # MCP Tool Hub
  policy_os/                # Policy OS (boundary)
  kernel/                   # Kernel Loop Engine (execution backend)
  context/                  # Context compilation
  syscalls/                 # Syscall Router (boundary)
  integrations/             # Provider / framework integrations
  loop_engine/              # v0.4.0 Loop Engineering Runtime (product)
  quality/                  # v0.4.0 Quality Engine
  fusion_optimizer/         # v0.4.0 Fusion Optimizer
  boundary/                 # v0.4.0 Action Boundary facade
policies/
tests/
```

The v0.4.0 core loop:

```text
User Goal
  -> Understand / Normalize
  -> Define Success Criteria
  -> Plan
  -> Build
  -> Test
  -> Review
  -> Quality Score
  -> Convergence Decision
  -> Repair / Optimize (if continue)
  -> Deliver (if converge)
```

The preserved AIL / AI-ISA kernel loop:

```text
AIL Goal
-> compile into AIL runtime context
-> compile context
-> apply Policy OS constraints
-> compile or plan next AIL / AI-ISA instruction
-> validate and normalize the instruction
-> schedule the instruction
-> route external actions through a syscall
-> observe output
-> evaluate progress
-> apply an explicit state transition
-> write governed memory/event
-> continue or terminate
```

Kernel invariants:
- every external action is a syscall
- every syscall is policy checked
- every state transition is logged
- every durable memory or skill write is governed
- every loop is bounded and schedulable
- every run is replayable without repeating side effects
- **every v0.4.0 LoopIteration is fully populated** — failed tests feed
  findings, findings feed repair, repair feeds the next plan candidate;
  the data flow is real, not static.

## AIL Rules

AIL is the canonical internal language for runtime handoffs. AI-ISA remains the executable instruction compatibility layer.

Every AIL instruction must include:
- op
- id
- created_at
- reason_code
- args
- safety
- expected_observation
- metadata

Rules:
- `EXEC_TERMINAL` requires terminal policy metadata.
- `CALL_TOOL` requires routing or policy metadata.
- `STORE_MEMORY` cannot write durable memory directly; it must create a proposal or explicit write request.
- AIL codec adapters must preserve AI-ISA round-tripping.
- Kernel AIL operations use dotted names such as `GOAL.SET`, `TERM.EXEC`, and `LOOP.HALT`.
- Legacy AI-ISA operation names are accepted only through compatibility adapters.

## AI-ISA Minimum Instructions

Implement these typed operations:
- PLAN
- CALL_TOOL
- EXEC_TERMINAL
- OBSERVE
- EVALUATE
- UPDATE_STATE
- STORE_MEMORY
- EXTRACT_SKILL
- TERMINATE

Every instruction must include:
- op
- id
- created_at
- reason_code
- args
- safety
- expected_observation
- metadata

## Policy OS Rules

Policy OS is a structured decision layer, not a prompt blob.

It must run before:
- planning constraints are used
- instructions execute
- terminal commands run
- MCP-like tools are called
- durable memory is written
- context is compiled for planner or renderer
- final output is rendered

Policy outputs must be structured decisions with:
- allowed
- action
- severity
- reason_codes
- constraints
- tool_preferences
- memory_filters
- render_hints
- audit_required

Conflict priority:
system integrity > safety > permission/privacy > user explicit instruction > project policy > memory/user preference > style/optimization.

## Safety Rules

Never add code that executes destructive shell commands without an explicit permission gate.

Dangerous examples:
- rm -rf
- sudo
- chmod -R 777
- curl | bash
- disk formatting
- broad process killing
- changing global git config
- network exfiltration

All terminal commands must pass through a permission policy.
Policy OS decisions must not be bypassed by terminal, file, git, memory, or MCP paths.
Dry-run and replay paths must never execute a syscall adapter with side effects.

## Memory Rules

Memory is not raw text. Every memory item must include:
- id
- type
- content
- confidence
- source
- created_at
- updated_at
- version
- tags
- conflicts
- status

Global memory writes must go through Memory Governance.
Policy OS can deny, require review, or constrain memory writes before governance persists them.

## Testing Rules

For every new module:
- add deterministic unit tests
- avoid real network calls
- mock LLM calls
- mock shell execution except when testing the terminal executor

Preferred checks:

```bash
pytest
ruff check .
mypy .
```

If local tooling is unavailable, document it in the final response and run the closest available deterministic check.

## Maintainability Rule

LoopOS rejects code that merely runs.

AI-generated code must be:
- scoped
- typed
- tested
- traceable
- explainable
- maintainable
- reversible

Passing tests is necessary but not sufficient.

Do not:
- modify unrelated files
- duplicate existing logic
- bypass Policy OS
- bypass Syscall Router
- bypass Data Guard
- bypass Memory Governance
- bypass Trace
- add hidden global state
- swallow errors silently
- add broad compatibility hacks without migration plan
- add dependencies without justification

Every code change must include:
1. changed files summary
2. test coverage
3. maintainability reasoning
4. remaining technical debt
