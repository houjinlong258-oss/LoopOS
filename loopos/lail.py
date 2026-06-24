"""LAIL (compact public/CLI facade) — the v0.4.0 closeout signal bus.

**Layering (v0.4.0):**

There are two LAIL surfaces in the v0.4.0 codebase. They share a
name and a concept but serve different purposes:

* ``loopos.lail`` (this module) -- the **compact public/CLI
  facade**. A flat Pydantic record with ``kind`` / ``run_id`` /
  ``iteration_index`` / ``trace_id`` plus an in-process
  ``LailSignalBus``. This is the surface the CLI talks to
  (``loopos lail encode``) and the surface the loop engine drains
  to ``lail_signals.jsonl``. It is the *per-iteration training
  log*, not an inter-agent protocol.
* ``loopos.agent_language`` -- the **structured internal protocol
  package**. A typed ``AgentMessage`` with ``from_role`` /
  ``to_role`` / ``actionability`` / ``authority_delta`` plus a
  ``SignalRouter`` and a ``CommunicationDistanceOptimizer`` that
  measure the *retelling distance* of role-addressed signals. This
  is the surface the *kernel* uses for inter-agent communication;
  it is gated by ``authority_delta="none"`` and refuses to embed
  executable payloads.

**Why two?** The two surfaces answer different questions:

* The CLI / training log needs a *flat* record with a
  ``(run_id, iteration_index, trace_id)`` triple so an auditor
  can replay a training run in a different process.
* The internal protocol needs a *role-addressed* record with
  ``actionability`` and ``authority_delta`` so a non-executing
  LAIL signal can be routed without leaking side-effect intent.

**This module is a facade, not a competing source of truth.** The
``LailSignalBus`` is the in-process buffer the loop engine talks
to during a run; the ``loop_run_command`` drains the bus to
``lail_signals.jsonl``. The bus is **not** the structured
inter-agent protocol — that lives in ``loopos.agent_language``
and is consumed by ``SignalRouter`` /
``CommunicationDistanceOptimizer`` without being duplicated to
the JSONL training log.

LAIL is the v0.4.0 agent-internal language. It is **not** the v0.1
``loopos.ail`` package (which encodes the lower-level AIL
instructions). LAIL is the higher-bandwidth Project Training Loop
internal language: every signal in the loop is a typed LAIL record
with a stable ``run_id`` / ``iteration_index`` / ``trace_id`` triple.

LAIL reduces agent-to-agent communication waste in two ways:

1. **Typed signals.** Every signal has a Pydantic v2 type. A model
   can construct and consume signals without freeform text.
2. **Traceable payload.** Every signal carries the run / iteration /
   trace triple. Consumers can join signals across processes by
   ``trace_id``.

This module is the v0.4.0 minimum: a typed record, a compact
``LailSignalBus`` that stores / retrieves / serialises signals,
and a CLI-side ``encode`` helper that converts a dict into a
LAIL record.

The full LAIL spec is in ``docs/agent-internal-language.md``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Signal kinds — every kind is a typed record in the bus
# ---------------------------------------------------------------------------

LailKind = Literal[
    "iteration_started",
    "plan_emitted",
    "build_completed",
    "test_completed",
    "review_completed",
    "repair_planned",
    "optimization_planned",
    "evaluation_signal",
    "convergence_decided",
    "delivery_emitted",
    "checkpoint_saved",
    "memory_packet_compiled",
]


# ---------------------------------------------------------------------------
# The signal record
# ---------------------------------------------------------------------------


class LailSignal(BaseModel):
    """A single LAIL signal in the Project Training Loop.

    Every signal carries:

    * a ``kind`` (the typed channel),
    * a ``run_id`` / ``iteration_index`` / ``trace_id`` triple
      (the join key across processes),
    * a ``payload`` (the structured content, freeform-dict but
      typed at the bus level).
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"lail_{uuid4().hex[:8]}")
    kind: LailKind
    run_id: str
    iteration_index: int = 0
    trace_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def short(self) -> str:
        """A compact one-line summary used in CLI output."""
        return (
            f"[{self.kind}] run={self.run_id} iter={self.iteration_index} "
            f"trace={self.trace_id or '-'}"
        )


# ---------------------------------------------------------------------------
# The in-process bus
# ---------------------------------------------------------------------------


class LailSignalBus:
    """An in-process bus that buffers ``LailSignal`` records.

    The bus is **not** the persistence layer. The
    ``loopos.checkpoint_store`` writes signals to
    ``lail_signals.jsonl``. The bus is what the loop engine talks
    to during a run; the run command then drains the bus to disk.
    """

    def __init__(self) -> None:
        self._signals: list[LailSignal] = []

    def emit(self, signal: LailSignal) -> LailSignal:
        self._signals.append(signal)
        return signal

    def make(
        self,
        kind: LailKind,
        run_id: str,
        iteration_index: int = 0,
        trace_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> LailSignal:
        sig = LailSignal(
            kind=kind,
            run_id=run_id,
            iteration_index=iteration_index,
            trace_id=trace_id,
            payload=payload or {},
        )
        return self.emit(sig)

    def all(self) -> list[LailSignal]:
        return list(self._signals)

    def by_kind(self, kind: LailKind) -> list[LailSignal]:
        return [s for s in self._signals if s.kind == kind]

    def by_iteration(self, iteration_index: int) -> list[LailSignal]:
        return [s for s in self._signals if s.iteration_index == iteration_index]

    def drain(self) -> list[LailSignal]:
        """Return all signals and clear the bus."""
        out = list(self._signals)
        self._signals.clear()
        return out

    def kind_summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for s in self._signals:
            out[s.kind] = out.get(s.kind, 0) + 1
        return out


# ---------------------------------------------------------------------------
# The encode helper used by the CLI
# ---------------------------------------------------------------------------


def encode_signal(
    kind: LailKind,
    run_id: str,
    iteration_index: int = 0,
    trace_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> LailSignal:
    """CLI-facing helper that constructs a ``LailSignal``.

    The ``loopos lail encode`` command is a thin wrapper around this
    function. The signal is returned (and may be appended to a bus
    or written to disk by the caller).
    """
    return LailSignal(
        kind=kind,
        run_id=run_id,
        iteration_index=iteration_index,
        trace_id=trace_id,
        payload=payload or {},
    )


__all__ = [
    "LailKind",
    "LailSignal",
    "LailSignalBus",
    "encode_signal",
]
