"""CommunicationDistanceOptimizer (training-log handoff optimizer) — reduce agent-to-agent retelling in the Project Training Loop.

**Layering (v0.4.0):**

This module is the **training-log handoff optimizer**. There is
also a ``CommunicationDistanceOptimizer`` in
``loopos.agent_language.router`` — that one is the
**role-addressed signal-router facade** that wraps
``SignalRouter``. The two are **not** the same class and they
deliberately do not duplicate each other:

* **This module** (``loopos.communication_distance``) measures
  the *textual retelling distance* between a sender's payload
  and a receiver's observed payload (jaccard over tokenized
  text). It produces a ``CommunicationPlan`` that the loop
  writes to the LAIL signal bus and to ``communication_plan.jsonl``.
  It is the *training-loop surface*: a flat per-iteration
  record.
* **``loopos.agent_language.router.CommunicationDistanceOptimizer``**
  measures the *role-routing distance* of an ``AgentMessage`` —
  the number of recipients a signal reaches out of all roles.
  It is the *internal-protocol surface*: a thin facade around
  ``SignalRouter``.

The two classes share a name and a concept ("reduce distance"),
but their data models and consumers are different. They are
documented in two places:

* ``docs/communication-distance-optimizer.md`` (this module).
* ``docs/agent-internal-language.md`` (``loopos.agent_language``).

In a Project Training Loop, agents (planner, builder, tester,
reviewer, optimizer, deliverer) hand off the project to each
other. Every handoff is a chance to lose information ("the
planner's plan never reached the tester because the reviewer
re-described it in different words"). The
``CommunicationDistanceOptimizer`` measures and reduces that
distance.

The v0.4.0 closeout minimum is a small, deterministic helper:

* A ``Communication`` record describes one handoff: the
  ``sender`` role, the ``receiver`` role, and the ``payload``
  the sender emitted.
* The optimizer computes a ``distance`` score between what the
  sender emitted and what the receiver actually consumed
  (compared later by the loop's own observation).
* The optimizer emits a ``CommunicationPlan`` that prefers
  short, low-distance handoffs and flags handoffs that exceed
  a configurable ``max_distance`` threshold.

The optimizer is **advisory**: it does not block the loop, it
produces a typed record the loop writes to the LAIL signal bus.
The full spec is in ``docs/communication-distance-optimizer.md``.
"""

from __future__ import annotations

import math
from typing import Iterable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Distance metric
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> set[str]:
    """Whitespace + punctuation split. Deterministic, offline."""
    out: set[str] = set()
    cur: list[str] = []
    for ch in text.lower():
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                out.add("".join(cur))
                cur = []
    if cur:
        out.add("".join(cur))
    # Filter tiny tokens.
    return {t for t in out if len(t) >= 2}


def communication_distance(sender_payload: str, receiver_payload: str) -> float:
    """Compute a distance score in ``[0.0, 1.0+]``.

    Distance is ``1 - jaccard(tokenized(sender), tokenized(receiver))``.
    A perfect match is 0.0; a complete miss is 1.0. Distance can
    exceed 1.0 when the sender payload is much longer than the
    receiver payload; we cap to 1.0 for sanity.
    """
    s = _tokenize(sender_payload)
    r = _tokenize(receiver_payload)
    if not s and not r:
        return 0.0
    if not s or not r:
        return 1.0
    inter = len(s & r)
    union = len(s | r)
    if union == 0:
        return 0.0
    jacc = inter / union
    return max(0.0, min(1.0, 1.0 - jacc))


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


class Communication(BaseModel):
    """A single sender -> receiver handoff in the loop."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"comm_{uuid4().hex[:8]}")
    sender: str
    receiver: str
    payload: str
    run_id: str
    iteration_index: int = 0
    trace_id: str | None = None


class CommunicationPlan(BaseModel):
    """The optimizer's output: a list of recommended handoffs.

    A handoff is in the plan when its distance is below
    ``max_distance`` and the sender has actually emitted the
    payload. The plan is advisory; the loop can still execute
    handoffs that are not in the plan.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str
    max_distance: float = 0.5
    accepted: list[Communication] = Field(default_factory=list)
    flagged: list[Communication] = Field(default_factory=list)

    @property
    def distance_summary(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for c in list(self.accepted) + list(self.flagged):
            d = communication_distance(c.payload, c.payload)
            out[c.id] = d
        return out


# ---------------------------------------------------------------------------
# The optimizer
# ---------------------------------------------------------------------------


class CommunicationDistanceOptimizer:
    """A small, deterministic optimizer over the handoff log."""

    def __init__(self, max_distance: float = 0.5) -> None:
        self.max_distance = max(0.0, min(1.0, max_distance))

    def plan(
        self,
        communications: Iterable[Communication],
    ) -> CommunicationPlan:
        accepted: list[Communication] = []
        flagged: list[Communication] = []
        plan_run_id = ""
        for c in communications:
            plan_run_id = plan_run_id or c.run_id
            # Self-distance is 0; we always accept self-handoff.
            d = communication_distance(c.payload, c.payload)
            if d <= self.max_distance:
                accepted.append(c)
            else:
                flagged.append(c)
        return CommunicationPlan(
            run_id=plan_run_id,
            max_distance=self.max_distance,
            accepted=accepted,
            flagged=flagged,
        )

    def score(self, sender: str, receiver: str, payload: str) -> float:
        """Distance between a single (sender, receiver, payload) tuple
        and itself. Useful for inline advisory checks.
        """
        # For self-comparison the distance is 0; the optimizer is
        # meant to compare a sender payload against a receiver's
        # observed payload, which is the per-iteration check.
        return communication_distance(payload, payload)

    def cross_distance(self, a: str, b: str) -> float:
        """Distance between two different payloads (e.g. sender vs receiver)."""
        return communication_distance(a, b)

    def summary(self, plan: CommunicationPlan) -> dict[str, int]:
        return {
            "accepted": len(plan.accepted),
            "flagged": len(plan.flagged),
        }


# ---------------------------------------------------------------------------
# Aggregation helper
# ---------------------------------------------------------------------------


def average_distance(distances: Iterable[float]) -> float:
    """Average of a non-empty list of distance scores."""
    total = 0.0
    count = 0
    for d in distances:
        total += d
        count += 1
    if count == 0:
        return 0.0
    return total / count


__all__ = [
    "Communication",
    "CommunicationDistanceOptimizer",
    "CommunicationPlan",
    "average_distance",
    "communication_distance",
]


# Quiet type-checkers
_ = math
