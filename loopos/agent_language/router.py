"""Signal routing and communication-distance accounting for LAIL.

**Layering (v0.4.0):**

This module is the **role-addressed signal-router facade**. There
is also a ``CommunicationDistanceOptimizer`` in
``loopos.communication_distance`` — that one is the
**training-log handoff optimizer** that measures textual
retelling distance. The two are **not** the same class and they
deliberately do not duplicate each other:

* **This module** (``loopos.agent_language.router``) measures the
  *role-routing distance* of an ``AgentMessage`` — the number of
  recipients a signal reaches out of all roles. It is the
  *internal-protocol surface*: a thin facade around
  ``SignalRouter``.
* **``loopos.communication_distance.CommunicationDistanceOptimizer``**
  measures the *textual retelling distance* between a sender's
  payload and a receiver's observed payload (jaccard over
  tokenized text). It is the *training-loop surface*: a flat
  per-iteration record.

The two classes share a name and a concept ("reduce distance"),
but their data models and consumers are different. They are
documented in two places:

* ``docs/agent-internal-language.md`` (this module).
* ``docs/communication-distance-optimizer.md``
  (``loopos.communication_distance``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from loopos.agent_language.message import AgentMessage
from loopos.agent_language.roles import ALL_AGENT_ROLES, AgentRole
from loopos.agent_language.signals import DEFAULT_SUBSCRIPTIONS, RoleSubscription, SignalType


class CommunicationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    communication_distance: int = 0
    broadcast_count: int = 0
    recipient_count: int = 0
    token_cost_estimate: int = 0
    redundant_context_avoided: int = 0


class RoutedSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: AgentMessage
    recipients: list[AgentRole] = Field(default_factory=list)
    metrics: CommunicationMetrics


class SignalRouter:
    """Route LAIL messages directly to roles that need them."""

    def __init__(
        self,
        subscriptions: list[RoleSubscription] | tuple[RoleSubscription, ...] | None = None,
    ) -> None:
        subs = subscriptions or DEFAULT_SUBSCRIPTIONS
        self._subscriptions = {sub.signal_type: list(sub.recipients) for sub in subs}

    def route(self, message: AgentMessage) -> RoutedSignal:
        recipients = self._recipients_for(message)
        all_count = len(ALL_AGENT_ROLES)
        broadcast_count = 1 if len(recipients) >= all_count else 0
        metrics = CommunicationMetrics(
            communication_distance=1 if recipients else 0,
            broadcast_count=broadcast_count,
            recipient_count=len(recipients),
            token_cost_estimate=message.token_cost or message.token_estimate(),
            redundant_context_avoided=max(0, all_count - len(recipients)),
        )
        return RoutedSignal(message=message, recipients=recipients, metrics=metrics)

    def _recipients_for(self, message: AgentMessage) -> list[AgentRole]:
        if message.signal_type == SignalType.MEMORY_CONTEXT_COMPILED:
            target = message.payload.get("target_role")
            if target:
                return [AgentRole(str(target))]
        configured = self._subscriptions.get(message.signal_type)
        if configured is not None:
            return list(dict.fromkeys(configured))
        return list(dict.fromkeys(message.recipients()))


class CommunicationDistanceOptimizer:
    """Thin facade around ``SignalRouter`` for product-facing naming.

    This is the **role-addressed signal-router** variant. It is
    *not* the same class as
    ``loopos.communication_distance.CommunicationDistanceOptimizer``
    (the training-log handoff optimizer); see the module
    docstring above for the explicit layering.
    """

    def __init__(self, router: SignalRouter | None = None) -> None:
        self.router = router or SignalRouter()

    def optimize(self, message: AgentMessage) -> RoutedSignal:
        return self.router.route(message)


class ContextRecipientSelector:
    """Pick the role that receives a compiled context packet."""

    def select(self, target_role: AgentRole, available_roles: list[AgentRole]) -> list[AgentRole]:
        if target_role in available_roles:
            return [target_role]
        return []


__all__ = [
    "CommunicationDistanceOptimizer",
    "CommunicationMetrics",
    "ContextRecipientSelector",
    "RoutedSignal",
    "SignalRouter",
]
