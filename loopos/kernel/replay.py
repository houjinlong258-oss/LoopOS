"""Side-effect-free trace replay."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from loopos.kernel.models import RunRecord
from loopos.kernel.trace import TraceEvent, TraceStore


class ReplayResult(BaseModel):
    run_id: str
    step: int
    events: list[TraceEvent] = Field(default_factory=list)
    reconstructed_state: dict[str, Any] = Field(default_factory=dict)
    differences: list[str] = Field(default_factory=list)


class ReplayEngine:
    def __init__(self, trace_store: TraceStore) -> None:
        self.trace_store = trace_store

    def replay(self, run_id: str, step: int, *, durable: RunRecord | None = None) -> ReplayResult:
        events = self.trace_store.list(run_id)
        selected = [event for event in events if event.step <= step]
        state: dict[str, Any] = {}
        for event in selected:
            if event.kind == "transition":
                after = event.payload.get("after")
                if isinstance(after, dict):
                    state = dict(after)
            elif event.kind == "run" and isinstance(event.payload.get("state"), dict):
                state = dict(event.payload["state"])
        differences: list[str] = []
        if durable is not None and state:
            for field in ("status", "phase", "step"):
                replayed = state.get(field)
                current = getattr(durable, field)
                if replayed is not None and replayed != current and step >= durable.step:
                    differences.append(f"{field}: replay={replayed!r} durable={current!r}")
        return ReplayResult(
            run_id=run_id,
            step=step,
            events=[event for event in selected if event.step == step],
            reconstructed_state=state,
            differences=differences,
        )

