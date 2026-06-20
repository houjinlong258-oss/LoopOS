# Architecture

LoopOS is a state-machine agent runtime. Natural language is allowed at the user boundary, but internal execution uses structured objects: AIL, AI-ISA, typed events, policy decisions, observations, evaluations, and governed memory proposals.

## Runtime Flow

```text
Goal
-> AIL Goal / State
-> Context Compiler
-> Policy OS
-> Planner
-> AI-ISA / AIL Instruction
-> Instruction Validator
-> LoopEngine
-> Policy OS / Permission / PreActionGate
-> MCP Tool Router or Terminal Executor
-> Observation
-> Evaluator
-> LoopState update
-> EventLog append
-> Memory Governance
-> Terminate or continue
```

## Core Modules

- `loopos.ail`: Agent Internal Language models, validators, and AI-ISA adapters.
- `loopos.core`: AI-ISA, state, policy, loop engine, safety, context compiler.
- `loopos.execution`: terminal executor and permission policy.
- `loopos.memory`: event log, state store, beliefs, skills, governance, retrieval, pre-action gate.
- `loopos.memory.repository`: JSONL + SQLite Memory OS facade.
- `loopos.llm`: mock and OpenAI-compatible providers used for governed memory proposals.
- `loopos.mcp`: MCP-like tool specs and router.
- `loopos.policy_os`: YAML policy packs, loader, matcher, conflict resolver, engine, and audit log.
- `loopos.agents`: deterministic planner, critic, renderer.
- `loopos.integrations`: optional third-party adapter boundaries.
- `loopos.eval`: deterministic benchmark runner and metrics.
- `loopos.cli`: CLI/FLI entry point.

## Design Boundary

OpenHands, LangGraph, Letta, Zep, and projectmem are inspiration and optional integration targets. LoopOS owns its schemas and does not copy or require those projects for core tests.

## Memory-first Alpha

The Alpha memory layer keeps JSON/JSONL artifacts for audit and adds SQLite indexing for retrieval and proposal review. LLM output is restricted to `MemoryProposal` generation; governance and explicit accept/reject decisions control durable memory writes.

For deeper MVP details, see `docs/architecture-mvp.md`.

## Fusion / Policy OS Stage

The current stage adds AIL and Policy OS as the cross-cutting runtime contract. AI-ISA remains the executable instruction schema, but AIL is the canonical handoff shape between planner, policy, tools, memory, and renderer.

Policy OS evaluates structured requests for `instruction.validate`, `terminal.execute`, `tool.call`, `memory.write`, `context.compile`, `renderer.render`, `file.*`, and `git.operation`. Default policies live under `policies/`; the full concept docs are `docs/LoopOS_Fusion_Codex_Prompts.md` and `docs/LoopOS_Policy_OS.md`.
