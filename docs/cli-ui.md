# Terminal CLI

LoopOS exposes concise Rich terminal output and a strict JSON mode. Core commands are `run`, `status`, `trace`, `step replay`, `policy explain`, `tools list`, `memory`, `skills`, and `ail validate`.

`--dry-run` evaluates the complete kernel path without workspace side effects. `--yes` may satisfy medium-risk approval only. High-risk actions require an explicit interactive approval; blocked actions cannot be approved.

## Command Modularization

Phase 1 modularization has started without changing public command behavior:

- `loopos/cli/context.py` owns the shared data-path layout.
- `loopos/cli/commands/tasks.py`, `triggers.py`, `worktrees.py`, and `review.py` own outer-loop command logic.
- `loopos/cli/commands/models.py` owns provider and multi-model commands.
- `loopos/cli/commands/gateway.py` owns ChatOps commands.
- `loopos/cli/app.py` retains compatible imports plus Typer/argparse registration while remaining command groups are migrated.
- Modularization contracts verify that the app exports the same command callables and data paths.
