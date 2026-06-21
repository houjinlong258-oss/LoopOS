"""Kernel lifecycle management — boot, shutdown, and phase tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


LifecyclePhase = Literal[
    "uninitialized",
    "booting",
    "ready",
    "running",
    "shutting_down",
    "terminated",
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LifecycleEvent(BaseModel):
    """Recorded lifecycle state change."""
    phase: LifecyclePhase
    reason: str = ""
    timestamp: datetime = Field(default_factory=_utc_now)


class KernelLifecycle:
    """Track kernel-level lifecycle (not per-run, but the runtime itself)."""

    def __init__(self) -> None:
        self._phase: LifecyclePhase = "uninitialized"
        self._history: list[LifecycleEvent] = []

    @property
    def phase(self) -> LifecyclePhase:
        return self._phase

    @property
    def history(self) -> list[LifecycleEvent]:
        return list(self._history)

    _ALLOWED: dict[LifecyclePhase, set[LifecyclePhase]] = {
        "uninitialized": {"booting"},
        "booting": {"ready", "terminated"},
        "ready": {"running", "shutting_down"},
        "running": {"ready", "shutting_down"},
        "shutting_down": {"terminated"},
        "terminated": set(),
    }

    def transition(self, to: LifecyclePhase, *, reason: str = "") -> None:
        if to not in self._ALLOWED[self._phase]:
            raise ValueError(f"invalid lifecycle transition: {self._phase} -> {to}")
        self._phase = to
        self._history.append(LifecycleEvent(phase=to, reason=reason))

    @property
    def is_active(self) -> bool:
        return self._phase in {"ready", "running"}
