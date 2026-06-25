"""CLI helpers for nodes."""

from __future__ import annotations

import json

from loopos.nodes import NodeRegistry


def nodes_command(action: str = "list", *, code: str | None = None, json_output: bool = True) -> int:
    registry = NodeRegistry()
    if action in {"list", "health"}:
        rows = [node.model_dump(mode="json") for node in registry.list()]
        payload: dict[str, object] = {"status": "ok", "nodes": rows}
    elif action == "pair":
        payload = {"status": "ok", "paired": bool(code)}
    else:
        payload = {"status": "error", "message": f"unknown nodes action: {action}"}
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload)
    return 0 if payload["status"] == "ok" else 2


__all__ = ["nodes_command"]
