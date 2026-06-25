"""Token-aware tool catalog search."""

from __future__ import annotations

from loopos.tools.catalog import ToolCatalog
from loopos.tools.tool import Tool


class ToolCatalogSearch:
    """Return only tools relevant to a role/goal query."""

    def __init__(self, catalog: ToolCatalog | None = None) -> None:
        self.catalog = catalog or ToolCatalog()

    def search(self, query: str, *, limit: int = 5) -> list[Tool]:
        words = {w.lower() for w in query.replace(".", " ").replace("_", " ").split() if w}
        scored: list[tuple[int, Tool]] = []
        for tool in self.catalog.list():
            haystack = " ".join(
                [tool.tool_id, tool.name, tool.description, " ".join(tool.capabilities)]
            ).lower()
            score = sum(1 for word in words if word in haystack)
            if score:
                scored.append((score, tool))
        scored.sort(key=lambda item: (-item[0], item[1].schema_tokens_estimate))
        return [tool for _score, tool in scored[:limit]]

    def prompt_surface_reduction(self, query: str) -> dict[str, int]:
        total = sum(t.schema_tokens_estimate for t in self.catalog.list())
        selected = sum(t.schema_tokens_estimate for t in self.search(query))
        return {
            "all_tools_schema_tokens": total,
            "selected_schema_tokens": selected,
            "saved_tokens_estimate": max(0, total - selected),
        }


__all__ = ["ToolCatalogSearch"]
