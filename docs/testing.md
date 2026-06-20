# Testing LoopOS

LoopOS uses deterministic tests. The MVP must not call real LLM APIs or real network services.

## Test Layers

1. Unit tests: schema validation, safety classification, memory governance, retrieval, routing, and adapters.
2. Integration tests: state-machine loop, event log, state store, CLI smoke tests.
3. Golden trace tests: compare stable event types from deterministic runs.
4. Safety tests: blocked/high/medium/low command behavior.
5. CLI smoke tests: help, dry-run, missing state, empty stores.

## Commands

```bash
python -m pytest
python -m ruff check .
python -m mypy loopos tests
```

When `make` is available:

```bash
make test
make lint
make typecheck
make ci
```

## Fixtures

- `tests/fixtures/`: small reusable test inputs.
- `tests/golden/`: stable expected outputs for golden trace tests.

## Rules

- Mock LLM calls.
- Mock terminal execution unless testing `TerminalExecutor`.
- Avoid real network calls.
- Keep event ordering deterministic in golden tests.
- Do not depend on OpenHands, LangGraph, Letta, Zep, or projectmem being installed.
