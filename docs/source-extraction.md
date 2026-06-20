# Source Extraction for LoopOS

## OpenHands

### What to Reuse

- The action/observation/event separation as a vocabulary.
- The idea that workspace operations and terminal execution belong behind a runtime boundary.
- Sandbox and workspace lifecycle concepts.
- Clear distinction between app/server orchestration and execution backends.

### What Not to Reuse

- Do not copy the full runtime or server stack into LoopOS.
- Do not depend on private OpenHands modules for the MVP.
- Do not bring in the frontend, Docker stack, or hosted server assumptions.

### Integration Strategy

Expose `OpenHandsAdapter` with a minimal command/file interface. It should report availability, degrade gracefully when OpenHands is unavailable, and return LoopOS `Observation` objects.

## LangGraph

### What to Reuse

- Explicit graph nodes for planning, execution, observation, evaluation, memory governance, and routing.
- Checkpoint concepts for long-running stateful agents.
- Deterministic node/edge transitions for debuggability.

### What Not to Reuse

- Do not make LangGraph mandatory for the MVP.
- Do not replace the small LoopEngine until the core AI-ISA lifecycle is stable.

### Integration Strategy

Expose `create_loop_graph()` and `run_graph()` in an optional adapter. If LangGraph is not installed, fallback to the native LoopEngine or skip graph-specific tests.

## Letta

### What to Reuse

- Working memory versus archival memory.
- Agent state as structured data, not prompt text.
- Memory blocks with provenance and confidence.

### What Not to Reuse

- Do not import Letta services directly in the MVP.
- Do not adopt its full server or database model.

### Integration Strategy

Represent LoopOS memory as typed `MemoryItem` and `Skill` objects. Keep stores local and deterministic.

## Zep

### What to Reuse

- Temporal ranking of memory.
- Session/user scoped memory.
- Graph-like relationships as future metadata.

### What Not to Reuse

- Do not require an external Zep service.
- Do not add graph databases for the MVP.

### Integration Strategy

Implement recency-aware retrieval with tags and confidence now. Leave relationship graphs as a later extension.

## projectmem

### What to Reuse

- Event-sourced project memory.
- Pre-action judgement before repeating failed work.
- Compact context injection instead of prompt stuffing.

### What Not to Reuse

- Do not copy CLI command implementations.
- Do not tie LoopOS to a single editor or hook system.

### Integration Strategy

Add JSONL event logs, a `PreActionGate`, and a `ContextCompiler` that emits compact structured context.

## Unified Design Recommendation

LoopOS should own its internal contracts:
- AI-ISA for instructions.
- `LoopState` for execution state.
- `Observation` and `Evaluation` for feedback.
- `MemoryItem` and `Skill` for memory.
- `ToolSpec`, `ToolCall`, and `ToolResult` for tool boundaries.

Adapters may translate to and from third-party systems, but the core runtime should never depend on their private implementation details.

## Hermes Agent

### What to Reuse

- Persist successful and failed trajectories separately so skill extraction can require proven completion.
- Compress only bounded middle history while preserving initial intent and final actions.
- Treat skill discovery as a cached registry with deterministic duplicate handling and explicit reload.
- Bind edit approval to one run/session and keep sensitive paths outside auto-approval.

### What Not to Reuse

- Do not import the Hermes agent loop, gateway, provider matrix, or terminal backends.
- Do not store conversational scratchpads or model chain-of-thought in LoopOS traces.
- Do not use Hermes skill text as LoopOS internal protocol; LoopOS skills remain structured AIL steps.

### Integration Strategy

Apply these patterns inside LoopOS-owned TraceStore, SkillProposal, Context Compiler, and approval signals. Keep the Hermes source snapshot ignored and reference-only.

## Shortest Path to MVP

Build the native Python loop first, with mock LLM/planner behavior. Add terminal execution only after safety policy exists. Add memory governance before any persistent memory writes. Add optional integrations last.

## Components to Build Ourselves

- AI-ISA schema and parser.
- State machine loop.
- Permission policy and terminal executor.
- Event/state stores.
- Memory governance, retrieval, and pre-action gate.
- MCP-like router.
- CLI.
