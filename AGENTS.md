# AGENTS.md - LoopOS Coding Agent Instructions

## Project Identity

LoopOS is a terminal-native, state-machine-driven, self-improving AI agent runtime.

It combines:
- AIL: Agent Internal Language for structured runtime communication.
- AI-ISA: typed instructions for agent actions.
- State Machine Loop: deterministic execution of instructions.
- MCP Tool Hub: external tools behind protocol-like interfaces.
- Terminal Runtime: shell execution as a first-class, permission-gated tool.
- Policy OS: behavior, tool, terminal, memory, context, and render policy decisions.
- Memory OS: state, events, beliefs, skills, and preferences.
- Memory Governance: memory writes are validated, deduplicated, versioned, and confidence-scored.
- Skill Learning: successful traces can be compressed into reusable skills.
- CLI/FLI: no Web UI in the MVP.

## Core Principle

Do not build a chatbot. Build a state-driven runtime.

Natural language may exist at the input and output boundaries, but internal runtime communication must use structured objects:
- AIL models
- AI-ISA instructions
- Pydantic models
- JSON-compatible schemas
- typed events
- explicit state transitions
- deterministic functions
- structured policy decisions

Avoid:
- large prompt blobs embedded in business logic
- hidden global state
- unbounded loops
- direct shell execution without permission checks
- tool calls without Policy OS / permission checks
- memory writes without governance metadata

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
  ail/
  cli/
  core/
  agents/
  execution/
  memory/
  mcp/
  policy_os/
  integrations/
policies/
tests/
```

The core loop follows:

```text
Goal
-> compile into AIL runtime context
-> compile context
-> apply Policy OS constraints
-> compile or plan next AI-ISA instruction
-> validate AI-ISA / AIL instruction
-> execute instruction
-> observe output
-> evaluate progress
-> update state
-> write governed memory/event
-> continue or terminate
```

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
