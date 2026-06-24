"""LAIL (structured protocol package): the internal v0.4.0 agent language.

**Layering (v0.4.0):**

There are two LAIL surfaces in the v0.4.0 codebase. They share a
name and a concept but serve different purposes:

* ``loopos.lail`` -- the **compact public/CLI facade**. A flat
  Pydantic record with ``kind`` / ``run_id`` / ``iteration_index``
  / ``trace_id`` plus an in-process ``LailSignalBus``. This is the
  surface the CLI talks to (``loopos lail encode``) and the surface
  the loop engine drains to ``lail_signals.jsonl``. It is the
  *per-iteration training log*, not an inter-agent protocol.
* ``loopos.agent_language`` (this package) -- the **structured
  internal protocol package**. A typed ``AgentMessage`` with
  ``from_role`` / ``to_role`` / ``actionability`` / ``authority_delta``
  plus a ``SignalRouter`` and a ``CommunicationDistanceOptimizer``
  that measure the *retelling distance* of role-addressed signals.
  This is the surface the *kernel* uses for inter-agent
  communication; it is gated by ``authority_delta="none"`` and
  refuses to embed executable payloads.

**Why two?** The two surfaces answer different questions:

* The CLI / training log needs a *flat* record with a
  ``(run_id, iteration_index, trace_id)`` triple so an auditor
  can replay a training run in a different process.
* The internal protocol needs a *role-addressed* record with
  ``actionability`` and ``authority_delta`` so a non-executing
  LAIL signal can be routed without leaking side-effect intent.

The package does **not** duplicate the ``loopos.lail`` CLI bus;
``loopos.lail`` is a *facade*, not a competing source of truth.
The bus is drained to ``lail_signals.jsonl``; the structured
``AgentMessage`` is consumed by ``SignalRouter`` /
``CommunicationDistanceOptimizer`` and never duplicated to the
JSONL training log.

See ``docs/agent-internal-language.md`` for the full spec.
"""

from __future__ import annotations

from loopos.agent_language.codec import (
    compact_to_json,
    compact_to_message,
    json_to_compact,
    message_to_compact,
)
from loopos.agent_language.mcp_bridge import LailMcpBridge
from loopos.agent_language.message import Actionability, AgentMessage
from loopos.agent_language.protocol import make_signal
from loopos.agent_language.roles import ALL_AGENT_ROLES, AgentRole
from loopos.agent_language.router import (
    CommunicationDistanceOptimizer,
    CommunicationMetrics,
    ContextRecipientSelector,
    RoutedSignal,
    SignalRouter,
)
from loopos.agent_language.signals import DEFAULT_SUBSCRIPTIONS, RoleSubscription, SignalType
from loopos.agent_language.trace import AgentMessageTrace
from loopos.agent_language.translator import (
    message_to_evaluation_signal,
    review_finding_to_message,
    test_result_to_message,
)

__all__ = [
    "ALL_AGENT_ROLES",
    "Actionability",
    "AgentMessage",
    "AgentMessageTrace",
    "AgentRole",
    "CommunicationDistanceOptimizer",
    "CommunicationMetrics",
    "ContextRecipientSelector",
    "DEFAULT_SUBSCRIPTIONS",
    "LailMcpBridge",
    "RoleSubscription",
    "RoutedSignal",
    "SignalRouter",
    "SignalType",
    "compact_to_json",
    "compact_to_message",
    "json_to_compact",
    "make_signal",
    "message_to_compact",
    "message_to_evaluation_signal",
    "review_finding_to_message",
    "test_result_to_message",
]
