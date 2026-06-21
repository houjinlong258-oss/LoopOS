# Contributing to LoopOS

LoopOS accepts focused changes that preserve its state-driven, policy-governed runtime model.

## Development

1. Use Python 3.11 or newer and install `.[dev]`.
2. Create a focused branch and keep unrelated changes out of the patch.
3. Add deterministic tests; external providers, platforms, databases, and networks must be mocked.
4. Run `python -m pytest`, `python -m ruff check .`, and `python -m mypy loopos tests`.
5. Explain public contract, policy, migration, and security effects in the pull request.

Core changes require maintainer review. Plugins should follow `PLUGIN_SPEC.md`. Security reports
must follow `SECURITY.md` and must not be opened as public issues when they contain exploit details.

Contributions are licensed under Apache-2.0 as described in `LICENSE`.
