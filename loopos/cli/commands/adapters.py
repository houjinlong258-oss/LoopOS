"""v0.3 CLI: ``loopos adapters`` command.

Supports three sub-commands:

* ``list``     - table / JSON of all registered adapters
* ``inspect``  - JSON manifest for one adapter
* ``test``     - dry-run an adapter session and emit events
"""

from __future__ import annotations

import json
import sys
from typing import Any

from loopos.adapters import AdapterRegistry
from loopos.adapters.base import GoalSpec


def adapters_command(
    action: str = "list",
    value: str | None = None,
    *,
    json_output: bool = False,
) -> int:
    registry = AdapterRegistry()
    if action == "list":
        rows = [
            {
                "adapter_id": s.adapter_id,
                "display_name": s.display_name,
                "type": s.kind,
                "status": s.status,
                "live_tools": "guarded" if s.authority_live_tools else "no",
                "requires_aci": s.requires_aci,
                "requires_policy": s.requires_policy,
                "notes": s.notes,
            }
            for s in registry.list_adapters()
        ]
        if json_output:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            _print_adapters_table(rows)
        return 0
    if action == "inspect":
        if not value:
            return _emit_error(
                code="adapter_id_required",
                message="`loopos adapters inspect` requires an adapter id",
                json_output=json_output,
            )
        manifest = registry.inspect(value)
        if manifest is None:
            return _emit_error(
                code="adapter_not_found",
                message=f"Adapter {value!r} is not installed or not configured.",
                json_output=json_output,
            )
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    if action == "test":
        if not value:
            return _emit_error(
                code="adapter_id_required",
                message="`loopos adapters test` requires an adapter id",
                json_output=json_output,
            )
        adapter = registry.get_adapter(value)
        if adapter is None:
            return _emit_error(
                code="adapter_not_found",
                message=f"Adapter {value!r} is not installed or not configured.",
                json_output=json_output,
            )
        goal = GoalSpec(goal_id="goal_test", title="adapters test", intent="verify")
        session = adapter.start_session(goal)
        events = list(adapter.submit_goal(session.session_id, goal))
        if json_output:
            print(
                json.dumps(
                    {
                        "adapter_id": adapter.adapter_id,
                        "session_id": session.session_id,
                        "events": [e.model_dump(mode="json") for e in events],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"adapter_id: {adapter.adapter_id}")
            print(f"session_id: {session.session_id}")
            for e in events:
                print(f"  - {e.kind} payload_keys={list((e.payload or {}).keys())}")
        return 0
    return _emit_error(
        code="unknown_action",
        message=f"Unknown adapters action: {action!r}",
        json_output=json_output,
    )


def _print_adapters_table(rows: list[dict[str, Any]]) -> None:
    try:
        from loopos.cli_ui import get_console, render_adapters_table
        con = get_console()
        if con is not None:
            con.print(render_adapters_table(rows))
            return
    except Exception:
        pass
    headers = ("Adapter", "Type", "Status", "Live Tools", "Notes")
    widths = [max(len(str(r.get(k, ""))) for r in rows + [{k: k}]) for k in headers]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(line)
    for r in rows:
        print(
            "  ".join(
                str(r.get(k, "")).ljust(w) for k, w in zip(headers, widths)
            )
        )


def _emit_error(*, code: str, message: str, json_output: bool) -> int:
    if json_output:
        print(
            json.dumps(
                {
                    "schema_version": "0.3",
                    "status": "error",
                    "error_code": code,
                    "message": message,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        sys.stderr.write(f"ERROR {code}\n{message}\n")
    return 1


__all__ = ["adapters_command"]
