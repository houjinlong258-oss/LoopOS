"""Agent Bus — translation layer between external adapters and LoopOS kernel.

The Agent Bus is the **only** path through which an external agent
kernel can influence LoopOS state. It receives
:class:`~loopos.adapters.events.AgentKernelEvent` objects from an
adapter, translates them into one or more
:class:`~loopos.aci.models.AgentCommand` objects, and dispatches them
through the existing ACI runner.

Design invariants
-----------------

* The Agent Bus never executes shell, file writes, or provider calls
  directly; it always emits ``AgentCommand`` objects.
* The Agent Bus never mutates the adapter session state; it only
  observes events and forwards commands.
* The Agent Bus persists adapter events onto the LoopOS Trace so
  replay sees the same event stream.
"""

from __future__ import annotations

from loopos.agent_bus.bus import AgentBus, AgentBusReceipt
from loopos.agent_bus.events import AgentBusEvent, AgentBusEventKind
from loopos.agent_bus.session import AgentBusSession
from loopos.agent_bus.translation import (
    AgentEventTranslator,
    default_translator,
    translate_event,
)
from loopos.agent_bus.command_bridge import AgentCommandBridge

__all__ = [
    "AgentBus",
    "AgentBusReceipt",
    "AgentBusEvent",
    "AgentBusEventKind",
    "AgentBusSession",
    "AgentEventTranslator",
    "default_translator",
    "translate_event",
    "AgentCommandBridge",
]
