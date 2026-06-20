# LoopOS MVP Architecture

## Goals / Non-goals

Goals:
- Provide a Python-only, terminal-native AI agent runtime.
- Use typed AI-ISA instructions internally.
- Execute through a bounded state machine.
- Gate terminal commands through explicit safety policy.
- Persist state, events, beliefs, and skills locally.
- Support optional third-party adapters without core dependency.

Non-goals:
- No Web UI.
- No real LLM calls in the MVP.
- No full MCP protocol implementation yet.
- No external memory service requirement.
- No direct dependency on OpenHands, LangGraph, Letta, Zep, or projectmem internals.

## System Overview

```text
User goal
-> Planner / policy
-> AI-ISA Instruction
-> LoopEngine
-> Tool or terminal executor
-> Observation
-> Evaluator
-> LoopState update
-> EventLog append
-> Memory Governance
-> next instruction or termination
```

## Module Structure

- `loopos.core`: AI-ISA, state, loop engine, policy, safety, context compiler.
- `loopos.execution`: terminal executor and permission policy.
- `loopos.memory`: event/state stores, beliefs, skills, governance, retrieval, pre-action gate.
- `loopos.mcp`: MCP-like type contracts and router.
- `loopos.agents`: small planner, critic, and renderer interfaces.
- `loopos.integrations`: optional adapters for local source snapshots and future SDKs.
- `loopos.cli`: CLI/FLI entry point.

## AI-ISA Design

AI-ISA is the internal instruction set. It supports:

- `PLAN`
- `CALL_TOOL`
- `EXEC_TERMINAL`
- `OBSERVE`
- `EVALUATE`
- `UPDATE_STATE`
- `STORE_MEMORY`
- `EXTRACT_SKILL`
- `TERMINATE`

Each instruction includes safety metadata and expected observations.

## State Schema

`LoopState` tracks run id, goal, status, step index, progress score, current instruction, last observation, errors, tool history, memory references, and timestamps.

## Event Log Schema

Events are append-only JSONL records with id, run id, step index, event type, payload, and timestamp.

## Memory Schema

Memory items include id, type, content, confidence, source, timestamps, version, tags, conflicts, and status. Skills include id, name, description, trigger tags, reusable steps, source run id, confidence, created timestamp, and version.

## Loop Lifecycle

1. Create `LoopState`.
2. Ask policy/planner for next instruction.
3. Validate instruction against MVP rules.
4. Run the pre-action gate.
5. Execute instruction.
6. Evaluate observation.
7. Apply state transition.
8. Append event log records.
9. Persist state.
10. Stop on success, failure, cancellation, block, timeout, or max steps.

## Terminal Execution Safety

Every command is analyzed before execution. Blocked commands never run. High-risk commands require approval. CWD must be inside allowlisted paths when an allowlist is configured. The default executor is non-interactive and rejects approval-required commands.

## MCP Abstraction

The MVP uses a protocol-shaped router with `ToolSpec`, `ToolCall`, `ToolResult`, `ToolRegistry`, and `ToolRouter`. Built-ins are limited to terminal mock execution, file read/write with path checks, and git status.

## Testing Strategy

- Unit tests for schema validation, loop behavior, safety classification, memory governance, retrieval, and router behavior.
- CLI smoke tests.
- Optional integration adapter tests must pass without third-party packages installed.
- No real network calls.
- No real LLM calls.

## Milestone Plan

1. MVP skeleton and docs.
2. AI-ISA, state, loop, terminal safety.
3. Memory OS, governance, retrieval, skill learning, context compiler.
4. MCP-like router and CLI.
5. Optional OpenHands/LangGraph adapters.
6. Benchmarks and golden traces.

## Risks and Mitigations

- Unsafe shell execution: force all commands through `PermissionPolicy`.
- Memory pollution: require governance metadata and confidence thresholds.
- Dependency sprawl: keep third-party integrations optional.
- Unbounded loops: require max steps and terminal statuses.
- Schema drift: keep AI-ISA tests strict.
