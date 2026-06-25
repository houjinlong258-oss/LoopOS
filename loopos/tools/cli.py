"""CLI helpers for tools."""

from __future__ import annotations

import json

from loopos.tools.catalog import ToolCatalog
from loopos.tools.search import ToolCatalogSearch


def tools_catalog_command(
    action: str = "list",
    query: str | None = None,
    *,
    json_output: bool = True,
) -> int:
    if action == "search":
        search = ToolCatalogSearch()
        tools = search.search(query or "")
        payload = {
            "status": "ok",
            "tools": [tool.model_dump(mode="json") for tool in tools],
            "token_savings": search.prompt_surface_reduction(query or ""),
        }
    elif action == "list":
        payload = {
            "status": "ok",
            "tools": [tool.model_dump(mode="json") for tool in ToolCatalog().list()],
        }
    else:
        payload = {"status": "error", "message": f"unknown tools action: {action}"}
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload)
    return 0 if payload["status"] == "ok" else 2


__all__ = ["tools_catalog_command"]
