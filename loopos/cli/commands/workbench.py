"""v0.3 CLI: ``loopos workbench`` command.

The Workbench is the v0.3 product surface. It renders the eight
required panels (Goal / Agent / Policy / ACI / ALI / Trace-Replay /
Fusion / Readiness) and supports:

* ``--dry-run`` to guarantee no side effects
* ``--json`` to emit a machine-readable dump
* ``--watch`` to periodically refresh (one refresh only in tests)
* ``--adapter NAME`` to select an adapter
* ``--model NAME`` to select a model alias
* ``--budget USD`` to set a budget
* ``--mad-dog`` to escalate to mad-dog mode (still planning-only)
* ``--allow-live-provider`` to permit (but not require) a live
  provider call

The command is **deterministic**: same flags + same goal file ->
same output. No network calls, no shell.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loopos.product import (
    Workbench,
    build_panels_from_context,
    render_json,
    render_plain,
    render_status,
)


def workbench_command(
    goal_path: str | None = None,
    *,
    adapter: str = "mock",
    model: str = "mock-model",
    provider: str = "mock",
    mode: str = "single",
    budget_usd: float = 0.0,
    mad_dog: bool = False,
    allow_live_provider: bool = False,
    dry_run: bool = True,
    watch: bool = False,
    json_output: bool = False,
    project: str = "",
) -> int:
    """The ``loopos workbench`` entry point."""
    if mad_dog:
        mode = "mad_dog"
    goal: dict[str, Any] = {}
    if goal_path:
        path = Path(goal_path)
        if not path.exists():
            return _emit_error(
                code="goal_file_not_found",
                message=f"Goal file not found: {goal_path}",
                hints=["Pass a valid goal file path", "Or omit the argument for a demo goal"],
                json_output=json_output,
            )
        text = path.read_text(encoding="utf-8", errors="replace")
        # Trivial goal parser: a goal.md may have a title and an intent
        # line; we extract them as best-effort.
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                goal["title"] = stripped[2:].strip()
            elif stripped.lower().startswith("intent:"):
                goal["intent"] = stripped.split(":", 1)[1].strip()
            elif stripped.lower().startswith("acceptance:"):
                goal["acceptance"] = stripped.split(":", 1)[1].strip()
            elif stripped.lower().startswith("risk:"):
                goal["risk"] = stripped.split(":", 1)[1].strip()

    wb = Workbench(project=project or str(Path.cwd()))
    context = wb.build_context(
        goal=goal,
        adapter_id=adapter,
        model_id=model,
        provider_id=provider,
        mode=mode,
        budget_max_usd=budget_usd,
        allow_live_provider=allow_live_provider,
        dry_run=dry_run,
    )
    panels = build_panels_from_context(context)
    if json_output:
        payload = {
            "schema_version": "0.3",
            "status": "ok",
            "goal_id": context.goal.get("goal_id", "goal_???"),
            "session_id": context.ali.get("session_id", "ali_???"),
            "adapter_id": adapter,
            "mode": mode,
            "live_provider_calls": bool(allow_live_provider),
            "panels": render_json(panels),
            "status_line": render_status(panels),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    try:
        from loopos.cli_ui import get_console, render_panels_rich
        con = get_console()
        if con is not None:
            con.print(render_panels_rich(panels))
        else:
            print(render_plain(panels))
    except Exception:
        print(render_plain(panels))
    if watch:
        print()
        print(f"--- {render_status(panels)} ---")
    return 0


def _emit_error(
    *,
    code: str,
    message: str,
    hints: list[str],
    json_output: bool,
) -> int:
    if json_output:
        print(
            json.dumps(
                {
                    "schema_version": "0.3",
                    "status": "error",
                    "error_code": code,
                    "message": message,
                    "hints": hints,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        sys.stderr.write(f"ERROR {code}\n{message}\n\nHints:\n")
        for hint in hints:
            sys.stderr.write(f"  - {hint}\n")
    return 1


__all__ = ["workbench_command"]
