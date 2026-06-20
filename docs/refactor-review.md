# Refactor Review

## Summary

The MVP is intentionally small and keeps third-party source snapshots outside the core runtime. The current architecture is coherent for a Python-only LoopOS prototype:

- AI-ISA is typed and validated.
- The state-machine loop is bounded and deterministic.
- Terminal execution is permission-gated.
- Memory writes have governance metadata.
- MCP-like routing is replaceable.
- Third-party integrations are adapters, not core dependencies.

## Dependency Cycles

No obvious import cycle was found in the LoopOS package. The dependency direction is:

```text
core -> memory for optional stores in LoopEngine
execution -> core for Observation and safety
mcp -> execution and mcp types
integrations -> core/execution/memory
cli -> core/memory
```

This is acceptable for the MVP, but `LoopEngine` importing memory stores means the core package is not fully storage-agnostic. If this grows, move store wiring into a runtime factory module.

## Large Modules

- `loopos/cli/app.py` is the largest module because it contains Typer and argparse fallback paths. This is acceptable for MVP bootstrapping. Later, command implementations can move to `loopos/cli/commands.py`.
- `loopos/execution/permissions.py` centralizes policy. Keep it together until command parsing becomes platform-specific.

## Untested Core Paths

Covered:
- AI-ISA validation.
- Loop success and max-step failure.
- Terminal executor success, timeout, stderr, dangerous command blocking, cwd restriction.
- Memory governance, retrieval, repeated failure gate, skill suggestion.
- MCP router and default file tools.
- CLI smoke paths.
- Adapter fallback behavior.
- Golden event trace.
- Eval runner and metrics.

Remaining gaps:
- CLI `history`, `memory`, and `config` have direct function coverage through smoke paths but not rich table rendering assertions.
- `ContextCompiler` has no direct test yet.
- `OpenHandsAdapter.apply_patch()` is intentionally not implemented and only returns a structured unsupported result.

## Type Clarity

Public Pydantic models have explicit types. Dynamic Typer decorators require `disallow_untyped_decorators = false` in mypy config, while the rest of strict checks remain enabled.

## Security Risks

- `TerminalExecutor` uses `shell=True` for Windows built-in support. This is acceptable only because policy analysis runs first. Future hardening should add platform-specific tokenization and avoid shell mode where possible.
- Command risk analysis is conservative string matching, not a full parser.
- High-risk commands are always denied by the MVP policy even with auto-approve.

## AGENTS.md Alignment

Aligned:
- MVP is Python-only.
- No Web UI.
- Internal runtime uses structured models.
- Terminal execution goes through permission policy.
- Memory writes include governance fields.
- Third-party projects are optional adapters.

## Low-Risk Follow-Ups

1. Add a direct `ContextCompiler` unit test.
2. Add a CLI `config` smoke test.
3. Add a simple `benchmark` CLI command later, after benchmark UX is decided.
4. Split `loopos/cli/app.py` only when CLI behavior stabilizes.
