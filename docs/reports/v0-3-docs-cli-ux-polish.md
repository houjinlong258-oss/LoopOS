# v0.3.0 Docs + CLI UX Release Polish

This report covers the v0.3.0 public-facing documentation and CLI
help hardening pass. It is a docs-only change; no runtime code
path was modified and no new feature was added.

## Scope and non-scope

**In scope:**

- README.md top section rewrite.
- 4 new docs: `docs/quickstart.md`, `docs/cli-reference.md`,
  `docs/deployment.md`, plus 5 scenario walkthroughs in
  `docs/examples/`.
- Centralised CLI help text in `loopos/cli/help_text.py`,
  wired into the Typer bindings (`loopos/cli/typer_v0_3.py`,
  `loopos/cli/app.py`) and the argparse fallback
  (`loopos/cli/fallback.py`).
- This report (`docs/reports/v0-3-docs-cli-ux-polish.md`).

**Out of scope (deliberately not changed):**

- Runtime behaviour: no command function in `loopos/cli/commands/`
  was modified; no argument was added or removed; no flag was
  renamed.
- Existing advanced architecture docs under `docs/` — they are
  the deep reference and stay intact.
- The v0.1.0 / v0.2.0 tags, `dist/LoopOS-v0.2.0-source.zip`, the
  freeze notice, and `scripts/baselines/v0_1_0_loopos.txt`.
- CI / pre-commit / gitleaks config (no behaviour change there).

## README changes

The top section now leads with user value, then a 30-second
mental model, then the canonical sections. Concretely:

- Replaced the old "Why LoopOS" lead with a `What is LoopOS?`
  section that explains the runtime in 5–7 plain sentences.
- Added a `30-second mental model` table (You have / LoopOS adds).
- Added a `Why use LoopOS?` problem / solution table.
- Promoted the v0.3 highlights into `What v0.3 includes` with a
  clear separation from `What v0.3 does NOT include` (linked to
  `docs/v0-3-non-goals.md`).
- Added a 30-second install / first-run block at the top, with a
  pointer to `docs/quickstart.md` for the full version.
- Added a `Where to read next` table.
- Preserved the freeze notice in a clearly-labelled aside so
  v0.1.0 / v0.2.0 release evidence stays untouched.

## Docs added

| File                                                | Purpose                                                       |
| --------------------------------------------------- | ------------------------------------------------------------- |
| `docs/quickstart.md`                                | First-user tutorial: install, verify, three safe first runs. |
| `docs/cli-reference.md`                             | Human-oriented reference for the v0.3 command surface.        |
| `docs/deployment.md`                                | Install paths, provider config, readiness commands, troubleshooting. |
| `docs/examples/first-dry-run.md`                    | 60-second walkthrough of the safe first run.                  |
| `docs/examples/mock-model-call.md`                  | Walkthrough of the governed Provider Runtime (mock).          |
| `docs/examples/policy-block.md`                     | Walkthrough of `policy explain --cmd "curl …"`.               |
| `docs/examples/workbench-tour.md`                   | Walkthrough of the eight Workbench panels.                    |
| `docs/examples/fusion-mad-dog-planning.md`          | Walkthrough of the planning-only Fusion Router + mad-dog.     |

The quickstart covers: requirements, install (macOS / Linux /
Windows), verify install, three first safe runs (workbench dry-run,
mock model-call, policy explain), safe defaults table, next-steps
pointer, and a troubleshooting table. Everything in the
quickstart is dry-run, mock, or read-only.

## Commands whose help was improved

The following nine v0.3 commands now ship with:

- A `short` description (one line) used by `loopos --help`.
- A `long` description (multi-line) used by `<command> --help`,
  including "Safe by default", "Network?", "Budget?", and one or
  more example invocations.

| Command                | Path to definition            | Notes                                                       |
| ---------------------- | ----------------------------- | ----------------------------------------------------------- |
| `workbench`            | `loopos/cli/typer_v0_3.py`    | Highlights eight panels, dry-run by default.                |
| `adapters`             | `loopos/cli/typer_v0_3.py`    | Three subcommands, no network / shell.                      |
| `providers-runtime`    | `loopos/cli/typer_v0_3.py`    | Lists mock / openai-compatible / ollama.                    |
| `model-call`           | `loopos/cli/typer_v0_3.py`    | Mock vs live flags spelled out.                             |
| `opengod`              | `loopos/cli/typer_v0_3.py`    | "Planning-only. Never spends budget."                       |
| `session`              | `loopos/cli/typer_v0_3.py`    | Read-only.                                                  |
| `readiness`            | `loopos/cli/typer_v0_3.py`    | 26/26 proof.                                                |
| `fusion-router`        | `loopos/cli/app.py`           | "Intelligence density, not authority."                      |
| `mad-dog`              | `loopos/cli/app.py`           | Same safety stance as fusion-router.                        |

