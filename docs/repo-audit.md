# Repo Audit

## Directory Map

- `OpenHands-1.8.0/OpenHands-1.8.0`: OpenHands source snapshot with server, app server, sandbox, frontend, tests, Poetry/uv configuration, Docker assets, and documentation.
- `langgraph-1.2.6/langgraph-1.2.6`: LangGraph monorepo snapshot with Python libraries for graph runtime, checkpoints, SDK, CLI, examples, and docs.
- `letta-0.16.8/letta-0.16.8`: Letta Python source snapshot with agents, schemas, memory-oriented services, CLI, adapters, and server code.
- `zep-main/zep-main`: Zep source snapshot with memory-related integrations, examples, ontology assets, benchmarks, and MCP/plugin material.
- `projectmem-0.1.5/projectmem-0.1.5`: Project memory CLI/server package with models, storage, search, precheck, commands, and tests.
- `loopos`: previously contained only project documents. This MVP adds the actual Python package under the same directory.

## Detected Projects

| Project | Runtime | Main Entry Signals | Core Capabilities |
| --- | --- | --- | --- |
| OpenHands | Python, TypeScript, Docker | `pyproject.toml`, `openhands/`, `frontend/`, `docker-compose.yml` | hosted agent runtime, sandbox patterns, server-side events, workspace operations |
| LangGraph | Python, JavaScript examples | `libs/langgraph`, `libs/checkpoint*`, `libs/cli` | state graph, Pregel-style loop, checkpoints, node/edge execution |
| Letta | Python | `letta/agents`, `letta/schemas`, `letta/services` | agent state, working/archival memory concepts, tool calling |
| Zep | Python, TypeScript, docs/assets | `integrations/`, `benchmarks/`, `mcp/` | temporal and graph-like memory patterns, session/user scoped memory |
| projectmem | Python | `src/projectmem`, `tests` | event-sourced project memory, pre-action checks, compact context injection |

## Language/Runtime Summary

The root LoopOS project is now Python-only for the MVP. Third-party snapshots include Python, TypeScript, Docker, and benchmark assets, but they are treated as references or optional integration targets.

## Reusable Components

- Terminal/sandbox execution: borrow OpenHands' separation between runtime actions and observations, but keep LoopOS executor small and permission-gated.
- Agent loop: borrow event/action/observation vocabulary from OpenHands while keeping AI-ISA as the internal contract.
- Graph/state machine: borrow LangGraph's explicit node and edge model for optional backend work.
- Memory: borrow Letta's working versus archival memory, Zep's temporal/session memory, and projectmem's event-sourced pre-action judgement.
- MCP/tool protocol: borrow protocol-shaped tool specs and router boundaries; do not depend on a full MCP SDK in the MVP.
- Event/log system: use JSONL events first for debuggability and deterministic tests.

## Risk Areas

- Third-party snapshots are large and have their own dependency graphs. They should not be imported by default.
- OpenHands internals can change; use an adapter boundary rather than private APIs.
- LangGraph should be optional because the MVP loop is simpler and easier to test directly.
- Memory writes can pollute future context unless governance enforces confidence, provenance, dedupe, versioning, and status.
- Terminal execution is the highest risk area and must remain behind policy checks.

## Recommended MVP Path

1. Create LoopOS Python package and project config.
2. Implement AI-ISA schemas.
3. Implement deterministic state machine loop with mock policy/executor/evaluator.
4. Add event and state stores.
5. Add permission-gated terminal executor.
6. Add governed memory primitives.
7. Add skill extraction and context compilation.
8. Add MCP-like router.
9. Add CLI commands.
10. Add optional adapters and documentation.

## First 10 Implementation Tasks

1. Add `AGENTS.md`, `pyproject.toml`, and root README.
2. Add docs for repo audit, source extraction, architecture, safety, integrations, and memory design.
3. Add AI-ISA models and tests.
4. Add state and loop engine models and tests.
5. Add safety analyzer and terminal permission policy.
6. Add terminal executor tests with safe commands only.
7. Add memory event, state, belief, skill, and governance stores.
8. Add retrieval and pre-action gate.
9. Add MCP-like router and built-in mock tools.
10. Add CLI smoke tests and adapter fallbacks.
