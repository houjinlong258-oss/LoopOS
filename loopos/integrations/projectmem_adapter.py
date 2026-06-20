"""projectmem-inspired adapter stub."""

from __future__ import annotations

import importlib.util
from typing import Any

from loopos.memory.event_log import Event


class ProjectMemAdapter:
    """Optional adapter for event-sourced memory exchange."""

    def is_available(self) -> bool:
        return importlib.util.find_spec("projectmem") is not None

    def to_project_event(self, event: Event) -> dict[str, Any]:
        return {
            "id": event.id,
            "run_id": event.run_id,
            "step": event.step_index,
            "kind": event.type,
            "payload": event.payload,
            "created_at": event.created_at,
        }
