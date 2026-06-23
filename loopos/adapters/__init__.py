"""LoopOS v0.3 Agent Kernel Adapter Layer.

External agent kernels (Hermes, Scream Code, OpenHands, clean-room
Codex/Claude Code, enterprise agents) enter LoopOS exclusively through
an :class:`~loopos.adapters.base.AgentKernelAdapter`. Adapters never
execute shell, write files, or call providers directly: they emit
:class:`~loopos.adapters.events.AgentKernelEvent` objects that the
Agent Bus translates into governed ACI commands.

Design invariants
------------------

* An adapter declares its capabilities and authority via a
  :class:`~loopos.adapters.manifest.AgentKernelManifest`.
* ``requires_aci`` / ``requires_policy`` / ``requires_trace`` are
  always True for external adapters; the registry refuses to register
  an adapter that claims direct shell or direct file write authority.
* The :class:`~loopos.adapters.mock.MockAdapter` is the deterministic
  reference adapter used by the test-suite and the Workbench dry-run.
"""

from __future__ import annotations

from loopos.adapters.base import (
    AgentKernelAdapter,
    AgentKernelCapabilities,
    AgentKernelSession,
    AgentKernelSnapshot,
)
from loopos.adapters.events import AgentKernelEvent, AgentKernelEventKind
from loopos.adapters.manifest import AgentKernelAuthority, AgentKernelManifest
from loopos.adapters.registry import AdapterRegistry, AdapterSummary
from loopos.adapters.mock import MockAdapter

__all__ = [
    "AgentKernelAdapter",
    "AgentKernelCapabilities",
    "AgentKernelSession",
    "AgentKernelSnapshot",
    "AgentKernelEvent",
    "AgentKernelEventKind",
    "AgentKernelAuthority",
    "AgentKernelManifest",
    "AdapterRegistry",
    "AdapterSummary",
    "MockAdapter",
]
