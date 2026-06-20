# AGENTS.md - LoopOS Coding Agent Instructions

## Project Identity

LoopOS is a terminal-native, state-machine-driven, self-improving AI agent runtime.

It combines:
- AI-ISA: typed instructions for agent actions.
- State Machine Loop: deterministic execution of instructions.
- MCP Tool Hub: external tools behind protocol-like interfaces.
- Terminal Runtime: shell execution as a first-class, permission-gated tool.
- Memory OS: state, events, beliefs, skills, and preferences.
- Memory Governance: memory writes are validated, deduplicated, versioned, and confidence-scored.
- Skill Learning: successful traces can be compressed into reusable skills.
- CLI/FLI: no Web UI in the MVP.

## Core Principle

Do not build a chatbot. Build a state-driven runtime.

Natural language may exist at the input and output boundaries, but internal runtime communication must use structured objects:
- Pydantic models
- JSON-compatible schemas
- typed events
- explicit state transitions
- deterministic functions

Avoid:
- large prompt blobs embedded in business logic
- hidden global state
- unbounded loops
- direct shell execution without permission checks
- memory writes without governance metadata

## Language Choices

MVP implementation is Python-only:
- Python 3.11+
- Pydantic v2 for schemas
- Typer and Rich for CLI when available, with a standard-library fallback for local bootstrapping
- pytest-compatible tests

## Architecture Rules

The MVP structure follows:

```text
loopos/
  cli/
  core/
  agents/
  execution/
  memory/
  mcp/
  integrations/
tests/
```

The core loop follows:

```text
Goal
-> compile or plan next AI-ISA instruction
-> execute instruction
-> observe output
-> evaluate progress
-> update state
-> write governed memory/event
-> continue or terminate
```

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
