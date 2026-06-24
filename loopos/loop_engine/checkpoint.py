"""Checkpoint storage for LoopEngine runs."""

from __future__ import annotations

from loopos.loop_engine.models import ProjectCheckpoint


class InMemoryCheckpointStore:
    """Small deterministic checkpoint store used by v0.4.0 tests and demos."""

    def __init__(self) -> None:
        self._items: list[ProjectCheckpoint] = []

    def save(self, checkpoint: ProjectCheckpoint) -> ProjectCheckpoint:
        self._items.append(checkpoint)
        return checkpoint

    def list(self, goal_id: str | None = None) -> list[ProjectCheckpoint]:
        if goal_id is None:
            return list(self._items)
        return [item for item in self._items if item.goal_id == goal_id]


__all__ = ["InMemoryCheckpointStore"]
