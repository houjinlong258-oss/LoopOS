# LoopOS

LoopOS is a Python MVP for a terminal-native agent runtime. It is not a chatbot shell. The runtime converts goals into structured AI-ISA instructions, executes them through a state machine, gates terminal actions through a safety policy, records events, and writes long-term memory through governance.

## Current MVP

- Typed AI-ISA schema with validation and JSON round-tripping.
- Deterministic state-machine loop with mock planner, executor, evaluator, and event log.
- Permission-gated terminal executor.
- Memory OS primitives for events, state, beliefs, skills, governance, retrieval, and pre-action gates.
- MCP-like tool registry/router abstraction.
- CLI/FLI commands with Typer/Rich support and standard-library fallback.
- Optional adapters for OpenHands, LangGraph, Letta, Zep, and projectmem.

## Quickstart

```bash
python -m pip install -e ".[dev]"
python -m loopos.cli.app --help
python -m loopos.cli.app run "inspect this workspace" --dry-run
python -m loopos.cli.app run "demo task" --max-steps 3 --yes
```

Preferred development checks:

```bash
pytest
ruff check .
mypy .
```

If those tools are not installed, the test suite is also written to run with:

```bash
python -m unittest discover -s tests
```

## Architecture

```text
Goal
-> AI-ISA instruction
-> state machine loop
-> permission-gated tool execution
-> observation
-> evaluation
-> event log
-> governed memory
-> next instruction or final render
```

See `docs/architecture.md` and `docs/architecture-mvp.md` for details.

## Safety Model

Terminal commands are analyzed before execution. Blocked commands never run. High-risk commands require approval. The `--yes` flag only helps with low or medium risk commands; it does not bypass high or blocked actions.

See `docs/safety.md` for details.

## Documentation

- `docs/quickstart.md`
- `docs/architecture.md`
- `docs/ai-isa.md`
- `docs/memory.md`
- `docs/safety.md`
- `docs/testing.md`
- `docs/benchmarks.md`
- `docs/contributing.md`
- `docs/mvp-implementation-map.md`

## Third-Party Source Use

Local source snapshots of OpenHands, LangGraph, Letta, Zep, and projectmem may be present beside the project as architecture references. They are ignored by Git and are not copied into the core runtime. LoopOS extracts design patterns and exposes optional adapters where useful.

## License

No root license has been selected yet. Choose a license before public release.

## Roadmap

1. Harden the terminal executor across Windows, Linux, and macOS.
2. Add a real LLM instruction compiler behind the AI-ISA parser.
3. Expand memory governance and conflict resolution.
4. Add benchmark tasks and golden traces.
5. Deepen optional OpenHands and LangGraph integrations.
