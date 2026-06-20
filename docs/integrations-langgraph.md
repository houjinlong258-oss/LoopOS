# LangGraph Integration

LoopOS has a native state-machine loop first. LangGraph is optional.

## When to Use LoopEngine

Use `LoopEngine` for:

- MVP execution.
- Deterministic tests.
- Simple bounded loops.
- Environments without optional dependencies.

## When to Use LangGraph

Use LangGraph later for:

- long-running checkpointed workflows
- visualization of loop nodes and edges
- graph-level retries and branching
- external orchestration

## Planned Node Model

- `compile_context`
- `plan_instruction`
- `execute_instruction`
- `observe`
- `evaluate`
- `govern_memory`
- `extract_skill`
- `decide_next`

## Current Behavior

`langgraph_adapter.py` detects whether LangGraph can be imported. If not, `run_graph()` uses the native LoopEngine fallback so core tests remain independent.
