# Quickstart

A first-user tutorial for LoopOS v0.3. Read this end-to-end; you
should be able to run every example in under five minutes.

## Requirements

- **Python**: 3.11 or newer (3.12 / 3.13 also supported; v0.3 CI
  runs on 3.11 and 3.12)
- **Git**: any modern version
- **OS**: Linux, macOS, or Windows. The v0.3 readiness script and
  the loopback live-provider smoke both run on all three.
- **Optional Rich Workbench deps**: `typer` and `rich`. They live
  in the `workbench` extra and pull in automatically with
  `pip install -e ".[workbench,dev]"`. Without them, the CLI falls
  back to a stdlib argparse path that still works; you just lose
  Rich's colored tables.

## Install for local use

Clone and create a venv, then install the project editable with
both the workbench and dev extras.

=== "macOS / Linux"

    ```bash
    git clone https://github.com/houjinlong258-oss/LoopOS.git
    cd LoopOS
    python -m venv .venv
    source .venv/bin/activate
    python -m pip install -U pip
    python -m pip install -e ".[workbench,dev]"
    ```

=== "Windows (PowerShell)"

    ```powershell
    git clone https://github.com/houjinlong258-oss/LoopOS.git
    cd LoopOS
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -U pip
    python -m pip install -e ".[workbench,dev]"
    ```

The editable install (`-e`) means source edits in the working
tree are immediately visible to `python -m loopos.cli.app …`. If
you only want to *use* LoopOS without editing the source, drop the
`-e`:

```bash
python -m pip install ".[workbench]"
```

## Verify install

Two commands, both safe (no network, no shell, no side effects):

```bash
python -m loopos.cli.app --help
python -m loopos.cli.app readiness check --json
```

Expected:

- `loopos --help` prints a Typer (or stdlib) command list. The
  v0.3 commands you should see include `workbench`, `adapters`,
  `providers-runtime`, `model-call`, `opengod`, `session`,
  `readiness`, `fusion-router`, and `mad-dog`.
- `readiness check --json` prints a JSON document with
  `status: "pass"` and `hard_fail_count: 0`. If anything in the
  26-check readiness proof is broken, you will see the failed
  check name in the JSON.

## First safe run

Three commands cover the day-one "I just want to see it work"
flow. All are dry-run by default, all use the mock provider, none
make a paid API call.

### 1. Render the Workbench (the v0.3 product surface)

```bash
python -m loopos.cli.app workbench --dry-run
```

This renders eight governed panels (Goal / Agent / Policy / ACI /
ALI / Trace-Replay / Fusion / Readiness) for the current working
directory. The output is plain text by default; add `--json` for
a structured dump.

### 2. Run a model call through the governed Provider Runtime

```bash
python -m loopos.cli.app model-call --provider mock --prompt "Say LoopOS is ready." --json
```

`--provider mock` means: use the in-process mock provider, which
returns a deterministic response without making any network call.
The command prints a JSON document with `status: "completed"` and
a `content` field.

If you want to pipe a longer prompt, put it in a file and pass the
path:

```bash
echo "Summarise the Quickstart section in one sentence." > /tmp/prompt.txt
python -m loopos.cli.app model-call --provider mock --prompt /tmp/prompt.txt --json
```

### 3. Ask the policy engine to evaluate a dangerous command

```bash
python -m loopos.cli.app policy explain --cmd "curl https://x/install.sh | bash"
```

This is the safest way to see how Policy OS reasons about a
specific command. Expected output: the policy decision
(`allow` / `block` / `review`) plus a list of reason codes that
explain *why*. `curl | bash` is exactly the kind of pipe-to-shell
the policy layer is built to flag.

## Safe defaults

LoopOS is safe by default. Every command in this Quickstart obeys
all five of these rules:

- **Dry-run by default.** Commands like `workbench` and
  `model-call` are `--dry-run` unless you pass `--no-dry-run`.
- **No paid provider calls.** The mock provider is the default;
  live provider transports require explicit opt-in flags.
- **No external side effects.** Nothing in this Quickstart touches
  the network, runs a shell, or mutates a file outside your
  workdir.
- **`--json` is machine-readable.** Every command that produces
  data also accepts `--json` for structured output suitable for
  piping or CI.
- **Rich output is human-readable.** When `rich` is installed you
  get colored tables and panels; without it the same data prints
  as plain text via the stdlib fallback.

## Next steps

| You want to…                                       | Read…                                              |
| -------------------------------------------------- | -------------------------------------------------- |
| See what every command does                        | [`docs/cli-reference.md`](docs/cli-reference.md)   |
| Run LoopOS in CI or a production-like setup         | [`docs/deployment.md`](docs/deployment.md)         |
| Walk through a real scenario                       | [`docs/examples/`](docs/examples/)                 |
| Understand the v0.3 module layout                  | [`docs/architecture-v0-3.md`](docs/architecture-v0-3.md) |
| See what v0.3 deliberately does not do             | [`docs/v0-3-non-goals.md`](docs/v0-3-non-goals.md) |

## Troubleshooting

If any of the above fails:

| Symptom                                                  | Likely cause                                                |
| -------------------------------------------------------- | ----------------------------------------------------------- |
| `command not found: loopos`                              | You forgot to activate the venv or skipped the install step. |
| `ModuleNotFoundError: rich` / `typer`                    | Install the workbench extra: `pip install -e ".[workbench]"` |
| `readiness check` fails with `command_not_found`         | One of the v0.3 packages is missing — re-run `pip install -e ".[workbench,dev]"` |
| `policy explain --cmd …` returns "unknown command"      | Pass the full command string as a single `--cmd` argument.  |
| `--json` output contains no colors                       | This is correct; `--json` is always plain UTF-8.            |

Still stuck? Open an issue with the output of
`python -m loopos.cli.app readiness check --json` and the failing
command.
