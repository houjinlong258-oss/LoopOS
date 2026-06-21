# Testing LoopOS

LoopOS uses deterministic tests. The MVP must not call real LLM APIs or real network services.

## Test Layers

1. Unit tests: schema validation, safety classification, memory governance, retrieval, routing, and adapters.
2. Integration tests: state-machine loop, event log, state store, Data Guard, local index, registry,
   Gateway, worktree/review, and CLI smoke tests.
3. Golden trace tests: compare stable event types from deterministic runs.
4. Safety tests: blocked/high/medium/low command behavior.
5. CLI smoke tests: help, dry-run, missing state, empty stores.

## Commands

```bash
python -m pytest
python -m pytest -q -m "not slow"
python -m pytest -q -m "slow"
python -m pytest -m unit
python -m pytest -m integration
python -m pytest tests/acceptance_founding
python -m ruff check .
python -m mypy loopos tests
```

When `make` is available:

```bash
make test-all
make test-fast
make test-acceptance
make lint
make typecheck
make ci
```

`not slow` is the clean-environment feedback path. The `slow` marker is reserved for deterministic
but longer end-to-end paths: CLI subprocess suites, Founding acceptance contracts, SQLite demo
flows, mock webhook demo flows, the eval-runner smoke path, and the terminal timeout assertion.
These tests are still part of `python -m pytest`; they are only excluded from fast local checks.

## Fixtures

- `tests/fixtures/`: small reusable test inputs.
- `tests/golden/`: stable expected outputs for golden trace tests.

## Rules

- Mock LLM calls.
- Mock terminal execution unless testing `TerminalExecutor`.
- Avoid real network calls.
- Never connect to a real database; use workspace-local sample files for Data Guard tests.
- Never import or execute plugin code during registry tests.
- Keep event ordering deterministic in golden tests.
- Do not depend on OpenHands, LangGraph, Letta, Zep, or projectmem being installed.

The Founding acceptance suite proves the public safety and product contracts end to end with
temporary workspaces, local SQLite files, mock providers, and mock gateways. It must remain fully
offline and must not invoke destructive commands.
