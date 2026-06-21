# Terminal CLI

The CLI is the Alpha product surface. Typer/Rich provides interactive output and a standard-library
fallback preserves bootstrapping. `--json` output contains only machine-readable JSON.

Core groups: `run`, `resume`, `status`, `history`, `trace`, `step`, `tools`, `goal`, `policy`, `ail`,
`memory`, `profile`, `skills`, `db`, `index`, `search`, `files`, `mode`, `registry`, `tasks`,
`triggers`, `worktrees`, `review`, `providers`, `models`, and `gateway`.

`loopos/cli/app.py` owns Typer registration and REPL startup. Command behavior is under
`loopos/cli/commands/`, fallback parsing is isolated in `loopos/cli/fallback.py`, and reusable
Rich/JSON rendering is under `loopos/cli/renderers/`.

`run --dry-run` executes planning, policy, and trace without invoking side-effecting adapters.
`--yes` can satisfy medium-risk approval but cannot bypass L3 interactive, L4 user-only, or L5
blocked decisions. Medium-ambiguity goals require `--confirm-goal`; high-ambiguity goals require a
selected `--goal-option`.
