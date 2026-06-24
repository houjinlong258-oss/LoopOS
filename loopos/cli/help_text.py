"""v0.3 CLI help text — shared by Typer and argparse paths.

This module is the single source of truth for the v0.3 user-facing
command help strings. The Typer bindings in
:mod:`loopos.cli.typer_v0_3` and the argparse bindings in
:mod:`loopos.cli.fallback` both read from this table, so the
``loopos --help`` output is identical regardless of which CLI
backend is active.

The shape of each entry is:

``short``  — one-line description used by ``--help``'s command
             index (Typer ``help=`` and argparse ``help=``).
``long``   — multi-line description used by ``<command> --help``
             (argparse ``description=``).

No command behavior is encoded here. This is docstring-shaped
content only, and changing it never alters a runtime path.
"""

from __future__ import annotations

from typing import NamedTuple


class CommandHelp(NamedTuple):
    short: str
    long: str


COMMAND_HELP: dict[str, CommandHelp] = {
    "workbench": CommandHelp(
        short=(
            "Render the v0.3 Workbench (Goal / Agent / Policy / ACI / "
            "ALI / Trace-Replay / Fusion / Readiness panels)."
        ),
        long=(
            "Render the v0.3 product surface as eight governed panels.\n"
            "\n"
            "Safe by default:\n"
            "  - --dry-run is on unless you pass --no-dry-run\n"
            "  - uses the mock provider unless --allow-live-provider is set\n"
            "  - never makes a paid API call on its own\n"
            "  - secrets are redacted from rendered output\n"
            "\n"
            "Examples:\n"
            "  loopos workbench --dry-run\n"
            "  loopos workbench --json\n"
            "  loopos workbench --mad-dog --dry-run --json\n"
        ),
    ),
    "adapters": CommandHelp(
        short=(
            "List / inspect / test registered Agent Kernel Adapters."
        ),
        long=(
            "Inspect the Agent Kernel Adapter Layer.\n"
            "\n"
            "Subcommands:\n"
            "  list                    show all registered adapters (table or JSON)\n"
            "  inspect <adapter_id>    show one adapter's manifest (JSON)\n"
            "  test <adapter_id>       run a dry-rurn session and emit events\n"
            "\n"
            "Safe by default:\n"
            "  - no network calls\n"
            "  - no shell execution\n"
            "  - no provider budget spend\n"
            "\n"
            "Examples:\n"
            "  loopos adapters list\n"
            "  loopos adapters list --json\n"
            "  loopos adapters inspect mock\n"
            "  loopos adapters test mock --json\n"
        ),
    ),
    "providers-runtime": CommandHelp(
        short=(
            "List / test governed Provider Runtime transports "
            "(mock, OpenAI-compatible, Ollama)."
        ),
        long=(
            "Inspect the v0.3 governed Provider Runtime.\n"
            "\n"
            "Subcommands:\n"
            "  list                                show all registered runtimes\n"
            "  test <provider> [--model X]         dry-run a transport\n"
            "\n"
            "Safe by default:\n"
            "  - --dry-run is on unless you pass --no-dry-run\n"
            "  - the mock provider never touches the network\n"
            "  - live calls require explicit flags (see model-call)\n"
            "\n"
            "Examples:\n"
            "  loopos providers-runtime list\n"
            "  loopos providers-runtime list --json\n"
            "  loopos providers-runtime test mock --json\n"
        ),
    ),
    "model-call": CommandHelp(
        short=(
            "Run a governed model call through LoopOS Provider Runtime."
        ),
        long=(
            "Run a single governed model call.\n"
            "\n"
            "Safe by default:\n"
            "  - --dry-run unless live provider flags are supplied\n"
            "  - mock provider requires no API key\n"
            "  - live calls require explicit approval and budget\n"
            "  - secrets are redacted from persisted state\n"
            "\n"
            "Examples:\n"
            "  loopos model-call --provider mock --prompt 'hello' --json\n"
            "  loopos model-call --provider openai-compatible \\\n"
            "      --prompt 'hello' \\\n"
            "      --budget-usd 0.05 --allow-live-provider \\\n"
            "      --confirm-live-call --json\n"
        ),
    ),
    "opengod": CommandHelp(
        short=(
            "Run the OpenGod strategic planner (decisions, never exec)."
        ),
        long=(
            "OpenGod is a strategic planner. It emits decisions, "
            "verdicts, and evidence; it never executes anything.\n"
            "\n"
            "Safe by default:\n"
            "  - planning-only\n"
            "  - never spends budget automatically\n"
            "  - never bypasses Policy OS\n"
            "  - JSON decision is informational; route it through the\n"
            "    governed Kernel / ACI for actual execution\n"
            "\n"
            "Example:\n"
            "  loopos opengod g1 --goal-risk high --fusion-mode mad_dog --json\n"
        ),
    ),
    "session": CommandHelp(
        short=(
            "List, inspect, and replay Agent Bus sessions."
        ),
        long=(
            "Browse the v0.3 Agent Bus sessions stored under\n"
            "``--data-dir`` (default ``.loopos``).\n"
            "\n"
            "Subcommands:\n"
            "  list                       show recent sessions\n"
            "  status <session_id>        show one session's status\n"
            "  events <session_id>        show one session's event stream\n"
            "\n"
            "Read-only. No network calls. No shell.\n"
            "\n"
            "Examples:\n"
            "  loopos session list\n"
            "  loopos session status sess_abc123\n"
            "  loopos session events sess_abc123 --json\n"
        ),
    ),
    "readiness": CommandHelp(
        short=(
            "Run the v0.3 readiness proof (26/26 checks)."
        ),
        long=(
            "Run the v0.3 readiness script and emit the proof surface\n"
            "as a structured JSON document (or human summary).\n"
            "\n"
            "Use this to verify a fresh checkout or a release branch\n"
            "before tagging. Exit code is 0 on pass, non-zero on any\n"
            "hard failure.\n"
            "\n"
            "Examples:\n"
            "  loopos readiness check --json\n"
            "  python scripts/v0_3_readiness_check.py --json\n"
        ),
    ),
    "fusion-router": CommandHelp(
        short=(
            "Plan a multi-model escalation (Fusion Router)."
        ),
        long=(
            "Plan a multi-model escalation across the Fusion Router.\n"
            "\n"
            "Fusion increases intelligence density, not authority:\n"
            "  - planning-only by default\n"
            "  - does not bypass Policy OS\n"
            "  - does not auto-spend budget\n"
            "  - emits a plan / verdict; route through governed Kernel\n"
            "    to actually execute\n"
            "\n"
            "Subcommands: plan / explain / run / escalate / status / list / route.\n"
            "\n"
            "Examples:\n"
            "  loopos fusion-router plan task.json --json\n"
            "  loopos fusion-router escalate --run-id run_123 --reason repeated_failure\n"
            "  loopos fusion-router status <fusion_id> --json\n"
        ),
    ),
    "mad-dog": CommandHelp(
        short=(
            "Plan a high-density multi-model escalation (Mad Dog mode)."
        ),
        long=(
            "Mad Dog is a friendly alias for the Fusion Router's\n"
            "explicit user-force mode. It runs the same planning\n"
            "pipeline as ``fusion-router`` with overrides:\n"
            "\n"
            "  - mode       -> mad_dog\n"
            "  - trigger    -> user, reason=explicit_user_request\n"
            "  - severity   -> critical (override with --severity)\n"
            "\n"
            "Mad Dog increases intelligence density, not authority.\n"
            "  - It does not bypass Policy OS.\n"
            "  - It does not spend budget automatically.\n"
            "  - It emits a plan / verdict unless routed through\n"
            "    governed execution.\n"
            "\n"
            "Subcommands: plan / explain / escalate / status / list / route.\n"
            "\n"
            "Examples:\n"
            "  loopos mad-dog plan task.json --severity critical --json\n"
            "  loopos mad-dog escalate --run-id run_123 --reason explicit_user_request\n"
        ),
    ),
}


__all__ = ["COMMAND_HELP", "CommandHelp"]
