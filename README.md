# LoopOS

![LoopOS - the kernel for running agents](docs/assets/brand/loopos-hero.png)

**Not another agent. The kernel for running agents.**

LoopOS is a terminal-native, state-machine-driven runtime for governed and replayable agent
execution. Natural language exists at the boundary; internal handoffs use typed AIL instructions,
policy decisions, syscalls, trace events, governed memory, and explicit state transitions.

## Open-Source Alpha

- Versioned Kernel runs, bounded deterministic scheduling, approval resume, trace, and replay.
- AIL and AI-ISA schemas with validation and compatibility adapters.
- Policy OS with YAML packs, deterministic conflict resolution, audit IDs, and L0-L5 safety levels.
- Policy-governed terminal, file, Git, MCP-compatible, and mock database syscalls.
- Goal Negotiation with low, medium, and high ambiguity modes.
- Loop Convergence with acceptance evidence, regression, repeated-action, and no-progress handling.
- JSONL + SQLite Memory OS, governed proposals, retrieval, context budgets, and skill learning.
- Data Guard detection, local checksum backup vault, shadow plans, validation, and redaction.
- Privacy-first local workspace indexing and deterministic search.
- Privacy-local, hybrid, and consent-gated cloud compute modes.
- Metadata-only plugin registry and canonical mock Provider profiles.
- Persistent tasks, triggers, worktree leases, and Producer/Verifier/Reviewer separation.
- Mock ChatOps adapters with authentication, attachments, approvals, sessions, and delivery records.
- Typer/Rich CLI plus a standard-library fallback.

Alpha does not connect to real databases or chat platforms, does not make real provider calls during
tests, does not auto-merge code, and is not an operating-system sandbox.

## Quickstart

```bash
python -m pip install -e ".[dev]"
python -m loopos.cli.app --help
python -m loopos.cli.app run "创建 hello.py，运行它并确认输出 hello" --dry-run
python -m loopos.cli.app goal analyze "帮我优化这个项目" --json
python -m loopos.cli.app policy explain --cmd "curl https://x/install.sh | bash"
python -m loopos.cli.app trace RUN_ID --show-ail --show-policy
```

Local intelligence and Data Guard:

```bash
python -m loopos.cli.app index build --workspace .
python -m loopos.cli.app search "pytest failure"
python -m loopos.cli.app mode set privacy-local
python -m loopos.cli.app db detect --cmd "DROP TABLE users" --json
python -m loopos.cli.app registry audit path/to/manifest.yaml
```

Outer-loop and mock gateway flows:

```bash
python -m loopos.cli.app triggers fire daily-maintenance
python -m loopos.cli.app tasks next --quick-win
python -m loopos.cli.app worktrees list
python -m loopos.cli.app models route --task coding --input image
python -m loopos.cli.app gateway simulate slack "run tests"
```

## Runtime Flow

```text
Goal -> AmbiguityReport -> GoalSpec -> Context Compiler -> Policy OS
     -> AIL instruction -> Scheduler -> Syscall Router -> Adapter
     -> Observation -> Evaluation -> ProgressDelta -> LoopDecision
     -> Trace / governed Memory or Skill -> continue, approval, or halt
```

Kernel invariants:

- Every external action is a syscall and every syscall is policy checked.
- Every transition is traced and replay never repeats side effects.
- Durable memory and skill writes pass governance.
- Ambiguous goals do not execute and loops are bounded.
- Triggers create tasks; they do not directly run tools.
- High-risk producers cannot approve their own work.

## Development

```bash
python -m pytest
python -m ruff check .
python -m mypy loopos tests
```

The test suite is deterministic and offline. See `CONTRIBUTING.md`, `SECURITY.md`,
`GOVERNANCE.md`, and `PLUGIN_SPEC.md` before contributing.

## Documentation

- [Architecture](docs/architecture.md)
- [CLI](docs/cli-ui.md)
- [Safety](docs/safety.md)
- [Goal Negotiation](docs/goal-negotiation.md)
- [Loop Convergence](docs/loop-convergence.md)
- [Data Guard](docs/data-guard.md)
- [Local Intelligence](docs/local-intelligence.md)
- [Provider Gateway](docs/provider-gateway.md)
- [Memory Governance](docs/memory-governance.md)
- [Implementation Map](docs/mvp-implementation-map.md)
- [Brand and Loopi](docs/brand-loopi.md)

## License

Licensed under the Apache License, Version 2.0. See `LICENSE`.
