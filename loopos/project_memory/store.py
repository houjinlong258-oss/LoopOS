"""Stores for Project Memory OS."""

from __future__ import annotations

from loopos.project_memory.models import ProjectMemoryItem, ProjectMemoryKind


class InMemoryProjectMemoryStore:
    """Deterministic in-memory store for project-training signals."""

    def __init__(self) -> None:
        self._items: list[ProjectMemoryItem] = []

    def add(self, item: ProjectMemoryItem) -> ProjectMemoryItem:
        self._items.append(item)
        return item

    def list(
        self,
        *,
        type: ProjectMemoryKind | None = None,
        tags: list[str] | None = None,
    ) -> list[ProjectMemoryItem]:
        items = [item for item in self._items if item.status == "active"]
        if type is not None:
            items = [item for item in items if item.type == type]
        if tags:
            tag_set = {tag.lower() for tag in tags}
            items = [
                item
                for item in items
                if tag_set.intersection({tag.lower() for tag in item.tags})
            ]
        return list(items)


__all__ = ["InMemoryProjectMemoryStore"]