The fallback argparse path (`loopos/cli/fallback.py`) reads from
the same `loopos.cli.help_text.COMMAND_HELP` table, so the
`loopos --help` output is identical regardless of which CLI
backend is active.

## Install / deployment / config coverage

`docs/quickstart.md` + `docs/deployment.md` cover:

- **Local dev install** (editable, `.[dev,workbench]`).
- **Local user install** (non-editable, `loopos[workbench]`).
- **CI install** (editable + dev, plus the eight validation
  commands that `ci.yml` runs).
- **Provider configuration:** mock (no key), openai-compatible
  (`OPENAI_API_KEY`, `OPENAI_BASE_URL`), ollama (`OLLAMA_HOST`).
  No real keys are hard-coded anywhere.
- **Safe live provider smoke** via the loopback HTTP server
  (`scripts/v0_3_live_provider_smoke_http.py`); runs without
  touching a paid external provider.
- **Readiness commands** (`v0_2_readiness_check.py`,
  `v0_3_readiness_check.py`, `anti_bloat_check.py`).
- **Update / upgrade** (`git pull` + `pip install -e .[dev,workbench]`).
- **Uninstall / cleanup** (preserve `v0_1_0_loopos.txt` and the
  v0.2.0 source archive).
- **Troubleshooting** (venv activation, missing rich/typer,
  OPENAI_API_KEY, live provider flags, JSON cleanliness, slow
  tests, Windows paths).

## Validation

All eight gates required by the per-task instruction pass on this
`main` HEAD:

| Gate                                                       | Result                                                                |
| ---------------------------------------------------------- | --------------------------------------------------------------------- |
| `python -m pytest -m "not slow" -q`                        | 1019 passed, 9 skipped                                                |
| `python -m pytest -m "slow" -q`                            | 46 passed                                                             |
| `python -m ruff check .`                                   | All checks passed                                                     |
| `python -m mypy loopos tests`                              | 401 source files, 0 issues                                            |
| `python scripts/v0_2_readiness_check.py --json`            | status=pass, hard_fail_count=0                                        |
| `python scripts/v0_3_readiness_check.py --json`            | status=pass, hard_fail_count=0                                        |
| `python scripts/anti_bloat_check.py --json`                | hard_fail_count=0                                                     |
| `python rc_audit_cli_smoke.py`                             | ALL CLI SURFACES OK                                                   |

The two `--help` snapshot tests in
`tests/test_typer_v0_3_extraction.py` still pass:

- `test_cli_help_lists_all_v0_3_commands` — confirms the Typer
  `loopos --help` output still lists all seven v0.3 commands
  by name.
- `test_argparse_fallback_also_lists_v0_3_commands` — confirms
  the argparse `loopos --help` output still lists them.

These tests assert command *names* and `LoopOS` in the help
output, not specific help text strings, so the richer help
strings do not change the test contract.

## Maintainability reasoning

The CLI help text is centralised in `loopos/cli/help_text.py`
and exposed as a `dict[str, CommandHelp]` with a `short` and
`long` field. The Typer and argparse paths both import this
table, so:

- There is no duplicated help string in the codebase; updating
  one entry updates both `--help` paths.
- The help strings are pure data, not code; they have no side
  effects and cannot be triggered by accident.
- The names of the keys (`workbench`, `adapters`, etc.) are
  the same as the CLI command names, which makes the diff
  easy to audit.

No `loopos/cli/commands/*.py` was modified, so the help text
change cannot break any command behaviour. The fallback
`sub.add_parser(...)` calls got a `description=` and
`formatter_class=argparse.RawDescriptionHelpFormatter` so the
multi-line strings render as plain text rather than being
re-wrapped by argparse.

## Remaining doc gaps (deferred to v0.4)

The following items are *not* blocking v0.3 and are explicitly
deferred:

1. **A web-hosted docs site** (MkDocs / Sphinx). The current
   `docs/` is a flat directory; v0.4 should pick a build tool
   and generate a static site.
2. **Translated quickstart** (zh-CN, ja). The `docs/zh/` tree
   already exists for some pages; full parity is a v0.4 task.
3. **A `docs/migration/from-v0.2.md` page** that explains what
   v0.2 users need to change. This is mostly "use the v0.3
   Workbench instead of the v0.2 panel commands", but a
   dedicated page is the right place for it.
4. **In-CLI `loopos tutorial`** — an interactive REPL walkthrough
   that runs the safe-first-runs directly inside the CLI. This
   is a v0.4 feature, not a docs change.
5. **Top-level brand refresh** — the `docs/assets/brand/` tree
   exists; a coordinated visual refresh is out of scope for
   this docs-only pass.
