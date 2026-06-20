"""Append-only kernel trace with legacy event compatibility."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

TraceKind = Literal[
    "run",
    "instruction",
    "policy",
    "syscall",
    "observation",
    "evaluation",
    "transition",
    "memory",
    "skill",
    "signal",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TraceEvent(BaseModel):
    """Versioned trace event that remains readable by legacy EventLog."""

    model_config = ConfigDict(extra="ignore")

    schema_version: int = 2
    id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    step: int = Field(default=0, ge=0)
    step_index: int | None = None
    kind: TraceKind | None = None
    type: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    instruction_id: str | None = None
    syscall_id: str | None = None
    policy_decision_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def synchronize_legacy_fields(self) -> "TraceEvent":
        if self.step_index is None:
            self.step_index = self.step
        else:
            self.step = self.step_index
        if self.kind is None:
            self.kind = _legacy_kind(self.type or "run")
        if self.type is None:
            self.type = self.kind
        return self


class TraceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        kind: TraceKind,
        run_id: str,
        step: int,
        payload: dict[str, Any] | None = None,
        *,
        event_type: str | None = None,
        instruction_id: str | None = None,
        syscall_id: str | None = None,
        policy_decision_id: str | None = None,
    ) -> TraceEvent:
        event = TraceEvent(
            run_id=run_id,
            step=step,
            kind=kind,
            type=event_type or kind,
            payload=payload or {},
            instruction_id=instruction_id,
            syscall_id=syscall_id,
            policy_decision_id=policy_decision_id,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")
        return event

    def list(self, run_id: str | None = None, *, step: int | None = None) -> list[TraceEvent]:
        if not self.path.exists():
            return []
        events: list[TraceEvent] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                payload = json.loads(line)
                event = TraceEvent.model_validate(payload)
                if run_id is not None and event.run_id != run_id:
                    continue
                if step is not None and event.step != step:
                    continue
                events.append(event)
        return events


def _legacy_kind(event_type: str) -> TraceKind:
    value = event_type.lower()
    for kind in (
        "instruction",
        "policy",
        "syscall",
        "observation",
        "evaluation",
        "transition",
        "memory",
        "skill",
        "signal",
    ):
        if kind in value:
            return kind  # type: ignore[return-value]
    return "run"

