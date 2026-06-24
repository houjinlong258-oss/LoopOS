# CLI Reference

A human-oriented reference for the v0.3 LoopOS command line. This
is not an auto-generated API dump; every entry explains the *why*
of a command, the safety posture, and the minimum you need to
know to use it.

The full top-level help is always one command away:

```bash
python -m loopos.cli.app --help
```

and the per-command help (with examples) is:

```bash
python -m loopos.cli.app <command> --help
```

## Safety legend

Each command is tagged with one or more of:

- **dry-run** — defaults to dry-run; no side effects unless you
  pass `--no-dry-run` (Typer) or `--dry-run` is off (argparse).
- **mock** — uses the in-process mock provider; never touches the
  network.
- **planning-only** — emits plans or decisions; never executes
  anything. Safe to call.
- **live-gated** — needs explicit opt-in flags
  (`--allow-live-provider`, `--budget-usd`, `--confirm` etc.) to
  call a paid provider.
- **read-only** — never mutates state.
- **CI-friendly** — exits non-zero on any failure and emits
  machine-readable output with `--json`.

## Core

### `loopos --help`

Print the top-level command list.

- **Purpose:** discover the v0.3 command surface.
- **Safe by default?** yes (no side effects).
- **Network?** no.
- **Budget?** no.
- **Example:** `python -m loopos.cli.app --help`

### `loopos workbench [GOAL_PATH]`

Render the v0.3 product surface as eight governed panels (Goal /
Agent / Policy / ACI / ALI / Trace-Replay / Fusion / Readiness).

- **When to use:** when you want a one-glance picture of what the
  runtime would do for a goal.
- **Safe by default?** yes — dry-run, mock provider, no shell.
- **Network?** no (with mock).
- **Budget?** no (with mock).
- **Example:** `python -m loopos.cli.app workbench --dry-run --json`

See [`docs/examples/workbench-tour.md`](examples/workbench-tour.md)
for a full walkthrough.

### `loopos readiness check`

Run the v0.3 readiness proof and emit the result as JSON.

- **When to use:** before tagging a release; in CI; after pulling
  a fresh checkout.
- **Safe by default?** yes — read-only, deterministic.
- **Network?** no.
- **Budget?** no.
- **Example:** `python -m loopos.cli.app readiness check --json`

## Agent Runtime

### `loopos adapters list`

List all registered Agent Kernel Adapters (mock / hermes /
scream-code / cleanroom …).

- **Safe by default?** yes.
- **Network?** no.
- **Budget?** no.
- **Example:** `python -m loopos.cli.app adapters list --json`

### `loopos adapters inspect <adapter_id>`

Show one adapter's manifest (authority claims, capabilities,
requirements).

- **Safe by default?** yes.
- **Network?** no.
- **Budget?** no.
- **Example:** `python -m loopos.cli.app adapters inspect mock`

### `loopos adapters test <adapter_id>`

Dry-run a session through one adapter and emit the events it
would produce. No shell, no file writes, no network.

- **Safe by default?** yes.
- **Network?** no.
- **Budget?** no.
- **Example:** `python -m loopos.cli.app adapters test mock --json`

### `loopos session list`

List recent Agent Bus sessions from the local data dir.

- **Safe by default?** yes — read-only.
- **Network?** no.
- **Budget?** no.

### `loopos session status <session_id>`

Show one session's status (state, last step, halted reason, etc.).

- **Safe by default?** yes.
- **Network?** no.
- **Budget?** no.

### `loopos session events <session_id>`

Show one session's event stream as JSON or as a table.

- **Safe by default?** yes.
- **Network?** no.
- **Budget?** no.

## Provider Runtime

### `loopos providers-runtime list`

List all registered Provider Runtime transports (mock,
openai-compatible, ollama).

- **Safe by default?** yes.
- **Network?** no.
- **Budget?** no.
- **Example:** `python -m loopos.cli.app providers-runtime list --json`

### `loopos providers-runtime test <provider> [--model X]`

Dry-run one transport and emit a fake response.

- **Safe by default?** yes — `--dry-run` is on.
- **Network?** no (mock) / potentially yes (openai-compatible) —
  but only with explicit live flags.
- **Budget?** no.

### `loopos model-call --provider X --prompt Y`

Run a single governed model call.

- **Safe by default?** yes — mock provider, dry-run.
- **Network?** no (mock) / yes (openai-compatible with
  `--allow-live-provider --confirm`).
- **Budget?** only when going live; the shared `BudgetLedger`
  blocks overspend.
- **Examples:**

  ```bash
  # Safe dry-run
  loopos model-call --provider mock --prompt "hello" --json

  # Live call (requires explicit flags)
  loopos model-call --provider openai-compatible \
      --prompt "hello" \
      --budget-usd 0.05 \
      --allow-live-provider \
      --confirm-live-call \
      --json
  ```

See [`docs/examples/mock-model-call.md`](examples/mock-model-call.md)
for a full walkthrough.

## Planning and Routing

### `loopos opengod [<goal_id>]`

Run the OpenGod strategic planner. Emits a JSON decision,
verdict, and the evidence it used.

- **Safe by default?** yes — planning-only.
- **Network?** no.
- **Budget?** no (does not auto-spend).
- **Authority:** none. The decision is informational; route it
  through the governed Kernel / ACI for actual execution.
- **Example:** `python -m loopos.cli.app opengod g1 --goal-risk high --json`

See [`docs/examples/fusion-mad-dog-planning.md`](examples/fusion-mad-dog-planning.md)
for context.

### `loopos fusion-router <action>`

Plan a multi-model escalation through the Fusion Router.

- **Safe by default?** yes — planning-only.
- **Network?** no.
- **Budget?** no (does not auto-spend).
- **Authority:** none. Increases *intelligence density*, not
  *authority*. The plan / verdict is informational; only the
  governed Kernel / ACI / Syscall Router can execute it.
- **Subcommands:** `plan`, `explain`, `run`, `escalate`, `status`,
  `list`, `route`.
- **Example:** `python -m loopos.cli.app fusion-router plan task.json --json`

### `loopos mad-dog <action>`

A friendly alias for `fusion-router` in the user-force mode
(`mad_dog` mode, severity `critical`, reason
`explicit_user_request`).

- **Safe by default?** yes — planning-only.
- **Network?** no.
- **Budget?** no (does not auto-spend).
- **Authority:** none. The plan / verdict is informational.
- **Subcommands:** same as `fusion-router`.
- **Example:** `python -m loopos.cli.app mad-dog plan task.json --severity critical --json`

## Output modes

| Flag        | Effect                                                      |
| ----------- | ----------------------------------------------------------- |
| `--json`    | Emit a machine-readable JSON document instead of a table.   |
| `--human`   | Force a human-readable table even when `--json` is default. |
| `--no-color`| Strip Rich colors (also: disable colors via `NO_COLOR=1`).  |
| `--quiet`   | Suppress non-essential output (provider banners, etc.).     |

In CI / non-TTY environments, the CLI auto-disables colors. JSON
output is always plain UTF-8 with no embedded Rich markup.
