"""Append-only JSONL event log."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from loopos.core.state import utc_now


class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    step_index: int
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: object = Field(default_factory=utc_now)


class EventLog:
    """Small JSONL-backed event store."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        event_type: str,
        run_id: str,
        step_index: int,
        payload: dict[str, Any] | None = None,
    ) -> Event:
        event = Event(
            run_id=run_id,
            step_index=step_index,
            type=event_type,
            payload=payload or {},
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")
        return event

    def list(self, run_id: str | None = None) -> list[Event]:
        if not self.path.exists():
            return []
        events: list[Event] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                data = json.loads(line)
                event = Event.model_validate(data)
                if run_id is None or event.run_id == run_id:
                    events.append(event)
        return events
