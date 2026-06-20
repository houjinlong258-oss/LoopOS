# Contributing

## Development Setup

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```

Use the equivalent activation command for macOS or Linux.

## Checks

```bash
python -m pytest
python -m ruff check .
python -m mypy loopos tests
```

Or:

```bash
make ci
```

## Engineering Rules

- Keep MVP changes Python-only unless explicitly scoped.
- Do not add Web UI code to the MVP.
- Do not call real LLM APIs in tests.
- Do not call real network services in tests.
- Route terminal execution through `PermissionPolicy`.
- Route persistent memory writes through governance.
- Keep third-party integrations optional.

## Pull Requests

PRs should include:

- summary of behavior changed
- tests run
- safety impact
- memory and AI-ISA impact
- follow-up work

## License

No root `LICENSE` file is currently present. The project owner should choose a license before public release.
