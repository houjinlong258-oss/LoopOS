# Architecture

LoopOS is a state-machine agent runtime. Natural language is allowed at the user boundary, but internal execution uses structured objects.

## Runtime Flow

```text
Goal
-> Planner / Policy
-> AI-ISA Instruction
-> LoopEngine
-> Permission / PreActionGate
-> Tool or Terminal Executor
-> Observation
-> Evaluator
-> LoopState update
-> EventLog append
-> Memory Governance
-> Terminate or continue
```

## Core Modules

- `loopos.core`: AI-ISA, state, policy, loop engine, safety, context compiler.
- `loopos.execution`: terminal executor and permission policy.
- `loopos.memory`: event log, state store, beliefs, skills, governance, retrieval, pre-action gate.
- `loopos.memory.repository`: JSONL + SQLite Memory OS facade.
- `loopos.llm`: mock and OpenAI-compatible providers used for governed memory proposals.
- `loopos.mcp`: MCP-like tool specs and router.
- `loopos.agents`: deterministic planner, critic, renderer.
- `loopos.integrations`: optional third-party adapter boundaries.
- `loopos.eval`: deterministic benchmark runner and metrics.
- `loopos.cli`: CLI/FLI entry point.

## Design Boundary

OpenHands, LangGraph, Letta, Zep, and projectmem are inspiration and optional integration targets. LoopOS owns its schemas and does not copy or require those projects for core tests.

## Memory-first Alpha

The Alpha memory layer keeps JSON/JSONL artifacts for audit and adds SQLite indexing for retrieval and proposal review. LLM output is restricted to `MemoryProposal` generation; governance and explicit accept/reject decisions control durable memory writes.

For deeper MVP details, see `docs/architecture-mvp.md`.
