"""Outer-loop trigger CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopos.cli.context import data_paths
from loopos.tasks import TaskStore
from loopos.triggers import TriggerKernel


def triggers_command(
    action: str = "list",
    trigger_id: str | None = None,
    *,
    data_dir: str | Path = ".loopos",
) -> int:
    kernel = TriggerKernel(TaskStore(data_paths(data_dir)["tasks"]))
    if action == "list":
        print(
            json.dumps(
                [item.model_dump(mode="json") for item in kernel.list()],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if action == "fire":
        if not trigger_id:
            print("triggers fire requires TRIGGER_ID.", file=sys.stderr)
            return 1
        try:
            task = kernel.fire(trigger_id)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(task.model_dump_json(indent=2))
        return 0
    print(f"Unknown triggers action: {action}", file=sys.stderr)
    return 1
