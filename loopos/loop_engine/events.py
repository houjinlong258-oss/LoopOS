"""Loop-level events for the v0.4.0 loop engine.

Events are typed records emitted by ``LoopEngine`` as it drives an
iteration. They are not part of the public Pydantic surface of the
loop state itself; they are the trace layer's input.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class LoopEventKind(str, Enum):
    """The kinds of loop events v0.4.0 emits."""

    LOOP_STARTED = "loop.started"
    ITERATION_STARTED = "iteration.started"
    PLAN_EMITTED = "plan.emitted"
    BUILD_COMPLETED = "build.completed"
    TEST_COMPLETED = "test.completed"
    REVIEW_COMPLETED = "review.completed"
    REPAIR_PLANNED = "repair.planned"
    OPTIMIZATION_PLANNED = "optimization.planned"
    ITERATION_COMPLETED = "iteration.completed"
    CONVERGENCE_DECIDED = "convergence.decided"
    DELIVERY_EMITTED = "delivery.emitted"
    LOOP_HALTED = "loop.halted"
    LOOP_DELIVERED = "loop.delivered"


class LoopEvent(BaseModel):
    """A single loop event."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"loop_evt_{uuid4().hex[:8]}")
    kind: LoopEventKind
    iteration_index: int = 0
    trace_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


__all__ = ["LoopEvent", "LoopEventKind"]
